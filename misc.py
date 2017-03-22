defined_types = dict( { 'email': frozenset(('home', 'work')),
                        'adr': frozenset(('home', 'work')),
                        'tel': frozenset(('home', 'work', 'voice', 'text', 'fax', 'cell', 'video', 'pager', 'textphone')) } )

# case-insensitive-string comparison
class cis(object):
  def __init__(self, s):
    self.s = s
  def __cmp__(self, other):
    return cmp(self.s.lower(), other.lower())
  def __eq__(self, other):
    return self.s.lower() == other.lower()


def vcard21_to_vcard30(vcard):
  if vcard.contents.get('version', ['2.1'])[0].value == "2.1":
    for attr in ('adr_list', 'tel_list', 'email_list'):
      if hasattr(vcard, attr):
        for  val in getattr(vcard, attr):
          if 'TYPE' not in val.params:
            val.params['TYPE'] = val.singletonparams
            val.singletonparams = []
    vcard.version.value = "3.0"
  return vcard


def vcard30_to_vcard40(vcard):
  if vcard.contents.get('version', ['3.0'])[0].value == "3.0":
    for attr in ('adr_list','tel_list', 'email_list'):
      if hasattr(vcard, attr):
        for val in getattr(vcard, attr):
          if 'TYPE' in val.params:
            if cis('pref') in val.params['TYPE']:
              val.params['TYPE'].remove(cis('PREF'))
              val.params['PREF'] = ['1']
            if val.params['TYPE'] == []:
              del val.params['TYPE']
    vcard.version.value = '4.0'
  return vcard



def vcard_get_pref_value(vcard_entry):
  if cis('pref') in vcard_entry.params.get('TYPE', []): return 1
  return int(vcard_entry.params['PREF'][0]) if hasattr(vcard_entry, 'pref_param') else 101
