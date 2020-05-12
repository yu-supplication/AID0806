$(function () {

    $(".js-upload-photos").click(function () {
        $("#fileupload").click();
    });

    // 初始化数组存放文件名
    var fileArr = [];
    $("#fileupload").fileupload({
        dataType: 'json',
        autoUpload: false,
        sequentialUploads: true,
        acceptFileTypes: /(\.|\/)(jpg)$/i,


        // 禁止自动上传，定义图片上传前的动作
        add: function (e, data) {
var uploadErrors = [];
                var acceptFileTypes = /^image\/(gif|jpe?g|png)$/i;
                if(data.files[0]['type'].length && !acceptFileTypes.test(data.files[0]['type'])) {
                    uploadErrors.push('Not an accepted file type');
                }
                console.log(uploadErrors);
            $.each(data.files, function (index, file) {
                console.log('Selected file: ' + file.name);
                r = $.inArray(file.name, fileArr);
                if (r >= 0) {
                    data.files.splice(index, 1);
                    console.log('exists.');
                } else {

                    // 读取本地图片并预览
                    var reader = new FileReader();
                    reader.onload = function (e) {
                        var image = new Image();
                        image.src = e.target.result;
                        $("#preview-title").removeClass('hidden').attr('style', 'border-bottom: 2px solid #87b87f;margin-bottom: 10px;');
                        image.onload = function () {
                            img_preview = '<img onclick="modalImg(this);" src="' + this.src + '" name="' + this.width +
                                '" style="cursor: pointer;height:150px;overflow:hidden;padding-left:5px;" class="thumbnail col-xs-3 col-sm-4"/>';
                            $("#gallery-preview").append(img_preview);
                        }
                    };
                    // reader.readAsDataURL(data.files[0]);
                    reader.readAsDataURL(file);
                    fileArr.push(file.name);
                    state = $("#upload-btnn").attr('state');
                    if (state === '0') {
                        $(".js-upload-photos").after($('<button/>').attr('id', 'upload-btn').addClass('btn btn-success').css('margin-left', '5px').html('<span class="glyphicon glyphicon-cloud-upload"></span> 开始上传'));
                        $("#upload-btnn").attr('state', '1');
                    }
                    // 选择图片后添加上传按钮
                    // data.context = $('<button/>').html('<span class="glyphicon glyphicon-cloud-upload"></span> 开始上传')
                    // .appendTo($("#upload-btn")).click(function () {
                    // 选择图片后显示上传按钮
                    // if (data.files && data.files[0]) {
                    $("#upload-btn").removeClass('hidden');
                    //data.context = $('<button/>').html('<span class="glyphicon glyphicon-cloud-upload"></span> 开始上传');
                    //     data.context = $('<button/>').html('<span class="glyphicon glyphicon-cloud-upload"></span> 开始上传')
                    //         .appendTo($("#upload-btn")).click(function () {
                    // 点击上传后清空上传按钮

                    // data.context.click(function () {

                    $("#upload-btn").click(function () {
                        data.context = $('<p/>').text('').replaceAll($(this));
                        $("#upload-btnn").attr('state', '0');
                        // 点击上传后隐藏按钮
                        //$("#upload-btn").addClass('hidden');
                        data.submit();
                    });
                }

            });


            // }

        },

        start: function (e) {

            $("#modal-progress").modal("show");
            // 开始上传时清空图片预览
            $("#gallery-preview").empty();
        },

        stop: function (e) {
            $("#modal-progress").modal("hide");
        },

        progressall: function (e, data) {
            var progress = parseInt(data.loaded / data.total * 100, 10);
            var strProgress = progress + "%";
            $(".progress-bar").css({"width": strProgress});
            $(".progress-bar").text(strProgress);
        },

        done: function (e, data) {
            if (data.result.is_valid) {
                $("#preview-title").addClass('hidden');
                $("#gallery-title").removeClass('hidden').attr('style', 'border-bottom: 2px solid #87b87f;margin-bottom: 10px;');
                $("#gallery").prepend(
                    // "<tr><td><a href='" + data.result.url + "'>" + data.result.name + "</a></td></tr>"
                    '<img onclick="modalImg(this)" src="' + data.result.url + '" name="' + data.result.width + '" style="cursor:pointer;height:150px;overflow:hidden;" class="thumbnail col-xs-3 col-sm-4" />' +
                    '<input type="hidden" name="img_id" value="' + data.result.id + '" />'
                )
            }
        }

    });

});


