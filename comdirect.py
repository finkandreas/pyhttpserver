#!/usr/bin/env python3

import requests
from lxml import etree
from lxml.html import HtmlElement
import keyring
import datetime

#~ from http.client import HTTPConnection
#~ import logging
#~ HTTPConnection.debuglevel = 1

#~ logging.basicConfig()
#~ logging.getLogger().setLevel(logging.DEBUG)
#~ requests_log = logging.getLogger("requests.packages.urllib3")
#~ requests_log.setLevel(logging.DEBUG)
#~ requests_log.propagate = True


def get(delta=9):
  session = requests.session()
  response = session.get('https://kunde.comdirect.de/lp/wt/login')
  response.raise_for_status()
  postUrl = response.url

  keyringData = keyring.DbusKeyring().FindItem({'bank': 'comdirect'})
  payload = dict(login="login", rolle="", page="", param1=str(keyringData[0]['user']), direktzu="KontoUmsaetze",loginAction="loginAction")
  payload['param3'] = keyringData[1]
  payload['javax.faces.ViewState'] = ""
  doc = etree.HTML(response.content)
  for input in doc.xpath("//input"):
    if input.get("name") == 'javax.faces.ViewState': payload[input.get("name")] = input.get("value")

  # login to server and be forwarded to the status page
  response = session.post(postUrl, data=payload)
  response.raise_for_status()

  # get the account balance (there seems to be a bug in comdirect, that you do not see the account balance when you look for specific dates)
  doc = etree.HTML(response.content)
  umsatzliste = doc.cssselect("div.umsatzListe")[0]
  elements = umsatzliste[0].cssselect('span.uiOutputText')
  status = ("Commerzbank", elements[0].text.strip(), elements[1].text.strip()) # (name, date, amount)

  # get data for the last n days
  start = (datetime.date.today()-datetime.timedelta(days=delta)).strftime("%d.%m.%Y")
  end = datetime.date.today().strftime("%d.%m.%Y")
  payload2 ='f1=f1&f1-umsatzauswahl=KONTEN.OHNE.DEPOT&f1-intervall=10&f1-zeitraum=BEREICH&f1-datumVonBis-von={}&f1-datumVonBis-bis={}&f1-erweiterteSuche=&f1-suchbegriff=&f1-betragVon=&f1-betragBis=&f1-vorgang=Alle+Vorg%C3%A4nge&f1-umsatzTyp=ALLE&javax.faces.ViewState={}&javax.faces.RenderKitId=HTML_RD&f1-j_idt127=f1-j_idt127'.format(start,end, doc.cssselect('input[name="javax.faces.ViewState"]')[0].get('value'))

  response = session.post(response.url, data=payload2, headers={'Content-Type':'application/x-www-form-urlencoded'})
  response.raise_for_status()

  #~ open("response", "wb").write(response.content)

  doc = etree.HTML(response.content)
  umsatzliste = doc.cssselect("div.umsatzListe")[0]
  lastTransactions = []
  for transaction in umsatzliste[1:-1]:
    elements = transaction.cssselect('.uiGridLayoutColumn')
    if (len(elements) == 3):
      amount = " ".join(x.text.strip() for x in elements[2].cssselect('span.uiOutputText'))
      date = " ".join(x.text.strip() for x in elements[0].cssselect('span.uiOutputText'))
      text = " ".join(x.text.strip() for x in elements[1].cssselect('span.uiOutputText'))
      lastTransactions.append( (amount, date, text) )
    elif (len(elements) == 1):
      #~ text = " ".join(x.text.strip() for x in elements[0].cssselect('span.uiOutputText'))
      #~ lastTransactions.append( ("", "", text) )
      pass
    else:
      print("Error while parsing the transaction list. We matched {} elements with span.uiOutputText, but we expect 1 or 3 elements".format(len(elements)))

  # logout
  session.get('https://kunde.comdirect.de/lp/wt/logout').raise_for_status()

  return [(status, list(lastTransactions))]

if __name__ == '__main__':
  status, lastTransactions = get()[0]
  print(status)
  for t in lastTransactions:
    print("{} {} {}".format(*t))
