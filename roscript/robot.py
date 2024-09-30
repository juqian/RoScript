# -*- coding: utf-8 -*-
"""
Connect the robot
"""
import os
import math
import numpy as np

from test_script import TestScript
from config import Config
import contour
import screenshot
from sut_monitor import SutMonitor
from command_queue import CommandQueue

# 规避运动过程中远离离屏幕坐标系的距离，
# 防止机械臂遮挡屏幕，
# 但是对于大屏幕的设备，机械臂的运动范围可能会小于屏幕长度
MOVE_OUTSIDE_DISTANCE = {
    1: 2000,
    2: 1000,
    3: 700,
    4: 300,
    5: 0,
}

g_one_cm_steps = Config.get_one_cm_steps()  # 步进电机运动1cm需要的步进距离
pen_initial_height = Config.get_tip_initial_height()

PRESS_TIME = Config.get_press_time()  # 长按时间
DOUBLE_CLICK_TIME = Config.get_double_click_time()  # 双击时间
DETOUR_STEP_THRESHOLD = Config.get_detour_step_threshold()  # 获取分步规避阈值
DETOUR_STEP_DISTANCE = Config.get_detour_step_distance()  # 获取分步规避单次移动距离


def normalize_device_direction(sx, sy):
    """ 将像素运动方向转换成物理世界的运动方向
    主要负责运动方向的转换，不涉及数值的计算
    
    Args:
        sx, sy: 经计算后的机械臂运动步进距离
    
    Return: 
        [x,y]: 旋转后的机械臂x,y在机器人坐标系移动坐标距离
        (x,y) = (px,py)direction_matrix
    """
    # 获取机械臂布局矩阵
    direction_matrix = np.array(Config.get_robot_layout())
    # 机械臂移动的距离和方向
    # 根据矩阵乘法公式，获取机械臂实际的移动坐标和方向
    x, y = np.dot(np.array([sx, sy]), direction_matrix)
    return [x, y]


