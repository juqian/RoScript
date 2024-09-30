# -*- coding: utf-8 -*-
"""
Interface of the test engine

@author: szy
"""

import time
import atexit
from robot import Robot
import robot
from screenshot import Screenshot
from template_match import TemplateMatchResult, Algorithm
from keyboard import Keyboard
import contour
from config import Config
from rcslogger import RcsLogger
from test_script import TestScript
import argparse
import os
import cv2
import json


DETOUR_ACTION = {
    'assert exist',
    'assert not exist',
    'click',
    'double click',
    'drag',
    'find',
    'long press',
    'long press drag',
    'match',
    'press keyboard',
    'take screen photo',
    'wait',
    'move to',
}  # 需要执行规避动作的动作类型


def check_args():
    parser = argparse.ArgumentParser(description="Test script engine.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-vd", action="store_true", dest="virtual_debug", default=False, help="in virtual debug mode")
    parser.add_argument("-vdf", action="store", dest="vd_folder", help="exec record folder for virtual debug")
    parser.add_argument("-tmt", action="store", dest="tm_threshold", default=None, help="the template match threshold")
    options = parser.parse_args()
    if options.virtual_debug:
        Config.set_virtual_debug(options.vd_folder)
    if options.tm_threshold is not None:
        Config.set_template_match_threshold(options.tm_threshold)


check_args()


