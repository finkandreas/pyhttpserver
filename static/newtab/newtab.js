'use strict';

document.addEventListener("DOMContentLoaded", function() {
  let localStorage2 = localStorage || {};
  let builtVersion = -1;
  if (localStorage2.data != undefined) {
    let jsonData = sjcl.json.decode(localStorage2.data);
    builtVersion = jsonData.version || -1;
    try {
      buildWebsite(localStorage2.data, localStorage2.pw);
    } catch(err) {
      console.log("Error while building website: ", err);
    }
  }
  jQuery.support.cors = true;
  const urls = [
    'http://insecure.vserverli.de/bookmarks.php',
  ];
  for (let i=0; i<urls.length; ++i) {
     $.ajax({
      url: urls[i],
      dataType: 'json',
      success: function(data) {
        const jsonData = sjcl.json.decode(data.data);
        if (builtVersion < jsonData.version) {
          builtVersion = jsonData.version || -1;
          localStorage2.data = data.data;
          buildWebsite(localStorage2.data, localStorage2.pw);
        }
      },
      error: function(data, text, error ) {
        console.log("Ajax error...", data);
      },
    });
    if (!localStorage2.pw) {
      $.get("/keyring?type=newtab", function(data) {
        localStorage2.pw = data;
        buildWebsite(localStorage2.data, localStorage2.pw);
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

  let updatePingStatus = function() {
    $.get('http://insecure.vserverli.de/ping_status.php', function(data) {
      $('#ping_status').empty();
      data.forEach(function(element) {
        let nowTimestamp = Math.floor(Date.now() / 1000);
        let currentlyUp = nowTimestamp-element.timestamp < 600 ? "green" : "red";
        $('#ping_status').append(`<div class="tooltip" style="background: ${currentlyUp}; width: 20px; height: 20px; display: inline-block; border-radius: 10px;"><span class="tooltiptext">${element.hostname} ${element.ip_lan} ${element.ip_wan}</span></div>`);
      });
    });
  }
  setInterval(updatePingStatus, 60*5*1000);
  setTimeout(updatePingStatus, 1000);
});


function updateWeather(data) {
  window.charts = window.charts || {};

  let tempMinGlobal = 100;
  let tempMaxGlobal = -100;
  let rainMaxGlobal = 6;
  let time;
  let timeString;
  const weatherDataAll = {}

  data.forEach(function(data) {
    const weatherData = data.data;
    const nowHour = Math.max(0, (new Date(weatherData[0].current_time)).getHours()-1);
    weatherData[0].rainfall.splice(0, nowHour);
    weatherData[2].rainfall.splice(nowHour, 24-nowHour)
    weatherData[0].temperature.splice(0, nowHour);
    weatherData[2].temperature.splice(nowHour, 24-nowHour)
    weatherData[0].rainfall = weatherData[0].rainfall.concat(weatherData[1].rainfall, weatherData[2].rainfall);
    weatherData[0].temperature = weatherData[0].temperature.concat(weatherData[1].temperature, weatherData[2].temperature);
    const precipitationData = weatherData[0].rainfall.map(function(el, idx) { return {x: el[0], y: el[1]}; });
    const temperatureData = weatherData[0].temperature.map(function(el, idx) { return {x: el[0], y: el[1]}; });
    const tempMin = weatherData[0].temperature.reduce(function(min, el) { return el[1]<min?el[1]:min; }, weatherData[0].temperature[0][1]);
    const tempMax = weatherData[0].temperature.reduce(function(max, el) { return el[1]>max?el[1]:max; }, weatherData[0].temperature[0][1]);
    const rainMax = weatherData[0].rainfall.reduce(function(max, el) { return el[1]>max?el[1]:max; }, weatherData[0].rainfall[0][1]);

    time = weatherData[0].current_time;
    timeString = weatherData[0].current_time_string;
    tempMinGlobal = Math.min(tempMinGlobal, tempMin);
    tempMaxGlobal = Math.max(tempMaxGlobal, tempMax);
    rainMaxGlobal = Math.max(rainMaxGlobal, Math.ceil(rainMax));
    weatherDataAll[data.zip] = { temperature : temperatureData, precipitation: precipitationData };
  });

  const ctxName = 'weatherChart895300';
  if (ctxName in window.charts) { window.charts[ctxName].destroy(); }
  window.charts[ctxName] = new Chart(document.getElementById(ctxName).getContext('2d'), {
    type: 'bar',
    data: {
      datasets: [{
        label: 'Temperature 8953',
        data: weatherDataAll['895300'].temperature,
        borderColor: 'rgba(255, 0, 0, 1)',
        backgroundColor: 'rgba(0,0,0,0)',
        type: 'line',
        yAxisID: 'temperature-y-axis',
      }, {
        label: 'Temperature 8049',
        data: weatherDataAll['804900'].temperature,
        borderColor: 'rgba(0, 255, 0, 1)',
        backgroundColor: 'rgba(0,0,0,0)',
        type: 'line',
        yAxisID: 'temperature-y-axis',
      }, {
        label: 'Precipitation 8953',
        data: weatherDataAll['895300'].precipitation,
        backgroundColor: 'rgba(0, 255, 255, 0.5)',
        yAxisID: 'precipitation-y-axis'
      }, {
        label: 'Precipitation 8049',
        data: weatherDataAll['804900'].precipitation,
        backgroundColor: 'rgba(0, 0, 255, 0.5)',
        yAxisID: 'precipitation-y-axis'
      }],
    },
    options: {
      maintainAspectRatio: false,
      //~ legend: {
        //~ display: false
      //~ },
      annotation: {
        annotations: [{
          type: "line",
          mode: "vertical",
          scaleID: "time-x-axis",
          value: time,
          borderColor: "black",
          label: {
            content: timeString,
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
            max: rainMaxGlobal,
            fontColor: 'rgba(0,255,255,1)',
          },
          gridLines: {
            display: false
          }
        }, {
          id: 'temperature-y-axis',
          type: 'linear',
          ticks: {
            min: Math.ceil(tempMinGlobal)-1,
            max: Math.floor(tempMaxGlobal)+1,
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
}


function updateTransferwise(newValue) {
  $('#transferwise_status').html(` (${newValue})`);
}


function updateNettime(newValue) {
  $('#nettime_status').html(` (${newValue})`);
}


function updateTransferrateHistory() {
  let nbrOfReceivedData=0;
  const history = {};
  const ctxName = 'weatherChart895300';
  const updateChart = function(dataName, data) {
    data = data.replace(/[\[()\] ]/g, '').split(",")
    const plotData = new Array(data.length/2);
    for (let i=0; i<data.length/2; ++i) plotData[i] = {x:Number(data[2*i]+'000'), y:Number(data[2*i+1])};
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
          }, {
            label: 'currencyfair',
            data: history['currencyfair'],
            borderColor: 'rgba(0, 255, 0, 1)',
          }, {
            label: 'xendpay',
            data: history['xendpay'],
            borderColor: 'rgba(0, 0, 255, 1)',
          }],
        },
        options: {
          elements: {
            point: {
              radius: 0,
            },
            line: {
              tension: 0, // disables bezier curves
              backgroundColor: 'rgba(0,0,0,0)',
            }
          },
          maintainAspectRatio: false,
          legend: {
            display: true
          },
          scales: {
            xAxes: [{
              id: 'time-x-axis',
              type: 'time',
              position: 'bottom',
              bounds: 'ticks',
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


function buildWebsite(data, pw) {
  if (!data || !pw) return;
  document.dynamicNodes = document.dynamicNodes || jQuery();
  document.dynamicNodes.remove();
  document.dynamicNodes = jQuery();
  const bookmarksDOM = new DOMParser().parseFromString(decodeWithSjcl(data, pw), "text/xml");
  let bookmarksHeadChildren = document.importNode(bookmarksDOM.getElementsByTagName('head')[0], true);
  bookmarksHeadChildren = bookmarksHeadChildren.childNodes;
  for (let i=0; i<bookmarksHeadChildren.length; ++i) {
    const newNode = bookmarksHeadChildren[i].cloneNode(true);
    document.head.appendChild(newNode);
    document.dynamicNodes = document.dynamicNodes.add(newNode);
  }
  let bookmarksBodyChildren = document.importNode(bookmarksDOM.getElementsByTagName('body')[0], true);
  bookmarksBodyChildren = bookmarksBodyChildren.childNodes;
  for (let i=0; i<bookmarksBodyChildren.length; ++i) {
    let newNode = bookmarksBodyChildren[i].cloneNode(true);
    document.body.appendChild(newNode);
    document.dynamicNodes = document.dynamicNodes.add(newNode);
  }

  setInterval(function() {
    $('#Time').html(new Date().toString());
  }, 1000);

  $('#notifications').click(function() {
    $(this).hide();
  }).hide();

  let timeoutId = 0;
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

  $('#transferwise_status').hover((ev) => timeoutId = setTimeout(updateTransferrateHistory, 500), () => clearTimeout(timeoutId));

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
