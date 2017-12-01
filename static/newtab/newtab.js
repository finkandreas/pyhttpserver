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
});


function buildWeather() {
  [{'ctx': 'weatherChart', 'data': meteoschweizData[0]}, {'ctx': 'weatherChartTomorrow', 'data': meteoschweizData[1]}, {'ctx': 'weatherChartEth', 'data': meteoschweizDataEth[0]}, {'ctx': 'weatherChartEthTomorrow', 'data': meteoschweizDataEth[1]}].forEach(function(dataSet) {
    var ctx = document.getElementById(dataSet.ctx).getContext('2d');
    timeHours = ['00:00', '01:00', '02:00', '03:00', '04:00', '05:00', '06:00', '07:00', '08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00', '21:00', '22:00', '23:00'];
    precipitationData = dataSet.data.rainfall.map(function(el, idx) { return {t: timeHours[idx], y: el[1]}; });
    temperatureData = dataSet.data.temperature.map(function(el, idx) { return {t: timeHours[idx], y: el[1]}; });
    tempMin = dataSet.data.temperature.reduce(function(min, el) { return el[1]<min?el[1]:min; }, dataSet.data.temperature[0][1]);
    tempMax = dataSet.data.temperature.reduce(function(max, el) { return el[1]>max?el[1]:max; }, dataSet.data.temperature[0][1]);
    console.log(tempMin, tempMax)
    var myChart = new Chart(ctx, {
      type: 'bar',
      data: {
        datasets: [{
          label: 'Temperature',
          data: temperatureData,
          borderColor: 'rgba(255, 0, 0, 1)',
          backgroundColor: 'rgba(0,0,0,0)',
          type: 'line',
          yAxisID: 'temperature-y-axis'
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
        scales: {
          yAxes: [{
            id: 'precipitation-y-axis',
            type: 'linear',
            position: 'right',
            ticks: {
              max: 6,
            },
            gridLines: {
              display: false
            }
          }, {
            id: 'temperature-y-axis',
            type: 'linear',
            ticks: {
              min: Math.floor(tempMin)-1,
              max: Math.ceil(tempMax)+1,
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
              parser: 'HH:mm',
              displayFormats: {
                hour: 'HH:mm'
              }
            },
            gridLines: {
              display: false
            }
          }]
        }
      }
    });
  })
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

  $.get('/nettime', function(data) {
    $('#nettime_status').html(' ('+data+')');
  });

  buildWeather();
}


function decodeWithSjcl(text, pw) {
  try {
    return sjcl.decrypt(pw, text);
  } catch (error) {
    console.error("Error: ", error);
    return "<html><head /><body /></html>";
  }
}
