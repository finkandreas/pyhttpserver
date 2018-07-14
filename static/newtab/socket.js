'use strict';

document.addEventListener("DOMContentLoaded", function() {
  // connect to the websocket only 60 seconds after opening, thus stopping to connect for shortly opened new tabs
  setTimeout(() => {
    let socket = io(`http://${document.domain}:${document.location.port}`, {transports: ['websocket']})

    // events sent with socketio.send(...) will all be matched with this event handler
    socket.on('message', data => $('#notifications').html(data).show())

    // events sent with socketio.send(...json=True) will all be matched with this event handler
    socket.on('json', data => console.log("Received an unnamed event with data ", data));

    // events sent with socketio.emit(...) will have an event name
    socket.on('some event name', data => console.log("Received 'some event name' event", data));

    socket.on('weather', data => updateWeather(data));
    socket.on('transferwise', data => updateTransferwise(data.data));
    socket.on('nettime', data => updateNettime(data.data));
    socket.on('ping', data => $('#ping').html(`Last websocket ping: ${new Date().toString()}`));

    socket.on('connect', () => console.log("socket connect"));
    socket.on('connect_error', error => console.error(`socket connect_error. error=${error}`));
    socket.on('connect_timeout', timeout => console.warn(`socket connect_timeout. timeout=${timeout}`));
    socket.on('error', error => console.error(`socket error. error=${error}`));
    socket.on('disconnect', reason => console.warn(`socket disconnect. reason=${reason}`));
    socket.on('reconnect', attempt => console.log(`socket reconnect. attempt=${attempt}`));
    socket.on('reconnect_attempt', attempt => console.log(`socket reconnect_attempt. attempt=${attempt}`));
    socket.on('reconnecting', attempt => console.log(`socket reconnecting. attempt=${attempt}`));
    socket.on('reconnect_error', error => console.error(`socket reconnect_error. error=${error}`));
    socket.on('reconnect_failed', () => console.error('socket reconnect_failed'));
  }, 20*1000)

  console.log("Overriding console object");
  const orig_log = console.log;
  const orig_warn = console.warn;
  const orig_error = console.error;
  const consoleDivAdd = (msg, color="black") => {
    let now = new Date();
    let twoDigit = nbr => (nbr<10) ? '0'+nbr : ''+nbr;
    const DateString = `${twoDigit(now.getDate())}.${twoDigit(now.getMonth())}.${twoDigit(now.getHours())}:${twoDigit(now.getMinutes())}`;
    $(`<div style="color: ${color}; max-height: 2em; overflow-y: auto;" />`)
      .html(`${DateString}: ${msg}`)
      .prependTo($('#socket_info'))
      .click(e=> $(e.target).remove());
    const allChildren = $('#socket_info').children();
    for (let i=10; i<allChildren.length; ++i) allChildren[i].remove();
  };
  const argsToString = (...args) => {
    let ret = ''
    for (let i=0; i<args.length; ++i) {
      if (i>0) ret += ", ";
      if (typeof({})==typeof(args[i]) || typeof([])==typeof(args[i])) ret += JSON.stringify(args[i]);
      else ret += args[i];
    }
    return ret;
  };
  console.log   = (...args) => { orig_log.apply(this, args);   consoleDivAdd('Log: '+  argsToString.apply(this, args)); };
  console.warn  = (...args) => { orig_warn.apply(this, args);  consoleDivAdd('Warn: '+ argsToString.apply(this, args), "blue"); };
  console.error = (...args) => { orig_error.apply(this, args); consoleDivAdd('Error: '+argsToString.apply(this, args), "red"); };
});
