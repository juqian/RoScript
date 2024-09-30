# -*- coding: utf-8 -*-
"""
Created on Fri Feb 28 11:19:52 2020

@author: szy
"""

import threading
import cv2
import os
import time
from config import Config
from test_script import TestScript
import numpy as np

get_frame = threading.Event()  # 拍照时截取视频帧事件
get_frame_ready = threading.Event()  # 视频帧截取完毕
start_sut_monitor = threading.Event()  # 开始视频录制
get_detour_frame_event = threading.Event()  # 拍照时截取规避视频帧事件

sut_true_running = True  # 视频录制出现问题
close_sut_monitor = False  # 结束视频录制
cap_release = threading.Event()  # 确定关闭视频录制事件，必须加，否在在控制台中运行有bug44
detour_frame = ''

record_script_in_video = Config.get_sut_monitor_setting()  # 视频存放路径

fps = 20  # 秒内的视频帧数量

rotation_angle = Config.get_rotation_angle()  # 旋转角度
[width, height] = Config.get_screenshot_size()  # 分辨率

g_run_event = True  # 辅助摄像设备运行
g_sut_tip_event = threading.Event()  # 监视落笔过程
g_record_tip_img_event = threading.Event()  # 存储落笔图片


def rotate_image(image):
    """旋转图像到指定角度
    
    Args:
        image: 待旋转的图像
    Returns:
        rotated_image: 旋转后的图像
    """
    global rotation_angle, width, height

    # 获取图像分辨率
    (h, w) = image.shape[:2]
    (cX, cY) = (w // 2, h // 2)
    # getRotationMatrix2D有三个参数，第一个为旋转中心，第二个为旋转角度，第三个为缩放比例
    M = cv2.getRotationMatrix2D((cX, cY), rotation_angle, 1)
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    # 计算图像新边界的分辨率
    # compute the new bounding dimensions of the image
    nW = int((h * sin) + (w * cos))
    nH = int((h * cos) + (w * sin))
    # 计算旋转矩阵
    # adjust the rotation matrix to take into account translation
    M[0, 2] += (nW / 2) - cX
    M[1, 2] += (nH / 2) - cY
    # 旋转指定角度
    # perform the actual rotation and return the image
    rotated_image = cv2.warpAffine(image, M, (nW, nH))
    return rotated_image


class RecordVideo(object):
    """ Record video when the script is running. 
    
        Args:
            screen_shot_path: The path to store the video
            screen_shot_idx: The index of screen shot
    """

    def __init__(self):
        self.screen_shot_path = ''
        self.screen_shot_idx = 0

    def record_video(self, video_dir):
        """Record video when the script is running
        
        Args:
            video_dir: The folder path to store the video
        """
        global sut_true_running, close_sut_monitor, detour_frame, height, width

        focus = Config.get_camera_focus()

        cameraCapture = cv2.VideoCapture(Config.get_capture_id() + cv2.CAP_DSHOW)

        # 检测摄像设备是否与计算机相连
        if not cameraCapture.isOpened:
            print('Camera is not Opened')

        # 设置图像采集格式。默认为YUY2格式，MJPG格式比YUY2格式每秒读取的fps数多
        cameraCapture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

        # 设置摄像头的分辨率和焦距
        cameraCapture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cameraCapture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cameraCapture.set(cv2.CAP_PROP_FOCUS, focus)

        # video 视频存放路径
        moment = time.strftime('%H-%M')
        video_name = '{}_{}.avi'.format(TestScript.get_pyname(), moment)
        video_path = os.path.join(video_dir, video_name)

        # 写视频
        videoWriter = cv2.VideoWriter(
            video_path, cv2.VideoWriter_fourcc('I', '4', '2', '0'), fps, (width, height))

        # 写视频
        while True:
            ret, frame = cameraCapture.read()
            start_sut_monitor.set()
            get_detour_frame_event.set()
            # print(ret)
            if ret:
                # print(frame)
                # 旋转
                frame = rotate_image(frame)
                detour_frame = frame
                sut_true_running = True  # Set

                if record_script_in_video:
                    videoWriter.write(frame)  # 保存视频

                # 存放拍照时的结果帧
                if get_frame.is_set():
                    """保存两帧会优化图像质量，但会额外消耗时间"""
                    # TODO
                    # self.screen_shot_idx += 1
                    # if self.screen_shot_idx % 6 == 0:
                    # 好像存储的第六帧图像都会模糊
                    # ret, frame = cameraCapture.read()
                    ret, frame = cameraCapture.read()
                    #                    ret, frame = cameraCapture.read()
                    # 旋转
                    frame = rotate_image(frame)
                    cv2.imwrite(self.screen_shot_path, frame)

                    if record_script_in_video:
                        videoWriter.write(frame)  # 保存视频
                    get_frame_ready.set()
                    get_frame.clear()
            else:
                sut_true_running = False
                print('Cannot Sut Monitor in Threading')
                break

            # 关闭视频录制
            if close_sut_monitor:
                print('Close the Sut Monitor')
                break

        videoWriter.release()
        cameraCapture.release()
        cap_release.set()


    @staticmethod
    def monitor_pen_fall(start_fall_img_idx, tip_falling_dir):
        """ 存储落笔过程中辅助摄像头拍摄的图像"""
        global g_sut_tip_event
        camera_capture = cv2.VideoCapture(Config.get_capture2_id() + cv2.CAP_DSHOW)
        if not camera_capture.isOpened:
            print(False)

        # 设置分辨率
        camera_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)

        while True:
            ret, frame = camera_capture.read()
            if ret is False:
                print('Cannot Read Focus From Capture!')
            if ret is True:
                # 是否接收到图像
                if g_sut_tip_event.is_set():
                    # 接收图像时
                    ret, frame = camera_capture.read()
                    cv2.imwrite('{}/{}.png'.format(tip_falling_dir, start_fall_img_idx), frame)
                    start_fall_img_idx += 1
                    g_sut_tip_event.clear()
                    g_record_tip_img_event.set()
            else:
                print('Cannot get photo')
                break
            if not g_run_event:
                break

        camera_capture.release()
        cv2.destroyAllWindows()


