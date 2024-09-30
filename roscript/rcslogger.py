# -*- coding: utf-8 -*-
"""
Created on Fri Jan 22 15:36:55 2021

@author: 29965
"""
import os
import time
import logging

from test_script import TestScript


class ACTION_LOG():
    """单个动作数量记录
    Attributes:
        action_type: 动作类型
        action_exec_num: 动作指令数量
        action_total_time: 动作执行总时间
    """

    def __init__(self, action_type):
        self.action_type = action_type
        self.action_exec_num = 0
        self.action_total_time = 0
        self.average_exec_time = 0

    def record_action_exec_num(self):
        """记录操作执行次数"""
        self.action_exec_num += 1

    def record_action_total_time(self, action_exec_time):
        """记录操作执行总时间"""
        self.action_total_time += action_exec_time

    def get_message(self):
        """获取每个操作的信息, 用于最后记录单个操作的详细信息"""
        if self.action_exec_num != 0:
            self.average_exec_time = self.action_total_time / self.action_exec_num
        action_message = ("{}, times: {}, total time: {:.2f}s, "
                          "average time: {:.2f}s"
                          .format(self.action_type,
                                  self.action_exec_num,
                                  self.action_total_time,
                                  self.average_exec_time))
        return action_message


ACTION_SUMMARY = {
    'click': ACTION_LOG('click'),
    'swipe': ACTION_LOG('swipe'),
    'drag': ACTION_LOG('drag'),
    'press keyboard': ACTION_LOG('press keyboard'),
    'long press': ACTION_LOG('long press'),
    'double click': ACTION_LOG('double click'),
    'long press drag': ACTION_LOG('long press drag'),
    'move to': ACTION_LOG('move to'),
    'match': ACTION_LOG('match'),
    'wait': ACTION_LOG('wait'),
    'find': ACTION_LOG('find'),
    'template match': ACTION_LOG('template match'),
    'take photo': ACTION_LOG('take photo'),
    'detour': ACTION_LOG('detour'),
    'touch': ACTION_LOG('touch'),
    'move': ACTION_LOG('move'),
    'sleep': ACTION_LOG('sleep'),
    'pen down': ACTION_LOG('pen down'),
    'pen up': ACTION_LOG('pen up'),
    'move outside of screen': ACTION_LOG('move outside of screen'),
    'take screen photo': ACTION_LOG('take screen photo'),
    'reset arms': ACTION_LOG('reset arms'),
    'assert exist': ACTION_LOG('assert exist'),
    'assert not exist': ACTION_LOG('assert not exist'),
}

GUIACTIONS = ['click', 'swipe', 'drag', 'press keyboard', 'move to',
              'long press', 'double click', 'long press drag']


