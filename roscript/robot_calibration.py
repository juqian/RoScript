# -*- coding: utf-8 -*-
"""
Created on Thu Aug 20 15:43:30 2020

@author: 29965
"""

import cv2
import numpy as np
import os
import matplotlib.pyplot as plt
import time
import shutil
from os import path
from config import Config
import robot
from robot_communicate import RobotCommunicate
from sut_monitor import PenMonitor, SutMonitor
import template_match

# circle_to_pen_distance = [-800, -3800]  # Tpad
circle_to_pen_distance = Config.get_circle_to_pen_distance()
# circle_to_pen_distance = [200, -4300]  # 5S

SIGNAL_TIP_FALL = {
    0: 1000,
    1: 500,
    2: 250,
    3: 125,
    4: 50,
}


def plot_tip_fall_sim_trends(match_result_list, touch_idx, tip_fall_step, tip_falling_dir):
    # 因为输入都是Unicode字符，这里使用utf-8，免得来回转换

    title = 'signal_tip_fall_height:{}'.format(SIGNAL_TIP_FALL[tip_fall_step])
    x_data = []
    y_data = []

    touch_x = None
    for i in range(len(match_result_list)):
        file, sim = match_result_list[i]
        name, ext = os.path.splitext(os.path.basename(file))
        x_data.append(name)
        y_data.append(sim)

        if i == touch_idx:
            touch_x = name

    plt.title(title)
    plt.plot(x_data, y_data)

    x = [touch_x, touch_x]
    y = [min(y_data), 1]
    plt.plot(x, y, color='y', label='Touch')

    for i in range(len(match_result_list)):
        x = x_data[i]
        y = y_data[i]
        text = "%0.4f" % y
        plt.text(x, y, text, ha='center', va='bottom', fontsize=11, rotation=0)

    plt.xlabel(r'Image Name')
    plt.ylabel(r'Image similarity')
    plt.savefig(os.path.join(tip_falling_dir, 'fall_round{}.jpg'.format(tip_fall_step)))
    plt.clf()


def hough_circles(img_path,all_circle_img, max_circle_img):
    """ 检测圆形标志圆心在屏幕中的坐标
    Returns:
        circle: 标志物圆心在屏幕中的坐标
    """
    planets = cv2.imread(img_path)
    gray_img = cv2.cvtColor(planets, cv2.COLOR_BGR2GRAY)
    img = cv2.medianBlur(gray_img, 5)

    th, img = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY + cv2.THRESH_TRUNC)

    circles = cv2.HoughCircles(img, cv2.HOUGH_GRADIENT, 1, 120,
                               param1=130, param2=60,
                               minRadius=20, maxRadius=0)
    if circles is not None:
        circles = np.uint16(np.around(circles))
        cimg = cv2.imread(img_path)
        max_radius = 0
        max_circle_x = 0
        max_circle_y = 0
        if len(circles[0,:]) > 1:
            for i in circles[0,:]:
                # 绘制外圈圆（蓝色）
                cv2.circle(cimg, (i[0], i[1]), i[2], (0, 255, 0), 2)
                # 绘制圆心（红色）
                cv2.circle(cimg, (i[0], i[1]), 2, (0, 0, 255), 3)

                x = i[0]-i[2]
                y = i[1]-i[2]
                x2 = i[0]+i[2]
                y2 = i[1]+i[2]

                snap = img[y:y2,x:x2]
                # 计算矩形区域亮度
                mean = cv2.mean(snap)
                # print('矩形区域亮度：', mean[0])

                # 绘制外圈圆（蓝色）
                cv2.circle(cimg, (i[0], i[1]), i[2], (0, 255, 0), 2)

                # 绘制圆心（红色）
                cv2.circle(cimg, (i[0], i[1]), 2, (0, 0, 255), 3)
                cv2.imwrite(all_circle_img, cimg)

                # 亮度太低的不用
                if mean[0] < 100:
                    continue

                if i[2] > max_radius:
                    max_radius = i[2]
                    max_circle_x = i[0]
                    max_circle_y = i[1]

            cimg = cv2.imread(img_path)
            # 绘制外圈圆（蓝色）
            cv2.circle(cimg, (max_circle_x, max_circle_y), max_radius, (0, 255, 0), 2)

            # 绘制圆心（红色）
            cv2.circle(cimg, (max_circle_x, max_circle_y), 2, (0, 0, 255), 3)
            cv2.imwrite(max_circle_img, cimg)
            return np.array([max_circle_x, max_circle_y,max_radius])

        # 可能存在检测出多个圆形区域的情况（新机器上有个螺丝钉也是圆形）
        # 取半径最大的作为检测结果
        circle = circles[0][np.lexsort(-circles[0].T)][0]
        cimg = cv2.imread(img_path)
        # 绘制外圈圆（蓝色）
        cv2.circle(cimg, (circle[0], circle[1]), circle[2], (0, 255, 0), 2)

        # 绘制圆心（红色）
        cv2.circle(cimg, (circle[0], circle[1]), 2, (0, 0, 255), 3)
        cv2.imwrite(max_circle_img,cimg)
        return circle
    else:
        print("circles is None")
        return None

