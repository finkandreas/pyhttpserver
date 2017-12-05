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

class Nettime(object):
  def __init__(self):
    pass

  def update(socketio):
    newStatus = ""
    try:
      newStatus = Nettime().get()
    except RequestException as e:
      print("RequestException while trying to fetch Nettime. Exception: ", e)
      return (False, {})
    except Exception as e:
      print("Exception while trying to fetch Nettime: ", e)
      newStatus = Nettime().get_buffered()
    if newStatus:
      keyvalstore.KeyValueStore().set("nettime.status".format(zip), newStatus)
      print("{}: Updated Nettime".format(datetime.datetime.now()))
    return (True, {'channel': 'nettime', 'data': {'data': newStatus}})

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
