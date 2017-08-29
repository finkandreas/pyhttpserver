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
}


function decodeWithSjcl(text, pw) {
  try {
    return sjcl.decrypt(pw, text);
  } catch (error) {
    console.error("Error: ", error);
    return "<html><head /><body /></html>";
  }
}

function gotoMam(where, host) {
  if( where=="admin" ) {
    if (parent) parent.location = "http://"+host+":12400/MediaArchiveAdminSuite/login.aspx";
    else window.location = "http://"+host+":12400/MediaArchiveAdminSuite/login.aspx";
  } else if( where=="wsm" ) {
    if (parent) parent.location = "http://"+host+":12500/LoginServiceWS/Start.aspx";
    else window.location = "http://"+host+":12500/LoginServiceWS/Start.aspx";
  } else if( where=="naming" ) {
    if (parent) parent.location = "http://"+host+":12401/ConfigurationServiceWSAdmin/manageNaming/ManageNamingEntries.aspx";
    else window.location = "http://"+host+":12401/ConfigurationServiceWSAdmin/manageNaming/ManageNamingEntries.aspx";
  }
}
