# -*- coding: utf-8 -*-
"""

@author: szy
"""
import os
from ruamel import yaml
from PIL import Image

from config import Config
from screenshot import Screenshot
from test_script import TestScript

class Keyboard(object):
    def __init__(self, log, keyboard_name):
        self.log = log
        self.kb_images = ''
        self.kb_size = (0,0)
        self.fitted = 1
        kb_image_path = os.path.abspath(os.path.join(
                Config.get_keyboard_dir(), keyboard_name, 'keyboard.png'))  # 获取键盘图片
        keyboard_yaml = os.path.abspath(os.path.join(
                Config.get_keyboard_dir(), keyboard_name, 'keyboard.yaml'))  # 获取键盘配置文件
        try:
            keyboard_file = open(keyboard_yaml)
            kb_original_image = Image.open(kb_image_path)
        except FileNotFoundError as e:
            raise FileNotFoundError(e)
        keyboard_data = yaml.load(keyboard_file, Loader=yaml.Loader)  # 读取配置文件
        keyboard_file.close()
        
        kb_original_size = keyboard_data['keyboard']['original_screen_size']
        self.area = keyboard_data['keyboard']['area']
        self.__fit(kb_original_size)# 计算转换比例
        self.kb_size = kb_original_image.size
        self.kb_size = (int(self.kb_size[0] * self.fitted), 
                        int(self.kb_size[1] * self.fitted))
        self.kb_images = kb_original_image.resize(self.kb_size)  # 转换键盘图片大小
        
    def __fit(self, kb_original_size):
        #计算转换比例
        
        if kb_original_size[0] == 0 or kb_original_size[1] == 0:
            self.fitted = 1
        else:
            image_size = Config.get_screenshot_size()
            image_area = image_size[0] * image_size[1]
            kb_area = kb_original_size[0] * kb_original_size[1]
            self.fitted = (image_area / kb_area) ** 0.5# 开根号
        
    def __match_exist_image(self, dirs_path, image):# 检查图片是否存在
        try:
            open(dirs_path + '/' + image)
        except FileNotFoundError as e:
            raise FileNotFoundError(e)
        return dirs_path + '/' + image
    
    def get_keyboard_match_result(self, screen_shot_index, virtual_debug):
        """确定keyboard键盘坐标
        
        Args:
            screen_shot_index: 当前拍摄的图像编号
            virtual_debug: 虚拟调试功能
        """
        # 将转换大小后的临时键盘图像存储于widgets文件中，用于键盘匹配
        temporary_keyboard_path = TestScript.get_temporary_keyboard_image(screen_shot_index)
        self.kb_images.save(temporary_keyboard_path)
        
        # 获取对应的拍摄图像
        screen_shot = Screenshot(self.log,
                                 widget_image = 'keyboard_{}.png'.format(screen_shot_index),
                                 screen_shot_index = screen_shot_index,
                                 virtual_debug=virtual_debug)
        keyboard_match_result = screen_shot.get_image_match_result('sift')
        
#        keyboard_match_result = template_match.surf_match(screen_shot_path,
#                                                          temporary_keyboard_path)  # 计算键盘坐标
        h,w = keyboard_match_result.get_image_size()
        keyboard_match_result.add_coordinates(-w/2, -h/2)# 将识别坐标改为左上角坐标
        
        # 删除临时图像
        os.remove(temporary_keyboard_path)
        
        return keyboard_match_result
    
    def get_key_match_results(self, key, keyboard_area):
        """计算单个键位值key的坐标
        
        Args:
            key: 键值
            keyboard_area: 键盘图像在图中的坐标
            [key_x, key_y]: 
        """
        
        for i in self.area:
            # 检测键值在那个area内
            kBarea = KBArea(self.area[i])
            # 判断键值是否在该区间,若存在，返回坐标，否则，坐标为空
            key_area_coordinates = kBarea.find_key(key)
            
            if key_area_coordinates:
                # 键值在该区间内
                
                # 整个键盘图标的横纵坐标起点,长宽
                [x, y, w, h] = keyboard_area
                # 键值横坐标为键值横坐标比例*键盘宽度+键盘起点横坐标
                key_x = int(w * key_area_coordinates[0]) + x
                
                # 键值纵坐标为键值纵坐标比例*键盘高度+键盘起点纵坐标
                key_y = int(h * key_area_coordinates[1]) + y
                return [key_x, key_y]
        
        return [0,0]
    
