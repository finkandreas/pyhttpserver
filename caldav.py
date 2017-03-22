from vdirsyncer.storage.dav import CalDAVStorage
from vdirsyncer.utils.vobject import Item
import requests
import common
import vobject
from xdg import BaseDirectory
from pydal import DAL, Field
from dateutil.parser import parse
from dateutil.rrule import rrule,YEARLY
from datetime import datetime
from eventlet import tpool
from misc import *
import re

def _do_sync_background():
  try:
    c = CalDav()
    c.sync()
  except Exception as e:
    print("Exception while syncing CalDav. Exception: ", e)
    return 30
  print("{}: Successfully synced CalDav in the background".format(datetime.now()))
  return 3600

def sync_background(socketio):
  socketio.sleep(30)
  sleep = tpool.execute(_do_sync_background)
  socketio.sleep(sleep)
  socketio.start_background_task(sync_background, socketio)


class CalDav(object):
  def __init__(self):
    self.db = DAL('sqlite://caldav.db', folder=BaseDirectory.save_data_path('pyhttpserver'))
    self.db.define_table('collections', Field('url', type='string', required=True, unique=True),
                                        Field('displayname', type='string'),
                                        Field('subscribed', type='boolean', default=True))
    self.db.define_table('colitems', Field('href', type='string', required=True),
                                  Field('etag', type='string'),
                                  Field('collection', type='reference collections'),
                                  Field('content', type='blob'),
                                  Field('local_status', type='integer', default=0))
    self.davStorages = {}

  def __del__(self):
    self.db.close()


  def sync_collections(self):
    deletedCollections = set([ x.url for x in self.db(self.db.collections.url != None).select() ])
    cfg = common.get_davconfig()
    for serverCfg in cfg.get('servers', []):
      config = dict(username=serverCfg['username'], password=serverCfg['password'], url=serverCfg['url'])
      config['url'] = requests.get(config['url']).url
      storage = CalDAVStorage(**config)

      # Fetch all locally available collections, then fetch the collections from the server side and add them locally if they are not available yet
      # Afterwards delete all collections from the database that were not available on the server side anymore
      for s in storage.discover(**config):
        subStorage = CalDAVStorage(**s)
        displayname = subStorage.get_meta('displayname')
        deletedCollections.discard(s['url'])
        self.db.collections.update_or_insert(self.db.collections.url==s['url'], url=s['url'], displayname=displayname)
        self.davStorages[s['url']] = subStorage
    for deletedCollection in deletedCollections:
      print("Collections with url={} was deleted on the server side".format(deletedCollection))
      self.db(self.db.collections.url == deletedCollection).delete()
    self.db.commit()


  def sync(self, socketio=None):
    if socketio: socketio.sleep(3)
    self.sync_collections()
    # sync only subsribed collections...
    for collectionRow in self.db(self.db.collections.subscribed == True).select():
      davUrl = collectionRow.url
      davStorage = self.davStorages[davUrl]
      id = collectionRow.id

      # Sync local changes to the server
      self.sync_local_changes(davUrl)

      # get changes from server
      updated = set()
      new = set()
      deleted = set([ x['href']  for x in self.db(self.db.colitems.collection == id).select() ])
      for href,etag in davStorage.list():
        if href in deleted:
          deleted.remove(href)
          if self.db((self.db.colitems.collection == id) & (self.db.colitems.href == href)).select()[0].etag != etag:
            updated.add(href)
        else:
          new.add(href)

      if len(new)>0:     print("New objects at server: ", new)
      if len(updated)>0: print("Updated objects at server: ", updated)
      if len(deleted)>0: print("Deleted objects at server: ", deleted)

      # Delete server deleted items also from local database
      for deletedItem in deleted:
        print("Deleted object with href={} on the server side".format(deletedItem))
        self.db(self.db.colitems.href == deletedItem).delete()
      # Fetch server created/modified items and update in local db
      for href, item, etag in davStorage.get_multi(updated|new):
        self.db.colitems.update_or_insert((self.db.colitems.collection==id) & (self.db.colitems.href==href), href=href, etag=etag, collection=id, content=item.raw, local_status=0)

    for collectionRow in self.db(self.db.collections.subscribed == False).select():
      self.db(self.db.colitems.collection==collectionRow.id).delete();

    self.db.commit()

  def get_collection_id(self, url):
    return self.db(self.db.collections.url == url).select()[0].id


  def sync_local_changes(self, davStorageUrl):
    davStorage = self.davStorages[davStorageUrl]
    collectionId = self.get_collection_id(davStorageUrl)
    for deletedItem in self.db((self.db.colitems.local_status == 2) & (self.db.colitems.collection == collectionId)).select():
      print("Deleting locally removed item with etag={} from server".format(deletedItem.etag))
      davStorage.delete(deletedItem.href, deletedItem.etag)
      deletedItem.delete_record()
    for modifiedItem in self.db((self.db.colitems.local_status == 1) & (self.db.colitems.collection == collectionId)).select():
      print("Updating locally modified item with etag={} at server".format(modifiedItem.etag))
      newEtag = davStorage.update(modifiedItem.href, Item(modifiedItem.content), modifiedItem.etag)
      modifiedItem.update_record(etag=newEtag, local_status=0)
    for newItem in self.db((self.db.colitems.local_status == 3) & (self.db.colitems.collection == collectionId)).select():
      print("Adding a new ical to the server")
      href, etag = davStorage.upload(Item(newItem.content))
      newItem.update_record(etag=etag, href=href, local_status=0)
    self.db.commit()

  def get_subscribed_collections(self):
    return [ {'url': x.url, 'id': x.id, 'name': x.displayname} for x in self.db(self.db.collections.subscribed == True).select() ]

  def get(self, id):
    return vcard21_to_vcard30(vobject.readOne(self.db(self.db.colitems.id == id).select()[0].content))

  def get_structured(self, id):
    vcard = self.get(id)
    ret = {}
    vcardAsDict = vcard.contents
    if 'fn' not in vcardAsDict:
      print("vCard with id={} does not have the field FN set".format(id))
    else:
      if len(vcardAsDict['fn']) > 1: print("vCard with id={} has more than one FN field. Ignoring all but the first".format(id))
      ret['fn'] = vcardAsDict['fn'][0].value
    if 'n' not in vcardAsDict:
      print("vCard with id={} does not have the field N set".format(id))
      ret['fn'] = dict(given="",family="",prefix="",suffix="",additional="")
    else:
      if len(vcardAsDict['n']) > 1: print("vCard with id={} has more than one N field. Ignoring all but the first".format(id))
      ret['n'] = vcardAsDict['n'][0].value.__dict__
    if len(vcardAsDict.get('bday', [])) > 1: print("vCard with id={} has more than one BDAY field. Ignoring all but the first".format(id))
    ret['bday'] = ""
    if 'bday' in vcardAsDict and vcardAsDict['bday'][0].value:
      bday_datetime = parse(vcardAsDict['bday'][0].value).replace(tzinfo=None)
      ret['bday'] = '%02d. %02d. %04d' % (bday_datetime.day, bday_datetime.month, bday_datetime.year)
    for a in ['adr','tel','email']:
      for i in range(len(vcardAsDict.get(a, []))):
        setattr(vcardAsDict[a][i], 'orig_id', i)
    for attr in ['adr', 'tel', 'email']:
      ret[attr] = [ {'value': (x.value if type(x.value)==str else x.value.__dict__),
                     'type': [t.lstrip('x-') for t in x.params.get('TYPE', []) if t.lower() != 'pref'],
                     'pref': (vcard_get_pref_value(x) != 101),
                     'orig_id': x.orig_id
                    } for x in sorted(vcardAsDict.get(attr, []), key=vcard_get_pref_value) ]
    ret['itemid'] = id
    ret['colid'] = self.db(self.db.colitems.id == id).select()[0].collection;
    return ret

  def get_serialized(self, id):
    vcard = self.get_structured(id)
    vcard_formatted = 'Name: {}\n'.format(vcard['fn'])
    vcard_formatted += 'Full name: {} {} {} {} {}\n\n'.format(vcard['n']['prefix'],vcard['n']['given'],vcard['n']['additional'],vcard['n']['family'],vcard['n']['suffix'])
    if vcard['bday']: vcard_formatted += 'Birthday: {}\n\n'.format(vcard['bday'])
    for email in vcard['email']:
      vcard_formatted += 'Email {}{}:\n\t{}\n'.format(",".join(email['type']), " (pref)" if email['pref'] else "", email['value'])
    vcard_formatted += '\n'
    for adr in vcard['adr']:
      vcard_formatted += 'Address {}{}:\n\t{}\n\t{} {}\n\t{}\n\n'.format(",".join(adr['type']), " (pref)" if adr['pref'] else "", adr['value']['street'], adr['value']['code'], adr['value']['city'], adr['value']['country'])
    for tel in vcard['tel']:
      vcard_formatted += 'Telephone {}{}:\n\t{}\n'.format(",".join(tel['type']), " (pref)" if tel['pref'] else "", tel['value'])
    return vcard_formatted

  def get_all_items(self):
    def mk_item(db_item):
      ret = {"id": db_item.id, "colid": db_item.collection}
      vItem = self.get_structured(db_item.id)
      ret['fn'] = vItem['fn']
      ret['email'] = "<br />".join((x['value'] for x in vItem['email']))
      ret['tel'] = "<br />".join((x['value'] for x in vItem['tel']))
      ret['bday'] = vItem['bday']
      ret['bday_diff'] = 400
      if vItem['bday']:
        bday_datetime = datetime.strptime(vItem['bday'], "%d. %m. %Y")
        ret['bday_diff'] = (rrule(YEARLY, bymonth=bday_datetime.month, bymonthday=bday_datetime.day).after(bday_datetime, True) - datetime.today()).days
      return ret
    return ( mk_item(x) for x in self.db(self.db.colitems.local_status != 2).select() )

  def _merge_dict_to_vcard(self, itemDict, vcard):
    def get_vcard_item(vcard, item, append=False, cls=str):
      entry = vcard.add(item) if append else getattr(vcard, item) if hasattr(vcard, item) else vcard.add(item)
      if append: entry.value = cls()
      assert cls == type(entry.value)
      return entry
    get_vcard_item(vcard, 'n', cls=vobject.vcard.Name).value.__dict__.update(itemDict['n'])
    get_vcard_item(vcard, 'fn').value = "{0} {1}".format(itemDict['n']['given'], itemDict['n']['family'])
    if itemDict['bday']:
      get_vcard_item(vcard, 'bday').value = datetime.strptime(itemDict['bday'], "%d. %m. %Y").strftime("%Y%m%d")
      del vcard.contents['bday'][1:]
    elif 'bday' in vcard.contents: del vcard.contents['bday']
    for (attr, cls) in [('adr',vobject.vcard.Address), ('tel',str), ('email',str)]:
      entriesBefore = frozenset(range(len(vcard.contents.get(attr, []))))
      entriesNow = frozenset([ x['orig_id'] for x in itemDict[attr] if 'orig_id' in x ])
      for item in itemDict[attr]:
        orig_id = item.get('orig_id', None)
        entry = vcard.contents[attr][orig_id] if orig_id != None else get_vcard_item(vcard, attr, append="True", cls=cls)
        if (cls == str): entry.value = item['value']
        else: entry.value.__dict__.update(item['value'])
        knownTypes = frozenset(item['type']).intersection(defined_types[attr])
        userTypes = [ 'x-{}'.format(x) for x in frozenset(item['type']).difference(defined_types[attr]) ]
        pref = ['pref'] if item['pref'] else []
        entry.params['TYPE'] = list(knownTypes)+userTypes+pref
        if attr=='adr' and 'LABEL' in entry.params: del entry.params['LABEL']
      for deletedIdx in sorted(entriesBefore.difference(entriesNow), reverse=True): del vcard.contents[attr][deletedIdx]
    d = datetime.now()
    get_vcard_item(vcard, 'rev').value = "%04d%02d%02dT%02d%02d%02d"%(d.year,d.month,d.day,d.hour,d.minute,d.second)
    return vcard

  def update_item(self, id, itemDict, socketio=None):
    self.db(self.db.colitems.id == id).update(content=self._merge_dict_to_vcard(itemDict, self.get(id)).serialize(), local_status=1)
    self.db.commit()
    if socketio: socketio.start_background_task(self.sync, socketio)
    else: self.sync()
    return self.get_structured(id)

  def add_item(self, itemDict, collectionId=1, socketio=None):
    id = self.db.colitems.insert(content=self._merge_dict_to_vcard(itemDict, vobject.vCard()).serialize(), local_status=3, collection=collectionId, href="")
    self.db.commit()
    if socketio: socketio.start_background_task(self.sync, socketio)
    else: self.sync()
    return self.get_structured(id)

  def delete_item(self, id, socketio=None):
    item = self.db(self.db.colitems.id == id).select()[0]
    if item.local_status == 3: item.delete_record()
    else: item.update_record(local_status=2)
    self.db.commit()
    if socketio: socketio.start_background_task(self.sync, socketio)
    else: self.sync()


  def get_collections(self, user, pw, url):
    config = dict(username=user, password=pw, url=url)
    if not pw:
      keyringData = keyring.DbusKeyring().FindItem({'dav-url': url, 'dav-user': user})
      config['password'] = keyringData[1]
    config['url'] = requests.get(config['url']).url # do redirection magic
    storage = CalDAVStorage(**config)
    ret = []
    for s in storage.discover(**config):
      subscribed = False
      subStorage = CalDAVStorage(**s)
      displayname = subStorage.get_meta('displayname')
      dbSet = self.db(self.db.collections.url==s['url'])
      if not dbSet.isempty(): subscribed = dbSet.select()[0].subscribed
      ret.append({'url': s['url'], 'subscribed': subscribed, 'name': displayname})
    return ret

  def update_collection_subscriptions(self, incomingJson):
    for server in incomingJson['servers']:
      for caldav in server['caldav_collections']:
        self.db.collections.update_or_insert(self.db.collections.url==caldav['url'], url=caldav['url'], subscribed=caldav["subscribed"]);
