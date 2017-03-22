from flask import Flask, render_template, json, request
from flask_socketio import SocketIO
from flask_bootstrap import Bootstrap

import financestatus
import caldav
import carddav
import keyring
import common

app = Flask(__name__)
app.config['BOOTSTRAP_SERVE_LOCAL'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SECRET_KEY'] = 'secret!'
Bootstrap(app)
socketio = SocketIO(app)

socketio.start_background_task(financestatus.fetch_background, socketio)
socketio.start_background_task(carddav.sync_background, socketio)

@socketio.on('message')
def handle_message(message):
  print('received message: ' + message)

@app.route("/")
def hello():
  socketio.send("Hello")
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

@app.route("/dkb")
def get_financestatus():
  return render_template("financestatus.html", accountStatus=financestatus.FinanceStatus().get_buffered())

@app.route("/dkb/<int:days>")
def get_financestatus_days(days):
  return render_template("financestatus.html", accountStatus=financestatus.FinanceStatus().get_unbuffered(days))


if __name__ == "__main__":
  while True:
    print("Starting server...")
    socketio.run(app, host="localhost", port=8080)
