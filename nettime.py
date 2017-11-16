#!/usr/bin/env python3

import requests
from lxml import etree
from lxml.html import HtmlElement
import keyring
import datetime
import re

import keyvalstore
import datetime
from requests.exceptions import RequestException
from eventlet import tpool

def _do_fetch():
  newStatus = ""
  try:
    newStatus = Nettime().get()
  except RequestException as e:
    print("RequestException while trying to fetch the nettime status. Exception: ", e)
  except Exception as e:
    print("Exception while trying to fetch the nettime status: ", e)
    newStatus = Nettime().get_buffered() # set it to the old status so we do not retry in 30 seconds, the problem is probably sth completely different (e.g. parsing issues)
  return newStatus

def fetch_background(socketio):
  newStatus = tpool.execute(_do_fetch)
  oldStatus = Nettime().get_buffered()
  if (newStatus): keyvalstore.KeyValueStore().set("nettime.status", newStatus)
  print("{}: Updated nettime status".format(datetime.datetime.now()))
  socketio.sleep(14400 if newStatus else 30) # retry in 30 seconds if sth went wrong, otherwise sleep for 4h
  socketio.start_background_task(fetch_background, socketio)


class Nettime(object):
  def __init__(self):
    pass

  def get_buffered(self):
    return keyvalstore.KeyValueStore().get("nettime.status")

  def get(self):
    session = requests.session()
    response = session.get('https://nettime.cscs.ch/')
    response.raise_for_status()
    response = session.get('https://nettime.cscs.ch/infoweb/infoLog.asp')
    response.raise_for_status()
    pw = keyringData = keyring.DbusKeyring().FindItem({'claws-user': 'anfink'})[1]
    payload = dict(user="anfink", password=pw)
    response = session.post('https://nettime.cscs.ch/infoweb/main/infoCtrlLog.asp', data=payload)
    response.raise_for_status()
    response = session.get('https://nettime.cscs.ch/infoweb/main/infoMenu-New.asp?idMnu=03')
    response.raise_for_status()
    response = session.get('https://nettime.cscs.ch/infoweb/HolidayProg/infoHoliday.asp')
    response.raise_for_status()
    doc = etree.HTML(response.content)
    matched = doc.cssselect("table tr table tr td:last-child")
    return matched[-1].text.strip()
