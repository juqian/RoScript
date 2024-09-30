# -*- coding: utf-8 -*-
import sys

from ruamel import yaml
import json
import os
from os import path

# Specify whether use the directory containing python code as the tool home
# USE_PYTHON_PROJECT_AS_HOME = True
USE_PYTHON_PROJECT_AS_HOME = False


CODE_BASE = os.path.dirname(__file__)
rpos = CODE_BASE.rfind("RoScript")
if rpos>=0:
    RoScriptHome = CODE_BASE[: rpos + len("RoScript")]
    if not os.path.exists(os.path.join(RoScriptHome, "config")):
        RoScriptHome = None
else:
    RoScriptHome = None


if USE_PYTHON_PROJECT_AS_HOME or RoScriptHome is None:
    g_tool_home = CODE_BASE

    g_sut_path = "config/sut.yaml"
    g_config_path = "config/config.yaml"
    g_camera_data_path = 'config/camera.json'
    g_frontend_options_path = "../../../config/ui/frontend_options.yaml"
else:
    # 以最后一个RoScript文件夹为home位置
    g_tool_home = RoScriptHome

    g_sut_path = "config/roscript/sut.yaml"
    g_config_path = "config/roscript/config.yaml"
    g_camera_data_path = 'config/roscript/camera.json'
    g_frontend_options_path = "config/ui/frontend_options.yaml"


g_config_path = os.path.join(g_tool_home, g_config_path)
g_sut_path= os.path.join(g_tool_home, g_sut_path)
g_camera_data_path = os.path.join(g_tool_home, g_camera_data_path)


# if there are configs in the working directory, prefer to use these
local_sut_path = os.path.join(os.getcwd(), "config", "sut.yaml")
if os.path.exists(local_sut_path):
    g_sut_path = local_sut_path

local_config_path = os.path.join(os.getcwd(), "config", "config.yaml")
if os.path.exists(local_config_path):
    g_config_path = local_config_path

local_camera_path = os.path.join(os.getcwd(), "config", "camera.json")
if os.path.exists(local_camera_path):
    g_camera_data_path = local_camera_path


def read_config_file(config_file_path):
    file = open(config_file_path)
    file_content = yaml.load(file, Loader=yaml.Loader)
    file.close()
    return file_content


# config文件参数
g_config_content = read_config_file(g_config_path)
# data文件参数
g_sut_content = read_config_file(g_sut_path)
# 虚拟调试目录
g_virtual_debug_folder = None


