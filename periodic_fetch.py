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
from eventlet import tpool, greenthread


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
    def _do_run_in_thread(callback_fct, socketio, **kwargs):
      success, socketData = tpool.execute(callback_fct, socketio, **kwargs)
      if socketData:
        socketio.sleep(60)
        #~ print("Success={}, sending socketData={}".format(success, socketData))
        socketio.emit(socketData['channel'], socketData['data'])

    new_callbacks = []
    now = datetime.datetime.now()
    for callback_fct, frequency, single_shot, last_run, kwargs in self.callbacks:
      if (now-last_run).total_seconds() > frequency:
        # We need to run  the callback function
        print("{}: Spawning thread to run {}".format(datetime.datetime.now(), callback_fct))
        spawnedThread = greenthread.spawn(_do_run_in_thread, callback_fct, self.socketio, **kwargs)
        last_run = now
      if not single_shot:
        new_callbacks.append( (callback_fct, frequency, single_shot, last_run, kwargs) )
    self.callbacks = new_callbacks

    self.socketio.sleep(self.min_interval)
    print("{}: Woke up after socketio.sleep".format(datetime.datetime.now()))
    self.socketio.start_background_task(self.run)


class MeteoSchweiz(object):
  def __init__(self):
    pass

  def update(socketio):
    ret = []
    for zip in ['895300', '804900']:
      newStatus = ""
      try:
        newStatus = MeteoSchweiz().get(zip)
      except RequestException as e:
        print("RequestException while trying to fetch MeteoSchweiz. Exception: ", e)
        return (False, {})
      except Exception as e:
        print("Exception while trying to fetch MeteoSchweiz: ", e)
        newStatus = MeteoSchweiz().get_buffered(zip)
      if (newStatus):
        keyvalstore.KeyValueStore().set("meteoschweiz.{}.fullJson".format(zip), newStatus)
        ret.append({'zip': zip, 'data': newStatus})
    print("{}: Updated MeteoSchweiz".format(datetime.datetime.now()))
    return (True, {'channel': 'weather', 'data': ret})

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

  def update(socketio):
    newStatus = ""
    try:
      newStatus = Transferwise().get()
    except RequestException as e:
      print("RequestException while trying to fetch Transferwise. Exception: ", e)
      return (False, {})
    except Exception as e:
      print("Exception while trying to fetch Transferwise: ", e)
      newStatus = Transferwise().get_buffered()
    if newStatus:
      keyvalstore.KeyValueStore().set("transferwise.rate", newStatus)
      print("{}: Updated Transferwise".format(datetime.datetime.now()))
    return (True, {'channel': 'transferwise', 'data': {'data': newStatus}})

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
    transferwise = json.loads(response.content.decode('utf-8'))['transferwiseRate']/1.005

    response_currencyfair = session.get('https://app.currencyfair.com/calculator/quicktrade-quote?&mode=SELL&depositCurrency=EUR&beneficiaryCurrency=CHF&amount=10000')
    response_currencyfair.raise_for_status()
    currencyfair = json.loads(response_currencyfair.content.decode('utf-8'))['quote']['estimatesByTransferType']['1']['estimatedAmount']/10000

    response_xendpay = session.get('https://secure.xendpay.com/quote/api/get-quote?paymentCountryCode=DE&paymentCurrencyCode=EUR&deliveryCountryCode=CH&deliveryCurrencyCode=CHF&deliveryMethodCode=earthport-api&amount=10000.00&amountCurrencyCode=EUR&amountDeductFees=false&discretionalFee=&promoCode=')
    response_xendpay.raise_for_status()
    xendpay = float(json.loads(response_xendpay.content.decode('utf-8'))['data']['rate'])

    kvs = keyvalstore.KeyValueStore()
    timestamp = int(datetime.datetime.now().timestamp())
    twHistory = kvs.get('transferwise.history', [])
    cfHistory = kvs.get('currencyfair.history', [])
    xpHistory = kvs.get('xendpay.history', [])
    twHistory.append((timestamp, transferwise))
    cfHistory.append((timestamp, currencyfair))
    xpHistory.append((timestamp, xendpay))
    twHistory = twHistory[-100:]
    cfHistory = cfHistory[-100:]
    xpHistory = xpHistory[-100:]
    kvs.set('transferwise.history', twHistory)
    kvs.set('currencyfair.history', cfHistory)
    kvs.set('xendpay.history', xpHistory)

    return "{:.4f} - {:.4f} - {:.4f}".format(transferwise, currencyfair, xendpay)