class KBArea(object):
    def __init__(self, area):
        self.region = [0,0,1,1]  # 行区间
        self.defaut_row_margin = [0,0,0,0]  # 默认的每一行的与周围其他行的间隔
        self.defaut_key_margin = [0,0,0,0]  # 默认的每个键的与周围其他键的间隔
        self.rows = ''
        
        self.region = area['region']
        if 'defaut_row_margin' in area:
            self.defaut_row_margin = area['defaut_row_margin']
        if 'defaut_key_margin' in area:
            self.defaut_key_margin = area['defaut_key_margin']
        self.rows = area['rows']
        
    def find_key(self, key):
        """寻找键值key
        若存在，则返回key的坐标；否则，返回空
        """
        key_area_coordinates = [0,0]  # 键值在区域内的坐标
        key_row_coors = [0,0]  # 键值所在行的区域范围
        area_height = 0  # 所有区域的总高度
        ensure_key_exist = False  # 键值是否存在
        
        for row in self.rows:
            # 在每一行寻找对应的键值
            # 一次循环记录所有列的总高度
            kBRow = KBRow(row)
            # 获取当前行与其它行的间隔
            cur_row_margin = kBRow.row_margin
            
            if kBRow.match_row_key(key):
                # 找到键值，记录当前行的中心高度
                ensure_key_exist = True
                
                # 获取键在当前行中的横纵坐标比例
                key_row_coors = kBRow.get_key_coordinates(key)
                # 纵坐标需要加上之前的行高
                key_row_coors[1] += area_height
            
            # 记录总的区域高度,增加行高和间隔高度
            area_height += 1
            area_height += cur_row_margin[1]
            
        if not ensure_key_exist:
            return []
        
        # 去掉末行的间隔高度
        area_height -= self.defaut_row_margin[3]
        
        # 横坐标为: 当前区域region的范围*键值在行中的长度比例+region最左边的值
        key_area_coordinates[0] = ((self.region[2] - self.region[0])
                              * key_row_coors[0] + self.region[0])
        # 纵坐标为: 当前区域region的范围*键值在列中的高度比例+region最上边的值
        key_area_coordinates[1] = ((self.region[3] - self.region[1])
                              * key_row_coors[1] / area_height
                              + self.region[1])
        
        return key_area_coordinates
        
class KBRow(object):
    """keyboard每一行的信息
    
    Attributes:
        keys: 该行键值
        margin: 该行的键值之间的裂隙大小
    """
    def __init__(self, row):
        self.keys = []
        
        self.row_margin = [0,0,0,0]
        # 全部转换为小写，便于查找
        for key in row['keys']:
            if isinstance(key, dict):
                key =  {k.lower(): v for k, v in key.items()}
            self.keys.append(key)
#        self.keys = [key.lower() for key in row['keys']]
        if 'margin' in row:
            self.margin = row['margin']
    
    def match_row_key(self, key):
        key = key.lower()
        if key in self.keys:
            return True
        for k in self.keys:
            if isinstance(k,dict) and key in k:
                return True
        return False
    
    def get_key_coordinates(self, key):
        """获取键值在该行内的横坐标"""
        key = key.lower()
    
        key_x = 0  # 键值的横坐标
        key_y = 1/2  # 键值的纵坐标
        
        row_length = 0  # 当前行的总长度
        for k in self.keys:
            # 依次搜索每个键值
            if isinstance(k,dict) and key in k:
                # 键值拥有特殊的区域大小，且是key
                # 记录键值的当前坐标
                key_x = row_length + k[key][0]/2
                row_length += k[key][0]
                key_y = k[key][1]/2
            
            elif isinstance(k,dict):
                # 键值拥有特殊的大小，且不为key
                for key_value in k:
                    row_length += k[key_value][0]
            
            elif key == k:
                # key为普通键位，横向长度默认为1/2
                key_x = row_length + 1/2
                row_length += 1
                
            else:
                # 不为key的普通键位
                row_length += 1
            
            # 每个键值宽度加一下裂隙    
            row_length += self.row_margin[2]
        # 最后一个margin不需要
        row_length -= self.row_margin[2]
        
        return [key_x / row_length, key_y]
