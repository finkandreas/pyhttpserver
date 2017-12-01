#!/usr/bin/env python3

import requests
from lxml import etree
from lxml.html import HtmlElement
import keyring
import datetime
import re

import keyvalstore
import datetime
import json
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
  socketio.start_background_task(self.fetch_background)


class PeriodicFetcher(object):
  def __init__(self, socketio):
    self.min_interval = 600 # wake up every 10 minutes
    self.callbacks = []
    self.socketio = socketio

  # callback_fct = def my_function(socketio, **kwargs)
  # frequency = integer in seconds
  # single_shot = boolean if it is supposed to be executed only once after the frequency passed
  # if single_shot is false, the callback_fct is called right away, and then periodically with the provided frequency
  def register_callback(self, callback_fct, frequency, single_shot, **kwargs):
    delta = datetime.timedelta(0)
    if not single_shot: delta = datetime.timedelta(seconds=frequency)
    self.callbacks.append( (callback_fct, frequency, single_shot, datetime.datetime.now()-delta, kwargs) )

  def run(self):
    new_callbacks = []
    now = datetime.datetime.now()
    for callback_fct, frequency, single_shot, last_run, kwargs in self.callbacks:
      if (now-last_run).total_seconds() > frequency:
        # We need to run  the callback function
        success = callback_fct(socketio=self.socketio, **kwargs)
        last_run = now
      if not single_shot:
        new_callbacks.append( (callback_fct, frequency, single_shot, last_run, kwargs) )
    self.callbacks = new_callbacks

    self.socketio.sleep(self.min_interval)
    self.socketio.start_background_task(self.run)


class MeteoSchweiz(object):
  def __init__(self):
    pass

  def update(socketio):
    def do_update(zip):
      newStatus = ""
      try:
        newStatus = MeteoSchweiz().get(zip)
      except RequestException as e:
        print("RequestException while trying to fetch MeteoSchweiz. Exception: ", e)
      except Exception as e:
        print("Exception while trying to fetch MeteoSchweiz: ", e)
        newStatus = MeteoSchweiz().get_buffered(zip)
      return newStatus

    for zip in ['895300', '804900']:
      newStatus = tpool.execute(do_update, zip)
      if (newStatus): keyvalstore.KeyValueStore().set("meteoschweiz.{}.fullJson".format(zip), newStatus)
    print("{}: Updated MeteoSchweiz".format(datetime.datetime.now()))
    return True

  def get_buffered(self, zip='895300'):
    return keyvalstore.KeyValueStore().get("meteoschweiz.{}.fullJson".format(zip))

  def get(self, zip):
    session = requests.session()
    response = session.get('http://www.meteoschweiz.admin.ch/home.html')
    response.raise_for_status()

    doc = etree.HTML(response.content)
    jsonUrl = doc.cssselect('div.overview__local-forecast')[0].get('data-json-url')
    jsonUrl = 'http://www.meteoschweiz.admin.ch' + jsonUrl.replace("800100.json", "{}.json".format(zip))
    response = session.get(jsonUrl)
    response.raise_for_status()
    return response.content.decode('utf-8')


class Transferwise(object):
  def __init__(self):
    pass

  def get_buffered(self):
    return keyvalstore.KeyValueStore().get("transferwise.rate")

  def get(self):
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0'}
    session = requests.session()
    response = session.get('https://transferwise.com', headers=headers)
    response.raise_for_status()

    headers['X-Authorization-key'] = 'dad99d7d8e52c2c8aaf9fda788d8acdc'
    headers['X-Authorization-token'] = ''
    headers['X-Language'] = 'en'

    response = session.get('https://transferwise.com/api/v1/payment/calculate?amount=10000&amountCurrency=source&getNoticeMessages=true&hasDiscount=false&isFixedRate=false&isGuaranteedFixedTarget=false&payInMethod=ADYEN_DEBIT&sourceCurrency=EUR&targetCurrency=CHF', headers=headers)
    response.raise_for_status()
    return json.loads(response.content.decode('utf-8'))['transferwiseRate']
