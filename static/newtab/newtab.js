$(function() {
  localStorage2 = localStorage || {};
  builtVersion = -1;
  if (localStorage2.data != undefined) {
    var jsonData = sjcl.json.decode(localStorage2.data);
    builtVersion = jsonData.version || -1;
    try {
      buildWebsite();
    } catch(err) {
      console.log("Error while building website: ", err);
    }
  }
  jQuery.support.cors = true;
  var urls = [
    'http://insecure.v22016112059440056.megasrv.de/bookmarks.php',
  ];
  for (var i=0; i<urls.length; ++i) {
     $.ajax({
      url: urls[i],
      dataType: 'json',
      success: function(data) {
        var jsonData = sjcl.json.decode(data.data);
        if (builtVersion < jsonData.version) {
          builtVersion = jsonData.version || -1;
          localStorage2.data = data.data;
          buildWebsite();
        }
      },
      error: function(data, text, error ) {
        console.log("Ajax error...", data);
      },
    });
    if (!localStorage2.pw) {
      $.get("/keyring?type=newtab", function(data) {
        localStorage2.pw = data;
        buildWebsite();
      });
    }
  };

  $('body').keypress(function(data) {
    if (data.charCode == 105 && data.ctrlKey) {
      $('#weatherParent').toggle();
      if ($('#weatherParent').is(':visible')) {
        $.get('/newtab/info', function(data) {
          updateFromInfo(data);
        });
      }
      data.preventDefault();
      data.stopPropagation();
    }
  });
});


function updateWeather(data) {
  window.charts = window.charts || {};
  data.forEach(function(data) {
    var weatherData = JSON.parse(data.data);
    var nowHour = Math.max(0, (new Date(weatherData[0].current_time)).getHours()-1);
    weatherData[0].rainfall.splice(0, nowHour);
    weatherData[2].rainfall.splice(nowHour, 24-nowHour)
    weatherData[0].temperature.splice(0, nowHour);
    weatherData[2].temperature.splice(nowHour, 24-nowHour)
    weatherData[0].rainfall = weatherData[0].rainfall.concat(weatherData[1].rainfall, weatherData[2].rainfall);
    weatherData[0].temperature = weatherData[0].temperature.concat(weatherData[1].temperature, weatherData[2].temperature);
    var ctxName = 'weatherChart'+data.zip;
    if (ctxName in window.charts) { window.charts[ctxName].destroy(); }
    var precipitationData = weatherData[0].rainfall.map(function(el, idx) { return {x: el[0], y: el[1]}; });
    var temperatureData = weatherData[0].temperature.map(function(el, idx) { return {x: el[0], y: el[1]}; });
    var tempMin = weatherData[0].temperature.reduce(function(min, el) { return el[1]<min?el[1]:min; }, weatherData[0].temperature[0][1]);
    var tempMax = weatherData[0].temperature.reduce(function(max, el) { return el[1]>max?el[1]:max; }, weatherData[0].temperature[0][1]);
    window.charts[ctxName] = new Chart(document.getElementById(ctxName).getContext('2d'), {
      type: 'bar',
      data: {
        datasets: [{
          label: 'Temperature',
          data: temperatureData,
          borderColor: 'rgba(255, 0, 0, 1)',
          backgroundColor: 'rgba(0,0,0,0)',
          type: 'line',
          yAxisID: 'temperature-y-axis',
        }, {
          label: 'Precipitation',
          data: precipitationData,
          backgroundColor: 'rgba(0, 255, 255, 0.5)',
          yAxisID: 'precipitation-y-axis'
        }],
      },
      options: {
        maintainAspectRatio: false,
        legend: {
          display: false
        },
        annotation: {
          annotations: [{
            type: "line",
            mode: "vertical",
            scaleID: "time-x-axis",
            value: weatherData[0].current_time,
            borderColor: "black",
            label: {
              content: weatherData[0].current_time_string,
              enabled: true,
              position: "top"
            }
          }]
        },
        scales: {
          yAxes: [{
            id: 'precipitation-y-axis',
            type: 'linear',
            position: 'right',
            ticks: {
              max: 6,
              fontColor: 'rgba(0,255,255,1)',
            },
            gridLines: {
              display: false
            }
          }, {
            id: 'temperature-y-axis',
            type: 'linear',
            ticks: {
              min: Math.ceil(tempMin)-1,
              max: Math.floor(tempMax)+1,
              fontColor: 'rgba(255,0,0,1)',
              callback: function(value, index, values) { return Math.floor(value)==value ? value : null; },
            },
            gridLines: {
              display: true
            }
          }],
          xAxes: [{
            id: 'time-x-axis',
            type: 'time',
            position: 'bottom',
            time: {
              unit: 'hour',
              //~ parser: 'HH:mm',
              parser: 'x',
              displayFormats: {
                hour: 'HH:mm'
              },
              tooltipFormat: 'HH:mm',
            },
            gridLines: {
              display: false
            }
          }]
        }
      }
    });
  });
}


function updateTransferwise(newValue) {
  $('#transferwise_status').html(' ('+newValue+')');
}


