#!/usr/bin/env python3

import requests
from lxml import etree
from lxml.html import HtmlElement
import keyring
import datetime
import re

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
  response = session.get('https://www.dkb.de/banking')
  response.raise_for_status()

  keyringData = keyring.DbusKeyring().FindItem({'bank': 'dkb'})
  payload = dict(hiddenSubmit="", browserName="Firefox", browserVersion="50.0", screenWidth="1920", screenHeight="1200", jsEnabled="true", osName="UNIX", j_username=str(keyringData[0]['user']), j_password="")
  payload['$event'] = "login"
  payload['$sID$'] = ""
  payload['token'] = ""
  payload['j_password'] = keyringData[1]
  doc = etree.HTML(response.content)
  for input in doc.xpath("//input"):
    if input.get("name") == '$sID$': payload[input.get("name")] = input.get("value")
    if input.get("name") == 'token': payload[input.get("name")] = input.get("value")

  # login to server and be forwarded to the status page
  response = session.post('https://www.dkb.de/banking', data=payload)
  response.raise_for_status()
  #~ open("response", "wb").write(response.content)
  doc = etree.HTML(response.content)
  allRows = doc.cssselect("table.financialStatusTable tr.mainRow")
  accountStatus = [ (row[0][0].text.strip(), row[0][1].text.strip(), row[-2][0].text.strip()) for row in allRows ] # array with all account status (Name, IBAN, Balance)
  logoutHref = "https://www.dkb.de{}".format(doc.cssselect('#logout')[0].get('href'))

  accounts = ["1", "2", "3", "4", "6"]
  accountTransactions = []
  removeCommon = re.compile('{}|{}|{}|{}|{}|{}|{}|1\.TAN\s+\d+'.format(re.escape('GV-Code: '), 'Gutschrift', 'Überweisung', 'Dauerauftrag', re.escape('Kartenzahlung/-abrechnung'), re.escape('Lohn, Gehalt, Rente'), 'Lastschrift'), re.IGNORECASE)
  for accountId in accounts:
    payload = dict(slAllAccounts=accountId, slTransactionStatus="0")
    start = (datetime.date.today()-datetime.timedelta(days=(delta+(2 if accountId=="6" else 0)))).strftime("%d.%m.%Y")
    end = datetime.date.today().strftime("%d.%m.%Y")
    if accountId == "6":
      payload.update(dict(searchPeriod="0", postingDate=start, toPostingDate=end))
    else:
      payload.update(dict(slSearchPeriod="1", searchPeriodRadio="1", transactionDate=start, toTransactionDate=end))
    payload['$event'] = "search"
    response = session.post('https://www.dkb.de/banking/finanzstatus/{}'.format("kontoumsaetze" if accountId != "6" else "kreditkartenumsaetze"), data = payload)
    response.raise_for_status()
    #~ open("response{}.raw".format(accountId), "wb").write(response.content)
    doc = etree.HTML(response.content)

    # get the print button and load the print page, because it contains all transactions, i.e. no paging is there
    response = session.get('https://www.dkb.de'+doc.cssselect('div.content>h1>a')[0].get('onclick').split('"')[1])
    response.raise_for_status()
    #~ open("response{}.print".format(accountId), "wb").write(response.content)
    doc = etree.HTML(response.content)
    allRows = doc.cssselect("table tr.mainRow")
    localTransactions = []
    for row in allRows:
      cost = ""
      date = ""
      explanation = ""
      for td in row:
        if td.get('headers').find("disposalDate")>0 or td.get('headers').find('transactionDate')>0: date = td.cssselect('.valueDate')[0].text
        if td.get('headers').find('amountToTransfer')>0 or td.get('headers').find('localAmount.value')>0: cost = " ".join([t.strip() for t in td.itertext()])
        if td.get('headers').find('text')>0 or td.get('headers').find('type')>0: explanation = removeCommon.sub('', " ".join([t.strip() for t in td.itertext()]).replace('GV-Code: ', "")).strip()
      localTransactions.append( (cost, date, explanation) )
    accountTransactions.append(localTransactions)

  # logout
  session.get(logoutHref).raise_for_status()

  return list(zip(accountStatus, accountTransactions))

if __name__ == '__main__':
  for accountStatus, accountTransactions in get():
    print("{:<35}{:<35}{:>10}".format(*accountStatus))
    print("\n".join("\t{:<10}{:<10} {}".format(*accountTransaction) for accountTransaction in accountTransactions))
    print("\n")
