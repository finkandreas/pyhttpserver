from flask import Flask, render_template, json, request, make_response
from flask_socketio import SocketIO
from flask_bootstrap import Bootstrap

import caldav
import carddav
import common
import financestatus
import keyring
import keyvalstore
import nettime
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

@socketio.on('message')
def handle_message(message):
  print('received message: ' + message)

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
  return render_template('newtab.html', startupData=json.dumps(dict(meteoschweiz895300=json.loads(MeteoSchweiz().get_buffered('895300')), meteoschweiz804900=json.loads(MeteoSchweiz().get_buffered('804900')), transferwise=Transferwise().get_buffered(), nettime=nettime.Nettime().get_buffered())))

@app.route("/newtab/info")
def get_newtab_info():
  return json.jsonify(dict(meteoschweiz895300=json.loads(MeteoSchweiz().get_buffered('895300')), meteoschweiz804900=json.loads(MeteoSchweiz().get_buffered('804900')), transferwise=Transferwise().get_buffered(), nettime=nettime.Nettime().get_buffered()))

@app.route("/nettime")
def get_nettime():
  return nettime.Nettime().get_buffered()

if __name__ == "__main__":
  while True:
    print("Starting server...")
    socketio.run(app, host="localhost", port=8080)
