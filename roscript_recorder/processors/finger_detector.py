import cv2,numpy
from roscript_recorder.models.area import Area
from roscript_recorder.constants import *

def get_YCrCb_skin_mask(image, YCrCb_low=None, YCrCb_high=None):
    if YCrCb_low is None:
        YCrCb_low = (SKIN_Y_LOW, SKIN_CR_LOW, SKIN_CB_LOW)
    if YCrCb_high is None:
        YCrCb_high = (SKIN_Y_HIGH, SKIN_CR_HIGH, SKIN_CB_HIGH)

    YCrCb_image = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    YCrCb_skin_mask = cv2.inRange(YCrCb_image, YCrCb_low, YCrCb_high)
    YCrCb_skin_mask = cv2.morphologyEx(YCrCb_skin_mask, cv2.MORPH_OPEN, numpy.ones((SKIN_OPEN_KERNEL,SKIN_OPEN_KERNEL), numpy.uint8))
    YCrCb_skin_mask = cv2.morphologyEx(YCrCb_skin_mask, cv2.MORPH_CLOSE, numpy.ones((SKIN_CLOSING_KERNEL,SKIN_CLOSING_KERNEL), numpy.uint8))
    return YCrCb_skin_mask

def YCrCb_fingertip_detect(image, background, hand_color_low, hand_color_high, is_contour_cadidate, choose_y):
    image_height, image_width = image.shape[:2]
    YCrCb_skin_mask = get_YCrCb_skin_mask(image, hand_color_low, hand_color_high)

    # 计算和第一张图像的变化，只有变化的部分可能是手
    kerne = 51
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (kerne, kerne), 0)
    motion = cv2.absdiff(background, gray)
    motion = cv2.threshold(motion, 20, 255, cv2.THRESH_BINARY)[1]

    contours, _ = cv2.findContours(YCrCb_skin_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)[-2:]
    candidate_contour, candidate_bounding_area = None, None
    for contour in contours:
        x1, y1, w, h = cv2.boundingRect(contour)
        if is_contour_cadidate((x1, y1, w, h), candidate_bounding_area, (image_height, image_width))\
           and numpy.sum(motion[y1:y1+h, x1:x1+w])>0:  
            candidate_contour = contour
            candidate_bounding_area = Area(x1, y1, x1+w, y1+h)

    hand_contour = candidate_contour
    hand_bounding_area = candidate_bounding_area
    if hand_bounding_area == None:
        return None
    fingertip_y = choose_y(hand_bounding_area)
    point_x_sum, point_count = 0, 0
    for cnt in hand_contour:
        if abs(fingertip_y - cnt[0][1]) > FINGERTIP_CANDIDATE_Y_TOLERANCE:
            continue
        point_x_sum += cnt[0][0]
        point_count += 1
    fingertip_x = int(point_x_sum/point_count)
    return (fingertip_x, fingertip_y)

def overlook_is_contour_candidate(bounding_rect, current_candidate_bounding_area, image_measure):
    _x1, y1, w, h = bounding_rect
    image_height, image_width = image_measure
    image_size = image_width * image_height

    if w * h < image_size * HAND_MIN_SIZE_RATIO:
        return False

    if image_height - (y1+h) > HAND_EDGE_TOLERANCE \
        and image_width - (_x1+w)> HAND_EDGE_TOLERANCE \
        and _x1> HAND_EDGE_TOLERANCE:
         return False

    if current_candidate_bounding_area != None and y1 > current_candidate_bounding_area.lt[1]:
        return False
    return True

def sidelook_is_contour_candidate(bounding_rect, current_candidate_bounding_area, image_measure):
    _x1, y1, w, h = bounding_rect
    image_height, image_width = image_measure
    image_size = image_width * image_height
    if w * h < image_size * HAND_MIN_SIZE_RATIO:
        return False
    if y1 > HAND_EDGE_TOLERANCE:
        return False
    if current_candidate_bounding_area != None and y1+h < current_candidate_bounding_area.rb[1]:
        return False
    return True

def YCrCb_overlook_fingertip_detect(image, background, hand_color_low, hand_color_high, dev_location, dev_real_measure, pixel_to_real_ration):
    return YCrCb_fingertip_detect(image, background, hand_color_low, hand_color_high, overlook_is_contour_candidate, lambda bounding_area:bounding_area.lt[1])

def YCrCb_sidelook_fingertip_detect(image, background, hand_color_low, hand_color_high, dev_real_measure, pixel_to_real_ration):
    return YCrCb_fingertip_detect(image, background, hand_color_low, hand_color_high, sidelook_is_contour_candidate, lambda bounding_area:bounding_area.rb[1])