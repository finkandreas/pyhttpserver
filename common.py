import json
import os
from xdg import BaseDirectory

import keyring

def get_config_dir():
  return BaseDirectory.save_data_path('pyhttpserver')

def get_davconfig_path():
  return os.path.join(get_config_dir(), "davconfig.json")

def get_davconfig():
  try:
    cfg = json.load(open(get_davconfig_path(), 'r'))
    k = keyring.DbusKeyring()
    for serverConfig in cfg['servers']:
      serverConfig['password'] = k.FindItem({'dav-user': serverConfig['username'], 'dav-url': serverConfig['url']})[1] or ""
    return cfg
  except:
    return { }

def save_davconfig(newConfig):
  for serverConfig in newConfig['servers']:
    keyring.DbusKeyring().UpdateOrInsertItem({'dav-url': serverConfig['url'], 'dav-user': serverConfig['username']}, serverConfig['password'])
    del serverConfig['password']
  json.dump(newConfig, open(get_davconfig_path(), 'w'))

def get_addressbook_db_name():
  return 'carddav.db'
def get_addressbook_db_path():
  return os.path.join(get_config_dir(), get_addressbook_db_name())

def get_calendar_db_name():
  return 'caldav.db'
def get_calendar_db_path():
  return os.path.join(get_config_dir(), get_calendar_db_name())
