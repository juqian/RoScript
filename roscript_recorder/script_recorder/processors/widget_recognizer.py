import cv2,numpy
from ..models.area import Area
from ..constants import *


def recognize_by_mixed_approach(frame, touch_position):
    return recognize(frame, touch_position, recognize_by_mixed_approach0)

def recognize_by_fixed_size(frame, touch_position):
    return recognize(frame, touch_position, recognize_by_fixed_size0)

def recognize_by_canny(frame, touch_position):
    return recognize(frame, touch_position, recognize_by_canny0)

# 确保手指位置在屏幕范围内(偶尔会识别到屏幕外面去，造成后续处理异常）
def ensure_in_screen(image, touchpos, pixel_to_real_ratio):
    image_height, image_width = image.shape[:2]
    x, y = touchpos
    fingertip_pixel_offset = FINGERTIP_OFFSET * pixel_to_real_ratio

    if x <= 0:
        x = fingertip_pixel_offset
    elif x>=image_width:
        x = image_width - fingertip_pixel_offset

    if y <= 0:
        y = fingertip_pixel_offset
    elif y >= image_height:
        y = image_height - fingertip_pixel_offset
    return (x, y)


def recognize(frame, touch_position, recognize_method):
    pixel_to_real_ratio =  frame.parent.parameters["pixel_to_real_ratio"]
    offset = frame.parent.parameters["device_location"].lt
    device_touch_position = (touch_position[0]-offset[0], touch_position[1]-offset[1])
    device_image = frame.get_device_image()
    device_touch_position = ensure_in_screen(device_image, device_touch_position, pixel_to_real_ratio)
    video_path = frame.parent.path
    video_hash = frame.parent.video_hash
    frame_index = frame.index
    device_widget_rect = recognize_method(video_path, video_hash, frame_index, device_image, device_touch_position, pixel_to_real_ratio)
    if device_widget_rect == None:
        return None
    device_x1, device_y1, device_x2, device_y2 = device_widget_rect
    target_widget_area = Area(device_x1+offset[0], device_y1+offset[1], device_x2+offset[0], device_y2+offset[1])
    return target_widget_area

def recognize_by_mixed_approach0(video_path, video_hash, frame_index, image, touch_position, pixel_to_real_ratio):
    canny_widget_rect = recognize_by_canny0(video_path, video_hash, frame_index, image, touch_position, pixel_to_real_ratio)
    if canny_widget_rect:
        return canny_widget_rect
    fixed_size_widget_rect = recognize_by_fixed_size0(video_path, video_hash, frame_index, image, touch_position, pixel_to_real_ratio)
    return fixed_size_widget_rect

def recognize_by_fixed_size0(video_path, video_hash, frame_index, image, touch_position, pixel_to_real_ratio):
    default_side_pixel_length = DEFAULT_SIDE_LENGTH * pixel_to_real_ratio
    image_height, image_width = image.shape[:2]
    touch_x, touch_y = touch_position

    # 边缘处理
    if touch_x < default_side_pixel_length/2:
        touch_x = default_side_pixel_length/2
    elif touch_x > image_width - default_side_pixel_length/2:
        touch_x = image_width - default_side_pixel_length/2

    if touch_y < default_side_pixel_length/2:
        touch_y = default_side_pixel_length/2
    elif touch_y > image_height - default_side_pixel_length/2:
        touch_y = image_height - default_side_pixel_length/2

    x1 = int(max(touch_x - default_side_pixel_length/2, 0))
    y1 = int(max(touch_y - default_side_pixel_length/2, 0))
    x2 = int(min(touch_x + default_side_pixel_length/2, image_width))
    y2 = int(min(touch_y + default_side_pixel_length/2, image_height))
    return (x1, y1, x2, y2)

def recognize_by_canny0(video_path, video_hash, frame_index, image, touch_position, pixel_to_real_ratio):
    widget_max_pixel_size = WIDGET_MAX_SIZE * pixel_to_real_ratio * pixel_to_real_ratio
    extension_pixel_size_limit = EXTENSION_SIZE_LIMIT * pixel_to_real_ratio * pixel_to_real_ratio
    extend_pixel_length = EXTEND_LENGTH * pixel_to_real_ratio
    mb_image = cv2.medianBlur(image, WIDGET_MEDIAN_BLUR)
    canny_image = cv2.Canny(mb_image, WIDGET_CANNY_LOW, WIDGET_CANNY_HIGH)
    closed_image = cv2.morphologyEx(canny_image, cv2.MORPH_CLOSE, numpy.ones((WIDGET_CLOSING_KERNEL,WIDGET_CLOSING_KERNEL), numpy.uint8))
    contours, _ = cv2.findContours(closed_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)[-2:]

    # copy = image.copy()
    # cv2.drawContours(copy, contours, -1, (0,0,255), 1)
    # cv2.imwrite("contour.png", copy)

    boxes = []
    for contour in contours:
        boxes.append(cv2.boundingRect(contour))

    # 附加上OCR所得的结果区域
    from . import ocr
    if video_path is None or video_hash is None or frame_index is None:
        ocr_results = ocr.recognize(image)
    else:
        cache_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ocr_cache")
        ocr_results = ocr.find_ocr_cache(cache_root, video_path, video_hash, frame_index)
        if ocr_results is None:
            ocr_results = ocr.recognize(image)
            ocr.flush_ocr_cache(cache_root, video_path, video_hash, frame_index, ocr_results)

    for r in ocr_results:
        boxes.append(r["bounds"])

    # 找一组候选的控件区域，逐步增加吸收区域，看看包含触控点的最大轮廓是哪个
    candidate_widget_areas = []
    extend_times = 0
    extend = 0
    max_extend_times = FINGERTIP_OFFSET/1    #步长1mm
    while extend_times < max_extend_times:
        for box in boxes:
            x, y, w, h = box
            # 考虑吸收范围的控件区域
            xa = int(x - extend)
            xb = int(x + w + extend)
            ya = int(y - extend)
            yb = int(y + h + extend)
            area = Area(xa, ya, xb, yb)
            # 如果区域过大，则淘汰 (改成看抠图区域，而不是吸收区域)
            #if (w+2*extend) * (h + 2*extend) > widget_max_pixel_size:
            if (w * h) > widget_max_pixel_size:
                continue
            # 如果吸收范围内包含点击区域，则加入为候选
            if area.contain_position(touch_position):
                candidate_widget_areas.append(Area(x, y, x+w, y+h))
        # 如果已经找到候选区域，则不再尝试扩大吸收面积
        if len(candidate_widget_areas) > 0:
            break

        extend_times += 1
        extend += extend_pixel_length

    if len(candidate_widget_areas) == 0:
        return None

    chosen_widget_area = max(candidate_widget_areas, key=lambda area:area.get_size())

    # 如果面积太小，在抠图的时候将控件区域适当放大（过大或过小可能影响匹配，此处也可以不激活）
    # if chosen_widget_area.get_size() < extension_pixel_size_limit:
    #     chosen_widget_area = chosen_widget_area.expand(extend_pixel_length)

    x1, y1 = chosen_widget_area.lt
    x2, y2 = chosen_widget_area.rb
    return(x1, y1, x2, y2)
