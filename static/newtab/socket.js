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

    socket.on('connect', function() { console.log("socket connect"); });
    socket.on('connect_error', function(error) { console.log("socket connect_error. error="+error); });
    socket.on('connect_timeout', function(timeout) { console.log("socket connect_timeout. timeout="+timeout); });
    socket.on('error', function(error) { console.log("socket error. error="+error); });
    socket.on('disconnect', function(reason) { console.log("socket disconnect. reason="+reason); });
    socket.on('reconnect', function(attempt) { console.log("socket reconnect. attempt="+attempt); });
    socket.on('reconnect_attempt', function(attempt) { console.log('socket reconnect_attempt. attempt='+attempt); });
    socket.on('reconnecting', function(attempt) { console.log("socket reconnecting. attempt="+attempt); });
    socket.on('reconnect_error', function(error) { console.log('socket reconnect_error. error='+error); });
    socket.on('reconnect_failed', function() { console.log('socket reconnect_failed'); });
  }, 20*1000)

  console.log("Overriding console object");
  orig_log = console.log;
  orig_warn = console.warn;
  orig_error = console.error;
  var consoleDivAdd = function(msg) {
    var now = new Date();
    var twoDigit = function(nbr) {
      if (nbr<10) return '0'+nbr;
      else return ''+nbr;
    }
    DateString = '' + twoDigit(now.getDate()) + "." + twoDigit(now.getMonth()) + " " + twoDigit(now.getHours()) + ":" + twoDigit(now.getMinutes());
    $('#socket_info').append('<div />').html(DateString + ":" + msg);
    allChildren = $('#socket_info').children();
    for (var i=0; i<allChildren.length-10; ++i) allChildren[i].remove();
  };
  console.log   = function() { orig_log.apply(this, arguments);   consoleDivAdd('Log: '+  JSON.stringify(arguments)); };
  console.warn  = function() { orig_warn.apply(this, arguments);  consoleDivAdd('Warn: '+ JSON.stringify(arguments)); };
  console.error = function() { orig_error.apply(this, arguments); consoleDivAdd('Error: '+JSON.stringify(arguments)); };
});
