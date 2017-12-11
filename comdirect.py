#!/usr/bin/env python3

import requests
from lxml import etree
from lxml.html import HtmlElement
import keyring
import datetime
import sys

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
    if input.get("name") in frozenset(['javax.faces.ViewState', 'csfCsrfToken']): payload[input.get("name")] = input.get("value")

  # login to server and be forwarded to the status page
  response = session.post(postUrl, data=payload)
  response.raise_for_status()
  #~ open("comdirect.resp1", "wb").write(response.content)

  # get the account balance (there seems to be a bug in comdirect, that you do not see the account balance when you look for specific dates)
  doc = etree.HTML(response.content)
  kontostandElements = doc.cssselect("div.cif-scope-content-wrapper div.grid--no-gutter span.output-text")
  status = ("Commerzbank", kontostandElements[0].text.strip(), kontostandElements[1].text.strip()) # (name, date, amount)

  # get data for the last n days
  start = (datetime.date.today()-datetime.timedelta(days=delta)).strftime("%d.%m.%Y")
  end = datetime.date.today().strftime("%d.%m.%Y")
  payload2 ='j_idt9-filterForm=j_idt9-filterForm&j_idt9-filterForm-produktauswahl=Alle%20Konten&j_idt9-filterForm-intervall=30&j_idt9-filterForm-zeitraum=BEREICH&j_idt9-filterForm-von={}&j_idt9-filterForm-bis={}&j_idt9-filterForm-erweiterteSuche=false&j_idt9-filterForm-suchbegriff=&j_idt9-filterForm-betragVon=&j_idt9-filterForm-betragBis=&j_idt9-filterForm-vorgang=Alle%20Vorg%C3%A4nge&j_idt9-filterForm-umsatzTyp=ALLE&javax.faces.ViewState={}&javax.faces.RenderKitId=CIF_HTML_RW&javax.faces.source=j_idt9-filterForm-j_idt67&javax.faces.partial.event=click&javax.faces.partial.execute=j_idt9-filterForm-j_idt67%20j_idt9-filterForm&javax.faces.partial.render=0&event=click&propagate=true&syncIE=false&serializeForm=&extraParams=&dataType=xml&beforeSend=function()%7B%7D&complete=function()%7B%7D&sendProcessIdOnly=false&ignoreEmptyFields=false&onlyOnce=false&executionTimestamp=null&onLoad=false&regexFilter=&refocus=false&source=j_idt9-filterForm-j_idt67&dialogId=j_idt9-filterForm-pinEingabeDialog&javax.faces.behavior.event=click&javax.faces.partial.ajax=true'.format(start,end, doc.cssselect('input[name="javax.faces.ViewState"]')[0].get('value'))
  response = session.post(response.url, data=payload2, headers={'Content-Type':'application/x-www-form-urlencoded'})
  response.raise_for_status()
  #~ open("comdirect.resp2", "wb").write(response.content)

  doc = etree.HTML(response.content)
  umsatzliste = doc.cssselect("tr.table__row.table__row--details-trigger")
  lastTransactions = []
  for transaction in umsatzliste:
    elements = transaction.cssselect('td.table__column span.output-text')
    if (len(elements) == 3):
      amount = elements[2].text
      date = elements[0].text
      text = elements[1].text
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
  status, lastTransactions = get(int(sys.argv[1]) if len(sys.argv)>1 else 3)[0]
  print(status)
  for t in lastTransactions:
    print("{} {} {}".format(*t))
