String.prototype.format = String.prototype.f = function() {
  var s = this, i = arguments.length;
  while (i--) s = s.replace(new RegExp('\\{' + i + '\\}', 'gm'), arguments[i]);
  return s;
};

$(function() {
  var accountTmpl = '\
    <div class="panel panel-default">\
      <div class="panel-heading" role="tab" id="server-heading-{0}">\
        <h4 class="panel-title">\
          <a role="button" data-toggle="collapse" data-parent="#accounts_accordion" href="#server-collapse-{0}" aria-expanded="true" aria-controls="server-collapse-{0}">\
            {1}\
          </a>\
          <button type="button" class="btn btn-danger btn-xs delete_server" style="float: right"><span class="glyphicon glyphicon-remove"></span></button>\
        </h4>\
      </div>\
      <div id="server-collapse-{0}" class="panel-collapse collapse {2}" role="tabpanel" aria-labelledby="server-heading-{0}">\
        <div class="panel-body">\
          <form class="form-horizontal">\
            <div class="form-group">\
              <label for="name-{0}" class="col-sm-2 control-label">Name</label>\
              <div class="col-sm-10">\
                <input type="text" class="form-control" name="name" placeholder="Name" value="{1}" />\
              </div>\
            </div>\
            <div class="form-group">\
              <label for="url-{0}" class="col-sm-2 control-label">URL</label>\
              <div class="col-sm-10">\
                <input type="text" class="form-control" name="url" placeholder="URL" value="{3}" />\
              </div>\
            </div>\
            <div class="form-group">\
              <label for="username-{0}" class="col-sm-2 control-label">Username</label>\
              <div class="col-sm-10">\
                <input type="text" class="form-control" name="username" placeholder="Username" value="{4}" />\
              </div>\
            </div>\
            <div class="form-group">\
              <label for="password-{0}" class="col-sm-2 control-label">Password</label>\
              <div class="col-sm-10">\
                <input type="password" class="form-control" name="password" placeholder="Password" value="{5}" />\
              </div>\
            </div>\
          </form>\
          <div class="subscribed_collections">\
          </div>\
        </div>\
      </div>\
    </div>' //.format(idx, name, showClass={'in', ''}, url, username, password)

  var collectConfig = function() {
    var servers = $('#accounts_accordion .panel-collapse').map(function(idx, el) {
      var ret = {};
      ['name', 'url', 'username', 'password'].forEach(function(field, idx, arr) { ret[field] = $('input[name="{0}"]'.f(field), el).val(); });
      ret['carddav_collections'] = $.makeArray($('.subscribed_collections .carddav input[type="checkbox"]', el).map(function(idx, el) { return {url: $(el).val(), subscribed: $(el).prop("checked")}; }));
      ret['caldav_collections'] = $.makeArray($('.subscribed_collections .caldav input[type="checkbox"]', el).map(function(idx, el) { return {url: $(el).val(), subscribed: $(el).prop("checked")}; }));
      return ret;
    });
    console.log("Sending: ", servers);
    return {servers: $.makeArray(servers)};
  };

  var serverIdx = 0;

  $('#accounts_accordion').on('change', 'input[name="name"]', function(ev) { $('h4 a', $(this).closest('.panel-default')).text($(this).val()); });
  $('#accounts_accordion').on('click', '.delete_server', function(ev) {
    $(this).closest('.panel-default').remove();
    if ($('#accounts_accordion .panel-collapse.in').length==0) $('#accounts_accordion .panel-collapse').first().addClass('in');
  });
  $('#accounts_accordion').on('change', 'input', function(ev) { syncCollectionsAndUpdate($(this).closest('.panel-default')); });

  $('#add_server_button').click(function(ev) {
    $('#accounts_accordion').append(accountTmpl.f(serverIdx, "Unnamed", $('#accounts_accordion>div').length?'':'in', "", "", ""));
    $('#accounts_accordion .panel-collapse').removeClass("in").last().addClass('in');
    serverIdx += 1;
  });

  $('#save_server_config_button').click(function(ev) {
    $('#save_server_config_button').attr("disabled", "disabled");
    $.ajax({
      url: "/dav",
      data: JSON.stringify(collectConfig()),
      contentType: "application/json",
      type: "POST",
      success: function(data) {
        window.location.reload();
      }
    });
  });

  collectedCollections = {};
  var syncCollectionsAndUpdate = function(panel) {
    if (collectedCollections[$('.panel-heading', panel)[0].id]) return;
    url = $('input[name="url"]', panel).val();
    username = $('input[name="username"]', panel).val();
    password = $('input[name="password"]', panel).val();
    if (url && username) {
      if (!password) {
        $('.subscribed_collections', panel).empty().append("<p>Fetching password. Please wait...</p>");
        $.get("/keyring", {'dav-url': url, 'dav-user': username}, function(pw) { $('input[name="password"]', panel).val(pw).change(); });
      } else {
        $('.subscribed_collections', panel).empty().append("<p>Fetching available collections. Please wait...</p>");
        $.getJSON('/dav/collections', {url: url, user: username, pass: password}).done(function(data, textStatus, jqXHR) {
          $('.subscribed_collections', panel).empty();
          carddavs = data.carddav.map(function(el) {return '<div class="checkbox"><label><input type="checkbox" {1} value="{2}" /> {0}</label></div>'.f(el.name, el.subscribed?"checked":"", el.url); }).join("");
          caldavs = data.caldav.map(function(el) {return '<div class="checkbox"><label><input type="checkbox" {1} value="{2}" /> {0}</label></div>'.f(el.name, el.subscribed?"checked":"", el.url); }).join("");;
          $('.subscribed_collections', panel).empty().append(
           '<div class="row">\
              <div class="col-xs-6">\
                <div >CardDAV collections</div>\
                <div class="well"><form class="carddav">{0}</form></div>\
              </div>\
              <div class="col-xs-6">\
                <div>CalDAV collections</div>\
                <div class="well"><form class="caldav">{1}</form></div>\
              </div>\
            </div>'.f(carddavs, caldavs)
          );
          collectedCollections[$('.panel-heading', panel)[0].id] = true;
        }).fail(function(jqXHR, textStatus, errorThrown) {
          $('.subscribed_collections', panel).empty().append('<p class="text-danger">Could not get any collections. Thrown error = {0}</p>'.f(errorThrown));
        });
      }
    }
  };

  // configData is being passed via template and is magically here ;)
  configData.servers.forEach(function(server, idx, arr) {
    $('#accounts_accordion').append(accountTmpl.f(serverIdx, server.name, serverIdx==0?'in':'', server.url, server.username, server.password));
    syncCollectionsAndUpdate($('#accounts_accordion>div:last-child'));
    serverIdx += 1;
  });
});