class SutMonitor(object):
    """ 视频监控 """

    # 开启视频监控
    # Attributes:
    #     rv: robot video

    def __init__(self):
        global close_sut_monitor
        if Config.get_virtual_debug_model():
            return
        self.rv = RecordVideo()
        video_dir = TestScript.script_video_dir()

        # record_video即记录实时显示图像，file是存储路径；建立实时采集线程
        t = threading.Thread(target=self.rv.record_video,
                             args=(video_dir,))
        t.setDaemon(True)
        t.start()
        t.join(1)

        start_sut_monitor.wait()
        time.sleep(0.01)
        # 为了等待摄像头启动，刚开机反应不是很快
        if not sut_true_running:
            close_sut_monitor = True
            cap_release.wait()
            raise Exception('Cannot Sut Monitor')

    # Take photo in threading
    # Args:
    #     index: The index of the new photo
    def take_photo(self, index):
        get_frame.set()
        self.rv.screen_shot_path = "{}/{}_{}.png".format(
            TestScript.script_temporary_dir(),
            TestScript.get_pyname(),
            index)
        get_frame_ready.wait()
        get_frame_ready.clear()

    # Close the threading and video
    @staticmethod
    def close():
        global close_sut_monitor
        close_sut_monitor = True
        cap_release.wait()

    # Get snap screen
    # Args:
    #     snap_screen_path: The folder path to store the snap screen
    def snap_screen(self, snap_screen_path):

        get_frame.set()
        self.rv.screen_shot_path = snap_screen_path

        get_frame_ready.wait()
        get_frame_ready.clear()

    @staticmethod
    def record_detour_frame():
        """返回规避运动的视频帧存储路径"""
        global detour_frame
        time.sleep(0.1)
        # 视频帧的获取总会比想象的快一些，不加sleep的话会获取之前的视频帧，导致无法测试
        get_detour_frame_event.clear()
        get_detour_frame_event.wait()
        # 获取存放路径
        detour_image_path = TestScript.get_detour_image_path()
        # 存放视频帧
        cv2.imwrite(detour_image_path,
                    cv2.resize(detour_frame, (width, height),
                               interpolation=cv2.INTER_AREA))

    @staticmethod
    def get_img(save_path, size=Config.get_screenshot_size()):
        """主摄像机拍摄的图像
        Args:
            save_path: 保存路径
            size: 图像分辨率
        """
        focus = Config.get_camera_focus()

        camera_capture = cv2.VideoCapture(Config.get_capture_id() + cv2.CAP_DSHOW)
        # 检测摄像设备是否与计算机相连
        if not camera_capture.isOpened:
            print('Camera is not Opened')

        # 设置摄像头的分辨率和焦距
        camera_capture.set(cv2.CAP_PROP_FRAME_WIDTH, size[0])
        camera_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, size[1])
        camera_capture.set(cv2.CAP_PROP_FOCUS, focus)

        ret, frame = camera_capture.read()
        if ret:
            # 旋转
            ret, frame = camera_capture.read()
            frame = rotate_image(frame)
            cv2.imwrite(save_path, frame)
        else:
            print('Cannot capture camera image')
        camera_capture.release()


