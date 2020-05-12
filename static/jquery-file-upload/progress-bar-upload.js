$(function () {
    $(".js-upload-files").click(function () {
        $("#fileupload2").click();
    });

    // 初始化数组存放文件名
    var fileArr = [];
    $("#fileupload2").fileupload({
        dataType: 'json',
        autoUpload: false,
        sequentialUploads: true,
        // maxFileSize: 1024 * 1024,
        // acceptFileTypes: /(\.|\/)(jpg|png)$/i,

        add: function (e, data) {
            var fileErr = 0;
            var uploadErrors = [];
            var acceptFileTypes = /(gz|py|sls|json|js)$/i;

            var file_type = null;
            var file_index = data.files[0].name.toLowerCase().lastIndexOf(".");
            if (file_index > -1) {
                file_type = data.files[0].name.substring(file_index)
            } else {
                file_type = null
            }
            if (!acceptFileTypes.test(file_type)) {
                uploadErrors.push('文件类型不支持！');
                fileErr = 1;
            }
            console.log(data.files[0]);
            console.log(data.files[0].name + ' ' + data.files[0]['type']);
            // console.log(data.originalFiles[0]['size']);
            if (data.files[0]['size'] && data.files[0]['size'] > 1024 * 1024 * 200) {
                uploadErrors.push('文件大小超过200M！');
                fileErr = 2;
            }
            existsFile = $.inArray(data.files[0].name, fileArr);
            if (existsFile >= 0) {
                uploadErrors.push('文件不能重复选择！');
                fileErr = 3;
            }
            // if (existsFile >= 0 || fileErr === 1 || fileErr === 2) {
            if (uploadErrors.length > 0) {
                $("<div/>").addClass('alert alert-warning alert-dismissable').html('<button type="button" class="close" data-dismiss="alert"' +
                    ' aria-hidden="true"> &times; </button>' + data.files[0].name + uploadErrors.join("\n")).css('margin-bottom', '10px').appendTo($("#msg-alert2"));
                data.files.splice(0, 1);
                // alert(uploadErrors.join("\n"));
            } else {
                $("#attchment-title").removeClass('hidden');
                $("#attchment-preview").append("<p><i class='icon-folder-open'></i> " + data.files[0].name + "</p>");
                fileArr.push(data.files[0].name);
                state = $("#btn-state2").attr('state');
                if (state === '0') {
                    $(".js-upload-files").after($('<button/>').attr('id', 'upload-btn2').addClass('btn btn-success').css('margin-left', '5px').html('<span class=""></span> 开始上传'));
                    $("#btn-state2").attr('state', '1');
                }
                $("#upload-btn2").removeClass('hidden');
                $("#upload-btn2").click(function () {
                    data.context = $('<p/>').text('').replaceAll($(this));
                    $("#btn-state2").attr('state', '0');
                    data.submit();
                });
            }
        },

        start: function (e) {
            // $(".modal-backdrop").css('opacity', 0);
            // $(".modal-backdrop .in").css('opacity', 0);
            // $(".modal").css('z-index', 9999999);
            $("#modal-progress").modal("show");
            // 开始上传时清空图片预览
            $("#attchment-preview").empty();
        },

        stop: function (e) {
            $("#modal-progress").modal("hide");
        },

        progressall: function (e, data) {
            // $(".modal").css('z-index', 9999999);
            // $(".modal-backdrop").css('z-index', 999999);
            // $(".modal-backdrop .in").css('opacity', 0);
            var progress = parseInt(data.loaded / data.total * 100, 10);
            var strProgress = progress + "%";
            $(".progress-bar").css({"width": strProgress});
            $(".progress-bar").text(strProgress);
        },

        done: function (e, data) {
            // $(".modal-backdrop .in").css('opacity', 0);
            if (data.result.is_valid) {
                $("#msg-alert2").empty();
                $("#attchment-title").addClass('hidden');
                $("#attchment-upload").removeClass('hidden').attr('style', 'border-bottom: 2px solid #87b87f;margin-bottom: 10px;');
                var icon = '';
                var href_id = '';
                html = '<p><i class="fa fa-folder-open"></i> ' + data.result.name + '</p>';
                $("#attchment").prepend(html+'<input type="hidden" name="attchment_id" value="' + data.result.id + '" />');
            }
        }

    });

});

