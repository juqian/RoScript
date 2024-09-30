import math
import cv2, numpy
from . import group_processor
from ..models.area import Area
from ..constants import *

def get_action_type(touch_fingertip_groups, pre_action_frame, keyboard_models):
    pixel_to_real_ratio = pre_action_frame.parent.parameters["pixel_to_real_ratio"]
    fps = pre_action_frame.parent.parameters["fps"]
    pixel_move_distance = pixel_to_real_ratio * ACTION_TYPE_MOVE_DISTANCE
    stay_frame_count_limit = int(fps * STAY_TIME_LIMIT)
    touch_during_frame_count = touch_fingertip_groups[-1][-1].index - touch_fingertip_groups[0][0].index
    keyboard_info = get_keyboard_info(pre_action_frame, keyboard_models)
    first_deepest_fingertip = group_processor.get_deepest_from_sidelook(touch_fingertip_groups[0])
    if keyboard_info != None and keyboard_info[1].contain_position(first_deepest_fingertip.get_touch_position()):
        return "press_keyboard"

    start_touch_position = touch_fingertip_groups[0][0].get_touch_position()
    end_touch_position = touch_fingertip_groups[-1][-1].get_touch_position()
    distance_square = math.pow((start_touch_position[0] - end_touch_position[0]), 2) + math.pow((start_touch_position[1] - end_touch_position[1]), 2)
    # 如果运动距离近
    if distance_square <= math.pow(pixel_move_distance, 2):
        # 如果触控时间短，那么是click或double_click，否则是长按
        if touch_during_frame_count <= stay_frame_count_limit:
            if len(touch_fingertip_groups) == 1:
                return "click"
            else:
                return "double_click"
        else:
            return "long_press"
    else:
        # 如果触控时间短，则为swipe
        if touch_during_frame_count <= stay_frame_count_limit:
            return "swipe"
        else:
            for i in range(len(touch_fingertip_groups)):
                idx1 = touch_fingertip_groups[i][0].index - touch_fingertip_groups[0][0].index
                idx2 = touch_fingertip_groups[i][-1].index - touch_fingertip_groups[0][0].index
                if idx1 <= stay_frame_count_limit < idx2:
                    idx = stay_frame_count_limit - idx1
                    stay_time_touch_position = touch_fingertip_groups[i][idx].get_touch_position()
                    break
                elif idx1 > stay_frame_count_limit:
                    stay_time_touch_position = touch_fingertip_groups[i][-1].get_touch_position()
            distance_square = math.pow((start_touch_position[0] - stay_time_touch_position[0]), 2) + math.pow((start_touch_position[1] - stay_time_touch_position[1]), 2)
            if distance_square <= math.pow(pixel_move_distance, 2):
                return "drag"
            return "swipe"


def get_keyboard_info(frame, keyboard_models):
    if keyboard_models == None:
        return None
    offset = frame.parent.parameters["device_location"].lt
    device_image = frame.get_device_image()
    candidate_keyboards_detail = []
    for keyboard_name, keyboard_info in keyboard_models.items():
        match_count, x1, y1, x2, y2 = surf_match(device_image, keyboard_info["image"])
        if match_count == -1:
            continue
        candidate_keyboards_detail.append((keyboard_name, match_count, x1, y1, x2, y2))
    if len(candidate_keyboards_detail) == 0:
        return None
    keyboard_name, _, x1, y1, x2, y2 = max(candidate_keyboards_detail, key=lambda x:x[1])
    keyboard_area = Area(x1+offset[0], y1+offset[1], x2+offset[0], y2+offset[1])
    return (keyboard_name, keyboard_area)

def surf_match(target_image, template_image):
    #surf = cv2.xfeatures2d.SURF_create(400)
    surf = cv2.xfeatures2d.SIFT_create()
    kp1, des1 = surf.detectAndCompute(template_image, None)
    kp2, des2 = surf.detectAndCompute(target_image, None)
    FLANN_INDEX_KDTREE = 0
    index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
    search_params = dict(checks = 60)
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    matches = flann.knnMatch(des1, des2, k=2)
    good_dot = []
    for m,n in matches:
        if m.distance < 0.6 * n.distance:
            """
            ratio=0. 4：对于准确度要求高的匹配； 
            ratio=0. 6：对于匹配点数目要求比较多的匹配；
            ratio=0. 5：一般情况下。
            """
            good_dot.append(m)
    match_count = len(good_dot)
    if match_count > SURF_KEYBOARD_MIN_MATCH_COUNT:
        try:
            screen_pts = numpy.array([kp2[m.trainIdx].pt for m in good_dot], dtype=numpy.float).reshape(-1, 1, 2)
            widget_pts = numpy.array([kp1[m.queryIdx].pt for m in good_dot], dtype=numpy.float).reshape(-1, 1, 2)
            M, _ = cv2.findHomography(widget_pts, screen_pts, cv2.RANSAC, 5.0)
            h,w = template_image.shape[:2]
            pts = numpy.array([[0, 0], [0, h-1], [w-1, h-1], [w-1, 0]], dtype=numpy.float).reshape(-1, 1, 2)
            dst = cv2.perspectiveTransform(pts, M)
            x,y = [],[]
            for i in range(len(dst)):
                x.append(int(dst[i][0][0]))
                y.append(int(dst[i][0][1]))
            template_match_result = (match_count, min(x), min(y), max(x), max(y))
            return template_match_result
        except:
            template_match_result = (-1, None, None, None, None)
            return template_match_result
    else:
        template_match_result = (-1, None, None, None, None)
        return template_match_result


