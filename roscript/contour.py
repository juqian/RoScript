# -*- coding: utf-8 -*-
"""
Screen region detection
Created on Mon Mar 25 21:04:22 2019
@author: 29965
"""
import os.path

import cv2
import numpy
import numpy as np
from config import Config

DEVICE_LEAN_TOLERANCE = 3
POWER_LINE_THICKNESS_RATIO = 0.35
DEVICE_SIZE_LIMIT_RATIO = 0.96


def get_region_contour(region=[0, 0, 1, 1]):
    """获取设备屏幕轮廓在图像中的像素坐标
    Args:
        region: 四个参数分别对应表示该区域占整个屏幕轮廓区域的比例
            例如[0,0,1,1]表示整个被测设备屏幕
            [0.5,0,1,1]表示屏幕左半部分
            [0,0.5,1,1]表示屏幕下半部分
    """
    contour = Config.get_equipment_contour()
    width = contour[2] - contour[0]
    height = contour[3] - contour[1]
    region_size = [width, height, width, height]
    region_range = [a * b for a, b in zip(region_size, region)]
    region_origin = [contour[0], contour[1], contour[0], contour[1]]
    region_area = np.array(region_range) + np.array(region_origin)
    return region_area.tolist()


def caculate_image_contour(img, is_first=True):
    h, w = img.shape[:2]
    canny = cv2.Canny(img, 50, 100)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(canny, cv2.MORPH_CLOSE, kernel)  # 闭运算加强轮廓的连通性
    _, contours, _ = cv2.findContours(closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # 对每一个轮廓计算与其外切的最小矩形的坐标和面积，并根据面积大小进行排序
    size_dict = {}
    for contour in contours:
        x1, y1, cnt_w, cnt_h = cv2.boundingRect(contour)  # 得到该轮廓外接矩形的左上角坐标以及宽高
        x2 = x1 + cnt_w
        y2 = y1 + cnt_h
        if cnt_w > cnt_h * 4:
            # 过滤掉宽高比大于4的框
            continue
        if is_first and (x1 == 0 or y1 == 0 or x2 == w or y2 == h):
            # 过滤掉与四周相接的框
            continue
        size = cnt_w * cnt_h
        size_dict[((x1, y1), (x2, y2))] = size  # 键为由矩形左上角和右下角坐标组成的一个二元组，值为矩形面积

    size_list = sorted(size_dict.items(), key=lambda x: x[1], reverse=True)  # 根据矩形面积进行排序
    expected_item_index = 0
    if len(size_list) == 0:
        return [0, 0, h, w]

    expected_item = size_list[expected_item_index]
    if expected_item[1] > h * w * 0.95:  # 取面积最大的矩形作为轮廓，但如果该矩形面积与原图像面积接近，则取第二大面积的矩形作为轮廓
        expected_item_index += 1
        expected_item = size_list[expected_item_index]

    expected_x1, expected_y1 = expected_item[0][0]
    expected_x2, expected_y2 = expected_item[0][1]
    contour_map = [int(expected_x1), int(expected_y1), int(expected_x2), int(expected_y2)]
    return contour_map


def detect_screen_region(img_path, isCutTwice=True, isAdvanced=False):
    if not os.path.exists(img_path):
        raise FileNotFoundError(img_path)

    img = cv2.imread(img_path)
    # if isAdvanced, then enable a mode that allow detect screen with cable connected
    if isAdvanced:
        _, device_contour = simple_detect(img)
        screen_region = advanced_detect(img, device_contour)
    else:
        screen_region = caculate_image_contour(img)

    x_left, y_top, x_right, y_down = screen_region
    print("Exterior screen region: [{},{},{},{}] ".format(x_left, y_top, x_right, y_down))
    exterior_screen_img = img[y_top:y_down, x_left:x_right]

    print("Detect interior screen region: ", isCutTwice)
    interior_screen_img = None

    # if isCutTwice, then try to detect the interior screen
    if isCutTwice:
        contour_map2 = caculate_image_contour(exterior_screen_img, is_first=False)
        x_left2, y_top2, x_right2, y_down2 = contour_map2
        new_x_left, new_y_top = x_left + x_left2, y_top + y_top2  # 裁切后的图像相对原始图像的坐标，应该是两次得到的相对坐标相加的值
        new_x_right, new_y_down = x_left + x_right2, y_top + y_down2
        screen_region = [new_x_left, new_y_top, new_x_right, new_y_down]

        print("Interior screen region: [{},{},{},{}] ".format(new_x_left,new_y_top,new_x_right, new_y_down))
        interior_screen_img = img[new_y_top:new_y_down, new_x_left:new_x_right]

    return screen_region, exterior_screen_img, interior_screen_img


def simple_detect(image):
    image_height, image_width = image.shape[:2]
    image_size = image_width * image_height
    canny_image = cv2.Canny(image, 60, 130)
    closed_image = cv2.morphologyEx(canny_image, cv2.MORPH_CLOSE,
                                    numpy.ones((5, 5), numpy.uint8))
    contours, _ = cv2.findContours(closed_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)[-2:]
    candidate_contour, candidate_bounding_area = None, (0, 0, 0, 0)
    for contour in contours:
        x1, y1, w, h = cv2.boundingRect(contour)
        if (candidate_bounding_area[2] - candidate_bounding_area[0]) * \
                (candidate_bounding_area[3] - candidate_bounding_area[1]) \
                < w * h < image_size * DEVICE_SIZE_LIMIT_RATIO:
            candidate_contour = contour
            candidate_bounding_area = (x1, y1, x1 + w, y1 + h)
    device_contour = candidate_contour
    device_location = candidate_bounding_area
    return device_location, device_contour


def advanced_detect(image, device_contour):
    image_height, image_width = image.shape[:2]
    device_x1, device_y1, device_w, device_h = cv2.boundingRect(device_contour)
    device_x2, device_y2 = device_x1 + device_w, device_y1 + device_h

    # 直线检测
    repaint_device_contour_image = numpy.zeros((image_height, image_width), numpy.uint8)
    cv2.drawContours(repaint_device_contour_image, [device_contour], -1, color=255, thickness=3)
    lines = cv2.HoughLines(repaint_device_contour_image, rho=1, theta=numpy.pi / 180, threshold=50, lines=2)

    # 筛选出水平和垂直方向的直线
    horizon_rho_and_theta_list = []
    vertical_rho_and_theta_list = []
    for line in lines:
        rho, theta = line[0]
        if (1 / 2 - DEVICE_LEAN_TOLERANCE / 180) * numpy.pi < theta < (
                1 / 2 + DEVICE_LEAN_TOLERANCE / 180) * numpy.pi:
            horizon_rho_and_theta_list.append((rho, theta))
        if theta < DEVICE_LEAN_TOLERANCE / 180 * numpy.pi or theta > (1 - DEVICE_LEAN_TOLERANCE / 180) * numpy.pi:
            vertical_rho_and_theta_list.append((rho, theta))

    # 轮廓区域优化
    if device_x1 <= 0 or device_x2 >= image_width - 1:
        device_x1, device_x2 = _calculate_device_two_optimized_coordinate_value((device_x1, device_x2), image_width,
                                                                                "x", vertical_rho_and_theta_list,
                                                                                repaint_device_contour_image)
    if device_y1 <= 0 or device_y2 == image_height - 1:
        device_y1, device_y2 = _calculate_device_two_optimized_coordinate_value((device_y1, device_y2), image_height,
                                                                                "y", horizon_rho_and_theta_list,
                                                                                repaint_device_contour_image)

    return device_x1, device_y1, device_x2, device_y2


def get_contour_center(region=[0, 0, 1, 1]):
    """获取所指屏幕轮廓中心点,像素坐标
    Args:
        region: 四个参数分别对应表示该区域占整个屏幕轮廓区域的比例
            例如[0,0,1,1]表示整个被测设备屏幕
            [0.5,0,1,1]表示屏幕左半部分
            [0,0.5,1,1]表示屏幕下半部分
    """
    device_contour = get_region_contour(region)
    center_x = (device_contour[2] - device_contour[0]) / 2
    center_y = (device_contour[3] - device_contour[1]) / 2
    return [center_x, center_y]  # 返回设备中心点以及长宽


def get_contour_size(region=[0, 0, 1, 1]):
    """获取屏幕像素大小，默认为整个设备屏幕
    Return:
        width, height: 设备长宽
    """
    region_contour = get_region_contour(region)
    width = region_contour[2] - region_contour[0]
    height = region_contour[3] - region_contour[1]
    return width, height


def get_contour_border(direction, length):
    """获取屏幕角落边界坐标"""
    contour = get_region_contour([0, 0, 1, 1])
    direction_switcher = {  # 计算不同方向的移动起点，
        'top': [(contour[0] + contour[2]) / 2, contour[1]],
        'bottom': [(contour[0] + contour[2]) / 2, contour[2]],
        'left': [contour[0], (contour[1] + contour[3]) / 2],
        'right': [contour[2], (contour[1] + contour[3]) / 2],
    }
    coefficient = [1, 1]
    coefficient[0] = contour[0] / abs(contour[0])
    coefficient[1] = contour[1] / abs(contour[1])
    coefficient_switcher = {  # 将滑动距离转换为当前坐标下的移动系数
        'top': [1, coefficient[1]],  # 例 横向移动不变，纵向向屏幕中心移动
        'bottom': [1, -coefficient[1]],
        'left': [coefficient[0], 1],
        'right': [-coefficient[0], 1],
    }
    length[0], length[1] = abs(length[0]), abs(length[1])
    abs_length = [a * b for a, b in zip(length, coefficient_switcher[direction])]
    return direction_switcher[direction], abs_length


def _calculate_device_two_optimized_coordinate_value(device_values, max_judge_value, zoom, rho_and_theta_list,
                                                     device_contour_image):
    def _calculate_two_points_from_rho_and_theta(rho, theta, bound_val):
        a, b = numpy.cos(theta), numpy.sin(theta)
        x0, y0 = a * rho, b * rho
        x1 = int(x0 + bound_val * (-b))
        y1 = int(y0 + bound_val * a)
        x2 = int(x0 - bound_val * (-b))
        y2 = int(y0 - bound_val * a)
        return (x1, y1), (x2, y2)

    def _calculate_line_information(coordinate_1, coordinate_2, binary_image):
        x1, y1 = coordinate_1
        x2, y2 = coordinate_2
        height, width = binary_image.shape[:2]
        point_count = 0
        x_min, y_min = width, height
        x_max, y_max = -1, -1
        xDis, yDis = x2 - x1, y2 - y1
        if (abs(xDis) > abs(yDis)):
            maxstep = abs(xDis)
        else:
            maxstep = abs(yDis)
        xUnitstep, yUnitstep = xDis / maxstep, yDis / maxstep
        x, y = x1, y1
        for _ in range(maxstep):
            x = x + xUnitstep
            y = y + yUnitstep
            x_temp = int(x)
            y_temp = int(y)
            if x_temp < 0 or x_temp >= width or y_temp < 0 or y_temp >= height:
                continue
            if binary_image[y_temp][x_temp] != 255:
                continue
            point_count += 1
            x_min = min(x_min, x_temp)
            x_max = max(x_max, x_temp)
            y_min = min(y_min, y_temp)
            y_max = max(y_max, y_temp)
        if point_count == 0:
            return None
        else:
            return point_count, (x_min, x_max, y_min, y_max)

    def _calculate_min_optimized_coordinate_value(lines_information, device_values):
        device_val_1, device_val_2 = device_values
        max_point_count = max(lines_information, key=lambda x: x[0])[0]
        lines_information.sort(key=lambda info: max(info[1][0], info[1][1]))
        for line_info in lines_information:
            point_count = line_info[0]
            val_min = min(line_info[1][0], line_info[1][1])
            if point_count > max_point_count * POWER_LINE_THICKNESS_RATIO \
                    and abs(device_val_2 - val_min) > abs(device_val_2 - device_val_1) * 0.3:
                device_val_1 = val_min
                break
        return device_val_1

    def _calculate_max_optimized_coordinate_value(lines_information, device_values):
        device_val_1, device_val_2 = device_values
        max_point_count = max(lines_information, key=lambda x: x[0])[0]
        lines_information.sort(key=lambda info: min(info[1][0], info[1][1]), reverse=True)
        for line_info in lines_information:
            point_count = line_info[0]
            val_max = max(line_info[1][0], line_info[1][1])
            if point_count > max_point_count * POWER_LINE_THICKNESS_RATIO \
                    and abs(val_max - device_val_1) > abs(device_val_2 - device_val_1) * 0.3:
                device_val_2 = val_max
                break
        return device_val_2

    lines_information = []
    device_val_1, device_val_2 = device_values
    for rho, theta in rho_and_theta_list:
        point1, point2 = _calculate_two_points_from_rho_and_theta(rho, theta, max(device_val_1, device_val_2))
        line_information = _calculate_line_information(point1, point2, device_contour_image)
        if line_information:
            lines_information.append(line_information)
    if zoom == "x":
        new_lines_information = [(info[0], (info[1][0], info[1][1])) for info in lines_information]
    elif zoom == "y":
        new_lines_information = [(info[0], (info[1][2], info[1][3])) for info in lines_information]
    else:
        raise Exception("Wrong ZOOM!")
    print(new_lines_information)
    if device_val_1 == 0:
        device_val_1 = _calculate_min_optimized_coordinate_value(new_lines_information, device_values)
    if device_val_2 == max_judge_value:
        device_val_2 = _calculate_max_optimized_coordinate_value(new_lines_information, device_values)
    return device_val_1, device_val_2