# 读取并分析配置文件
class Config(object):
    """配置文件读写以及路径获取"""
    @staticmethod
    def load_config(config_path):
        global g_config_path, g_config_content
        g_config_path = config_path
        g_config_content = read_config_file(config_path)
        return g_config_content

    @staticmethod
    def load_sut_config(sut_config_path):
        global g_sut_path, g_sut_content
        g_sut_path = sut_config_path
        g_sut_content = read_config_file(sut_config_path)
        return g_sut_content
    
    @staticmethod     
    # 获取bbs算法路径
    def get_bbs_lib_path():
        dll_dir = path.join(g_tool_home, 'rsc/dll/')
        return path.join(dll_dir, 'BBS.dll')

    @staticmethod 
    # 获取相机标定后的相机配置文件
    def get_calibration_camera_file_path():
        return g_camera_data_path

    @staticmethod
    def get_sys_config_file_path():
        return g_config_path

    @staticmethod
    def get_sut_config_file_path():
        return g_sut_path

    @staticmethod 
    # output文件夹
    def get_output_dir():
        return path.join(g_tool_home, 'output/')
    
    @staticmethod 
    # 存储落笔过程的文件夹
    def get_tip_falling_dir():
        return path.join(Config.get_output_dir(), 'pen_falling')
    
    @staticmethod 
    # 键盘文件夹
    def get_keyboard_dir():
        return path.join(g_tool_home, 'rsc/keyboard/')
    
    @staticmethod 
    # 获取校准图片的路径
    def get_calibration_image():
        return path.join(Config.get_output_dir(), 'calibration.png')
    
    @staticmethod 
    # 机械臂定位图片路径
    def get_calibration_robot_image():
        return path.join(Config.get_output_dir(), 'robotMarkings.png')
    
    @staticmethod 
    # 获取设备轮廓图片路径
    def get_devicescreen_image():
        return path.join(Config.get_output_dir(), 'deviceScreen.png')
    
    @staticmethod 
    # 设备轮廓校准前拍照路径
    def get_calibration_screenshot_image():
        return path.join(Config.get_output_dir(), 'snapScreen.png')
    
    @staticmethod
    # 获取落笔点击原图像路径
    def get_tip_status_img_pth():
        return path.join(Config.get_output_dir(), '_tip_status.png')
    
    @staticmethod
    # 获取落笔点击局部图像路径
    def get_tip_region_img_pth():
        return path.join(Config.get_output_dir(), '_tip_region.png')
    
    @staticmethod  
    # 获取机器人型号参数
    def get_robot_manufactor():
        # 机器人型号参数
        robot_manufactor = g_config_content['Robot']['ROBOT_MANUFACTOR']['ID']
        return robot_manufactor
    
    @staticmethod  
    # 获取相机编号
    def get_capture_id():
        # 摄像机编号
        capture_id = g_config_content['Robot']['CAPTURE']['ID']
        return capture_id
    
    @staticmethod
    def get_capture2_id():
        # 获取辅助摄像头id
        capture2_id = g_config_content['Robot']['CAPTURE']['ID2']
        return capture2_id
    
    @staticmethod  
    # 获取摄像机焦距
    def get_camera_focus():
        # 焦距
        focus = g_sut_content['Camera']['Focus']
        return focus
    
    @staticmethod  
    # 获取相片旋转角度
    def get_rotation_angle():
        # 图片旋转角度
        angle = g_sut_content['Camera']['RotationAngle']
        if angle % 90 == 0:
            return angle
        return 0
    
    @staticmethod  
    # 获取笔的高度
    def get_tip_height():
        # 笔的高度
        pen_altitude = g_sut_content['Robot']['TipHeight']  # 计算落笔高度
        return pen_altitude
    
    @staticmethod  
    # 获取笔的初始落笔高度
    def get_tip_initial_height():
        # 笔的高度
        pen_initial_height = g_config_content['Robot']['ROBOT_MANUFACTOR']['TipHeight']
        return pen_initial_height
    
    @staticmethod
    def get_tip_contour():
        """获取落笔识别区域"""
        tip_contour = g_sut_content['Camera']['TipContour']
        w, h = [int(size) for size in tip_contour.split("*")][:2]
        return w, h
    
    @staticmethod  
    # 获取被测设备厚度
    def get_model_thickness():
        # 被测设备厚度
        model_thickness = g_sut_content['Model']['FullSize']['thickness']
        return model_thickness
    
    @staticmethod  
    # 获取笔高度落差
    def get_pen_high_dead():
        # 笔高度的落差
        hight_error = [g_config_content['Robot']['ROBOT_MANUFACTOR']['ROBOT_ARM_HEIGHT_ERROR']['X'],
                       g_config_content['Robot']['ROBOT_MANUFACTOR']['ROBOT_ARM_HEIGHT_ERROR']['Y']]
        return hight_error
    
    @staticmethod
    def get_one_cm_steps():
        # 获取1cm步进电机的运动步数、
        one_cm_steps = g_config_content['Robot']['ROBOT_MANUFACTOR']['ONE_CM_STEPS']
        return one_cm_steps
    
    @staticmethod
    # 获取标志物到笔尖的实际相对距离
    def get_circle_to_pen_distance():
        return g_config_content['Robot']['ROBOT_MANUFACTOR']['CIRCLE_TO_PEN']
    
    @staticmethod  
    # 获取机械臂移动范围
    def get_robot_arm_range():
        #机械臂移动范围
        robot_arm_range = [g_config_content['Robot']['ROBOT_MANUFACTOR']['LENGTH']['X'], 
                        g_config_content['Robot']['ROBOT_MANUFACTOR']['LENGTH']['Y']]
        return robot_arm_range
            
    
    @staticmethod  
    # 获得缩放比例，即照片和物理世界的比例尺
    def get_scale_rate():# 获取像素与物理距离的比例
        '''get photo to reality scale rate
        Returns:
            pixel_to_physical: 像素与物理世界的距离比例关系，保留两位小数
        '''
        calibration_camera_file_path = Config.get_calibration_camera_file_path()
        if os.path.isfile(calibration_camera_file_path):
            # 如果存在camera.json文件，则读取文件中的配置
            with open(calibration_camera_file_path, 
                    'r', encoding='utf-8') as rf:
                data = json.load(rf)
            proportion = data['pixel_to_physical']
        else:
            # 如果不存在camera文件，则使用被测设备实际尺寸和像素分辨率进行计算
            device_width = g_sut_content['Model']['FullSize']['width']
            device_height = g_sut_content['Model']['FullSize']['height']
            contour_width = g_sut_content['Model']['ContourPosition']['width']
            contour_height = g_sut_content['Model']['ContourPosition']['height']
            device_area = device_width * device_height
            contour_area = contour_width * contour_height
            proportion = (contour_area/device_area) ** 0.5
        return round(proportion, 2)
    
    @staticmethod     
    # 获取机器人串口通信串口号
    # 当无法自动检测到机器人串口信息时，则使用本函数获取配置文件的串口配置
    def get_robot_port():
        robot_port = g_config_content['Robot']['ROBOT_MANUFACTOR']['Port']
        return robot_port
    
    @staticmethod     
    # 获取机器人相对位置，即机器人位置布局,
    def get_robot_layout():
        robot_layout = eval(g_config_content['Robot']['ROBOT_MANUFACTOR']['Layout'])
        return robot_layout
    
    @staticmethod  
    # 获取图像匹配算法和相应的阈值
    def get_template_match_algorithm():
        # 算法
        template_match_algorithm = g_sut_content['TemplateMatch']['Algorithm']
        return template_match_algorithm
    
    @staticmethod     
    #返回图像匹配算法关系运算
    def get_template_match_relation():
        relationOperator = g_sut_content['TemplateMatch']['Relation']
        return relationOperator
    
    @staticmethod     
    #返回图像匹配算法阈值
    def get_template_match_threshold():
        threshold = g_sut_content['TemplateMatch']['Value']
        return threshold

    @staticmethod
    def set_template_match_threshold(threshold):
        g_sut_content['TemplateMatch']['Value'] = float(threshold)

    @staticmethod    
    # 获取相机拍摄的图片分辨率大小
    def get_screenshot_size():# 获取图片分辨率
        camera_size = g_sut_content['Camera']['Size']
        return list(map(int, camera_size.split('*')))
    
    @staticmethod  
    # 获取起点规避距离
    def get_origin_detour_length():
        origin_detour_length = [0,0]
        origin_detour_length[0] = g_sut_content['Robot']['ORIGIN_DETOUR']['x']
        origin_detour_length[1] = g_sut_content['Robot']['ORIGIN_DETOUR']['y']
        return origin_detour_length
    
    @staticmethod  
    def get_detour_step_threshold():
        """获取分步规避动作的界限"""
        detour_step = g_sut_content['Robot']['DETOUR_STEP_THRESHOLD']
        return detour_step
    
    @staticmethod  
    def get_detour_step_distance():
        """获取分步规避动作单次的移动距离"""
        detour_step = g_sut_content['Robot']['DETOUR_STEP_DISTANCE']
        return detour_step
    
    @staticmethod  
    def is_log_enabled():
        """获取log记录许可"""
        log_license = g_config_content['Log']
        return log_license

    @staticmethod
    def set_virtual_debug(exec_record_folder):
        global g_sut_path, g_config_path, g_camera_data_path, g_config_content, g_sut_content, g_virtual_debug_folder

        # 重新设置各项配置
        if exec_record_folder is not None:
            exec_record_folder = os.path.abspath(exec_record_folder)
            if not os.path.exists(exec_record_folder):
                print("Virtual debug folder not exist: " + exec_record_folder)
                sys.exit(0)
                return

            g_sut_path = os.path.join(exec_record_folder, "config/sut.yaml")
            g_config_path = os.path.join(exec_record_folder, "config/config.yaml")
            g_camera_data_path = os.path.join(exec_record_folder, 'config/camera.json')
            g_config_content = read_config_file(g_config_path)
            g_sut_content = read_config_file(g_sut_path)
            g_virtual_debug_folder = os.path.join(exec_record_folder, "temp")

        g_config_content['VirtualDebug'] = True

    @staticmethod  
    #虚拟调试功能
    def get_virtual_debug_model():
        virtual_debug = g_config_content['VirtualDebug']
        return virtual_debug

    @staticmethod
    # 虚拟调试图片所在的文件夹
    def get_virtual_debug_dir():
        global g_virtual_debug_folder

        if g_virtual_debug_folder is not None:
            return g_virtual_debug_folder
        else:
            # TODO 后续结果验证还需要进行更改
            virtual_debug_dir = path.join(os.getcwd(), 'temp/')
            #        script_name = '/{}'.format(TestScript.get_pyname())
            #        print('virtual_debug_dir:',virtual_debug_dir)
            #        return path.join(virtual_debug_dir, script_name)
            return virtual_debug_dir

    @staticmethod  
    def get_sut_monitor_setting():
        """开启视频录制监控"""
        sut_monitor = g_config_content['SutMonitor']
        return sut_monitor
    
    @staticmethod  
    def get_motor_speed():
        """获取电机旋转速度"""
        motor_speed = g_config_content['Robot']['ROBOT_MANUFACTOR']['MOTOR_SPEED']
        return motor_speed
    
    @staticmethod  
    def get_press_time():
        """获取长按持续时间"""
        press_time = g_sut_content['Robot']['PressTime']
        return press_time
    
    @staticmethod  
    def get_double_click_time():
        """获取双击间隔时间"""
        press_time = g_sut_content['Robot']['DoubleClickTime']
        return press_time
    
    @staticmethod  
    def get_wait_time():
        """获取等待间隔时间"""
        wait_time = g_sut_content['Robot']['WaitTime']
        return wait_time
    
    @staticmethod
    def get_tip_fall_center():
        """获取落笔点击识别区域中心坐标"""
        x = g_sut_content['TipFall']['X']
        y = g_sut_content['TipFall']['Y']
        return [x, y]
    
    @staticmethod  
    # 记录标定板标定后的结果信息
    def update_calibration_result(calibration_result):
        json_str = json.dumps(calibration_result, indent=4)
        with open(Config.get_calibration_camera_file_path(), 'w') as json_file:
            json_file.write(json_str)
    
    @staticmethod  
    #更新相机焦距，默认为73
    def update_focal_length(focus=73):# 更新相机焦距
        file = open(g_sut_path, 'w')
        g_sut_content['Camera']['Focus'] = int(focus)
        yaml.dump(g_sut_content, file, Dumper=yaml.RoundTripDumper)
        file.close()
    
    @staticmethod
    # 更新落笔高度
    def update_tip_height(tip_height):
        file = open(g_sut_path, 'w')
        g_sut_content['Robot']['TipHeight'] = int(tip_height)
        yaml.dump(g_sut_content, file, Dumper=yaml.RoundTripDumper)
        file.close()
        
    @staticmethod 
    def get_equipment_contour():
    #返回轮廓区域
        x = g_sut_content['Model']['ContourPosition']['x']
        y = g_sut_content['Model']['ContourPosition']['y']
        w = g_sut_content['Model']['ContourPosition']['width']
        h = g_sut_content['Model']['ContourPosition']['height']
        return [x, y, x+w ,y+h]
    
    @staticmethod
    def update_circle_to_pen(circle_to_pen_distance):
        """更新笔尖到标志圆心的距离"""
        file = open(g_config_path, 'w')
        g_config_content['Robot']['ROBOT_MANUFACTOR']['CIRCLE_TO_PEN'] = circle_to_pen_distance
        yaml.dump(g_config_content, file, Dumper=yaml.RoundTripDumper)
        file.close()
    
    @staticmethod      
    # 更新设备在图片中的轮廓信息    
    def update_model_contour():
        # 临时文件路径
        temporary_calibration_file_path = path.join(Config.get_output_dir(), 'temporary.json')
        with open(temporary_calibration_file_path, 'r', encoding='utf-8') as rf:
            temporary_contour = json.load(rf)
        
        #更新contour信息然后再写回文件中
        file = open(g_sut_path, 'w')
        g_sut_content['Model']['ContourPosition'] = temporary_contour
        yaml.dump(g_sut_content, file, Dumper = yaml.RoundTripDumper)
        file.close()
    
    @staticmethod
    def update_ports(ports):
        """更新串口信息"""
        read_file = open(path.join(g_tool_home, g_frontend_options_path))
        frontend_content = yaml.load(read_file, Loader=yaml.Loader)
        read_file.close()
        frontend_content['ports'] = ports
        file = open(path.join(g_tool_home, g_frontend_options_path), 'w')
        yaml.dump(frontend_content, file, Dumper = yaml.RoundTripDumper)
        file.close()
    
    @staticmethod
    def update_robot_layout(direction_matrix):
        """更新机械臂位置布局
        Args:
            direction_matrix: 机械臂布局矩阵
            (x,y) = (px,py)direction_matrix
        """
        #更新contour信息然后再写回文件中
        file = open(g_config_path, 'w')
        g_config_content['Robot']['ROBOT_MANUFACTOR']['Layout'] = str(direction_matrix.tolist())
        yaml.dump(g_config_content, file, Dumper = yaml.RoundTripDumper)
        file.close()
    
    @staticmethod
    def update_tip_fall_center(x,y):
        """更新落笔点击笔尖像素坐标
        Args:
            x,y = 落笔点击笔尖像素坐标
        """
        file = open(g_sut_path, 'w')
        g_sut_content['TipFall']['X'] = int(x)
        g_sut_content['TipFall']['Y'] = int(y)
        yaml.dump(g_sut_content, file, Dumper = yaml.RoundTripDumper)
        file.close()
        
    @staticmethod      
    #记录临时数据
    def record_calibration_file(contour_map):#记录临时数据
        contour = {
                "x": contour_map[0],
                "y": contour_map[1],
                "width": contour_map[2] - contour_map[0],
                "height": contour_map[3] - contour_map[1],
                }
        
        json_str = json.dumps(contour, indent=4)
        #临时数据文件路径
        temporary_calibration_file_path = path.join(Config.get_output_dir(), 'temporary.json')
        with open(temporary_calibration_file_path, 'w') as json_file:
            json_file.write(json_str)

