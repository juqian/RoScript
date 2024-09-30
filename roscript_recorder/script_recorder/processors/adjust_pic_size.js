$("img").on('load', function(){
    width = parseInt($(this).css('width').replace("px", ""));
    height = parseInt($(this).css('height').replace("px", ""));
    new_height = 50;
    new_width = Math.round(width * new_height/height);
    $(this).css('width', new_width+"px");
    $(this).css('height', new_height+"px");
});

// 双重检查，防止图片早于该js被加载完成
window.onload = function(){
    images = $('img');
    Array.prototype.forEach.call(images,function(e){
        width = parseInt($(e).css('width').replace("px", ""));
        height = parseInt($(e).css('height').replace("px", ""));
        new_height = 50;
        new_width = Math.round(width * new_height/height);
        $(e).css('width', new_width+"px");
        $(e).css('height', new_height+"px");
    });
}