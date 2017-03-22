String.prototype.format = String.prototype.f = function() {
  var s = this, i = arguments.length;
  while (i--) s = s.replace(new RegExp('\\{' + i + '\\}', 'gm'), arguments[i]);
  return s;
};

$(document).ready( function () {
  var addressbookTable = $('#addressbook').DataTable({
    fixedHeader: { header: true, footer: true },
    columnDefs: [{ targets: [1,3,4], orderable: false}],
    dom: '<"#lengthParent"l><"#searchParent"f>iptr',
    lengthMenu: [ 10, 15, 20, 25, 50, 75, 100 ],
    pageLength: 15,
  });
  $('#lengthParent').detach().appendTo($('#lengthWrapper'));
  $('#searchParent').detach().appendTo($('#searchWrapper'));

  $('#bday').datepicker({changeMonth: true, changeYear: true, dateFormat: "dd. mm. yy", yearRange: "1900:2020"})
  $('input[type="search"]').focus();

  var lastClicked = 0;
  $('#addressbook tbody').on('click', 'tr', function(ev) {
    var tr = $(this);
    lastClicked = $(this).attr('data');
    $.get("/addressbook/vcard?itemid={0}".f(lastClicked), function(data) {
      $('#vcard').html(data).parent().show().offset({top: ev.pageY, left: ev.pageX});
    });
  });


  var showEditDialog = function() {
    // ugly hack but otherwise the birthday calendar is not able to pick the month/year
    var enforceModalFocusFn = $.fn.modal.Constructor.prototype.enforceFocus;
    $.fn.modal.Constructor.prototype.enforceFocus = function() {};
    $('#vcard_edit_parent').on('hidden.bs.modal', function() { $.fn.modal.Constructor.prototype.enforceFocus = enforceModalFocusFn; });
    $('#vcard_edit_parent').modal({backdrop: false})
  };
  var updateEditDialog = function(data) {
    adrData = data;
    selectCollection( adrData.itemid!="new" ? adrData.colid : $('#collections_parent li').attr('colid') );
    if (adrData.itemid != "new") $('#collections_parent .dropdown-toggle').attr('disabled', "disabled");
    else $('#collections_parent .dropdown-toggle').removeAttr('disabled');

    ['prefix','given','additional','family','suffix'].forEach(function(field, idx, arr) {
      $('#{0}'.f(field)).val(data.n[field])
    });
    $('#bday').datepicker("setDate", data.bday);
    fillAdrTypeCombo();
    selectAddress(0);
    fillPhoneMailTable();
  };

  var selectCollection = function(colId) {
    $('#collections_parent button').text($('#collections_parent li[colid="{0}"] a'.f(colId)).text());
    adrData.colid = colId;
  };
  $('#collections_parent li a').click(function(ev) { selectCollection($(this).closest('li').attr('colid')); });

  $('.add_contact_button').click(function(ev) {
    showEditDialog();
    updateEditDialog({fn: '', n: {given:'', family:'', prefix:'', additional:'', suffix:''}, email: [], tel: [], adr: [], bday: '', itemid: 'new', colid: ''});
  });

  $('#addressbook tbody').on('click', '.del_contact_button', function(ev) {
    ev.stopPropagation();
    var id = $(this).closest('tr').attr('data');
    $.ajax({
      url: "/addressbook/json?itemid={0}".f(id),
      type: "DELETE",
      success: function() {
        addressbookTable.row($('#addressbook tr[data="{0}"]'.f(id))).remove().draw();
      }
    });
  });

  $('#vcard_edit').click(function(ev) {
    showEditDialog()
    $.getJSON("/addressbook/json?itemid={0}".f(lastClicked), function(data) {
      updateEditDialog(data);
    });
  });

  var hideFullContactWindowTimeout = 0;
  $('#vcard_close').click(function(ev) {
    $('#vcard').parent().hide();
  });
  $('#vcard').parent().hover(function() { clearTimeout(hideFullContactWindowTimeout); }, function() {
    hideFullContactWindowTimeout = setTimeout(function() { $('#vcard').parent().hide(); }, 400);
  });

  // general section edit handling
  $('#generalDiv input').change(function(ev) {
    if (this.id == 'bday') adrData[this.id] = $(this).val();
    else adrData['n'][this.id] = $(this).val();
  });

  // Address handling
  var curAddressIdx = -1;
  var adrData = {}
  var selectAddress = function(idx) {
    idx = Number(idx);
    idx = (idx<adrData.adr.length) ? idx : adrData.adr.length ? 0 : -1; // if out of bound we select address 0, if there is an address at all
    curAddressIdx = idx;
    if (idx>=0) {
      $('input,.dropdown-toggle, #address_type_edit, #address_remove', $('#addressesDiv')).removeAttr('disabled');
      $('#address_type_text').text($('#addressesDiv .dropdown-menu li:nth-child({0}) a'.f(idx+1)).text());
      ['box','city','code','country','extended','region','street'].forEach(function(field,fieldIdx,fieldArr) {
        $('#{0}'.f(field)).val(adrData.adr[idx].value[field])
      });
    } else {
      $('#address_type_text').text("");
      $('input,.dropdown-toggle, #address_type_edit, #address_remove', $('#addressesDiv')).attr('disabled', 'disabled');
      $('#addressesDiv input').val("");
    }
  };

  var fillAdrTypeCombo = function() {
    $('#addressesDiv .dropdown-menu').empty();
    adrData.adr.forEach(function(adr, idx, arr) {
      $('#addressesDiv .dropdown-menu').append('<li><a adr_idx="{0}" href="#">{1} {2}</a></li>'.f(idx, adr.type.join(',')||"No type", adr.pref ? "[Preferred]" : ""));
    });
    $('#addressesDiv .dropdown-menu a').click(function(ev) {
      selectAddress($(this).attr('adr_idx'))
    });
  };

  $('#address_remove').click(function(ev) {
    adrData.adr.splice(curAddressIdx, 1);
    fillAdrTypeCombo();
    selectAddress(curAddressIdx);
  });
  $('#address_add').click(function(ev) {
    adrData.adr.push({type: ["home"], pref: false, value: {box:"", city:"", code:"", country:'', extended:'', region:'', street:''}});
    fillAdrTypeCombo();
    selectAddress(adrData.adr.length-1);
  });
  $('#address_type_edit').click(function(ev) {
    $('#adr_pref_cb').prop('checked', adrData.adr[curAddressIdx].pref);
    $('#adr_work_type_cb').prop('checked', adrData.adr[curAddressIdx].type.indexOf("work")>=0);
    $('#adr_home_type_cb').prop('checked', adrData.adr[curAddressIdx].type.indexOf("home")>=0);
    $('#adr_custom_type').val(adrData.adr[curAddressIdx].type.filter(function(e) { return (e != 'work' && e != 'home'); }).join(","));
  });
  $('#addressesDiv input.adr_field').change(function(ev) {
    adrData.adr[curAddressIdx].value[this.id] = $(this).val();
  });

  var updateAdrTypesTimeout = 0;
  $('#address_type_div').hover(function(ev) { clearTimeout(updateAdrTypesTimeout); }, function(ev) {
    updateAdrTypesTimeout = setTimeout(function() {
      adrData.adr[curAddressIdx].type = []
      adrData.adr[curAddressIdx].pref = $('#adr_pref_cb').prop('checked');
      if ($('#adr_work_type_cb').prop("checked")) adrData.adr[curAddressIdx].type.push('work');
      if ($('#adr_home_type_cb').prop("checked")) adrData.adr[curAddressIdx].type.push('home');
      if ($('#adr_custom_type').val()) adrData.adr[curAddressIdx].type = adrData.adr[curAddressIdx].type.concat($('#adr_custom_type').val().split(","));
      $('#address_type_div').collapse('hide');
      fillAdrTypeCombo();
      selectAddress(curAddressIdx);
    }, 400);
  });

  // email/phone handling
  var fillPhoneMailTable = function() {
    var tbody = $('#phoneEmailDiv tbody');
    tbody.empty();
    var tmpl = '<tr data-attr="{0}" data-row="{1}">\
                  <td class="types">{2}</td>\
                  <td><div class="input-group"><span class="input-group-addon">{3}</span><input type="text" class="form-control" value="{4}" /></div></td>\
                  <td><input type="radio" name="{0}" {5} /></input></td>\
                  <td><button type="button" class="btn btn-danger btn-xs" style="margin-left: 10px;" aria-label="Delete phone/mail"><span class="glyphicon glyphicon-remove"></span></button></td>\
                </tr>';
    ['tel','email'].forEach(function(attr) {
      adrData[attr].forEach(function(telEmail, idx) {
        tbody.append(tmpl.f(attr, idx, telEmail.type.join(","), attr=='tel'?'&#9742;':'@', telEmail.value, telEmail.pref?"checked":""));
      });
      tbody.append('<tr><td></td><td></td><td></td><td></td></tr>')
    });
    $('#phoneEmailDiv input[type="radio"]').change(function(ev) {
      adrData[$(this).closest('tr').attr('data-attr')].forEach(function(el) { el.pref = false; });
      adrData[$(this).closest('tr').attr('data-attr')][$(this).closest('tr').attr('data-row')].pref = true;
    });
    $('#phoneEmailDiv input[type="text"]').change(function(ev) {
      adrData[$(this).closest('tr').attr('data-attr')][$(this).closest('tr').attr('data-row')].value = $(this).val();
    });
    $('#phoneEmailDiv td button.btn-danger').click(function(ev) {
      adrData[$(this).closest('tr').attr('data-attr')].splice([$(this).closest('tr').attr('data-row')], 1);
      fillPhoneMailTable();
    });
    $('#phoneEmailDiv td.types').click(function(ev) {
      $('#phoneEmailDiv tr.typesRow').remove();
      var updateTelEmailTypesTimeout=0;
      var listOfTypes = $(this).closest('tr').attr('data-attr')=='tel' ? ['work','home','text','voice','fax','cell','video','pager','textphone'] : ['work','home'];
      var selectedTypes = adrData[$(this).closest('tr').attr('data-attr')][$(this).closest('tr').attr('data-row')].type;
      var userTypes = selectedTypes.filter(function(x) { return listOfTypes.indexOf(x)<0; });
      var cb = listOfTypes.map(function(x) { return '<label class="checkbox-inline"><input type="checkbox" value="{0}" {1}> {0}</label>'.f(x, selectedTypes.indexOf(x)>=0?"checked":""); }).join("");
      $('<tr style="display:none" class="typesRow"><td colspan="4"><form class="form-inline">{0}<div class="form-group" style="padding: 10px;"><label for="adr_custom_type">Custom </label><input type="text" class="form-control" placeholder="Custom types" size="20" value="{1}" /></div></td></tr>'.f(cb, userTypes.join(","))).insertAfter($(this).closest('tr')).hover(function() { clearTimeout(updateTelEmailTypesTimeout); }, function() {
        setTimeout(function() {
          var types = $('#phoneEmailDiv tr.typesRow input[type="checkbox"]:checked').map(function(idx, cb) { return $(cb).val(); });
          var row = $('#phoneEmailDiv tr.typesRow').prev();
          adrData[row.attr('data-attr')][row.attr('data-row')].type = $.makeArray(types).concat($('#phoneEmailDiv tr.typesRow input[type="text"]').val().split(',')).filter(function(x) { return x; });
          fillPhoneMailTable();
        }, 400);
      }).show(400);
    });
  };
  $('#telAdd,#emailAdd').click(function() {
    adrData[this.id=='telAdd'?'tel':'email'].push({pref: false, type: ['home'], value: ""});
    fillPhoneMailTable();
  });

  var updateContactInMainTable = function(contactInfo, tr) {
    tr = tr || $('#addressbook tr[data="{0}"]'.f(contactInfo.itemid))[0];
    tr.children[0].innerHTML = "{0} {1}".f(contactInfo.n.given, contactInfo.n.family);
    tr.children[1].innerHTML = contactInfo.email.map(function(x) { return x.value; }).join("<br />");
    tr.children[2].innerHTML = contactInfo.bday;
    tr.children[3].innerHTML = contactInfo.tel.map(function(x) { return x.value; }).join("<br />");
  }

  // save changes of edit dialog
  $('#edit_save').click(function(ev) {
    $.ajax({
      url: "/addressbook/json?itemid={0}&colid={1}".f(adrData.itemid, adrData.colid),
      data: JSON.stringify(adrData),
      contentType: "application/json",
      type: adrData.itemid == "new" ? "POST" : "PUT",
      success: function(contactInfo) {
        $('#vcard_edit_parent').modal('hide');
        var tr = undefined;
        if (adrData.itemid == "new") {
          tr = $('<tr><td></td><td></td><td></td><td></td><td><button type="button" class="btn btn-danger btn-xs del_contact_button" aria-label="Delete contact"><span class="glyphicon glyphicon-remove"></span></button></td></tr>');
          tr = tr.attr('data', contactInfo.itemid)[0];
        }
        updateContactInMainTable(contactInfo, tr);
        if (adrData.itemid == "new") {
          addressbookTable.row.add(tr).draw('full-reset');
        }
      }
    });
  });
});
