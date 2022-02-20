import cv2,numpy
import socket
from roscript_recorder.models.area import Area
from roscript_recorder.constants import *
# from .east import east_predictor

def recognize_by_mixed_approach(frame, touch_position):
    return recognize(frame, touch_position, recognize_by_mixed_approach0)

def recognize_by_fixed_size(frame, touch_position):
    return recognize(frame, touch_position, recognize_by_fixed_size0)

def recognize_by_canny(frame, touch_position):
    return recognize(frame, touch_position, recognize_by_canny0)

def recognize_by_east(frame, touch_position):
    return recognize(frame, touch_position, recognize_by_east0)

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
    device_widget_rect = recognize_method(device_image, device_touch_position, pixel_to_real_ratio)
    if device_widget_rect == None:
        return None
    device_x1, device_y1, device_x2, device_y2 = device_widget_rect
    target_widget_area = Area(device_x1+offset[0], device_y1+offset[1], device_x2+offset[0], device_y2+offset[1])
    return target_widget_area

def recognize_by_mixed_approach0(image, touch_position, pixel_to_real_ratio):
    east_widget_rect = recognize_by_east0(image, touch_position, pixel_to_real_ratio)
    if east_widget_rect:
        return east_widget_rect
    canny_widget_rect = recognize_by_canny0(image, touch_position, pixel_to_real_ratio)
    if canny_widget_rect:
        return canny_widget_rect
    fixed_size_widget_rect = recognize_by_fixed_size0(image, touch_position, pixel_to_real_ratio)
    return fixed_size_widget_rect

def recognize_by_fixed_size0(image, touch_position, pixel_to_real_ratio):
    default_side_pixel_length = DEFAULT_SIDE_LENGTH * pixel_to_real_ratio
    image_height, image_width = image.shape[:2]
    touch_x, touch_y = touch_position

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

def recognize_by_canny0(image, touch_position, pixel_to_real_ratio):
    widget_max_pixel_size = WIDGET_MAX_SIZE * pixel_to_real_ratio * pixel_to_real_ratio
    extension_pixel_size_limit = EXTENSION_SIZE_LIMIT * pixel_to_real_ratio * pixel_to_real_ratio
    extend_pixel_length = EXTEND_LENGTH * pixel_to_real_ratio
    mb_image = cv2.medianBlur(image, WIDGET_MEDIAN_BLUR)
    canny_image = cv2.Canny(mb_image, WIDGET_CANNY_LOW, WIDGET_CANNY_HIGH)
    closed_image = cv2.morphologyEx(canny_image, cv2.MORPH_CLOSE, numpy.ones((WIDGET_CLOSING_KERNEL,WIDGET_CLOSING_KERNEL), numpy.uint8))
    contours, _ = cv2.findContours(closed_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)[-2:]

    # 找一组候选的控件区域，逐步增加吸收区域，看看包含触控点的最大轮廓是哪个
    candidate_widget_areas = []
    extend_times = 0
    extend = 0
    while extend_times < 3:
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            # 考虑吸收范围的控件区域
            xa = int(x - extend)
            xb = int(x + w + extend)
            ya = int(y - extend)
            yb = int(y + h + extend)
            area = Area(xa, ya, xb, yb)

            if (w * h) > widget_max_pixel_size:
                continue

            if area.contain_position(touch_position):
                candidate_widget_areas.append(Area(x, y, x+w, y+h))

        if len(candidate_widget_areas) > 0:
            break

        extend_times += 1
        extend += extend_pixel_length

    if len(candidate_widget_areas) == 0:
        return None

    chosen_widget_area = max(candidate_widget_areas, key=lambda area:area.get_size())


    x1, y1 = chosen_widget_area.lt
    x2, y2 = chosen_widget_area.rb
    return(x1, y1, x2, y2)

def recognize_by_east0(image, touch_position, pixel_to_real_ratio):
    # try:
    #     text_rects = east_predictor.predict(image)
    #     text_areas = [Area(x1, y1, x2, y2) for x1, y1, x2, y2 in text_rects]
    #     touch_area = None
    #     for area in text_areas:
    #         if area.contain_position(touch_position):
    #             touch_area = area
    #             break
    #     if touch_area == None:
    #         return None
    #     merged_area = east_text_areas_merge(touch_area, text_areas, pixel_to_real_ratio)
    #     x1, y1 = merged_area.lt
    #     x2, y2 = merged_area.rb
    #     return (x1, y1, x2, y2)
    # except:
    #     print("EAST检测失败，跳过！")
    #     return None
    return None

def east_text_areas_merge(touch_area, text_areas, pixel_to_real_ratio):
    east_max_pixel_word_space = EAST_MAX_WORD_SPACE * pixel_to_real_ratio
    east_max_pixel_width = EAST_MAX_WIDTH * pixel_to_real_ratio
    current_area = touch_area
    areas_in_same_row = []
    for area in text_areas:
        if Area.is_in_same_row(touch_area, area):
            areas_in_same_row.append(area)
    chosen_text_area_set = {touch_area}
    while current_area.get_width() < east_max_pixel_width:
        chosen_text_area = None
        for text_area in areas_in_same_row:
            if text_area in chosen_text_area_set:
                continue
            current_extend_area_lt = (current_area.lt[0]-east_max_pixel_word_space, current_area.lt[1])
            current_extend_area_rb = (current_area.rb[0]+east_max_pixel_word_space, current_area.rb[1])
            current_extend_area = Area(current_extend_area_lt[0], current_extend_area_lt[1], current_extend_area_rb[0], current_extend_area_rb[1])
            if Area.is_overlapped(current_extend_area, text_area):
                    chosen_text_area = text_area
                    break
        if chosen_text_area == None:
            break
        chosen_text_area_set.add(chosen_text_area)
        current_area = Area.merge(current_area, chosen_text_area)
    return current_area