function updateNettime(newValue) {
  $('#nettime_status').html(' ('+newValue+')');
}


function updateTransferrateHistory() {
  var nbrOfReceivedData=0;
  var history = {};
  var ctxName = 'weatherChart895300';
  var updateChart = function(dataName, data) {
    data = data.replace(/[\[()\] ]/g, '').split(",")
    var plotData = new Array(data.length/2);
    for (var i=0; i<data.length/2; ++i) plotData[i] = {x:Number(data[2*i]+'000'), y:Number(data[2*i+1])};
    nbrOfReceivedData += 1;
    history[dataName] = plotData;
    window.charts[ctxName].destroy();
    if (nbrOfReceivedData==3) {
      window.charts[ctxName] = new Chart(document.getElementById(ctxName).getContext('2d'), {
        type: 'line',
        data: {
          datasets: [{
            label: 'transferwise',
            data: history['transferwise'],
            borderColor: 'rgba(255, 0, 0, 1)',
            backgroundColor: 'rgba(0,0,0,0)',
          }, {
            label: 'currencyfair',
            data: history['currencyfair'],
            borderColor: 'rgba(0, 255, 0, 1)',
            backgroundColor: 'rgba(0,0,0,0)',
          }, {
            label: 'xendpay',
            data: history['xendpay'],
            borderColor: 'rgba(0, 0, 255, 1)',
            backgroundColor: 'rgba(0,0,0,0)',
          }],
        },
        options: {
          maintainAspectRatio: false,
          legend: {
            display: true
          },
          scales: {
            xAxes: [{
              id: 'time-x-axis',
              type: 'time',
              position: 'bottom',
              time: {
                unit: 'hour',
                parser: 'x',
                displayFormats: {
                  hour: 'HH:mm'
                },
                tooltipFormat: 'HH:mm',
              },
              gridLines: {
                display: false
              }
            }]
          }
        }
      });
    }
  };
  $.get('/kvs?key=transferwise.history', function(data) {updateChart('transferwise', data);});
  $.get('/kvs?key=currencyfair.history', function(data) {updateChart('currencyfair', data);});
  $.get('/kvs?key=xendpay.history', function(data) {updateChart('xendpay', data);});
}

function updateFromInfo(data) {
  updateNettime(data.nettime)
  updateTransferwise(data.transferwise);
  updateWeather(data.meteoschweiz)
}


function buildWebsite() {
  data = localStorage2.data;
  pw = localStorage2.pw;
  if (!data || !pw) return;
  document.dynamicNodes = document.dynamicNodes || jQuery();
  document.dynamicNodes.remove();
  document.dynamicNodes = jQuery();
  var bookmarksDOM = new DOMParser().parseFromString(decodeWithSjcl(data, pw), "text/xml");
  var bookmarksHeadChildren = document.importNode(bookmarksDOM.getElementsByTagName('head')[0], true);
  var bookmarksHeadChildren = bookmarksHeadChildren.childNodes;
  for (var i=0; i<bookmarksHeadChildren.length; ++i) {
    var newNode = bookmarksHeadChildren[i].cloneNode(true);
    document.head.appendChild(newNode);
    document.dynamicNodes = document.dynamicNodes.add(newNode);
  }
  var bookmarksBodyChildren = document.importNode(bookmarksDOM.getElementsByTagName('body')[0], true);
  var bookmarksBodyChildren = bookmarksBodyChildren.childNodes;
  for (var i=0; i<bookmarksBodyChildren.length; ++i) {
    var newNode = bookmarksBodyChildren[i].cloneNode(true);
    document.body.appendChild(newNode);
    document.dynamicNodes = document.dynamicNodes.add(newNode);
  }

  setInterval(function() {
    $('#Time').html(new Date().toString());
  }, 1000);

  $('#notifications').click(function() {
    $(this).hide();
  }).hide();

  var timeoutId = 0;
  $('#financestatus').hover(function(ev) {
    timeoutId = setTimeout(function() {
      $('<div id="financestatus_div" style="position: absolute; width: 1200px; height: 800px"><iframe src="/dkb" style="width: 100%; height: 100%" /></div>').offset({top: 0, left: ev.pageX}).appendTo($('body'));
    }, 500);
  }, function() {
    clearTimeout(timeoutId);
    $('#financestatus_div').hover(function() {
      clearTimeout(timeoutId);
    }, function() {
      timeoutId = setTimeout(function() { $('#financestatus_div').remove(); }, 200);
    })
    timeoutId = setTimeout(function() { $('#financestatus_div').remove(); }, 200);
  });

  $('#transferwise_status').hover(function(ev) { timeoutId = setTimeout(updateTransferrateHistory, 500); }, function() { clearTimeout(timeoutId); });

  if (typeof startupData !== "undefined") {
    $('#weatherParent').show();
    updateFromInfo(startupData);
  }
}


function decodeWithSjcl(text, pw) {
  try {
    return sjcl.decrypt(pw, text);
  } catch (error) {
    console.error("Error: ", error);
    return "<html><head /><body /></html>";
  }
}