class Rcs(object):
    """ 执行引擎入口类
    
    Attributes:
        virtual_debug: boolean, 虚拟调试开关
        robot_dev: 连接机器人设备
        match_result: 模板匹配结果, 包含控件信息, 识别相似度, 匹配中心坐标
        lasted_widget: string, 上一步控件识别控件名
        algorithm: Algorithm类, 算法类，包含算法、阈值、阈值与识别结果关系运算符
        log: 记录不同的操作执行时间
        screen_shot_index: int, 图片图像拍摄计数
    """

    def __init__(self):
        """数据初始化."""
        self.virtual_debug = Config.get_virtual_debug_model()  # 虚拟调试模式
        self.log = RcsLogger(TestScript.get_pyname(), self.virtual_debug)  # 脚本运行时间记录
        self.robot_dev = Robot(self.log, self.virtual_debug)  # 链接机器人设备
        self.match_result = TemplateMatchResult(0, 0, 0, 0, 0)  # 控件信息,相似度,横坐标,纵坐标
        self.lasted_widget = ''  # 上一步查找的图像
        self.algorithm = Algorithm()
        self.screen_shot_index = 0  # screenshot计数
        # 实际运行前，控制机械臂移动一段距离，以避免阻挡拍摄
        self.robot_dev.detour_from_origin()
        self.action_log = []

        atexit.register(self.exit_hooks)

    @staticmethod
    def __is_image_file(image_name):
        """检测控件输入是否为图像
        
        Returns: 
            True or False
        """
        # 检测是否是图片
        if 'png' in image_name:
            return True
        elif 'jpg' in image_name:
            return True
        elif 'gif' in image_name:
            return True
        return False

    @staticmethod
    def __is_region(region):
        """检测是否为标准格式的region
        
        Returns: 
            True or False
        """
        if len(region) == 4:
            if max(region) <= 1 and min(region) >= 0:
                return region
        return [0, 0, 1, 1]

    def detour(self, action_type,
               widget_image_name='',
               region=None):
        """规避动作 
        
        Args: 
            action_type: string, 需要执行规避动作的动作类型
            widget_image_name: string, 控件图像名,默认为空
            region: 规避移动范围,默认为整个设备屏幕
        Returns: 
            Boolean, 规避动作是否成功
        """
        if self.virtual_debug:
            return False

        # 对于不需要执行分步规避动作的指令来说，默认规避动作执行成功
        if action_type not in DETOUR_ACTION:
            return True
        # 像drag等操作需要两个图片、以及find需要返回结果集的情况下需要将所有区域都规避出来
        # 对于没有图片匹配要求的规避动作,则进行全部规避
        if widget_image_name == '':
            # 现仅对于键盘来说，执行完全规避动作
            self.robot_dev.move_outside_of_screen()
            return True

        # 屏幕型号（像素横纵距离）
        if region is None:
            region = [0, 0, 1, 1]
        screen_size = contour.get_contour_size(region)
        # 像素与物理的转换比例
        p2r = Config.get_scale_rate()
        # 将屏幕轮廓大小转换成机械臂坐标长度
        g_one_cm_steps = Config.get_one_cm_steps()  # 步进电机运动1cm需要的步进距离
        size_x = (float(screen_size[0]) / p2r) * g_one_cm_steps
        size_y = (float(screen_size[1]) / p2r) * g_one_cm_steps
        screen_real_size = robot.normalize_device_direction(size_x, size_y)

        # 进行分步规避动作
        while self.__do_detour_step(screen_real_size):
            # 当未执行完全部的规避距离时，每执行一次分步规避则进行一次图像匹配
            # 若已经执行完了全部的规避距离，即detour_step_status = True,则分步规避失败，
            # 此时会在当前动作中以完全规避的状态执行一次图像匹配
            if self.__detour_check_widget_exist(widget_image_name, region):
                return True
        return False

    def __do_detour_step(self, screen_real_size):
        """控制机器人执行分步规避运动 
        
        Args:
            screen_real_size: 设备型号在机器人坐标系中的长宽
            
        Returns:
            分步规避执行状态：True or False
            例如,一段10cm的分步规避距离,按每次规避3cm计算,如果规避到6cm时,返回True,证明正在执行规避动作；
            当规避到10cm时，返回False,证明已经执行完了规避运动
        """
        # 机器人当前坐标
        robot_current_coordinates = self.robot_dev.get_current_coordinates()
        # 判断机器人是否需要进行规避动作
        block_in_x, block_in_y = False, False
        # 确保机械臂与屏幕轮廓在同一侧且在屏幕区间内
        if (robot_current_coordinates[0] * screen_real_size[0] > 0
                and abs(robot_current_coordinates[0]) < abs(screen_real_size[0])):
            block_in_x = True

        if abs(robot_current_coordinates[1]) < abs(screen_real_size[1]):
            block_in_y = True

        # 机器人确实处于屏幕中心，且对设备产生了遮挡,执行分步规避运动
        if block_in_x and block_in_y:
            self.log.record_detour_start()
            self.robot_dev.step_detour_outside_of_screen()
            self.log.record_detour_result()
            return True
        return False

    def __detour_check_widget_exist(self, widget_image_name,
                                    region=None):
        """检测规避运动中控件在屏幕中是否存在 
        
        Args:
            widget_image_name: string, 控件名称
            region: 控件查询的范围,默认为整个被测设备屏幕
            
        Returns:
            如果控件名为空,返回False
            如果查询结果低于模板匹配算法阈值,即没有匹配到控件图像返回False
            匹配到控件图像,返回True
        """
        # 控件名为空，表示是查询文字或者规避键盘查询
        if widget_image_name == '':
            return False

        # 标准化查询范围
        if region is None:
            region = [0, 0, 1, 1]
        reg = self.__is_region(region)
        # 获取规避运动视频帧存储路径
        detour_frame_path = self.robot_dev.get_detour_frame_path()
        # 找出图像位置,需要机器处于静止状态
        screen_shot = Screenshot(self.log,
                                 widget_image_name,
                                 screen_shot_index=0,
                                 region=reg,
                                 virtual_debug=self.virtual_debug,
                                 detour_frame_path=detour_frame_path)
        # 选择要比对的图片
        match_result = screen_shot.get_image_match_result(self.algorithm.id)
        # 如果在规避过程中能匹配到空间图像，则终止规避
        if self.algorithm.match_result_is_right(match_result.get_similarity()):
            self.match_result = match_result
            screen_shot_index = self.robot_dev.get_photo_index('detour',
                                                               save_frame=True)
            screen_shot.save_detour_frame(screen_shot_index,
                                          self.virtual_debug)
            return True
        return False

    def __check_widget_exist(self, widget_image_name, region=None):
        """检测控件在屏幕中是否存在 
        
        Args:
            widget_image_name: string, 控件名称
            region: 控件查询的范围,默认为整个被测设备屏幕
            
        Returns:
            如果控件名为空,返回False
            如果查询结果低于模板匹配算法阈值,返回False
            否则,返回True
        """
        if widget_image_name == '':
            return False
        if region is None:
            region = [0, 0, 1, 1]
        reg = self.__is_region(region)
        self.__get_snapscreen('match')
        # 找出图像位置,需要机器处于静止状态
        screen_shot = Screenshot(self.log,
                                 widget_image_name,
                                 self.screen_shot_index,
                                 region=reg,
                                 virtual_debug=self.virtual_debug)
        # 选择要比对的图片
        self.match_result = screen_shot.get_image_match_result(self.algorithm.id)
        return self.algorithm.match_result_is_right(self.match_result.get_similarity())

    def end_script_run(self):
        """结束脚本运行"""
        # 释放接口
        if self.virtual_debug:
            return
        self.robot_dev.reset()
        self.robot_dev.release()

    def find(self, widget_image_name, region=None):
        """检测控件在屏幕中可能存在的位置
        
        Args:
            widget_image_name: string, 控件名称
            region: 控件查询的范围,默认为整个被测设备屏幕
            
        Returns:
            一个包含所有可能结果的集合
            集合单元为: 算法识别相似度、识别坐标
        """
        # 查找控件坐标
        # 分步规避动作
        self.log.record_action_start("find", "'{}'".format(widget_image_name))
        self.detour('find', region=region)

        if region is None:
            region = [0, 0, 1, 1]
        reg = self.__is_region(region)
        self.__get_snapscreen('find')
        screen_shot = Screenshot(self.log,
                                 widget_image_name,
                                 screen_shot_index=self.screen_shot_index,
                                 region=reg,
                                 virtual_debug=self.virtual_debug)
        self.lasted_widget = widget_image_name
        self.match_result = screen_shot.get_image_match_result(self.algorithm.id)
        similarity = self.match_result.get_similarity()
        x, y = self.match_result.get_coordinates()

        self.dbg_record_action('find', [widget_image_name, region], [self.match_result], [(x, y)])

        if self.virtual_debug:
            print("[Virtual Debug] find('{}'): Succeed!".format(widget_image_name))
        self.log.record_action_end()
        return [similarity, x, y]

    def match(self, widget_image_name, region=None):
        """对控件进行模板匹配
        
        Args:
            widget_image_name: string, 控件名称
            region: 控件查询的范围,默认为整个被测设备屏幕
            
        Returns:
            如果控件名为空,返回False
            如果查询结果低于模板匹配算法阈值,返回False
            否则,返回True
        """
        # 获取控件存在状态
        self.log.record_action_start("match", "'{}'".format(widget_image_name))
        # 匹配结果
        match_widget_exist = False
        # 规避动作
        if region is None:
            region = [0, 0, 1, 1]
        if self.detour('match', widget_image_name, region):
            match_widget_exist = True

        # 如果在规避过程中识别出结果        
        if not match_widget_exist:
            match_widget_exist = self.__check_widget_exist(widget_image_name, region)
            self.dbg_record_action('match', [widget_image_name, region], [self.match_result], [self.match_result.get_coordinates()])

        if match_widget_exist:
            self.lasted_widget = widget_image_name
        else:
            self.lasted_widget = ''
        #        action_exec_time = self.robot_dev.get_action_exec_time()
        if self.virtual_debug:
            print("[Virtual Debug] match('{}'): {} on screen {}".format(widget_image_name,
                  'Yes' if match_widget_exist else 'No', self.screen_shot_index))

        self.log.record_action_end()
        return match_widget_exist

    def click(self, target, region=None):
        """点击指定目标
        
        Args:
            target: string, 点击目标,可以是文字,也可以是图片
            region: 控件查询的范围,默认为整个被测设备屏幕
            
        Returns:
            点击结果,Ture or False
        """
        self.log.record_action_start("click", "'{}'".format(target))

        result = True
        if region is None:
            region = [0, 0, 1, 1]
        if self.__is_image_file(str(target)):
            result = self.__click_photo(target, region)
        else:
            result = self.__click_text(target, region)

        if not result:
            if self.virtual_debug:
                print("[Virtual Debug] click('{}'): Failed on screen {} (sim={})!".format(target,
                        self.screen_shot_index, self.match_result.get_similarity()))
                self.log.record_action_end()
                return result
            else:
                self.log.record_exception()
                self.reset_arms()
                raise Exception("click('{}') Error!".format(target))
        else:
            if self.virtual_debug:
                print("[Virtual Debug] click('{}'): Succeed on screen {}".format(target, self.screen_shot_index))
                # action_exec_time = self.robot_dev.get_action_exec_time()
        self.log.record_action_end()

        return result

    def __click_photo(self, widget_image_name, region=[0, 0, 1, 1]):
        """点击指定控件图
        
        Args:
            widget_image_name: string, 控件名称
            region: 控件查询的范围,默认为整个被测设备屏幕
            
        Returns:
            点击结果,Ture or False
            
        Raises: 
            Exception: 没有找到制定控件
        """
        # 规避动作
        if self.detour('click', widget_image_name, region):
            self.lasted_widget = widget_image_name
        # 点击操作：click(phone.png)
        if self.lasted_widget == widget_image_name:
            x, y = self.match_result.get_coordinates()
            self.dbg_record_action('click', [widget_image_name, region], [self.match_result], [(x, y)])
            self.robot_dev.click(x, y)
            return True
        # 比对图片,返回控件信息
        if self.__check_widget_exist(widget_image_name, region):
            x, y = self.match_result.get_coordinates()
            self.dbg_record_action('click', [widget_image_name, region], [self.match_result], [(x, y)])
            self.robot_dev.click(x, y)
        else:
            self.dbg_record_action('click', [widget_image_name, region], [self.match_result], None)
            print('Click Error: ', self.match_result.get_similarity())
            return False
        return True

    def __click_text(self, text, region=[0, 0, 1, 1]):
        """点击指定控件图
        
        Args:
            text: string, 被点击的文字
            region: 控件查询的范围,默认为整个被测设备屏幕
            
        Returns:
            点击结果,Ture or False
        """
        # TODO outdated
        self.detour('click', region=region)
        number_image = self.robot_dev.get_photo()
        text_click = Keyboard(self.log, number_image)
        self.match_result = text_click.text_recognition()
        x, y = self.match_result.get_coordinates()
        self.robot_dev.click(x, y)
        return True

    def double_click(self, widget_image_name, region=[0, 0, 1, 1]):
        """双击指定控件图
        
        Args:
            widget_image_name: string, 控件名称
            region: 控件查询的范围,默认为整个被测设备屏幕
            
        Returns:
            双击结果,Ture or False
            
        Raises: 
            Exception: 没有找到指定控件
        """
        self.log.record_action_start("double click", "'{}'".format(widget_image_name))
        if self.detour('double click', widget_image_name, region):
            self.lasted_widget = widget_image_name

        if self.lasted_widget == widget_image_name:
            x, y = self.match_result.get_coordinates()
            self.dbg_record_action("double_click", [widget_image_name, region], [self.match_result], [(x, y)])
            self.robot_dev.double_click(x, y)
            self.lasted_widget = ''
            # action_exec_time = self.robot_dev.get_action_exec_time()
            if self.virtual_debug:
                print("[Virtual Debug] double click('{}'): Succeed on screen {}".format(widget_image_name, self.screen_shot_index))
            self.log.record_action_end()
            return True

        if self.__check_widget_exist(widget_image_name, region):
            x, y = self.match_result.get_coordinates()
            self.dbg_record_action("double_click", [widget_image_name, region], [self.match_result], [(x, y)])
            self.robot_dev.double_click(x, y)
            if self.virtual_debug:
                print("[Virtual Debug] double click('{}'): Succeed on screen {}".format(widget_image_name, self.screen_shot_index))
        else:
            self.dbg_record_action("double_click", [widget_image_name, region], [self.match_result], None)
            # 未能识别成功
            if self.virtual_debug:
                print("[Virtual Debug] double click('{}'): Failed on screen {}!".format(widget_image_name, self.screen_shot_index))
                self.log.record_action_end()
                return
            else:
                self.log.record_exception()
                self.reset_arms()
                raise Exception("double_click('{}') Error!".format(widget_image_name))

        # action_exec_time = self.robot_dev.get_action_exec_time()
        self.log.record_action_end()

        return True

    def press_keyboard(self, keyboard_name, text):
        """在虚拟键盘中键入指定文字信息
        
        Args:
            keyboard_name: string, 指定键盘
            text: 键入的信息
            
        Raises: 
            Exception: 没有找到指定键盘
        """
        self.log.record_action_start("press keyboard", "'{}', '{}'".format(keyboard_name, text))
        self.detour('press keyboard')

        if self.virtual_debug:
            self.screen_shot_index = self.robot_dev.get_virtual_debug_index()
        else:
            self.screen_shot_index = self.robot_dev.get_photo_index('press keyboard')

        keyboard_model = Keyboard(self.log, keyboard_name)  # 获取指定键盘信息
        ensure_keyboard_result = keyboard_model.get_keyboard_match_result(self.screen_shot_index, self.virtual_debug)

        x, y = ensure_keyboard_result.get_coordinates()
        h, w = ensure_keyboard_result.get_image_size()
        # 屏幕型号（像素横纵距离）
        screen_size = contour.get_contour_size()

        if (x <= 0 or y <= 0) or (x + w >= screen_size[0] or y + h >= screen_size[1]):
            # 没有匹配到键盘图像模型,或者匹配到的键盘模型在边界上
            self.dbg_record_action('press_keyboard', [keyboard_name, text], [ensure_keyboard_result], None)

            if self.virtual_debug:
                print("[Virtual Debug] press keyboard('{}', '{}'): "
                      "Failed on screen {}!".format(keyboard_name, text, self.screen_shot_index))
                self.log.record_action_end()
                return
            else:
                self.log.record_exception()
                self.reset_arms()
                raise Exception("Can not find keyboard:'{}'!".format(keyboard_name))

        key_str = ''
        key_esc = False  # 是否转义
        key_pos_seq = []
        # 按顺序键入按键。使用“[”和"]"作为转义字符,存贮特殊按键,比如"Enter"
        for key in text:
            if key_esc:
                if key == ']' and key_str != '':
                    key_esc = False
                    kpos = self.__click_key(keyboard_model, [x, y, w, h], key_str)
                    key_pos_seq.append(kpos)
                    key_str = ''
                else:
                    key_str += key
            elif key == '[':
                key_esc = True

            else:
                key_str += key
                kpos = self.__click_key(keyboard_model, [x, y, w, h], key_str)
                key_pos_seq.append(kpos)
                key_str = ''

        self.dbg_record_action('press_keyboard', [keyboard_name, text], [ensure_keyboard_result], key_pos_seq)

        #        action_exec_time = self.robot_dev.get_action_exec_time()
        if self.virtual_debug:
            print("[Virtual Debug] press keyboard('{}', '{}'): "
                  "Succeed on screen {}".format(keyboard_name, text, self.screen_shot_index))

        self.log.record_action_end()

    def __click_key(self, keyboard_file, keyboard_area, text):
        """在虚拟键盘中键入单个文字
        
        Args:
            keyboard_file: string, 指定键盘文件
            keyboard_area: 键盘在设备中所处的位置
            text: 键入的单个按键
            
        Returns:
            识别结果
        """
        # 获取键位坐标和键盘识别结果
        key_x, key_y = keyboard_file.get_key_match_results(text, keyboard_area)
        self.robot_dev.click(key_x, key_y)
        return key_x, key_y

    def swipe(self, direction, region=[0, 0, 1, 1]):
        """在屏幕中朝指定方向滑动
        
        Args:
            direction: string, 滑动方向
            region: 控件查询的范围,默认为整个被测设备屏幕
        """
        self.log.record_action_start("swipe", "'{}'".format(direction))
        self.detour('swipe', region=region)
        self.__get_snapscreen('swipe')
        reg = self.__is_region(region)
        px, py, dx, dy = self.robot_dev.swipe(reg, direction)
        self.dbg_record_action("swipe", [direction, region], [], [(px, py), (px+dx, py+dy)])

        #        action_exec_time = self.robot_dev.get_action_exec_time()
        if self.virtual_debug:
            print("[Virtual Debug] swipe('{}'): Succeed on screen {}".format(direction, self.screen_shot_index))

        self.log.record_action_end()

    def long_press(self, widget_image_name, region=[0, 0, 1, 1]):
        """在指定控件位置长按
        
        Args:
            widget_image_name: string, 控件图名称
            long_press_time: int, 长按时间,默认为1s
            region: 控件查询的范围,默认为整个被测设备屏幕
            
        Returns:
            操作结果,Ture or False
            
        Raises: 
            Exception: 没有找到指定控件
        """
        self.log.record_action_start("long press", "'{}'".format(widget_image_name))
        # 规避动作
        if self.detour('long press', widget_image_name, region):
            self.lasted_widget = widget_image_name

        if self.lasted_widget == widget_image_name:
            x, y = self.match_result.get_coordinates()
            self.dbg_record_action("long_press", [widget_image_name, region], [self.match_result], [(x, y)])
            self.robot_dev.long_press(x, y)
            self.lasted_widget = ''
            #            action_exec_time = self.robot_dev.get_action_exec_time()
            self.log.record_action_end()

            if self.virtual_debug:
                print("[Virtual Debug] long press('{}') Succeed on screen {}".format(widget_image_name, self.screen_shot_index))
            return True

        if self.__check_widget_exist(widget_image_name, region):
            x, y = self.match_result.get_coordinates()
            self.dbg_record_action("long_press", [widget_image_name, region], [self.match_result], [(x, y)])
            self.robot_dev.long_press(x, y)
            if self.virtual_debug:
                print("[Virtual Debug] long press('{}') Succeed on screen {}".format(widget_image_name, self.screen_shot_index))
        else:
            self.dbg_record_action("long_press", [widget_image_name, region], [self.match_result], None)
            # 未能识别成功            
            if self.virtual_debug:
                print("[Virtual Debug] long press('{}'): Failed on screen {} (sim={})!".format(widget_image_name, self.screen_shot_index, str(self.match_result.get_similarity())))
            else:
                self.log.record_exception()
                self.reset_arms()
                raise Exception("long press('{}') Error!".format(widget_image_name))

        #        action_exec_time = self.robot_dev.get_action_exec_time()
        self.log.record_action_end()

        return True

    def move(self, dx, dy):
        """控制机械臂移动指定距离
        
        Args:
            dx, dy: 实际移动距离,单位1cm
        """
        # 移动相对坐标,单位1毫米
        self.log.record_action_start("move",
                                     "'{}', '{}'".format(dx, dy))
        self.detour('move')
        self.robot_dev.move(dx, dy)

        #        action_exec_time = self.robot_dev.get_action_exec_time()
        if self.virtual_debug:
            print("[Virtual Debug] move('{}', '{}'): Succeed".format(dx, dy))

        self.log.record_action_end()

    def move_to(self, *args):
        """控制机械臂移动到指定位置
        
        Args:
            args: 可以传空间图像名或者坐标两种参数
            
        Raises: 
            Exception: 没有找到指定控件
        """
        self.log.record_action_start("move to", "'{}'".format(args[0]))
        self.detour('move to')

        # 判断参数类型
        if len(args) == 1 and self.__is_image_file(args[0]):
            w_exist = self.__check_widget_exist(args[0])
            if w_exist:
                x, y = self.match_result.get_coordinates()
                self.dbg_record_action('move_to', [args[0]], [self.match_result], [self.match_result.get_coordinates()])
            else:
                self.dbg_record_action('move_to', [args[0]], [self.match_result], None)

                if self.virtual_debug:
                    print("[Virtual Debug] move_to('{}'): Failed on screen {} (sim={})!".format(
                        args[0], self.screen_shot_index, self.match_result.get_similarity()))
                    self.log.record_action_end()
                    return
                else:
                    self.log.record_exception()
                    self.reset_arms()
                raise Exception("move_to('{}') Error!".format(args[0]))
        elif len(args) == 2:
            (x, y) = args
        else:
            if not self.virtual_debug:
                print("[Virtual Debug] move_to('{}'): Failed on screen {}!".format(args[0], self.screen_shot_index))
            else:
                self.log.record_exception()
                self.reset_arms()
                raise Exception("move_to('{}') Error!".format(args[0]))

        self.robot_dev.move_to(x, y)

        #        action_exec_time = self.robot_dev.get_action_exec_time()
        if self.virtual_debug:
            print("[Virtual Debug] move_to('{}'): Succeed on screen {}".format(args[0], self.screen_shot_index))

        self.log.record_action_end()

    def pen_down(self):
        """控制机械臂落笔"""
        self.log.record_action_start("pen down")
        self.detour('pen down')
        self.robot_dev.pen_down()
        #        action_exec_time = self.robot_dev.get_action_exec_time()
        if self.virtual_debug:
            print('[Virtual Debug] pen_down(): Succeed')

        self.log.record_action_end()

    def pen_up(self):
        """控制机械臂落笔"""
        self.log.record_action_start("pen up")
        self.detour('pen up')
        self.robot_dev.pen_up()

        #        action_exec_time = self.robot_dev.get_action_exec_time()
        if self.virtual_debug:
            print('[Virtual Debug] pen_up(): Succeed')

        self.log.record_action_end()

    def move_outside_of_screen(self):
        """将笔移到屏幕坐标系之外"""
        self.log.record_action_start("move outside of screen")
        self.robot_dev.move_outside_of_screen()
        #        action_exec_time = self.robot_dev.get_action_exec_time()
        if self.virtual_debug:
            print('[Virtual Debug] move_outside_of_screen(): Succeed')
        self.log.record_action_end()

    def __get_snapscreen(self, command='match'):
        """获取当前图像帧,并增加图像拍摄计数
        
        Args:
            command: 操作类型
            部分操作在获取图像时需要进行规避运动
        """
        self.screen_shot_index = self.robot_dev.get_photo_index(command)

    def take_screen_photo(self):
        """获取当前被测设备屏幕图像"""
        self.log.record_action_start("take screen photo")
        self.detour('take screen photo')

        if self.virtual_debug:
            self.screen_shot_index = self.robot_dev.get_virtual_debug_index()
        else:
            # 查看照片,最后一次拍照的时候关闭opencv
            self.__get_snapscreen('reset')
        #            action_exec_time = self.robot_dev.get_action_exec_time()
        self.log.record_action_end()
        return self.screen_shot_index

    def drag(self, start_widget, end_widget,
             start_region=[0, 0, 1, 1], end_region=[0, 0, 1, 1]):
        """将指定位置a拖拽到指定位置b
        
        Args:
            start_widget: string, 控件图名称,拖拽起点坐标
            end_widget: string, 控件图名称,拖拽终点坐标
            start_region: 起点控件查询的范围,默认为整个被测设备屏幕
            start_region: 终点控件查询的范围,默认为整个被测设备屏幕
            
        Raises: 
            Exception: 没有找到指定控件
        """
        self.log.record_action_start("drag", "'{}', '{}'".format(start_widget, end_widget))
        self.detour('drag', region=start_region)

        region1 = [0, 0, 1, 1]
        region2 = [0, 0, 1, 1]
        match_result1 = TemplateMatchResult(0, 0, 0, 0, 0)
        match_result2 = TemplateMatchResult(0, 0, 0, 0, 0)
        # 检测region信息
        if len(start_region) == 4:
            region1 = self.__is_region(start_region)
        if len(end_region) == 4:
            region2 = self.__is_region(end_region)

        # 收集两个控件信息
        if self.lasted_widget == start_widget:
            match_result1 = self.match_result
            self.lasted_widget = ''
            if self.__check_widget_exist(end_widget, region2):
                match_result2 = self.match_result
            else:
                self.dbg_record_action('drag', [start_widget, end_widget, start_region, end_region], [match_result1, self.match_result], None)

                if self.virtual_debug:
                    print("[Virtual Debug] drag('{}', '{}'): Failed! (No end widget found (sim={}))".format(start_widget, end_widget, self.match_result.get_similarity()))
                    self.log.record_action_end()
                    return
                else:
                    self.log.record_exception()
                    self.reset_arms()
                    raise Exception("drag('{}') Error!".format(end_widget))

        elif self.lasted_widget == end_widget:
            match_result2 = self.match_result
            self.lasted_widget = ''
            if self.__check_widget_exist(start_widget, region1):
                match_result1 = self.match_result
            else:
                self.dbg_record_action('drag', [start_widget, end_widget, start_region, end_region], [self.match_result, match_result2], None)

                if self.virtual_debug:
                    print("[Virtual Debug] drag('{}', '{}'): Failed! (No start widget found (sim={}))".format(start_widget, end_widget, self.match_result.get_similarity()))
                    self.log.record_action_end()
                    return
                else:
                    self.log.record_exception()
                    self.reset_arms()
                    raise Exception("drag('{}') Error!".format(start_widget))
        else:
            if self.__check_widget_exist(start_widget, region1):
                match_result1 = self.match_result
            else:
                self.dbg_record_action('drag', [start_widget, end_widget, start_region, end_region], [self.match_result, None], None)

                if self.virtual_debug:
                    print("[Virtual Debug] drag('{}', '{}'): Failed! (No start widget found (sim={}))".format(start_widget, end_widget, self.match_result.get_similarity()))
                    self.log.record_action_end()
                    return
                else:
                    self.log.record_exception()
                    self.reset_arms()
                    raise Exception("drag('{}') Error!".format(start_widget))

            if self.__check_widget_exist(end_widget, region2):
                match_result2 = self.match_result
            else:
                self.dbg_record_action('drag', [start_widget, end_widget, start_region, end_region], [match_result1, self.match_result], None)

                if self.virtual_debug:
                    print("[Virtual Debug] drag('{}', '{}'): Failed! (No end widget found (sim={}))".format(start_widget, end_widget, self.match_result.get_similarity()))
                    self.log.record_action_end()
                    return
                else:
                    self.log.record_exception()
                    self.reset_arms()
                    raise Exception("drag('{}') Error!".format(end_widget))

        #        action_exec_time = self.robot_dev.get_action_exec_time()
        if self.virtual_debug:
            print("[Virtual Debug] drag('{}', '{}'): Succeed!".format(start_widget, end_widget))

        x1, y1 = match_result1.get_coordinates()
        x2, y2 = match_result2.get_coordinates()

        self.dbg_record_action('drag', [start_widget, end_widget, start_region, end_region], [match_result1, match_result2], [(x1, y1), (x2, y2)])
        self.robot_dev.drag(x1, y1, x2, y2)
        self.log.record_action_end()

    def assert_exist(self, widget_image_name, region=[0, 0, 1, 1]):
        """检查控件是否存在
        
        Args:
            widget_image_name: string, 控件图名称
            region: 控件查询的范围,默认为整个被测设备屏幕
            
        Returns: 
            找到指定控件返回True,否则返回False
        """
        self.detour('assert exist', region=region)
        self.log.record_assert_match_start("assert exist",
                                           "'{}'".format(widget_image_name))
        self.__get_snapscreen('match')
        screen_shot = Screenshot(self.log,
                                 widget_image_name,
                                 screen_shot_index=self.screen_shot_index,
                                 region=region,
                                 virtual_debug=self.virtual_debug)
        # 选择要比对的图像
        self.match_result = screen_shot.get_image_match_result(self.algorithm.id)

        if self.algorithm.match_result_is_right(self.match_result.get_similarity()):
            self.log.record_assert_match_result("Yes")
            self.dbg_record_action('assert_exist', [widget_image_name, region], [self.match_result], [self.match_result.get_coordinates()])
            if self.virtual_debug:
                print("[Virtual Debug] assert_exist('{}'): Yes on screen {}".format(widget_image_name, self.screen_shot_index))
            else:
                print("assert_exist('{}'): Yes!".format(widget_image_name))
            return True
        else:
            self.log.record_assert_match_result("No")
            self.dbg_record_action('assert_exist', [widget_image_name, region], [self.match_result], None)
            if self.virtual_debug:
                print("[Virtual Debug] assert_exist('{}'): No on screen {} (sim={})!".format(
                      widget_image_name, self.screen_shot_index, self.match_result.get_similarity()))
            else:
                print("assert_exist('{}'): No!".format(widget_image_name))
            return False

    # 检查是否不存在某个控件
    def assert_not_exist(self, widget_image_name, region=[0, 0, 1, 1]):
        """检查控件是否不存在
        
        Args:
            widget_image_name: string, 控件图名称
            region: 控件查询的范围,默认为整个被测设备屏幕
            
        Returns: 
            没有找到指定控件返回True,否则返回False
        """
        self.detour('assert not exist', region=region)
        self.log.record_assert_match_start("assert not exist",
                                           "'{}'".format(widget_image_name))
        self.__get_snapscreen('match')
        screen_shot = Screenshot(self.log,
                                 widget_image_name,
                                 screen_shot_index=self.screen_shot_index,
                                 region=region,
                                 virtual_debug=self.virtual_debug)
        self.match_result = screen_shot.get_image_match_result(self.algorithm.id)

        if not self.algorithm.match_result_is_right(self.match_result.get_similarity()):
            self.log.record_assert_match_result("Yes")
            self.dbg_record_action('assert_not_exist', [widget_image_name, region], [self.match_result], None)

            if self.virtual_debug:
                print("[Virtual Debug] assert_not_exist('{}'): Yes on screen {}".format(widget_image_name, self.screen_shot_index))
            else:
                print("assert_not_exist('{}'): Yes!".format(widget_image_name))
            return True
        else:
            self.log.record_assert_match_result("No")
            self.dbg_record_action('assert_not_exist', [widget_image_name, region], [self.match_result], [self.match_result.get_coordinates()])

            if self.virtual_debug:
                print("[Virtual Debug] assert_not_exist('{}'): No on screen {}!".format(widget_image_name, self.screen_shot_index))
            else:
                print("assert_not_exist('{}'): No!".format(widget_image_name))
            return False

    def wait(self, widget_image_name,
             wait_time=Config.get_wait_time(),
             region=[0, 0, 1, 1]):
        """等待指定控件图像的出现
        
        Args:
            widget_image_name: string, 控件图名称
            wait_time: 等待时间,默认为5s
            region: 控件查询的范围,默认为整个被测设备屏幕
            
        Returns: 
            在等待时间内是否出现指定控件,出现返回True,否则返回False
            
        Raises: 
            Exception: 没有等到指定控件
        """
        self.log.record_action_start("wait",
                                     "'{}'".format(widget_image_name))
        self.detour('wait', region=region)

        # 每一秒进行一次查询
        for i in range(wait_time):
            if not self.virtual_debug:
                time.sleep(1)
                self.log.record_sleep_time(1)
            if self.__check_widget_exist(widget_image_name, region):
                self.log.record_action_end()
                self.dbg_record_action('wait', [widget_image_name, region], [self.match_result], [self.match_result.get_coordinates()])

                if self.virtual_debug:
                    print("[Virtual Debug] Wait('{}') Succeed on screen {}".format(widget_image_name, self.screen_shot_index))
                return True

        self.dbg_record_action('wait', [widget_image_name, region], [self.match_result], [self.match_result.get_coordinates()])
        self.log.record_custom_message("Wait('{}') Failed!".format(widget_image_name))
        if self.virtual_debug:
            print("[Virtual Debug] Wait('{}') Failed until screen {}!".format(widget_image_name, self.screen_shot_index))
        else:
            print("Wait('{}') Failed!".format(widget_image_name))
        self.log.record_action_end()
        return False

    def sleep(self, num):
        """脚本休眠"""
        self.log.record_action_start("sleep", "{}".format(num))

        if not self.virtual_debug:
            time.sleep(num)

        self.log.record_sleep_time(num)
        self.log.record_action_end()

    def reset_arms(self):
        """控制机器人返回机器人坐标系的起点
        
        一般用于程序结束,该函数结束后所有的接口和线程会全部终止
        """

        self.log.record_action_start("reset arms")
        self.__get_snapscreen('reset')
        # 控制机器和程序结束运行
        # self.end_script_run()  # 将里面的release放在exit钩子里
        if self.virtual_debug is False:
            self.robot_dev.reset()
        else:
            # 记录reset执行时间
            # action_exec_time = self.robot_dev.get_action_exec_time()
            print('[Virtual Debug] reset_arms(): Succeed')

        self.log.record_action_end()
        # 记录脚本执行结束
        # self.log.record_script_end()  # 放在exit钩子里面

    def long_press_drag(self, start_widget, end_widget,
                        start_region=[0, 0, 1, 1],
                        end_region=[0, 0, 1, 1]):
        """在指定位置a长按后拖拽到指定位置b
        
        Args:
            start_widget: string, 控件图名称,拖拽起点坐标
            end_widget: string, 控件图名称,拖拽终点坐标
            start_region: 起点控件查询的范围,默认为整个被测设备屏幕
            start_region: 终点控件查询的范围,默认为整个被测设备屏幕
            
        Raises: 
            Exception: 没有找到指定控件
        """
        self.log.record_action_start("long press drag", "'{}', '{}'".format(start_widget, end_widget))
        self.detour('long press drag', region=start_region)

        region1 = [0, 0, 1, 1]
        region2 = [0, 0, 1, 1]
        # 检测region是否有误
        if len(start_region) == 4:
            region1 = self.__is_region(start_region)
        if len(end_region) == 4:
            region2 = self.__is_region(end_region)

        # 收集两个控件坐标
        if self.lasted_widget == start_widget:
            match_result1 = self.match_result
            self.lasted_widget = ''
            if self.__check_widget_exist(end_widget, region2):
                match_result2 = self.match_result
            else:
                self.dbg_record_action('long_press_drag', [start_widget, end_widget, start_region, end_region], [match_result1, self.match_result], None)
                if self.virtual_debug:
                    print("[Virtual Debug] long press drag('{}', '{}'): Failed!".format(start_widget, end_widget))
                    self.log.record_action_end()
                    return
                else:
                    self.log.record_exception()
                    self.reset_arms()
                    raise Exception("long press drag('{}') Error!".format(end_widget))

        elif self.lasted_widget == end_widget:
            match_result2 = self.match_result
            self.lasted_widget = ''
            if self.__check_widget_exist(start_widget, region1):
                match_result1 = self.match_result
            else:
                self.dbg_record_action('long_press_drag', [start_widget, end_widget, start_region, end_region], [self.match_result, match_result2], None)
                if self.virtual_debug:
                    print("[Virtual Debug] long press drag('{}', '{}'): Failed!".format(start_widget, end_widget))
                    self.log.record_action_end()
                    return
                else:
                    self.log.record_exception()
                    self.reset_arms()
                    raise Exception("long press drag('{}') Error!".format(start_widget))

        else:
            if self.__check_widget_exist(start_widget, region1):
                match_result1 = self.match_result
            else:
                self.dbg_record_action('long_press_drag', [start_widget, end_widget, start_region, end_region], [self.match_result, None], None)
                if self.virtual_debug:
                    print("[Virtual Debug] long press drag('{}', '{}'): Failed!".format(start_widget, end_widget))
                    self.log.record_action_end()
                    return
                else:
                    self.log.record_exception()
                    self.reset_arms()
                    raise Exception("long press drag('{}') Error!".format(start_widget))

            if self.__check_widget_exist(end_widget, region2):
                match_result2 = self.match_result
            else:
                self.dbg_record_action('long_press_drag', [start_widget, end_widget, start_region, end_region], [match_result1, self.match_result], None)
                if self.virtual_debug:
                    print("[Virtual Debug] long press drag('{}', '{}'): Failed!".format(start_widget, end_widget))
                    self.log.record_action_end()
                    return
                else:
                    self.log.record_exception()
                    self.reset_arms()
                    raise Exception("long press drag('{}') Error!".format(end_widget))

        if self.virtual_debug:
            print("[Virtual Debug] long press darg('{}', '{}'): "
                  "Succeed!".format(start_widget, end_widget))

        x1, y1 = match_result1.get_coordinates()
        x2, y2 = match_result2.get_coordinates()

        self.dbg_record_action('long_press_drag', [start_widget, end_widget, start_region, end_region], [match_result1, match_result2], [(x1, y1), (x2, y2)])
        self.robot_dev.press_drag(x1, y1, x2, y2)
        # 记录操作执行时间
        #        action_exec_time = self.robot_dev.get_action_exec_time()
        self.log.record_action_end()

    def report_error(self, error_text):
        """错误提示"""
        # TODO
        self.log.record_custom_message(error_text)
        self.reset_arms()
        raise Exception(error_text)

    def exit_hooks(self):
        if self.virtual_debug:
            # 记录动作信息，便于调试
            action_log_path = os.path.join(TestScript.script_test_dir(), '%s.actions' % (TestScript.get_pyname()))
            with open(action_log_path, 'w') as f:
                dev_pos = Config.get_equipment_contour()
                data = {"dev_pos": dev_pos, "debug_folder": Config.get_virtual_debug_dir(), "actions": self.action_log}
                json.dump(data, f, indent=4)
            return

        if self.robot_dev.is_need_reset():
            self.reset_arms()
        self.robot_dev.release()
        self.log.record_script_end()

    def dbg_record_action(self, action_type, action_params, tm_match_results, coordinate_seq):
        if not self.virtual_debug:
            return

        record = {"action": action_type, "params": action_params, "tm_match": [], "positions": coordinate_seq}
        if tm_match_results is not None:
            for m in tm_match_results:
                if m is None:
                    record["tm_match"].append(None)
                else:
                    record["tm_match"].append({
                        "image": os.path.abspath(m.image),
                        "template": os.path.abspath(m.template),
                        "bounds": [m.x - m.w/2, m.y - m.h/2, m.x + m.w/2, m.y + m.h/2],
                        "similarity": m.similarity})

        self.action_log.append(record)

        if coordinate_seq is None:
            return

        screenshot_path = Screenshot.get_screenshot_path(self.screen_shot_index, self.virtual_debug)
        screenshot = cv2.imread(screenshot_path)
        # 获取当前屏幕操作区域
        dev_region = Config.get_equipment_contour()
        device_image = screenshot[dev_region[1]: dev_region[3], dev_region[0]: dev_region[2]]
        cv2.putText(device_image, action_type, (30, 40), cv2.FONT_HERSHEY_COMPLEX, 1, (0,255,0), 3)

        if action_type=="click" or action_type=='long_press' or action_type=='double_click':
            point = (int(coordinate_seq[0][0]), int(coordinate_seq[0][1]))
            cv2.circle(device_image, point, 3, (0,0,255), 8)
        elif action_type=="drag" or action_type=='long_press_drag' or action_type=="swipe":
            start_point, end_point = coordinate_seq[0], coordinate_seq[1]
            start_point = (int(start_point[0]), int(start_point[1]))
            end_point = (int(end_point[0]), int(end_point[1]))
            cv2.circle(device_image, start_point, 3, (0,0,255), 6)
            cv2.circle(device_image, end_point, 3, (0,0,255), 6)
            cv2.arrowedLine(device_image, start_point, end_point, (0,0,255), 2,8,0,0.2)
        elif action_type=="press_keyboard":
            last_pt = None
            for pt in coordinate_seq:
                point = (int(pt[0]), int(pt[1]))
                cv2.circle(device_image, point, 3, (0,0,255), 6)
                if last_pt is not None:
                    cv2.arrowedLine(device_image, last_pt, point, (0, 0, 255), 2, 8, 0, 0.2)
                last_pt = point

        action_image_path = TestScript.script_test_dir() + os.sep \
                            + "%s_action_%d.png" % (TestScript.get_pyname(), self.screen_shot_index)
        cv2.imwrite(action_image_path, device_image)