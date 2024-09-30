# -*- coding: utf-8 -*-
'''
Manage test script related information
@author: szy
'''

import sys
import os
from os import path
import time

class TestScript(object):
    """测试脚本文件配置"""
    widget_dir = None
    
    @staticmethod  
    # 测试脚本绝绝对路径
    def script_py_dir():
        return os.getcwd()
    
    @staticmethod  
    # 控件图片集
    def script_widgets_dir():
        if TestScript.widget_dir is None:
            images_dir = path.join(os.getcwd(), 'images')
            if not os.path.exists(images_dir):
                os.makedirs(images_dir)
            TestScript.widget_dir = images_dir
        return TestScript.widget_dir

    @staticmethod
    def set_script_widgets_dir(dir):
        TestScript.widget_dir = dir
    
    @staticmethod
    def script_video_dir():
        """脚本执行视频存放路径"""
        images_dir = path.join(os.getcwd(), 'video/')
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
        
        return images_dir
    
    @staticmethod  
    # 存放中间结果路径
    def script_temporary_dir():
        temporary_dir = path.join(os.getcwd(), 'temp/')
        if not os.path.exists(temporary_dir):
            os.makedirs(temporary_dir)
        
        return temporary_dir

    @staticmethod  
    # 截取控件时拍摄的图片路径
    def script_snapscreen_path():
        return path.join(TestScript.script_temporary_dir(), '_snapscreen.png')
    
    @staticmethod  
    # 存储测试结果文件夹
    def script_test_dir():
        test_dir = path.join(os.getcwd(), 'test/')
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)
        return test_dir
    
    @staticmethod  
    # 获取default.snapscreen路径
    def get_default_snapscreen_path():
        return path.join(TestScript.script_widgets_dir(), 'default.snapscreen')

    @staticmethod  
    # 获取当前操作的测试脚本文件名    
    def get_pyname():
        document = path.basename(sys.argv[0])
        (pyname, extension) = os.path.splitext(document)
        return pyname
    
    @staticmethod  
    # 获取测试对应的中间图片路径
    def get_temp_image():
        return path.join(TestScript.script_temporary_dir(),
                         TestScript.get_pyname())
    
    @staticmethod  
    def get_detour_image_path():
        """获取规避运动中间图片的路径"""
        return path.join(TestScript.script_test_dir(), 
                         '{}_detour.png'.format(TestScript.get_pyname())) 
    
    @staticmethod  
    # 存放每个测试脚本的log文件的路径
    def get_log_path():
        log_path = path.join(os.getcwd(), 'log/')
        if not os.path.exists(log_path):
            os.makedirs(log_path)
            
        local_time_array = time.localtime(time.time())
        local_time = time.strftime("%Y-%m-%d_%H%M%S", local_time_array)
        log_file_name = '{}_{}.log'.format(TestScript.get_pyname(), local_time)
        
        return path.join(log_path, log_file_name)
    
    @staticmethod  
    # 记录脚本的拍照文件路径
    def get_photoshot_log_path():
        """获取脚本的拍照文件日志记录路径"""
        log_path = path.join(os.getcwd(), 'log/')
        if not os.path.exists(log_path):
            os.makedirs(log_path)
        photoshot_log_path = path.join(log_path, '_photo_shot.log')
        # 清空原有的日志信息
        open(photoshot_log_path, 'w').close()
#        if os.path.exists(photoshot_log_path):
#            os.remove(photoshot_log_path)
        
        return photoshot_log_path
    
    @staticmethod  
    # 记录脚本的模板匹配时间文件的路径
    def get_template_match_log_path():
        log_path = path.join(os.getcwd(), 'log/')
        if not os.path.exists(log_path):
            os.makedirs(log_path)
            
        template_match_log_path = path.join(log_path, '_template_match.log')
        # 清空原有的日志信息
        open(template_match_log_path, 'w').close()
#        if os.path.exists(template_match_log_path):
#            os.remove(template_match_log_path)
        
        return template_match_log_path
    
    @staticmethod  
    # 测试过程使用的临时键盘图片路径
    def get_temporary_keyboard_image(screen_shot_index):
        return path.join(TestScript.script_widgets_dir(), 
                         'keyboard_{}.png'.format(screen_shot_index))
    
    @staticmethod  
    # 测试过程使用的键盘识别结果存放路径
    def get_match_result_keyboard_path(screen_shot_index):
        return path.join(TestScript.script_test_dir(), 
                         '{}_{}_keyboard.png'.format(
                                 TestScript.get_pyname(), screen_shot_index))