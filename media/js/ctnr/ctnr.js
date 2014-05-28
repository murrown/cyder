$(document).ready(function() {
    var ctnr = $('#ctnr-data');
    var title = $('#title').text().split(' ');
    var ctnr_name = title[title.length - 1].trim();
    var searchUrl = null;
    var addObjectUrl = ctnr.attr('data-addObjectUrl');
    var ctnrPk = ctnr.attr('data-ctnr-pk');
    var objPk = null;
    var objName = null;
    var objType = null;
    var confirmation = false;
    var csrfToken = $('#view-metadata').attr('data-csrfToken');

    $('.minus, .plus, .remove.user, .remove.object').click(function(e) {
        e.preventDefault();
        var url = $(this).attr('href');
        var lvl;
        var detailUrl = $(this).parent().parent().find('a:first').attr('href');
        var pk = detailUrl.split('/').slice(-2)[0];
        var obj_type = detailUrl.split('/').slice(2)[0];
        var action = 'user_level';
        var acknowledge = true;
        if ($(this).attr('class') == 'minus') {
            lvl = -1;
        } else if ($(this).attr('class') == 'plus') {
            lvl = 1;
        } else {
            action = 'obj_remove';
            if (obj_type == 'user') {
                name = $(this).parent().parent().find('.username_column').text().trim();
            } else {
                name = $(this).parent().parent().find('.name_column').text().trim();
            }
            if (name) {
                acknowledge = confirm("Are you sure you want to remove " +
                    obj_type + ", " + name + ", from " + ctnr_name + "?");
            } else {
                acknowledge = confirm("Are you sure you want to remove this " +
                    obj_type + " from " + ctnr_name + "?");
            }
        }

        if (acknowledge) {
            postData = {
                obj_type: obj_type,
                pk: pk,
                lvl: lvl,
                action: action,
                csrfmiddlewaretoken: csrfToken,
            };

            $.post(url, postData, function(data) {
                if (data.error) {
                    if ($('.container.message').find('.messages').length) {
                        $('.container.message').find('.messages').remove();
                    }
                    $('.container.message').append(
                        '<ul class="messages"><li class="error">' +
                        data.error + '</li></ul>');
                } else {
                    location.reload();
                }
            }, 'json' );
        }
        return false;
    });
    jQuery.each( $("input[name='obj_type']:checked"), function() {
        if ( this.value == 'user' ) {
            $('#add-user-form').slideDown();
        } else {
            $('#add-user-form').slideUp();
        }
        objType = this.value;
        searchUrl = ctnr.attr(('data-search' + this.value + 'Url'));
        $('label[for="object-searchbox"]').text(this.value + '*:');
        search(searchUrl);

    });

    $("input[name='obj_type']").change( function() {
        if ( this.value == 'user' ) {
            $('#add-user-form').slideDown();
        } else {
            $('#add-user-form').slideUp();
        }
        objType = this.value;
        searchUrl = ctnr.attr(('data-search' + this.value + 'Url'));
        $('label[for="object-searchbox"]').text(this.value + '*:');
        search(searchUrl);
    });

    // Auto complete for object search dialog.
    function search(searchUrl) {
        $('#object-searchbox').autocomplete({
            minLength: 1,
            source: searchUrl,
            delay: 400,
            select: function(event, ui) {
                objPk = ui.item.pk;
                objName = ui.item.label;
            }
        });
    }

    // Add object to ctnr.
    $('#obj-form form').live('submit', function(event) {
        if (objName != ($('#object-searchbox').val())) {
            objPk = null;
            objName = ($('#object-searchbox').val());
        }
        var postData = {
            obj_pk: objPk,
            obj_name: objName,
            obj_type: objType,
            csrfmiddlewaretoken: csrfToken,
        };
        if (objType == 'user') {
            level = $('input[name="level"]:checked');
            if (level.length) {
                postData.level = level[0].value;
            } else {
                $('#add-user-errorlist').append(
                    '<li class="error"><font color="red"> ' +
                    'This field is required</font></li>');
                return false;
            }
            postData.confirmation = confirmation;
        }
        confirmation = false;
        $.post(addObjectUrl, postData, function(data) {
            if (data.acknowledge) {
                if (confirm(data.acknowledge)) {
                    confirmation = true;
                    $('#add-object-ctnr').click();
                    data.removeClass("error");
                }
            }
            if (data.error) {
                $('.error').empty();
                $('#add-object-errorlist').empty();
                // Put error message.
                console.log(data.error);
                var forms = $('#add-object-errorlist');
                forms.append('<li><font color="red">' + data.error +'</font></li>');
            }
            // Not going to use ajax for other objects due to users tables being on top
            if (data.success) {
                $('.error').empty();
                document.location.reload();
            }
        }, 'json');
    });

});
