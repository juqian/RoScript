# -*- coding: utf-8 -*-
"""
Screenshot processing

@author: szy
"""

import os
import numpy as np
from PIL import Image
import cv2
import template_match
from test_script import TestScript
from config import Config
from ruamel import yaml

DELTA = 0.05

#获取当前操作区域
def _get_device_contour(oper_region, contour_size):
    width = contour_size[2] - contour_size[0]
    height = contour_size[3] - contour_size[1]
    
    region_size = [width, height, width, height]
    if len(oper_region) != 4:
        oper_region = [0,0,1,1]
    
    region_range = [a*b for a, b in zip(region_size, oper_region)]
    origin_region = [contour_size[0], contour_size[1]] * 2
    region_area = np.array(region_range) + np.array(origin_region)
    
    return region_area.tolist()


class Screenshot(object):
    """图像控制类
    
    Attributes:
        log: 日志记录
        widget_image: 控件图像名
        screen_shot_index: 图像编号
        region: 匹配区域，默认为整个屏幕
        virtual_debug: 虚拟调试功能
        detour_frame_path: 分步规避运动的视频帧存储路径
    """
    
    def __init__(self,
                 log,
                 widget_image='', 
                 screen_shot_index=0,
                 region=[0, 0, 1, 1], 
                 virtual_debug=False, 
                 detour_frame_path=''):
        self.log = log
        self.widget_scaled = False
        self.widget_image_path = self.__get_widget_path(widget_image)
        self.oper_region = region
        if screen_shot_index != 0:
            self.screen_shot_path = Screenshot.get_screenshot_path(screen_shot_index, virtual_debug)
        elif detour_frame_path != '':
            self.screen_shot_path = detour_frame_path
        else:
            raise FileNotFoundError('No Screen Shot Image')
    
    # 返回目标图片集的绝对路径
    def __get_widget_path(self, widget_image):
        """获取根据屏幕分辨率修改后的控件图像
        Args:
            widget_image: 控件图像名
        Return: 根据裁剪时和运行时的屏幕分辨率缩放后的控件图像
        """
        widget_dir = TestScript.script_widgets_dir()
        widget_path = os.path.join(widget_dir, widget_image)
        Screenshot.__check_image_exist(widget_path)
        return self.__scale_normalize(widget_path, widget_image)
    
    # 修改widget大小
    def __scale_normalize(self, widget_path, widget_image):# 大小修改
        """修改控件大小
        Args:
            widget_path: 原始控件路径
            widget_image: 控件名
        """
        wiget_device_contour = self.__get_widget_device_contour(widget_image)
        if wiget_device_contour == self.__get_cur_device_contour():
            return widget_path
        
        button_device_area = wiget_device_contour[0] * wiget_device_contour[1]
        
        cur_device_contour = self.__get_cur_device_contour()
        cur_device_area = cur_device_contour[0] * cur_device_contour[1]
        # 计算缩放比例，如果缩放较小，可以使用原图匹配
        # 缩放公式：当前设备轮廓/记录控件时的设备轮廓
        scaling = (cur_device_area / button_device_area) ** 0.5
        if scaling < (1 + DELTA) and scaling > (1 - DELTA):
            return widget_path

        # 记录缩放数据
        self.log.record_TM_scale(scaling)

        origin_widget = Image.open(widget_path)
        #原始控件的大小
        width, height = origin_widget.size
        scaling_widget = origin_widget.resize((int(width * scaling), int(height * scaling)), Image.ANTIALIAS)
        #将缩放后的控件存为临时控件
        scaling_widget_path = os.path.join(TestScript.script_test_dir(), widget_image)
        scaling_widget.save(scaling_widget_path)
        self.widget_scaled = True
        return scaling_widget_path
    
    # 检测图片是否存在
    @staticmethod
    def __check_image_exist(path):
        """检测文件是否存在 """
        if not os.path.exists(path):
            raise FileNotFoundError(path)
    
    #获取当前设备轮廓
    def __get_cur_device_contour(self):
        """获取当前写在sut.yaml中的设备分辨率"""
        cur_device_contour = Config.get_equipment_contour()
        width = cur_device_contour[2] - cur_device_contour[0]
        height = cur_device_contour[3] - cur_device_contour[1]
        return [width, height]
    
    #读取图片的配置文件widget_path, widget_image
    def __get_widget_device_contour(self, widget_image):
        """获取采集控件图像时的屏幕分辨率,即控件图像对应的'.snapscreen'文件
        
        Args:
            widget_image: 控件图像名
        Return:
            若存在对应的文件,则直接返回文件内记录的屏幕分辨率,
            若不存在，则返回默认的配置文件'default.snapscreen',
            若默认的配置文件也不存在,则使用当前记录的设备分辨率,写在'sut.yaml'中。
        """
        #获取控件图片集的绝对路径
        widget_dir = TestScript.script_widgets_dir()
        #获取控件图片对应的配置文件路径
        (widget_name, extension) = os.path.splitext(widget_image)
        widget_config_path = os.path.join(widget_dir, 
                                          '{}.snapscreen'.format(widget_name))
        
        # 判断是否存在该图片的特殊配置文件
        if os.path.isfile(widget_config_path):
            screenshot_config_path = widget_config_path
        else:
            screenshot_config_path = TestScript.get_default_snapscreen_path()
            if not os.path.isfile(screenshot_config_path):
                return self.__get_cur_device_contour()
        
        return self.__get_screenshot_config(screenshot_config_path)
    
    #读取screenshot文件信息
    def __get_screenshot_config(self, config_file_path):
        
        widget_config_file = open(config_file_path)
        widget_config_content = yaml.load(widget_config_file, Loader= yaml.Loader)
        widget_config_file.close()
        
        if 'address' in widget_config_content:  
            # 如果存放了地址，则返回控件图像对应的设备轮廓图像位置
            button_contour_address = widget_config_content['addrerss']
            if os.path.isfile(button_contour_address):
                button_contour_image = Image.open(button_contour_address)
                return button_contour_image.size()                
        
        if 'contour' in widget_config_content:
            # 如果没有记录地址，则返回记录得设备轮廓区域分辨率
            x = widget_config_content['contour']['width']
            y = widget_config_content['contour']['height']
            return [x, y]        
        else:
            #如果都没有, 则返回当前设备轮廓的大小
            return self.__get_cur_device_contour()
    
    #当前屏幕图片
    @staticmethod
    def get_screenshot_path(screen_shot_index, virtual_debug):
        if virtual_debug:
            screen_shot_dir = Config.get_virtual_debug_dir()
            screen_shot_name = '{}_{}.png'.format(TestScript.get_pyname(), screen_shot_index)
            screen_shot_path = os.path.join(screen_shot_dir, screen_shot_name)
            if os.path.exists(screen_shot_path):
                return screen_shot_path
            else:
                name = os.path.basename(TestScript.script_py_dir())
                screen_shot_name = '{}_{}.png'.format(name, screen_shot_index)
                screen_shot_path = os.path.join(screen_shot_dir, screen_shot_name)
                Screenshot.__check_image_exist(screen_shot_path)
                return screen_shot_path
        else:
            screen_shot_dir = TestScript.script_temporary_dir()
            screen_shot_name = '{}_{}.png'.format(TestScript.get_pyname(), screen_shot_index)
            screen_shot_path = os.path.join(screen_shot_dir, screen_shot_name)
            Screenshot.__check_image_exist(screen_shot_path)
            return screen_shot_path
    
    #获取图像匹配结果
    def get_image_match_result(self, algorithm='tcfn'):
        # 目标匹配
        screen_shot =  Image.open(self.screen_shot_path)
        #获取当前屏幕操作区域
        equipment_contour = Config.get_equipment_contour()
        cur_device_contour = _get_device_contour(self.oper_region, equipment_contour)
        #切割设备屏幕
        device_image = screen_shot.crop((cur_device_contour[0],
                                         cur_device_contour[1],
                                         cur_device_contour[2],
                                         cur_device_contour[3]))# 获取设备轮廓图
        
        #保存屏幕轮廓图（可删）
        (filepath, tempfilename) = os.path.split(self.screen_shot_path)
        (filename, extension) = os.path.splitext(tempfilename)
        device_image_path = '{}/{}_contour.png'.format(TestScript.script_test_dir(), filename)
        device_image.save(device_image_path)# 存取识别轮廓图（可删）
        
        template_match_result = self.match(device_image_path, algorithm)# 识别结果只是轮廓区域的左上角
        h,w = template_match_result.get_image_size()
        
        #画识别区域
        #TODO
        #存放结果图片（可删）
        x, y = template_match_result.get_coordinates()
        
        device_screen_image = cv2.imread(device_image_path)# 获取当前图片
        cv2.rectangle(device_screen_image,(int(x), int(y)), (int(x + w), int(y + h)), (0,0,255),2)
        match_result_path = '{}/{}_match.png'.format(TestScript.script_test_dir(), filename)
        cv2.imwrite(match_result_path, device_screen_image)# 将识别结果存储到文件中
        os.remove(device_image_path)
        
        # 计算region区域到设备轮廓边界的距离
        px = cur_device_contour[0] - equipment_contour[0]
        py = cur_device_contour[1] - equipment_contour[1]
        #将位置调整到设备轮廓中的控件中心点，以设备左上角为原点
        template_match_result.add_coordinates(w/2 + px, h/2 + py)
        return template_match_result
    
    #进行图像匹配
    def match(self, device_image_path, algorithm):
        # 选择图像识别函数
        self.log.record_TM_start()
        #选择算法
        match_result = template_match.TEMPLATE_MATCHERS[algorithm](device_image_path, self.widget_image_path)
        self.log.record_TM_result(match_result)

        if self.widget_scaled:
            os.remove(self.widget_image_path)
        return match_result
    
    def save_detour_frame(self, screen_shot_index, virtual_debug):
        """保存规避过程中保留的视频帧"""
        
        temporary_dir = TestScript.script_temporary_dir()
        screen_shot_name = '{}_{}.png'.format(TestScript.get_pyname(),
                                              screen_shot_index)
        
        screen_shot_path = '{}/{}'.format(temporary_dir, screen_shot_name)
        # 读取临时帧路径，并保到指定文件中
        frame = cv2.imread(self.screen_shot_path)
        cv2.imwrite(screen_shot_path, frame)
        
    
def crop_snap_screen(snap_path):
    """裁剪出屏幕区域"""
    screen_shot =  Image.open(snap_path)
    #获取当前屏幕操作区域
    cur_device_contour = _get_device_contour([0,0,1,1],
                                              Config.get_equipment_contour())
    #切割设备屏幕
    device_image = screen_shot.crop((cur_device_contour[0],
                                     cur_device_contour[1],
                                     cur_device_contour[2],
                                     cur_device_contour[3]))
    
    device_image.save(snap_path)