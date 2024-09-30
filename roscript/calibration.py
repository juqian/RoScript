# -*- coding: utf-8 -*-
"""
Created on Tue Sep 10 21:10:58 2019

@author: szy
"""
import shutil
import sys
import cv2
import os

import sut_monitor
from sut_monitor import SutMonitor
from camera_calibration import Camera_Calibration_API
from config import Config
import contour
from robot_calibration import RobotCalibration


class Calibration(object):
    """机器设备包括机械臂与摄像设备的一些配置函数"""

    @staticmethod
    def camera_settings():
        """设置相机各项参数"""
        # 判断摄像设备是否连接到计算机上，带cv2.CAP_DSHOW拍摄效果似乎好些
        cap = cv2.VideoCapture(Config.get_capture_id() + cv2.CAP_DSHOW)
        if not cap.isOpened:
            print(False)
            return

        # 设置图像采集格式。默认为YUY2格式，MJPG格式比YUY2格式每秒读取的fps数多
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

        [width, height] = Config.get_screenshot_size()
        # 设置分辨率
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)

        # 设置自动调焦参数, 需要与cv2.CAP_DSHOW配合使用
        cap.set(cv2.CAP_PROP_SETTINGS, 1)

        fixed_focus_num = 0  # 收集焦距固定后的相同焦距数量
        current_focus = 0  # 当前帧的焦距
        last_focus = 0  # 前一帧的焦距

        rotation_angle = Config.get_rotation_angle()
        if rotation_angle in [90, 270]:
            show_size = (480, 640)
        else:
            show_size = (640, 480)

        # 在等待时间内收集相机焦距
        # 当焦距在一定时间内固定时，则结束对焦
        # 若时间结束仍未有固定焦距，则提示对焦失败
        while True:
            # 当无法接收视频帧时，抛出异常
            try:
                ret, frame = cap.read()
                [x, y, w, h] = contour.caculate_image_contour(frame)
            except:
                raise Exception('Cannot Read Focus From Capture!')

            cv2.rectangle(frame, (x, y), (h, w), (255, 0, 0), 2)
            frame = sut_monitor.rotate_image(frame)

            current_focus = cap.get(cv2.CAP_PROP_FOCUS)  # 读取当前视频帧的焦距
            fixed_focus_num = (fixed_focus_num + 1) if current_focus == last_focus else 0
            last_focus = current_focus

            cv2.imshow(r"Enter 'q' to QUIT", cv2.resize(frame, show_size))
            # 100ms收集一次图像信息，刷新视频图像
            if cv2.waitKey(100) & 0xFF == ord('q'):
                # 键盘输入'q'结束
                #                screenshot_path = os.path.realpath(Config.get_calibration_screenshot_image())
                #                ret, frame = cap.read()
                #                cv2.imwrite(screenshot_path, frame)
                if fixed_focus_num > 10:
                    Config.update_focal_length(current_focus)
                break

        # 关闭摄像头
        cap.release()
        # 关闭opencv弹出的窗口
        cv2.destroyAllWindows()

    @staticmethod
    def calibrate_camera_parameters(pattern_rows=None, pattern_columns=None, distance_in_world_units=None):
        """相机标定，用于使用标定板对物理与像素距离的转换
        Args:
            aya.argv[2]: pattern_rows, 标定板行数
            aya.argv[3]: pattern_columns, 标定板列数
            aya.argv[4]: distance_in_world_units, 标定图形圆心之间的距离
        Return: True or False, 是否标定成功
        """
        # 拍摄校准图片
        SutMonitor.get_img(Config.get_calibration_image())
        if pattern_rows is None:
            pattern_rows = int(sys.argv[2]),
            pattern_columns = int(sys.argv[3]),
            distance_in_world_units = int(sys.argv[4])

        symmetric_circles = Camera_Calibration_API(pattern_rows=pattern_rows,
                                                   pattern_columns=pattern_columns,
                                                   distance_in_world_units=distance_in_world_units)  # 设置参数

        symmetric_circles.double_count_in_column = False
        return symmetric_circles.calibrate_camera()

    @staticmethod
    def detect_screen_contour(contour_save_dir=None, isCutTwice=False, isAdvanced=False):
        """进行屏幕轮廓检测
        Args:
            aya.argv[2]: isCutTwice, 是否进行二次裁剪以取内屏
        """
        if contour_save_dir is None:
            isCutTwice = (sys.argv[2] == 'true')  # 二次裁剪
            isAdvanced = (sys.argv[3] == 'true')  # 是否使用高级检测

        # if not isCutTwice:
        screenshot_img_path = Config.get_calibration_screenshot_image()
        SutMonitor.get_img(save_path=screenshot_img_path)

        if contour_save_dir is not None:
            snapshot_path = contour_save_dir + os.sep + "snapscreen.png"
            print("Save camera shot to " + snapshot_path)
            shutil.copyfile(screenshot_img_path, snapshot_path)

        # 进行屏幕校准
        screen_region, exterior_img, interior_img = contour.detect_screen_region(screenshot_img_path, isCutTwice=isCutTwice, isAdvanced=isAdvanced)
        cv2.imwrite(Config.get_devicescreen_image(), exterior_img)

        if contour_save_dir is not None and isCutTwice:
            interior_path = contour_save_dir + "\\twice_deviceScreen.png"
            cv2.imwrite(interior_path, interior_img)

        Config.record_calibration_file(screen_region)
        print('Detect screen calibration end', flush=True)

    @staticmethod
    def record_device_contour():
        """存储被测设备轮廓信息"""
        Config.update_model_contour()
        print('Data update completed', flush=True)

    @staticmethod
    def initialize_robot_arm():
        """ 机械臂位置初始化"""
        RobotCalibration.initialize_robot_arm()

    @staticmethod
    def initialize_tip_height(tip_fall_step=None, tip_falling_dir=None):
        """点击器高度初始化"""
        if tip_fall_step is None:
            tip_fall_step = int(sys.argv[2])

        if tip_falling_dir is None:
            # 落笔过程存放目录
            tip_falling_dir = Config.get_tip_falling_dir()

        if not os.path.exists(tip_falling_dir):
            os.makedirs(tip_falling_dir)

        initial_tip_height = Config.get_tip_height()
        tip_height = RobotCalibration.calibrate_tip_height(initial_tip_height, tip_fall_step, tip_falling_dir)
        # 记录落笔高度数值
        Config.update_tip_height(tip_height)

    @staticmethod
    def test_tip_fall():
        """测试落笔效果"""
        RobotCalibration.test_tip_fall()

    @staticmethod
    def control_robot_arm_move():
        """控制机械臂运动
        有两种运动形式:
            1: 环绕设备轮廓一周
            2: 朝目标方向微调
        """
        arm_move_circle = (sys.argv[2] == 'true')
        RobotCalibration.control_robot_arm_move(arm_move_circle,
                                                int(sys.argv[3]) * 10,
                                                int(sys.argv[4]) * 10)

    @staticmethod
    def calibrate_robot_move_direction():
        """校准机械臂在图像中的的移动方向与实际移动之间的转换关系"""
        RobotCalibration.calibrate_robot_move_direction()

    @staticmethod
    def get_tip_status_img():
        """获取在辅助摄像头下的落笔点击图像"""
        RobotCalibration.get_tip_status_img()

    @staticmethod
    def ensure_tip_region():
        """确定落笔点击动作笔尖识别区域"""
        mouse_points = []  # 鼠标在落笔图像上的点击操作像素坐标
        tip_img_path = Config.get_tip_status_img_pth()
        tip_region_img_path = Config.get_tip_region_img_pth()
        tip_h,tip_w = Config.get_tip_contour()

        half_w = int(tip_w / 2)
        half_h = int(tip_h / 2)

        tip_image = cv2.imread(tip_img_path)

        def _mouse_click(event, x, y, flags, para):
            global tip_image
            if event == cv2.EVENT_LBUTTONDOWN:  # 左边鼠标点击
                tip_image = cv2.imread(tip_img_path)
                mouse_points.append([x, y])
                # x, y = mouse_points[-1]
                # 参数
                # tip_image: 原图像
                # ptLeftTop: 矩形左上角
                # ptRightBottom: 矩形右下角
                # point_color: 矩形颜色
                # thickness: 矩形宽度
                cv2.rectangle(tip_image, (x - half_w, y - half_h),
                              (x + half_w, y + half_h), (255, 0, 0), 3, 4)
                cv2.imshow(r"Enter 'e' to Ensure", tip_image)

        cv2.namedWindow(r"Enter 'e' to Ensure")
        cv2.setMouseCallback(r"Enter 'e' to Ensure", _mouse_click)
        while True:
            cv2.imshow(r"Enter 'e' to Ensure", tip_image)

            if cv2.waitKey() == ord('e'):
                if len(mouse_points) != 0:
                    x, y = mouse_points[-1]
                    cv2.rectangle(tip_image, (x - half_w, y - half_h),
                                  (x + half_w, y + half_h), (255, 0, 0), 3, 4)
                    cv2.imwrite(tip_region_img_path, tip_image)
                    Config.update_tip_fall_center(x, y)
                break
        cv2.destroyAllWindows()


# 转到不同的函数
calibration_switcher = {
    '1': Calibration.camera_settings,  # 相机设置，主要是对焦
    '2': Calibration.calibrate_camera_parameters,  # 相机标定
    '3': Calibration.detect_screen_contour,  # 检测设备屏幕
    '4': Calibration.record_device_contour,  # 记录设备屏幕
    '5': Calibration.initialize_robot_arm,  # 定位机械臂运动起点
    '6': Calibration.initialize_tip_height,  # 计算机械臂点击高度
    '7': Calibration.test_tip_fall,  # 测试落笔高度
    '8': Calibration.control_robot_arm_move,  # 控制机械臂运动，用于检测机械臂起点和标定结果
    '9': Calibration.calibrate_robot_move_direction,  # 检测机械臂运动方向
    '10': Calibration.get_tip_status_img,  # 获取在辅助摄像头下的触屏笔图像
    '11': Calibration.ensure_tip_region,  # 确定落笔点击动作笔尖识别区域
}

if __name__ == "__main__":
    #    calibration_switcher["1"]()# 跳转到不同的函数
    calibration_switcher[sys.argv[1]]()  # 跳转到不同的函数
