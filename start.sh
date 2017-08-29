#!/bin/bash

export EVENTLET_THREADPOOL_SIZE=3
export FLASK_APP=$HOME/coding/pyhttpserver/flasktest.py
~/coding/pyhttpserver_env/bin/flask run -p 8080
