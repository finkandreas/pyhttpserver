#!/bin/bash

set -e
set -x

export VENV=~/coding/pyhttpserver_env

python3 -m venv $VENV
$VENV/bin/pip install --upgrade pip
$VENV/bin/pip install pyramid requests lxml cssselect dbus-python flask flask-socketio flask-bootstrap eventlet vdirsyncer pydal pyxdg vobject exchangelib

FROM=$(python3 -c "import gi; import os; print(os.path.dirname(gi.__file__))")
TO=$($VENV/bin/python3 -c "import os; import cssselect; print(os.path.dirname(os.path.dirname(cssselect.__file__)))")
ln -s "$FROM" "$TO"