class Robot(object):
    """Some function that controls the motion of the machine.
    
    Attributes:
        temp_image_index: int, the index of the temporary image
        
        log: log take photo time.
        virtual_debug: debug in virtual test.
        sut: sut monitor
        cq: The queue in which the instructions are stored and the execution
            and use of the instructions are controlled.
        action_duration: Record the execution time of the duty action.
        robot_current_coordinates: The coordinates of the manipulator in the screen coordinate system.
    """

    def __init__(self, log, virtual_debug=False):
        self.temp_image_index = 0  # 实验图像编号
        self.log = log  # 记录拍照时间
        self.virtual_debug = virtual_debug  # 虚拟调试

        self.sut = SutMonitor()  # 视频监控
        self.cq = CommandQueue()  # 机器人指令队列

        self.action_duration = 0  # 指令动作持续时间

        self.robot_current_coordinates = np.array([0, 0])  # 机械臂在机器人坐标系内的坐标(物理距离)
        # 分析在不同方向上的规避许可
        self.x_evadable, self.y_evadable = self.__analyze_evdable_direction()

    def __record_cur_position(self, *coordinate):
        """记录当前机械臂在机器人坐标系的坐标
        
        Args:
            coordinate:坐标系坐标
        """
        if len(coordinate) == 1:
            x, y = coordinate[0]
        else:
            x, y = coordinate
        self.robot_current_coordinates = np.array([int(x), int(y)])

    def __robot_step(self, pixel_distance):
        """将像素距离转换成机器人物理运动步进距离
        
        Args:
            pixel_distance: 像素运动距离
            g_step_by_cm: 1cm物理运动，对应的步进运动距离
        Returns:
            step_distance: 物理运动距离，1cm=g_step_by_cm步step
        """
        p2r = Config.get_scale_rate()
        step_distance = float(pixel_distance / p2r * g_one_cm_steps)
        return int(step_distance)

    def __robot_steps_to_pixels(self, robot_steps):
        """将机器人物理运动步进距离转换成像素距离"""
        p2r = Config.get_scale_rate()
        pixel_distance = int((robot_steps / g_one_cm_steps) * p2r)
        return pixel_distance

    # 获取当前坐标
    def get_current_coordinates(self):
        """获取机器人当前坐标"""
        return self.robot_current_coordinates.tolist()

    # 返回一个完整的动作持续时间
    def get_action_exec_time(self):
        """获取当前动作持续时间"""
        return self.action_duration

    # 计算移动时间
    def __calculate_move_time(self, x, y,
                              motor_speed=Config.get_motor_speed()):
        """计算机械臂移动指定距离电机所需时间
        
        Args:
            x,y: int, 移动横纵坐标
            motor_A_move: 电机A转动距离
            motor_B_move: 电机B转动距离
            motor_speed: int, the speed of the robot motor,
                         The minimum speed at which the EBB can generate steps 
                         for each motor is 1.31 steps/second. 
                         The maximum speed is 25 kSteps/second.
            max_motor_move: 在相同时间内电机最大的转动量
            move_time: 转动时间
        """
        motor_A_rotation = x + y
        motor_B_rotation = x - y

        max_motor_rotation = max(abs(motor_A_rotation), abs(motor_B_rotation))
        motor_rotation_time = float(max_motor_rotation / motor_speed)
        return motor_rotation_time

    # 计算落笔时间
    def __estimate_pen_fall_height(self):
        # 获取笔的高度、设备厚度、笔的高度落差和机械臂的最大移动范围

        global g_one_cm_steps
        tip_altitude = Config.get_tip_height()  # 笔尖到屏幕的距离
        pen_high_dead = Config.get_pen_high_dead()  # 机械臂XY两轴的高度落差
        if pen_high_dead[0] == 0 and pen_high_dead[1] == 0:
            # 新机器比较稳定，几乎不存在落笔高度的误差
            return tip_altitude

        robot_arm_range = Config.get_robot_arm_range()  # 机械臂的移动范围

        # 计算笔高的变化速率，
        # 受杠杆作用影响，机械臂在不同位置高度笔的高度有差异，但可以视为在X轴上的线性变化
        # 毫米(mm)级
        # 配置文件中计算出来的笔的高度为笔在设备屏幕中心的高度
        # 根据笔的实际移动距离计算笔的高度
        one_cm_height_change_x = pen_high_dead[0] / robot_arm_range[0]  # 1cm内笔的高度变化率
        one_cm_height_change_y = pen_high_dead[1] / robot_arm_range[1]  # 1cm内笔的高度变化率
        # 机械臂当前在Y轴上的坐标
        current_coordinate_x = self.robot_current_coordinates[0]
        current_coordinate_y = self.robot_current_coordinates[1]

        # 被测设备中心坐标
        device_center = contour.get_contour_center()

        # 实际距离与像素坐标的转换
        p2r = Config.get_scale_rate()
        # 将图片中的像素坐标转换称实际移动距离和方向
        px = int(device_center[0] / p2r * g_one_cm_steps)
        py = int(device_center[1] / p2r * g_one_cm_steps)
        device_center_x, device_center_y = normalize_device_direction(px, py)

        # 当前坐标到设备中心在Y轴上的距离
        # 落笔检测检测出的是触屏笔在屏幕中心的点击高度
        # 因此需要计算当前坐标距离屏幕中心的距离
        # TODO, 计算出一个公式来
        relative_distance_X = device_center_x - current_coordinate_x
        relative_distance_Y = device_center_y - current_coordinate_y

        pen_fall_x = math.ceil(one_cm_height_change_x * relative_distance_X / 5)
        pen_fall_y = math.ceil(one_cm_height_change_y * relative_distance_Y / 5)

        pen_fall_x *= 1.5 if relative_distance_X > 0 else 1.3
        pen_fall_y *= 1.2 if relative_distance_Y > 0 else 1.5

        pen_fall_height = tip_altitude + pen_fall_x + pen_fall_y
        #        print('robot.py line: 201. pen_fall_height:', pen_fall_height)
        return int(pen_fall_height)

    # 计算不同action运动时间
    def __estimate_action_time(self, action_type, x=0, y=0, dx=0, dy=0,
                               press_time=PRESS_TIME):
        """ 计算不同的action运动时间
        Args:
            action_type: action类型
            x,y: 本次运动的步进距离
            dx,dy: action动作执行过程中的运动步进距离，例如swipe中间的滑动
            press_time=PRESS_TIME: 长按时间
        """
        pen_fall_height = self.__estimate_pen_fall_height()
        if action_type == 'click':
            """click time"""
            fall_pen_time = pen_fall_height / 10000
            action_wait_time = fall_pen_time * 2

        elif action_type == 'move':
            """move time"""
            move_time = self.__calculate_move_time(x, y)
            action_wait_time = move_time

        elif action_type == 'double click':
            """double click time"""
            fall_pen_time = pen_fall_height / 10000
            double_click_fall_pen_time = 0.2
            action_wait_time = (fall_pen_time + double_click_fall_pen_time) * 2

        elif action_type == 'swipe':
            """swipe time"""
            fall_pen_time = pen_fall_height / 10000
            move_time = self.__calculate_move_time(x, y, motor_speed=10000)
            action_wait_time = move_time + fall_pen_time * 2

        elif action_type == 'long press':
            """long press time"""
            fall_pen_time = pen_fall_height / 10000
            action_wait_time = fall_pen_time * 2 + press_time

        elif action_type == 'drag':
            """drag time"""
            fall_pen_time = pen_fall_height / 10000
            drag_time = self.__calculate_move_time(x, y, motor_speed=10000)
            action_wait_time = drag_time + fall_pen_time * 2

        elif action_type == 'press drag':
            """press drag time"""
            fall_pen_time = pen_fall_height / 10000
            drag_time = self.__calculate_move_time(x, y, motor_speed=10000)
            action_wait_time = drag_time + fall_pen_time * 2 + press_time

        elif action_type == 'reset':
            """reset time"""
            reset_time = self.__calculate_move_time(x, y)
            action_wait_time = reset_time
        elif action_type == 'pen down':
            "pen down"
            action_wait_time = pen_fall_height / 10000
        else:
            action_wait_time = 0

        self.action_duration = action_wait_time

    def __analyze_evdable_direction(self):
        """分析在不同方向规避的可行性"""
        # 获取屏幕轮廓的物理长宽
        contour_size = contour.get_contour_size()
        size = [0, 0]  # 屏幕长宽
        size_x = self.__robot_step(contour_size[0])
        size_y = self.__robot_step(contour_size[1])
        size = normalize_device_direction(size_x, size_y)  # 屏幕长宽转为实际长宽

        # 获取机械臂的可移动范围
        one_cm_steps = Config.get_one_cm_steps()
        robot_arm_range = np.array(Config.get_robot_arm_range()) * one_cm_steps
        coordinate_range = normalize_device_direction(robot_arm_range[0],
                                                      robot_arm_range[1])
        x_evadable = True
        y_evadable = True
        if abs(size[0]) > abs(coordinate_range[0]) - 7 * one_cm_steps:
            y_evadable = False
        if abs(size[1]) > abs(coordinate_range[1]) - 5 * one_cm_steps:
            x_evadable = False
        #        print('size::', size)
        #        print('coordinate_range:', coordinate_range)
        #        print('x_evadable, y_evadable:', x_evadable, y_evadable)
        return x_evadable, y_evadable

    # 控制机械臂移动和等待时间
    def __control_robot_move(self, x, y):
        """控制机械臂运动指定距离
        Args:
            x,y: 机械臂运动的实际横纵坐标
        """
        # 判断是否需要等待上个动作执行完毕
        self.cq.do_necessary_wait('move')
        # 计算当前动作执行总时间
        self.__estimate_action_time('move', x, y)
        move_time = math.ceil(self.__calculate_move_time(x, y) * 1000)
        # 参数: 坐标、移动时间
        # 指令加入到脚本指令队列中
        action_commands = []
        action_commands.append('XM,{},{},{}\r'.format(move_time, int(x), int(y)))
        # 这一句是为了等待机械臂挺稳，避免滑动造成误差
        action_commands.append('XM,{},0,0\r'.format(100))
        # 将指令集合加入到指令队列中
        self.cq.put(action_commands)

    # 控制机械臂移动相对距离
    def move(self, lx, ly):
        """控制机械臂移动相对距离
        Args:
            lx, ly: 机械臂移动的相对距离，单位厘米(cm)
        """
        global g_one_cm_steps
        move_distance = np.array([int(lx * g_one_cm_steps), int(ly * g_one_cm_steps)])
        # 计算机器人坐标系内移动的目标坐标
        target_x, target_y = self.robot_current_coordinates + move_distance
        #        print(target_x,target_y)
        #        print(self.robot_current_coordinates)
        self.__record_cur_position(target_x, target_y)
        if self.virtual_debug:
            return
        self.__control_robot_move(move_distance[0], move_distance[1])

    def drag(self, x1, y1, x2, y2):
        """
        Args:
            x1,y1: 拖拽运动起点像素坐标
            x2,y2: 拖拽运动终点像素坐标
        """
        px1 = self.__robot_step(x1)
        py1 = self.__robot_step(y1)
        px2 = self.__robot_step(x2)
        py2 = self.__robot_step(y2)

        # 计算运动起点到终点的步进运动距离
        dx, dy = normalize_device_direction(px2 - px1, py2 - py1)
        origin_coordinate = normalize_device_direction(px1, py1)

        relative_x, relative_y = origin_coordinate - self.robot_current_coordinates

        # 记录当前机械臂的坐标
        current_x, current_y = normalize_device_direction(px2, py2)
        self.__record_cur_position(current_x, current_y)

        # 计算机械臂与第一个目标之间的相对位置
        if self.virtual_debug:
            return

        # 先控制机械臂移动到指定位置
        self.__control_robot_move(relative_x, relative_y)

        # 执行拖拽动作

        self.cq.do_necessary_wait('drag')
        # 等待上个动作执行完毕
        self.__estimate_action_time('drag', dx, dy)
        # 拖拽，
        # 参数： 坐标、拖拽时间、落笔时间
        # 拖拽运动速度为10000步进/s
        drag_move_time = math.ceil(
            self.__calculate_move_time(dx, dy, motor_speed=10000) * 1000)
        pen_fall_height = self.__estimate_pen_fall_height()
        pen_fall_time = int(abs(pen_fall_height / 10))

        action_commands = []
        action_commands.append('SC,5,{}\r'.format(pen_initial_height + pen_fall_height))
        action_commands.append('SP,0,{}\r'.format(pen_fall_time))
        # 加此部分是为了等待笔的完全落笔，否则会导致在滑动开始时触屏笔没有完全落下的现象
        action_commands.append('XM,{},0,0\r'.format(50))
        action_commands.append('XM,{},{},{},\r'.format(
            drag_move_time, int(dx), int(dy)))
        action_commands.append('XM,{},0,0\r'.format(50))
        action_commands.append('SC,4,{}\r'.format(pen_initial_height))
        action_commands.append('SP,1,{}\r'.format(pen_fall_time + 50))
        # 将指令集合加入到指令队列中
        self.cq.put(action_commands)

    # 长按后拖拽，参数：拖拽起点坐标、终点坐标、长按时间
    def press_drag(self, x1, y1, x2, y2, press_time=PRESS_TIME):
        """
        Args:
            x1,y1: 拖拽运动起点像素坐标
            x2,y2: 拖拽运动终点像素坐标
        """
        px1 = self.__robot_step(x1)
        py1 = self.__robot_step(y1)
        px2 = self.__robot_step(x2)
        py2 = self.__robot_step(y2)

        dx, dy = normalize_device_direction(px2 - px1, py2 - py1)  # 两个目标之间的相对距离
        # 机器人坐标系中的移动距离
        origin_coordinate = normalize_device_direction(px1, py1)
        # 计算机械臂与第一个目标之间的相对位置
        relative_x, relative_y = origin_coordinate - self.robot_current_coordinates

        # 计算并记录运动完后的机械臂坐标    
        current_x, current_y = normalize_device_direction(px2, py2)
        self.__record_cur_position(current_x, current_y)
        if self.virtual_debug:
            return

        # 先控制机械臂移动到指定位置
        self.__control_robot_move(relative_x, relative_y)

        self.cq.do_necessary_wait('press drag')
        # 等待上个动作执行完毕
        self.__estimate_action_time('press drag', dx, dy)
        # 长按后拖拽，
        # 参数： 坐标、拖拽时间、长按时间、落笔时间
        # 机器人长按时间1s=1000数值
        # 拖拽运动速度为10000步进/s
        press_time = math.ceil(press_time * 1000)
        drag_move_time = math.ceil(
            self.__calculate_move_time(dx, dy, motor_speed=10000) * 1000)
        pen_fall_height = self.__estimate_pen_fall_height()
        pen_fall_time = math.ceil(abs(pen_fall_height / 10))

        action_commands = []
        action_commands.append('SC,5,{}\r'.format(pen_initial_height + pen_fall_height))
        action_commands.append('SP,0,{}\r'.format(pen_fall_time))
        # 加此部分是为了等待笔的完全落笔，否则会导致在滑动开始时触屏笔没有完全落下的现象
        action_commands.append('XM,{},0,0\r'.format(pen_fall_time))
        action_commands.append('XM,{},0,0\r'.format(press_time))
        action_commands.append('XM,{},{},{}\r'.format(drag_move_time,
                                                      int(dx), int(dy)))
        action_commands.append('XM,{},0,0\r'.format(50))
        action_commands.append('SC,4,{}\r'.format(pen_initial_height))
        action_commands.append('SP,1,{}\r'.format(pen_fall_time))
        # 加此部分是为了等待笔的完全抬高，否则容易出现抬笔过程中对其他控件产生拖拽现象
        action_commands.append('XM,{},0,0\r'.format(100))
        # 将指令集合加入到指令队列中
        self.cq.put(action_commands)

    @classmethod
    def snap_screen(self):
        # 接收当前截图的图像信息
        snap_path = os.path.realpath(TestScript.script_snapscreen_path())
        print(snap_path)
        # 获取_snap_screen.png 图像
        SutMonitor.get_img(snap_path)
        screenshot.crop_snap_screen(snap_path)

    # 获取当前图像编号（虚拟调试）
    def get_virtual_debug_index(self):
        self.temp_image_index += 1
        return self.temp_image_index

    def get_detour_frame_path(self):
        """获取规避运动中的视频帧"""
        # TODO 加一个对规避运动过程的判断
        self.cq.do_necessary_wait('detour')
        self.sut.record_detour_frame()
        return TestScript.get_detour_image_path()

    def get_photo_index(self, command, save_frame=False):
        """记录拍照时间和编号，接收操作过程中的图像编号（实际运行）
        Args:
            command: 拍照时的指令，某些指令需要指令完全结束后才能进行拍照
            save_frame: 保存视频图像帧，默认为False
        Returns:
            temp_image_index: 临时图像编号
        """
        self.temp_image_index += 1
        if self.virtual_debug:
            return self.temp_image_index

        if save_frame:  # 规避运动保存视频帧
            return self.temp_image_index
        self.cq.do_necessary_wait(command)
        self.log.record_TP_start()
        self.sut.take_photo(self.temp_image_index)
        # 记录拍照时间
        self.log.record_TP_result(self.temp_image_index)
        return self.temp_image_index

    # 滑动操作起始位置相对距离
    def __swipe_origin(self, region_contour, region_size, dx, dy):
        """ 屏幕中心点到swipe起点的距离
        
        Args:
            region_contour: 滑动区域在屏幕中的像素轮廓[x,y,x+w,y+h]
            region_size: 区域分辨率[w,h]
            dx,dy: int,滑动起点据屏幕中心的长度
        Return:
            px, py: 机械臂预计滑动的实际滑动距离
        """

        # 设备屏幕在图像中的轮廓[x,y,x+w,y+h]
        screen_contour = contour.get_region_contour()
        # 设备屏幕区域中心点在机器人运动坐标系中的坐标
        # 计算公式：区域像素坐标 + 半个区域分辨率 - 屏幕左上角在图像中的像素坐标
        region_center = [region_contour[i] + region_size[i] / 2 - screen_contour[i] for i in range(2)]
        # 计算滑动起点坐标
        origin_x = region_center[0] - dx * 1 / 3
        origin_y = region_center[1] - dy * 1 / 3
        px = self.__robot_step(origin_x)
        py = self.__robot_step(origin_y)
        return px, py

    def swipe(self, region, direction):
        """
        Args:
            region: 滑动区域
            direction: 滑动方向
        """
        # 获取滑动区域轮廓
        region_contour = contour.get_region_contour(region)
        region_size = contour.get_contour_size(region)
        swipe_x, swipe_y = 0, 0  # 滑动横纵坐标长度

        swipe_dc = 2 / 3  # 滑动距离系数，全称Swipe distance coefficient

        # 滑动计算步骤：
        # 1、控制机械臂运动到滑动起点:
        #   首先获取滑动起点实际坐标px,py
        #   其次将起点像素坐标转换成机械臂运动实际坐标swipe_start_coor
        #   最后计算机械臂运动到滑动起点的相对运动距离relative_origin_x,relative_origin_y
        # 2、确定滑动方向和距离
        #   首先根据滑动方向计算在该方向上的机械臂滑动像素长度dx,dy
        #   其次将像素长度转换为机械臂运动距离swipe_x,swipe_y
        #   最后再根据起点坐标(px, py)和滑动距离(swipe_x,swipe_y)
        #   记录运动后的终点坐标(swipe_end_x, swipe_end_y)

        if direction == 'up':  # 向上滑动
            # 计算滑动操作起点坐标
            px, py = self.__swipe_origin(region_contour, region_size, 0, -region_size[1])
            swipe_start_coor = normalize_device_direction(px, py)  # 将图像坐标系转换成机械臂坐标系

            # 计算当前位置到滑动起点的相对距离
            relative_origin_x, relative_origin_y = swipe_start_coor - self.robot_current_coordinates
            # 计算在y轴方向滑动距离,并转换成实际移动距离(半个操作空间长度)
            dy = region_size[1] * swipe_dc  # 在y轴方向滑动距离
            swipe_y = -self.__robot_step(dy)

        elif direction == 'down':  # 向下滑动
            # 计算滑动操作起点坐标
            px, py = self.__swipe_origin(region_contour, region_size, 0, region_size[1])
            swipe_start_coor = normalize_device_direction(px, py)  # 将图像坐标系转换成机械臂坐标系

            # 计算当前位置到滑动起点的相对距离
            relative_origin_x, relative_origin_y = swipe_start_coor - self.robot_current_coordinates
            # 计算在y轴方向滑动距离,并转换成实际移动距离(半个操作空间长度)
            dy = region_size[1] * swipe_dc
            swipe_y = self.__robot_step(dy)

        elif direction == 'left':  # 向左滑动
            # 计算滑动操作起点坐标
            px, py = self.__swipe_origin(region_contour, region_size, -region_size[0], 0)
            swipe_start_coor = normalize_device_direction(px, py)  # 将图像坐标系转换成机械臂坐标系

            # 计算当前位置到滑动起点的相对距离
            relative_origin_x, relative_origin_y = swipe_start_coor - self.robot_current_coordinates
            # 计算在x轴方向滑动距离,并转换成实际移动距离(半个操作空间长度)
            dx = region_size[0] * swipe_dc
            swipe_x = -self.__robot_step(dx)

        elif direction == 'right':  # 向右滑动
            # 计算滑动操作起点坐标
            px, py = self.__swipe_origin(region_contour, region_size, region_size[0], 0)
            swipe_start_coor = normalize_device_direction(px, py)  # 将图像坐标系转换成机械臂坐标系

            # 计算当前位置到滑动起点的相对距离
            relative_origin_x, relative_origin_y = swipe_start_coor - self.robot_current_coordinates
            # 计算在x轴方向滑动距离,并转换成实际移动距离(半个操作空间长度)
            dx = region_size[0] * swipe_dc
            swipe_x = self.__robot_step(dx)

        else:
            self.release()
            raise Exception('No Right Direction')

            # 将滑动相对距离转换成机械臂移动的实际位移
        robot_swipe_x, robot_swipe_y = normalize_device_direction(swipe_x, swipe_y)
        # 计算滑动操作终点坐标
        swipe_end_x = swipe_start_coor[0] + int(robot_swipe_x)
        swipe_end_y = swipe_start_coor[1] + int(robot_swipe_y)

        self.__record_cur_position(swipe_end_x, swipe_end_y)  # 记录移动后的机器人坐标

        swipe_start_pixel_x = self.__robot_steps_to_pixels(px)
        swipe_start_pixel_y = self.__robot_steps_to_pixels(py)
        swipe_pixel_dx = self.__robot_steps_to_pixels(swipe_x)
        swipe_pixel_dy = self.__robot_steps_to_pixels(swipe_y)
        if self.virtual_debug:
            return swipe_start_pixel_x, swipe_start_pixel_y, swipe_pixel_dx, swipe_pixel_dy

            # 先控制机械臂移动到指定起点位置
        self.__control_robot_move(relative_origin_x, relative_origin_y)

        self.cq.do_necessary_wait('swipe')
        # 等待上个动作执行完毕
        # 移动到滑动起始位置
        self.__estimate_action_time('swipe', robot_swipe_x, robot_swipe_y)
        # 计算滑动移动时间
        # 长按后拖拽，
        # 参数： 坐标、滑动时间、落笔时间
        swipe_move_time = math.ceil(
            self.__calculate_move_time(
                robot_swipe_x, robot_swipe_y, motor_speed=10000) * 1000)
        pen_fall_height = self.__estimate_pen_fall_height()
        pen_fall_time = math.ceil(abs(pen_fall_height / 10))
        # 生成机器执行指令集合
        action_commands = []
        action_commands.append('SC,5,{}\r'.format(pen_initial_height + pen_fall_height))
        action_commands.append('SP,0,{}\r'.format(pen_fall_time))
        # 加此部分是为了等待笔的完全落笔，否则会导致在滑动开始时触屏笔没有完全落下的现象
        action_commands.append('XM,{},0,0\r'.format(100))
        action_commands.append('XM,{},{},{}\r'.format(swipe_move_time,
                                                      int(robot_swipe_x), int(robot_swipe_y)))
        action_commands.append('SC,4,{}\r'.format(pen_initial_height))
        action_commands.append('SP,1,{}\r'.format(pen_fall_time + 50))
        # 加此部分是为了等待笔的完全抬高，否则容易出现抬笔过程中对其他控件产生拖拽现象
        action_commands.append('XM,{},0,0\r'.format(100))
        # 将指令集合加入到指令队列中
        self.cq.put(action_commands)

        return swipe_start_pixel_x, swipe_start_pixel_y, swipe_pixel_dx, swipe_pixel_dy

    def click(self, x, y):
        """点击目标坐标
        Args:
            x,y: 点击目标像素坐标点
        """
        px = self.__robot_step(x)
        py = self.__robot_step(y)
        robot_target_coor = normalize_device_direction(px, py)  # 像素转换成实际距离

        # 计算当前位置到滑动起点的相对距离
        relative_x, relative_y = robot_target_coor - self.robot_current_coordinates

        self.__record_cur_position(robot_target_coor)  # 记录当前机械臂坐标
        # 点击前机械臂与目标控件的相对位置
        if self.virtual_debug:
            return

        # 移动到动作起始位置
        self.__control_robot_move(relative_x, relative_y)

        self.cq.do_necessary_wait('click')
        # 判断等待上个动作执行完毕
        self.__estimate_action_time('click')
        # 计算落笔时间
        # 点击
        # 参数： 落笔时间
        pen_fall_height = self.__estimate_pen_fall_height()
        pen_fall_time = math.ceil(abs(pen_fall_height / 10))
        #        print('pen_fall_height:', pen_fall_height)
        action_commands = ['SC,5,{}\r'.format(pen_initial_height + pen_fall_height),
                           'SP,0,{}\r'.format(pen_fall_time),
                           'SC,4,{}\r'.format(pen_initial_height),
                           'SP,1,{}\r'.format(pen_fall_time + 50),
                           # 加此部分是为了等待笔的完全抬高，否则容易出现抬笔过程中对其他控件产生拖拽现象
                           'XM,{},0,0\r'.format(100)]
        # 将指令集合加入到指令队列中
        self.cq.put(action_commands)

    def double_click(self, x, y, double_fall_time=DOUBLE_CLICK_TIME):
        """点击目标坐标
        Args:
            x,y: 双击目标点像素坐标
            double_fall_time: 双击间隔时间
        """
        px = self.__robot_step(x)
        py = self.__robot_step(y)
        robot_move_coor = normalize_device_direction(px, py)  # 像素转换成实际距离

        # 计算当前位置到滑动起点的相对距离
        relative_x, relative_y = robot_move_coor - self.robot_current_coordinates
        # 记录当前机械臂的坐标
        self.__record_cur_position(robot_move_coor)

        if self.virtual_debug:
            return True
        # 控制机械臂移动到双击位置
        self.__control_robot_move(relative_x, relative_y)

        self.cq.do_necessary_wait('double click')
        # 判断等待上个动作执行完毕
        self.__estimate_action_time('double click')
        # 计算落笔时间
        # 双击击
        # 参数： 单次落笔时间
        pen_fall_height = self.__estimate_pen_fall_height()
        pen_fall_time = math.ceil(abs(pen_fall_height / 10))
        double_click_interval = math.ceil(double_fall_time * 1000)

        hover_distance = 1000
        # 转化成对应的机器指令
        action_commands = ['SC,5,{}\r'.format(pen_initial_height + pen_fall_height + hover_distance),
                           'SP,0,{}\r'.format(pen_fall_time),
                           'SC,5,{}\r'.format(pen_initial_height + pen_fall_height),
                           'SP,0,{}\r'.format(hover_distance // 10),
                           'SP,1,{}\r'.format(double_click_interval),
                           'SP,0,{}\r'.format(double_click_interval + 20),
                           'SC,4,{}\r'.format(pen_initial_height),
                           'SP,1,{}\r'.format(pen_fall_time + 50),
                           # 加此部分是为了等待笔的完全抬高，否则容易出现抬笔过程中对其他控件产生拖拽现象
                           'XM,{},0,0\r'.format(100)]
        # 将指令集合加入到指令队列中
        self.cq.put(action_commands)

    def long_press(self, x, y, press_time=PRESS_TIME):
        """在目标坐标处控制点击器长按
        Args:
            x,y: 长按目标点像素坐标
            press_time:长按时间，默认为配置文件中配置的时间
        """
        px = self.__robot_step(x)
        py = self.__robot_step(y)

        robot_move_coor = normalize_device_direction(px, py)  # 像素转换成实际距离

        # 计算当前位置到滑动起点的相对距离
        relative_x, relative_y = robot_move_coor - self.robot_current_coordinates
        # 记录当前机械臂的坐标
        self.__record_cur_position(robot_move_coor)

        if self.virtual_debug:
            return

        # 控制机械臂移动到长按位置
        self.__control_robot_move(relative_x, relative_y)

        # 长按控制
        self.cq.do_necessary_wait('long press')
        # 判断等待上个动作执行完毕
        self.__estimate_action_time('long press')
        # 计算落笔时间
        # 点击
        # 参数： 落笔时间、长按时间
        pen_fall_height = self.__estimate_pen_fall_height()
        pen_fall_time = math.ceil(abs(pen_fall_height / 10))
        press_time = math.ceil(press_time * 1000)

        # 转化成对应的机器指令
        action_commands = ['SC,5,{}\r'.format(pen_initial_height + pen_fall_height),
                           'SP,0,{}\r'.format(pen_fall_time),
                           'XM,{},0,0\r'.format(press_time),
                           'SC,4,{}\r'.format(pen_initial_height),
                           'SP,1,{}\r'.format(pen_fall_time + 50),
                           # 加此部分是为了等待笔的完全抬高，否则容易出现抬笔过程中对其他控件产生拖拽现象
                           'XM,{},0,0\r'.format(100)]
        # 将指令集合加入到指令队列中
        self.cq.put(action_commands)

    # 将机械臂移出屏幕坐标系
    # 计算当前机械臂位置，以及该往哪个角落移动
    def move_outside_of_screen(self):
        """整体规避动作函数"""
        contour_center = contour.get_contour_center()
        # 获取实际情况下到屏幕中心点的距离
        center_x = self.__robot_step(contour_center[0])
        center_y = self.__robot_step(contour_center[1])
        # 计算屏幕中心点实际坐标
        screen_center_coordinates = normalize_device_direction(center_x, center_y)

        # 计算在不同方向上规避运动的目标坐标
        # 坐标系：屏幕坐标系
        # 参数：机械臂当前坐标，屏幕中心坐标、屏幕外规避的距离
        target_x = self.__away_screen_lenght(self.robot_current_coordinates[0],
                                             screen_center_coordinates[0], 1)
        # 由于机械臂的遮挡，Y轴只能向一侧执行规避动作
        # 1500 为在右侧规避的距离
        target_y = screen_center_coordinates[1] * 2 - 1500

        # 计算在x,y方向上分别要移动的相对距离（步进运动距离）
        relative_x, relative_y = [target_x, target_y] - self.robot_current_coordinates

        if self.x_evadable and not self.y_evadable:
            relative_y = 0
        elif not self.x_evadable and self.y_evadable:
            relative_x = 0
        elif self.x_evadable and self.y_evadable:
            # 在据边界最近的方向上执行规避动作
            if abs(relative_x) < abs(relative_y):
                relative_y = 0
            else:
                relative_x = 0
        else:
            self.release()
            raise Exception('The screen is too large to detour normally.')
        detour_end_coor = self.robot_current_coordinates + [relative_x, relative_y]
        # 记录终点实际坐标
        self.__record_cur_position(detour_end_coor)

        if self.virtual_debug:
            return
        # 移动到规避预计位置
        self.__control_robot_move(relative_x, relative_y)
        # 等待规避结束
        self.cq.do_necessary_wait('detour')

    def step_detour_outside_of_screen(self):
        """分步规避函数"""
        # 获取屏幕中心在图像坐标系中的坐标
        contour_center = contour.get_contour_center()

        # 获取在屏幕坐标系中机器人到屏幕中心点的移动坐标距离
        center_x = self.__robot_step(contour_center[0])
        center_y = self.__robot_step(contour_center[1])
        screen_center_coordinates = normalize_device_direction(center_x, center_y)

        # 计算在不同方向上规避运动的目标坐标
        # 坐标系：屏幕坐标系
        # 参数：机械臂当前坐标，屏幕中心坐标、屏幕外规避的距离
        target_x = self.__away_screen_lenght(self.robot_current_coordinates[0],
                                             screen_center_coordinates[0], 1)
        # 由于机械臂的遮挡，Y轴只能向一侧执行规避动作
        target_y = screen_center_coordinates[1] * 2 - 1500

        # 计算在屏幕坐标系中，x,y方向上分别要移动的相对距离
        relative_x, relative_y = [target_x, target_y] - self.robot_current_coordinates
        #        print('robot target line 717:', target_x, target_y)
        # 将规避动作分为几步
        # 分步规避动作每次执行的长度
        detour_step_move_distance = 0
        # 检测规避动作长度是否低于分步规避的最低值
        # 分步规避移动范围低于DETOUR_STEP_THRESHOLD则执行整个规避动作

        if self.x_evadable ^ self.y_evadable:
            if self.x_evadable:
                # x方向可规避，y方向不可规避
                # 如果在X方向上规避距离高于阈值，则将其拆分成分步规避
                # 否则按照整体规避进行规避运动
                if abs(relative_x) > DETOUR_STEP_THRESHOLD:
                    detour_step_move_distance = DETOUR_STEP_DISTANCE

                if relative_x < 0:
                    relative_x += detour_step_move_distance
                else:
                    relative_x -= detour_step_move_distance

                # Y方向无运动
                relative_y = 0
            else:
                # x方向不可规避，y方向可规避
                # 如果在Y方向上规避距离高于阈值，则将其拆分成分步规避
                # 否则按照整体规避进行规避运动
                if abs(relative_y) > DETOUR_STEP_THRESHOLD:
                    detour_step_move_distance = DETOUR_STEP_DISTANCE
                # X轴上无运动
                relative_x = 0
                if relative_y < 0:
                    relative_y += detour_step_move_distance
                else:
                    relative_y -= detour_step_move_distance
                    # x,y方向均可规避
        elif self.x_evadable & self.y_evadable:
            # 判断最短方向上的规避距离是否高于阈值，
            # 高，则拆分成分步规避，否则，一次规避
            if min(abs(relative_x), abs(relative_y)) > DETOUR_STEP_THRESHOLD:
                detour_step_move_distance = DETOUR_STEP_DISTANCE

            # 在据边界最近的方向上执行规避动作
            if abs(relative_x) < abs(relative_y):
                # X轴上规避更近
                if relative_x < 0:
                    relative_x += detour_step_move_distance
                else:
                    relative_x -= detour_step_move_distance
                # Y轴上无运动
                relative_y = 0
            else:
                # Y轴距离更近，X轴无运动
                relative_x = 0
                if relative_y < 0:
                    relative_y += detour_step_move_distance
                else:
                    relative_y -= detour_step_move_distance
        else:
            # 规避距离过远，超出机械臂移动的范围
            self.release()
            raise Exception('The screen is too large to detour normally.')

            # 记录规避运动后的机器人坐标
        current_x, current_y = self.robot_current_coordinates + [relative_x, relative_y]
        self.__record_cur_position(current_x, current_y)

        if self.virtual_debug:
            return
        # 移动到规避预计位置
        self.__control_robot_move(relative_x, relative_y)

    @staticmethod
    def __away_screen_lenght(current_coordinate,
                             center_coordinate,
                             distance=4):
        """计算规避动作移动距离
        Args:
            current_coordinate: 当前机械臂所在屏幕坐标系坐标
            center_coordinate: 屏幕中心在屏幕坐标系内的坐标
            distance: 规避运动额外往外移动距离指标
        """
        #        length += MOVE_OUTSIDE_DISTANCE[distance]  # 移动到屏幕分辨率外的距离
        # 判断该方向位于坐标轴正方向还是负方向
        if center_coordinate > 0:
            if current_coordinate > center_coordinate:
                # 当前坐标大于中心坐标
                # 移动终点为屏幕外一段距离处
                move_distance = (center_coordinate * 2 +
                                 MOVE_OUTSIDE_DISTANCE[distance])
            else:
                # 当前坐标小于中心坐标
                move_distance = (-MOVE_OUTSIDE_DISTANCE[distance])
        else:
            if current_coordinate > center_coordinate:
                # 当前坐标大于中心坐标
                # 移动终点为屏幕外一段距离处
                move_distance = (current_coordinate)
            else:
                # 当前坐标小于中心坐标
                move_distance = (center_coordinate * 2 -
                                 MOVE_OUTSIDE_DISTANCE[distance])
        return move_distance

    def move_to(self, dx, dy):
        """移动相对坐标
        Args: 
            dx,dy: 移动的相对距离（步进运动距离）
        """
        px = self.__robot_step(dx)
        py = self.__robot_step(dy)
        robot_move_coor = normalize_device_direction(px, py)
        relative_x, relative_y = robot_move_coor - self.robot_current_coordinates

        self.__record_cur_position(robot_move_coor)

        if self.virtual_debug:
            return
        self.__control_robot_move(relative_x, relative_y)

    def pen_down(self):
        """控制舵机落笔"""
        if self.virtual_debug:
            return

        # 落笔控制
        self.cq.do_necessary_wait('pen down')
        # 判断等待上个动作执行完毕
        self.__estimate_action_time('pen down')
        # 计算落笔时间
        # 参数： 落笔时间
        pen_fall_height = self.__estimate_pen_fall_height()
        pen_fall_time = math.ceil(abs(pen_fall_height / 10))
        # 转化成对应的机器指令
        action_commands = ['SC,5,{}\r'.format(pen_initial_height + pen_fall_height),
                           'SP,0,{}\r'.format(pen_fall_time)]
        # 将指令集合加入到指令队列中
        self.cq.put(action_commands)

    def pen_up(self):
        """控制舵机抬笔"""
        if self.virtual_debug:
            return
        # 抬笔控制
        self.cq.do_necessary_wait('pen up')
        # 判断等待上个动作执行完毕
        self.__estimate_action_time('pen up')
        # 计算落笔时间
        # 参数： 落笔时间
        pen_fall_height = self.__estimate_pen_fall_height()
        pen_fall_time = math.ceil(abs(pen_fall_height / 10))
        # 转化成对应的机器指令
        action_commands = ['SC,4,{}\r'.format(pen_initial_height),
                           'SP,1,{}\r'.format(pen_fall_time),
                           # 加此部分是为了等待笔的完全抬高，否则容易出现抬笔过程中对其他控件产生拖拽现象
                           'XM,{},0,0\r'.format(pen_fall_time)]
        # 将指令集合加入到指令队列中
        self.cq.put(action_commands)

    def detour_from_origin(self):
        """将机械臂往设备屏幕外移动指定距离，以防止阻碍图像拍摄"""
        # 开始时的机械臂规避，不阻碍拍摄
        origin_detour_length = Config.get_origin_detour_length()
        # 参数: 坐标、移动时间
        x = -int(origin_detour_length[0])
        y = -int(origin_detour_length[1])
        self.robot_current_coordinates = np.array([x, y])  # 记录机械臂当前坐标 
        # 虚拟执行不需要实际运行
        if self.virtual_debug:
            return

        detour_move_time = math.ceil(
            self.__calculate_move_time(x, y) * 1000)
        # 转化成对应的机器指令
        action_commands = ['XM,{},{},{}\r'.format(
            detour_move_time, x, y)]
        # 将指令集合加入到指令队列中
        self.cq.put(action_commands)

    def is_need_reset(self):
        if self.robot_current_coordinates[0] == 0 and self.robot_current_coordinates[1] == 0:
            return False
        else:
            return True

    def reset(self):
        """将机械臂移动到坐标系原点，即设备屏幕左上角"""
        # 根据当前实际位置将机械臂归为原点
        # 固件2.7.0版本提供HM指令，可以将机械臂自动移动到初始起点位置
        current_x, current_y = self.robot_current_coordinates
        self.__record_cur_position(0, 0)  # 将当前坐标点归零
        if self.virtual_debug:
            return

        # 判断是否需要等待上个动作执行完毕
        self.cq.do_necessary_wait('reset')

        if self.cq.get_ebb_version() >= "2.6.2":
            # HM指令，机器人运动回初始起点位置, 只在2.6.2以上版本存在
            # 参数：StepFrequency，步进频率，表示运动过程中的速度   
            action_commands = ['HM,{}\r'.format(Config.get_motor_speed())]
        else:
            # 计算当前动作执行总时间
            self.__estimate_action_time('reset', int(current_x), int(current_y))
            # 参数: 坐标、移动时间
            x = -int(current_x)
            y = -int(current_y)
            reset_move_time = math.ceil(
                self.__calculate_move_time(current_x, current_y) * 1000)
            # 转化成对应的机器指令
            action_commands = ['XM,{},{},{}\r'.format(
                reset_move_time, x, y)]

        # 指令加入到脚本指令队列中
        self.cq.put(action_commands)

    # 释放当前接口
    def release(self):
        """释放机器人当前接口，即为结束当前测试活动"""
        self.cq.do_necessary_wait('release')
        # 等待上次动作执行结束
        # 关闭视频监控
        self.sut.close()
        # 关闭机械臂端口
        self.cq.close()
        return True