def _hough_circles():
    """ 检测圆形标志圆心在屏幕中的坐标
    Returns:
        circle: 标志物圆心在屏幕中的坐标
    """
    planets = cv2.imread(Config.get_calibration_robot_image())
    gray_img = cv2.cvtColor(planets, cv2.COLOR_BGR2GRAY)
    img = cv2.medianBlur(gray_img, 5)

    # 各项参数含义：
    # img: 8bit单通道灰度图像
    # method:霍夫检测方法，常用为cv2.HOUGH_GRADIENT
    # dp: 检测内侧圆心的累加器图像的分辨率与输入图像之比的倒数
    #     dp=1,累加器和输入图像具有相同的分辨率，
    #     dp=2，累加器宽度和高度均为输入图像的一半
    # minDist: 两个圆圆心之间的最小距离，120
    # 下面两个参数与cv2.HOUGH_GRADIENT对应
    # param1: 默认为100，表示传递给canny边缘检测算子的高阈值
    # param2: 默认为100，表示在检测阶段圆心的累加器阈值，越大，检测出来的圆越完美
    # minRadius: 默认为0，检测出来的圆半径最小值
    # maxRadius: 默认为0，检测出来的圆半径最大值

    circles = cv2.HoughCircles(img, cv2.HOUGH_GRADIENT, 1, 120,
                               param1=130, param2=60,
                               minRadius=20, maxRadius=0)
    if circles is not None:
        circles = np.uint16(np.around(circles))
        # 可能存在检测出多个圆形区域的情况（新机器上有个螺丝钉也是圆形）
        # 取半径最大的作为检测结果
        circle = circles[0][np.lexsort(-circles[0].T)][0]
        return circle
    else:
        return None


def find_screen_touch_step(match_result_list):
    """分析数据，获取落笔点中屏幕位置。返回0表示刚开始到初始位置就符合要求，返回i表示需要i次落笔"""
    slope_list = []
    for i in range(1, len(match_result_list)):
        sim_i = match_result_list[i][1]
        sim_i_1 = match_result_list[i - 1][1]
        slope_list.append(sim_i - sim_i_1)

    for i in range(len(slope_list)):
        # 相似度的增长率开始稳定，不再暴增
        if max(slope_list[i:]) <= 0.003 and abs(sum(slope_list[i:])) <= 0.003:
            return i

        # 倒数第二个图，如果和预期目标相似度很近，可以退出
        if i == 6 and match_result_list[i + 1][1] >= 0.99:
            return 6

    return len(match_result_list) / 2
    #return len(match_result_list) - 1


def _control_pen_move(x, y):
    """控制机械臂横向移动一段距离

    Args:
        x: x轴移动距离
        y: y轴移动距离
    """
    rc = RobotCommunicate()  # 机器人控制指令
    move_time = int((abs(x) + abs(y)) / 10)
    rc.run('XM,{},{},{}\r'.format(move_time, int(x), int(y)))
    rc.close()
    time.sleep(move_time / 1000)


