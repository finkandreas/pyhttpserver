import dkb
import comdirect
import keyvalstore
import datetime
from requests.exceptions import RequestException
from eventlet import tpool

class FinanceStatus(object):
  def __init__(self):
    pass

  def update(socketio):
    newStatus = []
    try:
      newStatus = dkb.get(3)+comdirect.get(3)
    except RequestException as e:
      print("RequestException while trying to fetch the finance status. Exception: ", e)
      return (False, {})
    except Exception as e:
      print("Exception while trying to fetch the finance status: ", e)
      newStatus = FinanceStatus().get_buffered() # set it to the old status so we do not retry in 30 seconds, the problem is probably sth completely different (e.g. parsing issues)
    oldStatus = FinanceStatus().get_buffered()
    if (newStatus): keyvalstore.KeyValueStore().set("financestatus.status3", newStatus)
    if newStatus and oldStatus != newStatus:
      print("Finance status changed")
      return (True, {'channel': 'message', 'data': newStatus})
    print("{}: Updated finance status".format(datetime.datetime.now()))
    return (True, {})


  def get_buffered(self):
    return keyvalstore.KeyValueStore().get("financestatus.status3")

  def get_unbuffered(self, days):
    try:
      return dkb.get(days)+comdirect.get(days)
    except RequestException as e:
      print("Exception while trying to fetch the finance status. Exception: ", e)
      return self.get_buffered()
