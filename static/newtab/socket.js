$(function() {
  // connect to the websocket only 60 seconds after opening, thus stopping to connect for shortly opened new tabs
  setTimeout(function() {
    var socket = io.connect('http://' + document.domain + ':' + document.location.port)
    // var socket = io.connect('http://' + document.domain + ':' + document.location.port + '/NAMESPACE')

    // events sent with socketio.send(...) will all be matched with this event handler
    socket.on('message', function(data) {
      $('#notifications').html(data).show()
      console.log("Received an unnamed event with data ", data);
    })

    // events sent with socketio.send(...json=True) will all be matched with this event handler
    socket.on('json', function(data) {
      console.log("Received an unnamed event with data ", data);
    })

    // events sent with socketio.emit(...) will have an event name
    socket.on('some event name', function(data) {
      console.log("Received 'some event name' event", data);
    })
  }, 60*1000)
})