# 记录落笔过程
class PenMonitor(object):

    @staticmethod
    def get_tip_status_img():
        """拍摄触屏笔状态图像"""
        camera_capture = cv2.VideoCapture(Config().get_capture2_id() + cv2.CAP_DSHOW)
        # 检测摄像设备是否与计算机相连
        if not camera_capture.isOpened:
            print(False)
        # 设置分辨率
        camera_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)

        while True:
            # 当无法接收视频帧时，抛出异常
            _, _ = camera_capture.read()
            ret, frame = camera_capture.read()

            if ret is True:
                # 是否接收到图像
                cv2.imwrite(Config.get_tip_status_img_pth(), frame)
            else:
                print('Can\'t get photo')
            break
        camera_capture.release()
        cv2.destroyAllWindows()

    @staticmethod
    def collect_pen_fall_images(pen_current_height,
                                pen_fall_height,
                                start_fall_img_idx,
                                signal_fall_num,
                                tip_falling_dir=None):
        """收集落笔过程中的图像
        Args:
            pen_current_height: 笔的当前高度
            pen_fall_height: 电机每次下落的高度
            start_fall_img_idx: 图像开始编号
            signal_fall_num: 电机下落的次数
        """
        print("collect pen fall images")
        global g_record_tip_img_event, g_run_event, g_sut_tip_event
        g_run_event = True
        t = threading.Thread(target=RecordVideo.monitor_pen_fall, args=(start_fall_img_idx,tip_falling_dir))
        t.setDaemon(True)
        t.start()

        from robot_communicate import RobotCommunicate

        rc = RobotCommunicate()

        # 等待机械臂触屏笔复位再拍照
        time.sleep(1)
        g_sut_tip_event.set()
        g_record_tip_img_event.wait()
        g_record_tip_img_event.clear()
        fall_idx = 0

        while fall_idx < signal_fall_num:
            # 图像还在变化证明电容笔还未接触到屏幕
            # print("pen_current_height：{}".format(pen_current_height))
            rc.run("SC,5,{}\r".format(pen_current_height))
            rc.run("SP,0,{}\r".format(abs(pen_fall_height)))
            time.sleep(abs(pen_fall_height) / 1000)  # 等待落笔完成

            g_sut_tip_event.set()
            g_record_tip_img_event.wait()
            g_record_tip_img_event.clear()

            pen_current_height += pen_fall_height
            fall_idx += 1

        rc.run("SP,1\r")
        rc.close()
        g_run_event = False
