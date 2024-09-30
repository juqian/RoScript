import os

import cv2,numpy
from ..models.area import Area
from ..constants import *

def get_YCrCb_skin_mask(image, YCrCb_low, YCrCb_high):
    YCrCb_image = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    YCrCb_skin_mask = cv2.inRange(YCrCb_image, YCrCb_low, YCrCb_high)
    YCrCb_skin_mask = cv2.morphologyEx(YCrCb_skin_mask, cv2.MORPH_OPEN, numpy.ones((SKIN_OPEN_KERNEL,SKIN_OPEN_KERNEL), numpy.uint8))
    YCrCb_skin_mask = cv2.morphologyEx(YCrCb_skin_mask, cv2.MORPH_CLOSE, numpy.ones((SKIN_CLOSING_KERNEL,SKIN_CLOSING_KERNEL), numpy.uint8))
    return YCrCb_skin_mask

def YCrCb_fingertip_detect(image, background, hand_color_low, hand_color_high, is_contour_cadidate,
                           choose_y, debug_dir, debug_prefix, frame_index):
    image_height, image_width = image.shape[:2]
    YCrCb_skin_mask = get_YCrCb_skin_mask(image, hand_color_low, hand_color_high)

    if debug_dir is not None:
        dbg_image_path = os.path.join(debug_dir, debug_prefix + "_mask_%d.jpg"%frame_index)
        os.makedirs(debug_dir, exist_ok=True)

    # 计算和第一张图像的变化，只有变化的部分可能是手
    kerne = 21
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (kerne, kerne), 0)
    motion = cv2.absdiff(background, gray)
    motion = cv2.threshold(motion, 20, 255, cv2.THRESH_BINARY)[1]

    #去掉边框等位置的环境干扰（这部分基本不变，在motion中应该没有）
    #YCrCb_skin_mask = cv2.bitwise_and(YCrCb_skin_mask, YCrCb_skin_mask, mask=motion)

    contours, _ = cv2.findContours(YCrCb_skin_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)[-2:]
    candidate_contour, candidate_bounding_area = None, None
    for contour in contours:
        x1, y1, w, h = cv2.boundingRect(contour)
        #if is_contour_cadidate((x1, y1, w, h), candidate_bounding_area, (image_height, image_width)):
        if is_contour_cadidate((x1, y1, w, h), candidate_bounding_area, (image_height, image_width))\
           and numpy.sum(motion[y1:y1+h, x1:x1+w])>0:  #手部必须至少包含一个运动点
            candidate_contour = contour
            candidate_bounding_area = Area(x1, y1, x1+w, y1+h)

    hand_contour = candidate_contour
    hand_bounding_area = candidate_bounding_area

    mask_rgb = cv2.cvtColor(YCrCb_skin_mask, cv2.COLOR_GRAY2RGB)
    dbg_image = cv2.add(image, mask_rgb)

    if hand_bounding_area == None:
        if debug_dir is not None:
            cv2.imwrite(dbg_image_path, dbg_image)
            # motion_image_path = os.path.join(debug_dir, debug_prefix + "_motion_%d.jpg" % frame_index)
            # cv2.imwrite(motion_image_path, motion)
            # diff_image_path = os.path.join(debug_dir, debug_prefix + "_diff_%d.jpg" % frame_index)
            # diff = cv2.absdiff(background, gray)
            # cv2.imwrite(diff_image_path, diff)
        return None

    fingertip_y = choose_y(hand_bounding_area)
    point_x_sum, point_count = 0, 0
    for cnt in hand_contour:
        if abs(fingertip_y - cnt[0][1]) > FINGERTIP_CANDIDATE_Y_TOLERANCE:
            continue
        point_x_sum += cnt[0][0]
        point_count += 1
    fingertip_x = int(point_x_sum/point_count)

    if debug_dir is not None:
        cv2.line(dbg_image, (0, fingertip_y), (image_width, fingertip_y), (0, 255, 0), 3)
        cv2.line(dbg_image, (fingertip_x, fingertip_y - 10), (fingertip_x, fingertip_y + 10), (0, 255, 0), 3)
        #cv2.imwrite(dbg_image_path, dbg_image)
        cv2.imencode(".jpg", dbg_image)[1].tofile(dbg_image_path)

    return (fingertip_x, fingertip_y)

def overlook_is_contour_candidate(bounding_rect, current_candidate_bounding_area, image_measure):
    _x1, y1, w, h = bounding_rect
    image_height, image_width = image_measure
    image_size = image_width * image_height
    # 手部区域过小的情况要过滤掉
    if w * h < image_size * HAND_MIN_SIZE_RATIO:
        return False
    # 手部区域如果与边缘不相接，则也不太正常（如果不裁切设备屏幕区域，则y方向下方必须相接；如果裁切，则必须左、右、下至少一个方向相接，如果是右手，则就是右、下至少有一边相接）
    # HAND_EDGE_TOLERANCE是相接的误差容忍度
    # if image_height - (y1+h) > HAND_EDGE_TOLERANCE:
    #     return False
    if image_height - (y1+h) > HAND_EDGE_TOLERANCE \
        and image_width - (_x1+w)> HAND_EDGE_TOLERANCE \
        and _x1> HAND_EDGE_TOLERANCE:
         return False
    # 如果和当前手部区域相比，y方向更大（高度更低），则也过滤掉
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

def YCrCb_overlook_fingertip_detect(image, background, hand_color_low, hand_color_high,
                                    dev_location, dev_real_measure, pixel_to_real_ration, debug_dir, frame_index):
    return YCrCb_fingertip_detect(image, background, hand_color_low, hand_color_high, overlook_is_contour_candidate,
                                  lambda bounding_area:bounding_area.lt[1], debug_dir, "overlook", frame_index)

def YCrCb_sidelook_fingertip_detect(image, background, hand_color_low, hand_color_high,
                                    dev_real_measure, pixel_to_real_ration, debug_dir, frame_index):
    return YCrCb_fingertip_detect(image, background, hand_color_low, hand_color_high, sidelook_is_contour_candidate,
                                  lambda bounding_area:bounding_area.rb[1], debug_dir, "sidelook", frame_index)