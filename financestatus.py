import dkb
import comdirect
import keyvalstore
import datetime
from requests.exceptions import RequestException
from eventlet import tpool

def _do_fetch():
  newStatus = []
  try:
    newStatus = dkb.get(3)+comdirect.get(3)
  except RequestException as e:
    print("RequestException while trying to fetch the finance status. Exception: ", e)
  except Exception as e:
    print("Exception while trying to fetch the finance status: ", e)
    newStatus = FinanceStatus().get_buffered() # set it to the old status so we do not retry in 30 seconds, the problem is probably sth completely different (e.g. parsing issues)
  return newStatus

def fetch_background(socketio):
  newStatus = tpool.execute(_do_fetch)
  oldStatus = FinanceStatus().get_buffered()
  if (newStatus): keyvalstore.KeyValueStore().set("financestatus.status3", newStatus)
  if oldStatus != newStatus:
    socketio.sleep(30) # Sleep because after a standby the websocket does not work directly again.
    socketio.send("{}: finance status changed".format(datetime.datetime.now()))
    print("Finance status changed")
  print("{}: Updated finance status".format(datetime.datetime.now()))
  socketio.sleep(3600 if newStatus else 30) # retry in 30 seconds if sth went wrong, otherwise sleep for 1h
  socketio.start_background_task(fetch_background, socketio)


class FinanceStatus(object):
  def __init__(self):
    pass

  def get_buffered(self):
    return keyvalstore.KeyValueStore().get("financestatus.status3")

  def get_unbuffered(self, days):
    try:
      return dkb.get(days)+comdirect.get(days)
    except RequestException as e:
      print("Exception while trying to fetch the finance status. Exception: ", e)
      return self.get_buffered()