def process_pen_fall_img(image_path):
    """ 处理落笔过程图像，主要是聚焦到笔尖区域 """
    image = cv2.imread(image_path, 0)
    # 图像本身大小
    h, w = image.shape[:2]

    # h:720,w:1280
    if h * w < 1280 * 720:
        # if h * w < 200 * 200:
        # 若为已处理的图像，则不再处理 100*50
        return

    # 旧图保存到如下名称的文件 1.full.png
    img_dir = os.path.dirname(image_path)
    img_name = os.path.basename(image_path)
    name, ext = os.path.splitext(img_name)
    original_img_path = os.path.join(img_dir, "pen_" + name + ".png")
    shutil.copy(image_path, original_img_path)

    # 由于只识别圈出来的笔的点击区域，则根据区域中心确定点击坐标
    x, y = Config.get_tip_fall_center()

    # 确定点击区域，并裁切出图像
    tip_fall_contour = Config.get_tip_contour()
    contour_y, contour_x = tip_fall_contour
    #    print(contour_y,contour_x)
    tip_block_img = image[y - int(contour_y / 2):y + int(contour_y / 2),
                          x - int(contour_x / 2):x + int(contour_x / 2)]
    cv2.imwrite(image_path, tip_block_img)


def match_pen_fall_images(singal_fall_num, start_fall_idx, tip_falling_dir):
    """收集在落笔过程中，每次下落一定高度与最终落笔高度的图像相似度
    Args:
        singal_fall_num: 单次落笔次数
        start_fall_idx: 落笔开始时的计数值
    """
    match_result = []
    # 模板匹配算法选择
    algorithm = template_match.tm_sqdiff_normed_match

    # 模板图片
    tempalted_image_path = '{}/{}.png'.format(tip_falling_dir, singal_fall_num)
    # 处理比对模板图像
    if start_fall_idx == 0:
        process_pen_fall_img(tempalted_image_path)

    # 循环匹配获取图片相似度
    for i in range(1, singal_fall_num + 1):
        # 第一张图像是复位图像，用于机械臂归到指定位置
        # 第二张是落笔开始图像，即为本次落笔的起点位置
        # 机械臂落笔从第二张图像开始
        # 但编号从0开始，正好把第一张图像略过了
        tip_fall_img_path = '{}/{}.png'.format(tip_falling_dir, start_fall_idx + i)
        # 处理图像
        process_pen_fall_img(tip_fall_img_path)
        similarity = algorithm(tempalted_image_path, tip_fall_img_path).get_similarity()
        # sqdiff的match结果是diff，不是sim，要处理一下
        similarity = 1 - similarity
        match_result.append((tip_fall_img_path, similarity))

    return match_result


def _change_circle_to_pen(x, y):
    """修改笔尖与标志圆心的相对距离"""
    circle_to_pen_distance['X'] += x
    circle_to_pen_distance['Y'] += y
    Config.update_circle_to_pen(circle_to_pen_distance)


def _calculate_robot_arm_direction(circle_coordinate_0,
                                   circle_coordinate_1,
                                   circle_coordinate_2):
    """计算机械臂的移动方向
    Args:
        circle_coordinate_0: 机械臂运动起点像素坐标
        circle_coordinate_1: 机械臂在X轴运动2cm后的像素坐标
        circle_coordinate_2: 机械臂在Y轴运动2cm后的像素坐标
    """
    coor_0 = np.array(circle_coordinate_0)[:2]
    coor_1 = np.array(circle_coordinate_1)[:2]
    coor_2 = np.array(circle_coordinate_2)[:2]
    # 将参数类型转换为int，否则做减法运算时，会有数值溢出，
    # 例如918 - 1090 = 65364
    coor_0 = coor_0.astype(np.int16)
    coor_1 = coor_1.astype(np.int16)
    coor_2 = coor_2.astype(np.int16)

    # 分别计算机械臂在x,y方向上运动时，像素坐标的运动方向
    direction_x = coor_1 - coor_0
    direction_y = coor_2 - coor_1

    # 讲机械臂像素移动方向转换成以-1，0，1为参数的矩阵
    if sum(direction_x) > 0:
        direction_x = direction_x / np.max(direction_x)
    else:
        direction_x = direction_x / abs(np.min(direction_x))
    direction_x = direction_x.astype(int)

    if sum(direction_y) > 0:
        direction_y = direction_y / np.max(direction_y)
    else:
        direction_y = direction_y / abs(np.min(direction_y))
    direction_y = direction_y.astype(int)

    # 将两个矩阵转换成一个2*2矩阵，并转置
    # (x,y) = (px,py)(direction_X, direction_Y)
    # 其中，(x,y)是机械臂移动的实际坐标，(px,py)是机械臂移动的像素坐标
    direction_matrix = np.vstack((direction_x, direction_y)).T
    Config.update_robot_layout(direction_matrix)


