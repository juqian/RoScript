# -*- coding: utf-8 -*-
"""
Created on Sun Jan 17 20:44:52 2021
@author: 29965
"""

import sys
import serial
import serial.tools.list_ports
from config import Config

class RobotSettings:
    """机器人配置有关的一些函数"""
    
    @staticmethod
    def get_ports():
        """获取设备中已有的串口号"""
        port_list = list(serial.tools.list_ports.comports())
        if len(port_list) == 0:
           raise Exception('Not Find any Ports')
        else:
            ports = {i: port_list[i].device for i in range(len(port_list))}
            Config.update_ports(ports)
    
# 转到不同的函数        
robot_settings_switcher = {
        '1': RobotSettings.get_ports, # 设备中已连接的串口信息
}

if __name__ == "__main__":
    robot_settings_switcher[sys.argv[1]]()# 跳转到不同的函数
