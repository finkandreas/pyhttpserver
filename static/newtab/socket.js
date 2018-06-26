$(function() {
  // connect to the websocket only 60 seconds after opening, thus stopping to connect for shortly opened new tabs
  setTimeout(function() {
    var socket = io('http://' + document.domain + ':' + document.location.port, {transports: ['websocket']})
    // var socket = io.connect('http://' + document.domain + ':' + document.location.port + '/NAMESPACE')

    // events sent with socketio.send(...) will all be matched with this event handler
    socket.on('message', function(data) {
      $('#notifications').html(data).show()
    });

    // events sent with socketio.send(...json=True) will all be matched with this event handler
    socket.on('json', function(data) {
      console.log("Received an unnamed event with data ", data);
    });

    // events sent with socketio.emit(...) will have an event name
    socket.on('some event name', function(data) {
      console.log("Received 'some event name' event", data);
    });

    socket.on('weather', function(data) {
      updateWeather(data);
    });
    socket.on('transferwise', function(data) {
      updateTransferwise(data.data);
    });
    socket.on('nettime', function(data) {
      updateNettime(data.data);
    });
    socket.on('ping', function(data) {
      $('#ping').html("Last websocket ping: " + new Date().toString());
    });

    socket.on('connect', function() { $('#socket_info').append('<div>connect at ' + new Date().toString() + "</div>"); });
    socket.on('connect_error', function(error) { $('#socket_info').append('<div>connect_error at ' + new Date().toString() + " error=" + error + "</div>"); });
    socket.on('connect_timeout', function(timeout) { $('#socket_info').append('<div>connect_timeout at ' + new Date().toString() + " timeout=" + timeout + "</div>"); });
    socket.on('error', function(error) { $('#socket_info').append('<div>error at ' + new Date().toString() + " error=" + error + "</div>"); });
    socket.on('disconnect', function(reason) { $('#socket_info').append('<div>disconnect at ' + new Date().toString() + " reason=" + reason + "</div>"); });
    socket.on('reconnect', function(attempt) { $('#socket_info').append('<div>reconnect at ' + new Date().toString() + " attempt=" + attempt + "</div>"); });
    socket.on('reconnect_attempt', function(attempt) { $('#socket_info').append('<div>reconnect_attempt at ' + new Date().toString() + " attempt=" + attempt + "</div>"); });
    socket.on('reconnecting', function(attempt) { $('#socket_info').append('<div>reconnecting at ' + new Date().toString() + " attempt=" + attempt + "</div>"); });
    socket.on('reconnect_error', function(error) { $('#socket_info').append('<div>reconnect_error at ' + new Date().toString() + " error=" + error + "</div>"); });
    socket.on('reconnect_failed', function() { $('#socket_info').append('<div>reconnect_failed at ' + new Date().toString() + "</div>"); });
  }, 20*1000)

  console.log("Overriding console object");
  orig_log = console.log;
  orig_warn = console.warn;
  orig_error = console.error;
  console.log   = function() { orig_log.apply(this, arguments);   $('#socket_info').append('<div>Log: '+  JSON.stringify(arguments)+'</div>'); };
  console.warn  = function() { orig_warn.apply(this, arguments);  $('#socket_info').append('<div>Warn: '+ JSON.stringify(arguments)+'</div>'); };
  console.error = function() { orig_error.apply(this, arguments); $('#socket_info').append('<div>Error: '+JSON.stringify(arguments)+'</div>'); };
});
