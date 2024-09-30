import sys
from ..constants import *

def group_by_action(fingertips):
    return group(fingertips, is_in_action, 0, ACTION_GAP_FRAME_COUNT_LIMIT, ACTION_MIN_FRAME_COUNT_LIMIT)

def group_by_touch(fingertips, threshold):
    return group(fingertips, is_in_touch, threshold, TOUCH_GAP_FRAME_COUNT_LIMIT, TOUCH_MIN_FRAME_COUNT_LIMIT)

def is_in_action(fingertip, threshold):
    return fingertip.overlook_position != None and fingertip.overlook_position[1] > threshold

def is_in_touch(fingertip, threshold):
    return fingertip.sidelook_position != None and fingertip.sidelook_position[1] > threshold

def group(fingertips, is_qualified, threshold, gap_frame_count_limit, min_frame_count_limit):
    fingertip_groups = []
    start_index, end_index = 0, 0
    for i in range(gap_frame_count_limit, len(fingertips)-gap_frame_count_limit):
        is_start = is_qualified(fingertips[i], threshold)
        for num in range(1,gap_frame_count_limit+1):
            is_start = is_start and not is_qualified(fingertips[i-num], threshold)  # 前面N帧都没有手指而该帧有手指则说明该帧是一次操作的开始
        if is_start:
            start_index = i
        is_end = is_qualified(fingertips[i], threshold)
        for num in range(1,gap_frame_count_limit+1):
            is_end = is_end and (not is_qualified(fingertips[i+num], threshold) or i+num==len(fingertips)-1)  # 后面N帧都没有手指而该帧有手指则说明该帧是一次操作的结束
        is_end = is_end and start_index != 0  # 对结束帧多一次判断，在结束帧之前必须存在开始帧
        if is_end:
            end_index = i
        if start_index != 0 and end_index != 0:
            if end_index - start_index >= min_frame_count_limit - 1:  # 由于可能存在手指误识别的情况，故将持续时间太短的操作排除
                fingertip_group = fingertips[start_index:end_index+1]
                fingertip_groups.append(fingertip_group)
            start_index = 0
            end_index = 0
    return fingertip_groups


def get_longest_from_overlook(fingertips):
    return min(fingertips, key=lambda fingertip:fingertip.overlook_position[1] if fingertip and fingertip.overlook_position else sys.maxsize)

def get_deepest_from_sidelook(fingertips):
    return max(fingertips, key=lambda fingertip:fingertip.sidelook_position[1] if fingertip and fingertip.sidelook_position else 0)