class RcsLogger(object):
    """记录时间,,parameter包括script, photo, opencv分别记录不同的数据
    
    Attributes:
        script_start_time: float, 脚本执行开始时间
        script_run_time: float, 脚本执行时间
        total_time: float, 运行总时间
        action_start_time: float, 记录开始时间时间
        log_type: string, log记录类型,
        logger: log记录
        action_number: int, 指令执行的操作数
        opencv_number: int, 图像识别的操作数
        take_photo_number: int, 视频截取的操作数
    """

    def __init__(self, script_name, virtual_debug):
        """初始化
        
        Args:
            log_type: string, 默认为script action,即为脚本执行记录
            log_license: Boolean, 是否记录日志，默认为True
            
            不同的log类型存放于不同的文件中,
            'script action'存放于单独的脚本日志中(即当前执行脚本日志),
                例如执行'place_fruit_order.py'时,生成'place_fruit_order.log'文件存放脚本执行日志
            'take photo'所有的拍摄信息存放于拍照日志('_photo_shot.log')中
            'template match'所有的模板匹配信息存放于模板匹配日志('_template_match.log')中
            
        """
        self.script_name = script_name
        self.logger = logging.getLogger("roscript")
        self.__config_log()
        self.__record_script_name(virtual_debug)

        self.script_start_time = time.time()  # 脚本开始时间
        self.script_total_time = time.time()  # 脚本执行总时间

        # 动作执行信息
        self.exec_action_name = ""  # 执行动作名
        self.exec_action_message = ""  # 执行动作信息
        self.exec_action_start_time = 0  # 动作执行开始时间
        self.exec_action_num = 0  # 动作执行数量

        # 模板匹配信息
        self.TM_start_time = 0  # 模板匹配开始时间
        self.TM_idx = 0  # 模板匹配编号

        # 拍照信息
        self.TP_start_time = 0  # 拍照开始时间 
        self.TP_idx = 0  # 视频拍摄编号
        self.TP_total_time = 0  # 视频拍摄总时间

        # 规避运动时间
        self.detour_start_time = 0  # 规避运动起始时间
        self.detour_idx = 0  # 规避过程

        # 记录睡眠时间
        self.sleep_total_time = 0

    def __config_log(self):
        """配置log输出格式
        
        格式参考: 时间,等级,操作信息
        """
        # log输出格式
        formatter = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s')

        self.logger.handlers.clear()  # 清空log
        self.logger.setLevel(logging.INFO)

        fh = logging.FileHandler(TestScript.get_log_path())
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)

        #        wh = logging.FileHandler(TestScript.get_log_path())
        #        wh.setLevel(logging.ERROR)
        #        wh.setFormatter(formatter)

        self.logger.addHandler(fh)

    #        self.logger.addHandler(wh)

    def __record_script_name(self, virtual_debug):
        """记录脚本名"""
        self.logger.info("script: {}".format(self.script_name))
        if virtual_debug:
            self.logger.info("[Virtual Debug]")

    #        print("script: {}".format(self.script_name))

    def record_action_start(self, action_name, message=""):
        """记录操作开始"""
        self.exec_action_name = action_name
        if self.exec_action_name in GUIACTIONS:
            self.exec_action_num += 1
        self.exec_action_start_time = time.time()
        self.exec_action_message = "{}({})".format(action_name, message)
        self.logger.info("----------------------------------------")
        self.logger.info("action {} start:".format(self.exec_action_message))
        ACTION_SUMMARY[self.exec_action_name].record_action_exec_num()

    def record_action_end(self):
        """记录动作结束"""
        action_exec_time = time.time() - self.exec_action_start_time
        self.script_total_time = time.time() - self.script_start_time

        # 记录动作信息        
        action_message = ("acion, number: {}, exec time: {:.2f}s, total time:"
                          " {:.2f}s".format(
            ACTION_SUMMARY[self.exec_action_name].action_exec_num,
            action_exec_time, self.script_total_time))
        self.logger.info(action_message)
        self.logger.info("action {} end.".format(self.exec_action_message))
        ACTION_SUMMARY[self.exec_action_name].record_action_total_time(action_exec_time)

    def record_script_end(self):
        """记录脚本结束"""

        self.script_total_time = time.time() - self.script_start_time
        # 记录脚本结束信息        
        script_message = ("Script end, total time: {:.2f}s, "
                          "sleep time: {:.2f}s.".format(self.script_total_time,
                                                        self.sleep_total_time))
        self.logger.info("----------------------------------------")
        self.logger.info(script_message)
        # 打印细节信息
        self.print_action_summary()

    def record_TM_start(self):
        """记录模板匹配开始时间"""
        self.TM_start_time = time.time()
        ACTION_SUMMARY["template match"].record_action_exec_num()

    def record_TM_scale(self, scaling):
        """记录模板匹配轮廓缩放"""
        TM_scale_message = "The widget's scaling: {:.2f}".format(scaling)
        self.logger.info(TM_scale_message)

    def record_TM_result(self, match_result):
        """记录模板匹配信息和结果"""
        TM_exec_time = time.time() - self.TM_start_time
        self.TM_idx += 1
        x, y = match_result.get_coordinates()
        TM_message = ("template match, number: {}, time: {:.2f}s, "
                      "similarity: {:.2f}, coordinates: [{}, {}], images: [{}, {}]"
                      .format(self.TM_idx, TM_exec_time, match_result.similarity, x, y,
                              os.path.basename(match_result.image), os.path.basename(match_result.template)))
        self.logger.info(TM_message)
        ACTION_SUMMARY["template match"].record_action_total_time(TM_exec_time)

    def record_TP_start(self):
        """记录拍照开始时间"""
        self.TP_start_time = time.time()
        ACTION_SUMMARY["take photo"].record_action_exec_num()

    def record_TP_result(self, image_index):
        """记录模板匹配信息和结果"""
        TP_exec_time = time.time() - self.TP_start_time
        self.TP_idx += 1
        self.TP_total_time += TP_exec_time
        TP_message = ("take photo, number: {}, time: {:.2f}s, "
                      "total time: {:.2f}s, image: {}"
                      .format(self.TP_idx, TP_exec_time, self.TP_total_time, image_index))
        self.logger.info(TP_message)
        ACTION_SUMMARY["take photo"].record_action_total_time(TP_exec_time)

    def record_touch_time(self, touch_time):
        """记录触摸动作时间"""
        touch_message = "robot touch: {:.2f}s".format(touch_time)
        self.logger.info(touch_message)
        ACTION_SUMMARY["touch"].record_action_total_time(touch_time)

    def record_move_time(self, move_time):
        """记录移动动作时间"""
        move_message = "robot move: {:.2f}s".format(move_time)
        self.logger.info(move_message)
        ACTION_SUMMARY["move"].record_action_total_time(move_time)

    def record_detour_start(self):
        """记录规避运动开始时间"""
        self.detour_start_time = time.time()
        ACTION_SUMMARY["detour"].record_action_exec_num()

    def record_detour_result(self):
        """记录规避运动"""
        detour_exec_time = time.time() - self.detour_start_time
        self.detour_idx += 1
        detour_message = ("detour: {:.2f}s".format(detour_exec_time))
        self.logger.info(detour_message)
        ACTION_SUMMARY["detour"].record_action_total_time(detour_exec_time)

    def record_exception(self):
        """记录异常信息"""
        self.logger.error("########################################")
        self.logger.error("Action {} Error!".format(self.exec_action_name))

    def print_action_summary(self):
        """打印每个动作的信息"""
        self.logger.info("Summary")
        if self.exec_action_num > 0:
            self.logger.info("The number of action is: {}, average time: {:.2f}s"
                             .format(self.exec_action_num,
                                     self.script_total_time / self.exec_action_num))
        else:
            self.logger.info("The number of action is: {}, average time: {:.2f}s"
                             .format(self.exec_action_num, self.script_total_time))
        for action in ACTION_SUMMARY:
            if ACTION_SUMMARY[action].action_exec_num != 0:
                self.logger.info(ACTION_SUMMARY[action].get_message())

    def record_assert_match_start(self, action_name, message=""):
        """记录操作开始"""
        self.exec_action_name = action_name
        self.exec_action_start_time = time.time()
        self.exec_action_message = "{}({})".format(action_name, message)
        self.logger.info("----------------------------------------")
        self.logger.info("{} start:".format(self.exec_action_message))
        ACTION_SUMMARY[self.exec_action_name].record_action_exec_num()

    def record_assert_match_result(self, result):
        """记录动作结束"""
        action_exec_time = time.time() - self.exec_action_start_time
        self.script_total_time = time.time() - self.script_start_time

        # 记录动作信息        
        action_message = ("exec time: {:.2f}s, total time:"
                          " {:.2f}s".format(
            action_exec_time, self.script_total_time))
        self.logger.info(action_message)
        self.logger.info("{}: {}!".format(self.exec_action_message, result))
        ACTION_SUMMARY[self.exec_action_name].record_action_total_time(action_exec_time)

    def record_sleep_time(self, time):
        """记录脚本休眠时间"""
        self.sleep_total_time += time

    def record_custom_message(self, message):
        """输出自定义信息"""
        self.logger.info(message)