class RobotCalibration(object):
    """机械设备配置初始化"""

    @staticmethod
    def __move_relative_distance(move_distance, p2r):
        """将机械臂移动图片中的指定像素距离
        Args:
            move_distance: 要移动的目标地址像素坐标
            p2r: 圆心处像素与实际距离转换

        """
        # 将像素距离转换成实际距离
        one_cm_steps = Config.get_one_cm_steps()
        px = int(move_distance[0] / p2r * one_cm_steps)
        py = int(move_distance[1] / p2r * one_cm_steps)
        # 根据相机拍摄方向与机械臂摆放位置计算位置转换
        x, y = robot.normalize_device_direction(px, py)
        print("Move relative distance: x:{},y:{}".format(x,y))
        _control_pen_move(x, y)

    @staticmethod
    def __refresh_arm_origin():
        """重置机械臂初始运动起点状态"""
        rc = RobotCommunicate()  # 机器人控制指令
        rc.run('R\r')
        rc.close()

    @staticmethod
    def __move_pen_to_device_corner():
        """初始化机械臂初始位置"""
        # 计算在设备高度上实际距离与像素距离的转换比例
        p2r = Config.get_scale_rate()
        img_size = Config.get_screenshot_size()  # 图片分辨率，

        # 图像中的设备左上角坐标
        device_corner = Config.get_equipment_contour()[:2]
        pixel_distance = [device_corner[0] - img_size[0] / 2,
                          device_corner[1] - img_size[1] / 2]

        # 计算运动的步进距离
        one_cm_steps = Config.get_one_cm_steps()
        px = int(pixel_distance[0] / p2r * one_cm_steps)
        py = int(pixel_distance[1] / p2r * one_cm_steps)

        # 圆形标志移动到设备轮廓左上角
        x0, y0 = robot.normalize_device_direction(px, py)
        # 机械臂点击器与圆形标志在设备层面上的物理距离
        # 控制机械臂移动到设备左上角
        x = x0 + circle_to_pen_distance['X']
        y = y0 + circle_to_pen_distance['Y']

        print("Arm position initialize: center to corner pixel distance: %s, physical distance: %d, %d, step distance %d, %d (1cm %d steps)"
              %(str(pixel_distance), int(pixel_distance[0] / p2r), int(pixel_distance[1] / p2r), px, py, one_cm_steps))
        print("   normalized step distance %d, %d, move distance %d, %d (pen to circile: %d, %d)"
              %(x0, y0, x, y, circle_to_pen_distance['X'], circle_to_pen_distance['Y']))
        _control_pen_move(x, y)

    @staticmethod
    def __put_circle_to_img_center(initialize_robot_arm_save_dir=None,move_idx=0):
        """将圆形标志移动到图片中心，即摄像设备垂直正下方
        Args:
            move_idx: 校准次数，由于最后精度较小，机器人可能不会进行运动，避免死循环
        """
        # 获取机械臂移动起点标志物坐标
        robot_calib_image_path = Config.get_calibration_robot_image()
        SutMonitor.get_img(robot_calib_image_path, size=[1600, 1200])
        shutil.copyfile(robot_calib_image_path, path.join(initialize_robot_arm_save_dir, str(move_idx)+'.png'))

        time.sleep(0.5)  # 短时间内频繁调用摄像头会导致程序崩溃，因此加个等待时间
        # 获取当前图像并进行圆形检测
        # circle = _hough_circles()
        # 替换
        all_circle_img = path.join(initialize_robot_arm_save_dir, 'all_circle_'+str(move_idx)+'.png')
        max_circle_img = path.join(initialize_robot_arm_save_dir, 'max_circle_'+str(move_idx)+'.png')
        circle = hough_circles(robot_calib_image_path, all_circle_img, max_circle_img)


        # 如果检测不到圆，则给出提示，第一次就检测不到则退出
        if circle is None:
            if move_idx == 0:
                raise Exception("Error: the circular marker on the end of the moving robot arms cannot be detected. \n" +
                    "Please check whether it is covered by electronic wires.")
            else:
                return

        h, w = cv2.imread(Config.get_calibration_robot_image()).shape[:2]  # 图片分辨率，用于


        img_size = [w, h]
        # 已知圆形半径为0.75cm，即可得到当前位置像素与实际距离的转化比例
        m_p2r = circle[2] / 0.75
        # 计算标志物到图片中心的距离
        relative = [img_size[i] / 2 - circle[i] for i in range(2)]
        # 如果标志物离图片中心比较远（x或y方向超过 5 像素），则将标志物移动到图像中心
        if max(abs(r) for r in relative) > 5 and move_idx < 4:
            # 控制机械臂将其圆形标志移动到照片中心
            RobotCalibration.__move_relative_distance(relative, m_p2r)
            # 递归地再开展一次移动，减少误差，避免因为圆形检测出现的误判
            RobotCalibration.__put_circle_to_img_center(initialize_robot_arm_save_dir,move_idx + 1)

    @staticmethod
    def __move_pen_to_device_center(reset=False):
        """将电容笔移动到被测设备中心
        Args:
            reset: True/False 将机械臂移动到原来的位置
        """
        device_contour = Config.get_equipment_contour()
        # 被测设备中心坐标
        device_center = [(device_contour[i + 2] - device_contour[i]) / 2 for i in range(2)]

        # 实际距离与像素坐标的转换
        p2r = Config.get_scale_rate()

        one_cm_steps = Config.get_one_cm_steps()
        # 将图片中的像素坐标转换称实际移动距离和方向
        px = int(device_center[0] / p2r * one_cm_steps)
        py = int(device_center[1] / p2r * one_cm_steps)
        x, y = robot.normalize_device_direction(px, py)
        if reset:
            _control_pen_move(-x, -y)
        else:
            _control_pen_move(x, y)

    @staticmethod
    def __move_surround_device():
        """控制机械臂环绕涉笔轮廓运动"""
        device_contour = Config.get_equipment_contour()
        p2r = Config.get_scale_rate()
        length = device_contour[2] - device_contour[0]
        weight = device_contour[3] - device_contour[1]
        print(weight, length)
        # TODO
        # 获取1cm在物理世界中的距离对应的步进电机步数
        one_cm_steps = Config.get_one_cm_steps()
        px = int(length / p2r * one_cm_steps)
        py = int(weight / p2r * one_cm_steps)

        # 根据相机拍摄方向与机械臂摆放位置计算位置转换
        x, y = robot.normalize_device_direction(px, py)

        # 到每个角落停顿一下，以便观察结果
        _control_pen_move(x, 0)
        time.sleep(0.5)
        _control_pen_move(0, y)
        time.sleep(0.5)
        _control_pen_move(-x, 0)
        time.sleep(0.5)
        _control_pen_move(0, -y)

    @staticmethod
    def __calculate_tip_height(tip_fall_step, last_tip_height, tip_falling_dir, virtual_debug):
        """计算落笔高度
        Arg:
            tip_fall_step: 第几轮落笔
            tip_falling_dir: 数据文件目录
            virtual_debug: 是否启用不连接机器人的虚拟调试模式
        Return:
            pen_down_distance: 落笔高度数值
        """
        # TODO 新机器舵机与旧机器舵机的旋转初始位置不同，
        # 新机器的初始位置相当于旧机器的前半圆，落笔高度的改变相当于抬笔
        # motor_height = 12000  # 12000为舵机的初始高度
        # 第一次落笔，单次落笔高度为1mm，第二次为0.5mm
        # pen_fall_height = SIGNAL_TIP_FALL[tip_fall_step]

        # 新机器初始高度是23000，落笔需要减去数值（装置原因，无法在另一半圆形上落笔）
        motor_height = Config.get_tip_initial_height()  # 12000为舵机的初始高度
        # 第一次落笔，单次落笔高度为1mm，第二次为0.5mm
        if motor_height > 20000:
            # 如果笔的初始高度大于20000，则笔在
            pen_fall_height = -SIGNAL_TIP_FALL[tip_fall_step]
        else:
            pen_fall_height = -SIGNAL_TIP_FALL[tip_fall_step]

        # z轴舵机初始笔位置参数pen_down_position
        # 如果为初次落笔，不需要调整舵机高度
        # 否则，将触屏笔的下落高度抬高上一轮落笔2格，即可对应为本轮落笔的4格
        # 本轮落笔高度=上一轮单次落笔高度/2
        if tip_fall_step == 0:
            pen_down_position = 0
        else:
            pen_down_position = last_tip_height - pen_fall_height * 4
            # pen_down_position = last_tip_height - pen_fall_height * 2

        # 收集的图像编号，同时为本轮的落笔次数
        collect_img_num = 8

        # 落笔首张图像编号，初始为0，其后几次以的后一张图片开始
        # 每次收集的第一张图像都是对笔的调整图像，第二章图像落笔开始的起点图像
        start_fall_img_idx = 0 if tip_fall_step <= 0 else tip_fall_step * (collect_img_num + 1)

        print("tip_fall_step=%d, motor_height=%d, tip_height=%d, pen_fall_height=%d, pen_down_position=%d, start_fall_img_idx=%d" %
             (tip_fall_step, motor_height, last_tip_height, pen_fall_height, pen_down_position, start_fall_img_idx))

        # 收集落笔过程图像
        # TODO
        if not virtual_debug:
            PenMonitor.collect_pen_fall_images(pen_down_position + motor_height,
                                               pen_fall_height,
                                               start_fall_img_idx,
                                               collect_img_num,
                                               tip_falling_dir)

        # 将落笔过程中的图片与最后落笔的图片进行相似度比较，获取相似度变化函数
        match_result_list = match_pen_fall_images(collect_img_num, start_fall_img_idx, tip_falling_dir)

        # 获取相似度曲线拐点横坐标，推测笔和屏幕接触是在哪一子步骤中
        touch_idx = find_screen_touch_step(match_result_list)

        # 生成折线图
        plot_tip_fall_sim_trends(match_result_list, touch_idx, tip_fall_step, tip_falling_dir)
        if tip_fall_step == 4:
            # 最后一轮额外加150单位，约3*0.05mm的高度
            touch_idx += 3

        pen_down_position += pen_fall_height * touch_idx
        print("touch_idx=%d, pen_down_position(tip_height)=%d" % (touch_idx, pen_down_position))
        return pen_down_position

    @staticmethod
    def calibrate_robot_move_direction():
        """校准机械臂在图像中的的移动方向与实际移动之间的转换关系"""
        # 获取机械臂移动起点标志物坐标
        SutMonitor.get_img(Config.get_calibration_robot_image(), size=[1600, 1200])
        circle_coordinate_0 = _hough_circles()
        # 获取机械臂X轴实际移动2000步进长度后标志物坐标
        _control_pen_move(2000, 0)
        SutMonitor.get_img(Config.get_calibration_robot_image(), size=[1600, 1200])
        circle_coordinate_1 = _hough_circles()
        # 获取机械臂Y轴实际移动2000步进长度后标志物坐标
        _control_pen_move(0, 2000)
        SutMonitor.get_img(Config.get_calibration_robot_image(), size=[1600, 1200])
        circle_coordinate_2 = _hough_circles()
        # 机械臂返回初始位置
        _control_pen_move(-2000, -2000)
        # 计算实际与像素的转换关系，并保存到配置文件中
        _calculate_robot_arm_direction(circle_coordinate_0,
                                       circle_coordinate_1,
                                       circle_coordinate_2)

    @staticmethod
    def initialize_robot_arm(initialize_robot_arm_save_dir=None):
        """ 机械臂位置初始化"""
        # 将圆形标志物移动到摄像设备正下方
        RobotCalibration.__put_circle_to_img_center(initialize_robot_arm_save_dir=initialize_robot_arm_save_dir)
        # 移动电容笔到被测设备轮廓左上角
        RobotCalibration.__move_pen_to_device_corner()
        # 初始化机械臂运动起点位置，将运动后的机械臂位置作为运动起点坐标
        RobotCalibration.__refresh_arm_origin()

    @staticmethod
    def calibrate_tip_height(initial_tip_height, tip_fall_step, tip_falling_dir, virtual_debug=False):
        """机械臂电容笔高度初始化
            将电容笔移动到被测设备屏幕中心，并测试落笔高度
            Args:
                initial_tip_height: 较准前的初始落笔高度
                tip_fall_step: 第几轮落笔，当值为-1时，则执行所有的落笔轮次
        """
        # 将机械臂移动到触屏设备屏幕中心
        # if not virtual_debug:
        #     RobotCalibration.__move_pen_to_device_center()

        if tip_fall_step == -1:
            tip_height = initial_tip_height
            # 收集每轮的落笔高度
            for i in range(len(SIGNAL_TIP_FALL)):
                tip_height = RobotCalibration.__calculate_tip_height(i, tip_height, tip_falling_dir, virtual_debug)
        else:
            # 收集本轮的落笔高度
            tip_height = RobotCalibration.__calculate_tip_height(tip_fall_step, initial_tip_height, tip_falling_dir, virtual_debug)

        # if not virtual_debug:
            # 将机械臂移动到触屏设备屏幕左上角（坐标原点）
            # RobotCalibration.__move_pen_to_device_center(reset=True)

        return tip_height

    @staticmethod
    def test_tip_fall():
        """测试落笔"""
        # RobotCalibration.__move_pen_to_device_center()
        pen_initial_height = Config.get_tip_initial_height()
        print("pen_initial_height:", pen_initial_height)
        tip_height = Config.get_tip_height()

        #note4  -4800  -6000
        #pad  -5400 -6900
        #5s  -5400 -7000
        print("tip_height:", tip_height)

        from robot_communicate import RobotCommunicate
        rc = RobotCommunicate()
        rc.run("SC,5,{}\r".format(pen_initial_height + tip_height))
        rc.run("SP,0,{}\r".format(int(abs(tip_height / 10))))
        rc.run("SP,1,{}\r".format(int(abs(tip_height / 10))))
        rc.close()
        # RobotCalibration.__move_pen_to_device_center(reset=True)

    @staticmethod
    def control_robot_arm_move(arm_move_circle, x, y):
        """控制机械臂运动
        Args:
            arm_move_circle: 
                True：环绕设备一周
                False：控制机械臂微调
            x,y: 移动相对距离，用于设备位置微调
        """
        if arm_move_circle:
            RobotCalibration.__move_surround_device()
        else:
            _control_pen_move(x, y)
            _change_circle_to_pen(x, y)
            RobotCalibration.__refresh_arm_origin()

    @staticmethod
    def get_tip_status_img():
        # 获取落笔状态图像
        RobotCalibration.__move_pen_to_device_center()
        PenMonitor.get_tip_status_img()
        RobotCalibration.__move_pen_to_device_center(reset=True)

    @staticmethod
    def pen_to_device_center(reset=False):
        RobotCalibration.__move_pen_to_device_center(reset=reset)

