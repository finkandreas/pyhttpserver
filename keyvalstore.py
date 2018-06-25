from common import get_config_dir
from pydal import DAL, Field, SQLCustomType
import pickle
import base64
import requests

class KeyValueStore(object):
  def __init__(self):
    self.db = DAL('sqlite://keyvalstore.db', folder=get_config_dir())
    self.db.define_table('store', Field('key', type='string', required=True, unique=True),
                                  Field('value', type='blob'),
                                  Field('version', type='integer', default=0))

  def __del__(self):
    self.db.close()

  def set(self, key, value):
    # We have to execute pure SQL statements because pydal does not support blobs as it seems
    res = self.db.executesql('SELECT value from store where key=?', placeholders=[key])
    if len(res)>0: self.db.executesql('UPDATE store SET value=? where key=?', placeholders=[pickle.dumps(value), key])
    else: self.db.executesql('INSERT INTO "store"("key","value") VALUES (?, ?)', placeholders=[key, pickle.dumps(value)])
    self.db.commit()

  def get(self, key, default=""):
    res = self.db.executesql('SELECT value from store where key=?', placeholders=[key])
    return default if len(res)==0 else pickle.loads(res[0][0])

  def set_versioned(self, key, value, version):
    response = requests.post('https://dibser.vserverli.de/php/keyvaluestore.php?key={}&version={}'.format(key, version), data=pickle.dumps(value), headers={'Content-Type': 'application/octet-stream'})
    response.raise_for_status()
    res = self.db.executesql('SELECT value from store where key=?', placeholders=[key])
    if len(res)>0: self.db.executesql('UPDATE store SET value=?, version=? where key=?', placeholders=[pickle.dumps(value), version, key])
    else: self.db.executesql('INSERT INTO "store"("key","value", "version") VALUES (?, ?, ?)', placeholders=[key, pickle.dumps(value), version])
    self.db.commit()


  def get_versioned(self, key, default=""):
    res = self.db.executesql('SELECT value,version from store where key=?', placeholders=[key])
    value = None
    if len(res)>0:
      newest_version = local_version = res[0][1]
      if not local_version: local_version=1
      value = res[0][0]

    # check remote version and update if remote is newer (status code == 200 if a newer version is available, otherwise status code 404 if not available or 304 if older/same version)
    response = requests.get('https://dibser.vserverli.de/php/keyvaluestore.php?key={}&version={}'.format(key, local_version))
    if response.status_code == 200:
      newest_version = int(response.headers['X-Keyvalstore-Version'])
      value=response.content
      print("Remote version is newer for key={}. Local version={} remote version={}".format(key, local_version, newest_version))

    return (default, -1) if value==None else (pickle.loads(value), newest_version)
