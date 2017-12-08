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

    socket.on('weather', function(data) {
      data.forEach(function(data) {
        var weatherData = JSON.parse(data.data);
        weatherData[0].rainfall = weatherData[0].rainfall.concat(weatherData[1].rainfall);
        weatherData[0].temperature = weatherData[0].temperature.concat(weatherData[1].temperature);
        updateWeather('weatherChart'+data.zip, weatherData[0]);
      });
    });
    socket.on('transferwise', function(data) {
      updateTransferwise(data.data);
    });
    socket.on('nettime', function(data) {
      updateNettime(data.data);
    });
  }, 60*1000)
})
