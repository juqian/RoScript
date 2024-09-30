import cv2,numpy
from ..models.area import Area
from ..constants import *

def detect(image):
    device_location, device_contour = simple_detect(image)
    device_x1, device_y1 = device_location.lt
    device_x2, device_y2 = device_location.rb
    image_height, image_width = image.shape[:2]
    if device_x1 > 0 and device_y1 > 0 and device_x2 < image_width-1 and device_y2 < image_height-1:
        return device_location
    advanced_device_location = advanced_detect(image, device_contour)
    return advanced_device_location

def simple_detect(image):
    image_height, image_width = image.shape[:2]
    image_size = image_width * image_height
    canny_image = cv2.Canny(image, DEVICE_CANNY_LOW, DEVICE_CANNY_HIGH)
    closed_image = cv2.morphologyEx(canny_image, cv2.MORPH_CLOSE, numpy.ones((DEVICE_CLOSING_KERNEL,DEVICE_CLOSING_KERNEL), numpy.uint8))
    contours, _ = cv2.findContours(closed_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)[-2:]

    # img = image.copy()
    # cv2.drawContours(img, contours, -1, (0, 255, 0), 2)
    # cv2.imwrite("contour.png", img)

    candidate_contour, candidate_bounding_area = None, Area(0,0,0,0)
    for contour in contours:
        x1, y1, w, h = cv2.boundingRect(contour)
        if w*h > candidate_bounding_area.get_size() and w*h < image_size * DEVICE_SIZE_LIMIT_RATIO:
            candidate_contour = contour
            candidate_bounding_area = Area(x1, y1, x1+w, y1+h)
    device_contour = candidate_contour
    device_location = candidate_bounding_area
    return device_location, device_contour

def advanced_detect(image, device_contour):
    image_height, image_width = image.shape[:2]
    device_x1, device_y1, device_w, device_h = cv2.boundingRect(device_contour)
    device_x2, device_y2 = device_x1 + device_w, device_y1 + device_h

    # 直线检测
    repaint_device_contour_image = numpy.zeros((image_height,image_width), numpy.uint8)
    cv2.drawContours(repaint_device_contour_image, [device_contour], -1, color=255, thickness=3)
    lines = cv2.HoughLines(repaint_device_contour_image, rho = 1, theta = numpy.pi/180, threshold = 50, lines = 2)

    # 筛选出水平和垂直方向的直线
    horizon_rho_and_theta_list = []
    vertical_rho_and_theta_list = []
    for line in lines:
        rho, theta = line[0]
        if theta > (1/2 - DEVICE_LEAN_TOLERANCE/180) * numpy.pi and theta < (1/2 + DEVICE_LEAN_TOLERANCE/180) * numpy.pi:
            horizon_rho_and_theta_list.append((rho, theta))
        if theta < DEVICE_LEAN_TOLERANCE/180 * numpy.pi or theta > (1 - DEVICE_LEAN_TOLERANCE/180) * numpy.pi:
            vertical_rho_and_theta_list.append((rho, theta))

    # 轮廓区域优化
    if device_x1 <= 0 or device_x2 >= image_width-1:
        device_x1, device_x2 = _calculate_device_two_optimized_coordinate_value((device_x1, device_x2), image_width, "x", vertical_rho_and_theta_list, repaint_device_contour_image)
    if device_y1 <= 0 or device_y2 == image_height-1:
        device_y1, device_y2 = _calculate_device_two_optimized_coordinate_value((device_y1, device_y2), image_height, "y", horizon_rho_and_theta_list, repaint_device_contour_image)

    return Area(device_x1, device_y1, device_x2, device_y2)


def _calculate_device_two_optimized_coordinate_value(device_values, max_judge_value, zoom, rho_and_theta_list, device_contour_image):
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
        point_count= 0
        x_min, y_min = width, height
        x_max, y_max = -1, -1
        xDis, yDis = x2 - x1, y2 - y1
        if(abs(xDis) > abs(yDis)):
            maxstep = abs(xDis)
        else:
            maxstep = abs(yDis)
        xUnitstep, yUnitstep = xDis/maxstep, yDis/maxstep
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
        max_point_count = max(lines_information,key=lambda x:x[0])[0]
        lines_information.sort(key=lambda info:max(info[1][0],info[1][1]))
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
        max_point_count = max(lines_information,key=lambda x:x[0])[0]
        lines_information.sort(key=lambda info:min(info[1][0],info[1][1]), reverse=True)
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
        new_lines_information = [(info[0], (info[1][0],info[1][1])) for info in lines_information]
    elif zoom =="y":
        new_lines_information = [(info[0], (info[1][2],info[1][3])) for info in lines_information]
    else:
        raise Exception("Wrong ZOOM!")
    if device_val_1 == 0:
        device_val_1 = _calculate_min_optimized_coordinate_value(new_lines_information, device_values)
    if device_val_2 == max_judge_value:
        device_val_2 = _calculate_max_optimized_coordinate_value(new_lines_information, device_values)
    return device_val_1, device_val_2