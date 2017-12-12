from common import get_config_dir
from pydal import DAL, Field, SQLCustomType
import pickle
import base64

class KeyValueStore(object):
  def __init__(self):
    self.db = DAL('sqlite://keyvalstore.db', folder=get_config_dir())
    self.db.define_table('store', Field('key', type='string', required=True, unique=True),
                                  Field('value', type='blob'))

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
