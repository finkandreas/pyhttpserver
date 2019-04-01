from flask import Flask, render_template, json, request, make_response
from flask_socketio import SocketIO, send
from flask_bootstrap import Bootstrap

import caldav
import carddav
import common
import datetime
import financestatus
import keyring
import keyvalstore
import nettime
import random
from periodic_fetch import PeriodicFetcher, MeteoSchweiz, Transferwise

app = Flask(__name__)
app.config['BOOTSTRAP_SERVE_LOCAL'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SECRET_KEY'] = 'secret!'
Bootstrap(app)
socketio = SocketIO(app)

periodicFetcher = PeriodicFetcher(socketio)
periodicFetcher.register_callback(MeteoSchweiz.update, frequency=1800, single_shot=False)
periodicFetcher.register_callback(Transferwise.update, frequency=600, single_shot=False)
periodicFetcher.register_callback(nettime.Nettime.update, frequency=14400, single_shot=False)
periodicFetcher.register_callback(financestatus.FinanceStatus.update, frequency=3600, single_shot=False)
periodicFetcher.register_callback(carddav.sync, frequency=3600, single_shot=False)
socketio.start_background_task(periodicFetcher.run)


def pingSocket(socketio):
  socketio.emit('pinging', '')
  socketio.sleep(10);
  socketio.start_background_task(pingSocket, socketio)
socketio.start_background_task(pingSocket, socketio)


@socketio.on('message')
def handle_message(message):
  print('received message: ' + message)
  socketio.send('received message: ' + message)

@app.route("/")
def hello():
  socketio.send('hello')
  return "Hello World!"

@app.route("/addressbook")
def show_addressbook():
  c = carddav.CardDav()
  return render_template("addressbook.html", items=c.get_all_items(), collections=c.get_subscribed_collections())

@app.route("/addressbook/vcard")
def get_vcard():
  return carddav.CardDav().get_serialized(request.args['itemid'])

@app.route("/addressbook/json", methods=['GET', 'POST', 'PUT', 'DELETE'])
def get_vcard_json():
  itemId = request.args.get('itemid')
  colId = request.args.get('colid')
  if request.method == 'PUT':
    incomingJson = request.get_json()
    return json.jsonify(carddav.CardDav().update_item(itemId, incomingJson, socketio=socketio))
  elif request.method == 'DELETE':
    carddav.CardDav().delete_item(itemId, socketio)
    return "success"
  elif request.method == 'POST':
    incomingJson = request.get_json()
    return json.jsonify(carddav.CardDav().add_item(incomingJson, collectionId=colId, socketio=socketio))
  return json.jsonify(carddav.CardDav().get_structured(itemId))

@app.route("/keyring")
def get_keyring_pw():
  #~ args = request.args.to_dict()
  #~ secret = args.pop('secret', None)
  #~ resp = make_response(keyring.DbusKeyring().FindItem(args)[1] or "")
  #~ if secret and secret==app.config['SECRET_KEY']:
    #~ resp.headers['Access-Control-Allow-Origin'] = '*'
  #~ return resp
  return keyring.DbusKeyring().FindItem(request.args)[1] or ""

@app.route("/dav", methods=['GET', 'POST'])
def show_dav_config():
  if request.method == 'POST':
    incomingJson = request.get_json()
    common.save_davconfig(incomingJson)
    for c in [carddav.CardDav(), caldav.CalDav()]:
      c.update_collection_subscriptions(incomingJson)
      c.sync(socketio)
  return render_template("davconfig.html", config=common.get_davconfig())

@app.route("/dav/collections")
def get_dav_collections():
  carddavCols = carddav.CardDav().get_collections(user=request.args.get("user"), pw=request.args.get("pass"), url=request.args.get("url"))
  caldavCols = caldav.CalDav().get_collections(user=request.args.get("user"), pw=request.args.get("pass"), url=request.args.get("url"))
  return json.jsonify(dict(carddav=carddavCols, caldav=caldavCols))

@app.route("/kvs")
def get_value():
  return str(keyvalstore.KeyValueStore().get(request.args['key']))

@app.route("/dkb")
def get_financestatus():
  return render_template("financestatus.html", accountStatus=financestatus.FinanceStatus().get_buffered())

@app.route("/dkb/<int:days>")
def get_financestatus_days(days):
  return render_template("financestatus.html", accountStatus=financestatus.FinanceStatus().get_unbuffered(days))

@app.route("/newtab")
def get_newtab():
  return render_template('newtab.html', startupData=json.dumps(dict(meteoschweiz=[{'zip': z, 'data': MeteoSchweiz().get_buffered(z)} for z in ('895300', '804900')], transferwise=Transferwise().get_buffered(), nettime=nettime.Nettime().get_buffered())))

@app.route("/newtab/info")
def get_newtab_info():
  return json.jsonify(dict(meteoschweiz=[dict(zip=z, data=json.loads(MeteoSchweiz().get_buffered(z))) for z in ('895300', '804900')], transferwise=Transferwise().get_buffered(), nettime=nettime.Nettime().get_buffered()))

@app.route("/nettime")
def get_nettime():
  return nettime.Nettime().get_buffered()

@app.route("/random")
def get_random_code():
  dateStr = request.args['date'] if 'date' in request.args else ''
  dd = request.args.to_dict()
  if 'date' in dd: del dd['date']
  pw = keyring.DbusKeyring().FindItem(dd)[1] if dd else '';
  today = datetime.datetime.today()
  dateArray = dateStr.split('.')
  date = today
  if len(dateArray)>0 and len(dateArray[0])>0: date = date.replace(day=int(dateArray[0]))
  if len(dateArray)>1 and len(dateArray[1])>0: date = date.replace(month=int(dateArray[1]))
  if len(dateArray)>2 and len(dateArray[2])>0: date = date.replace(year=int(dateArray[2]))
  seed=date.strftime('%d%m%Y') + pw
  random.seed(seed)
  result = ''
  for i in range(4): result += str(random.randrange(10))
  return result


if __name__ == "__main__":
  while True:
    print("Starting server...")
    socketio.run(app, host="localhost", port=8080)
