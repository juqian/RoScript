# -*- coding: utf-8 -*-
"""
Serial communication with the robot
@author: szy
"""

import time
import serial
import serial.tools.list_ports
from config import Config 

BAUDRATE = 9600 # 波特率
BYTESIZE = 8#字节大小
PARITY = 'N'#校验位
STOPBITS = 1#停止位
TIMEOUT = 0.5#读超时设置

class RobotCommunicate(object):
    
    def __init__(self, pen_fall_hight=5):
        if Config.get_virtual_debug_model():
            self.robot_port = 'COM3'
            self.ser = serial.Serial()
        else:
            self.robot_port = self.__get_robot_port()#获取机器人串口编号
            self.ser = serial.Serial()            
            self.__connect()
            self.__init_pen()
    
    # 初始化笔的位置
    def __init_pen(self):
        command = 'QP\r'
        self.ser.write(command.encode())
        pen_state = self.ser.read()
        if pen_state == b'0':
            command = 'SP,1\r'
            self.ser.write(command.encode())
            time.sleep(0.5)
            
    # 获取设备端口号
    def __get_robot_port(self):
        port_list = list(serial.tools.list_ports.comports())
        if len(port_list) == 0:
           raise Exception('No COM Find')
        else:
            for i in range(len(port_list)):
                manufacturer = Config.get_robot_manufactor()
                if manufacturer in port_list[i].manufacturer:
                    return port_list[i].device
            print("Cannot automatically obtain serial port. Read port from file!")
            return Config.get_robot_port()
        
    def __connect(self):
        try:
            self.ser = serial.Serial(self.robot_port,
                                     BAUDRATE, 
                                     bytesize=BYTESIZE, 
                                     parity=PARITY, 
                                     stopbits=STOPBITS, 
                                     timeout=TIMEOUT)
        except:
            raise Exception('No COM Find')
    
    def qure_step_movement(self):
        #步骤位置对应的并不是准确的x,y坐标，移动给的两个坐标与实际坐标也不同，例如move(1000，1000)，结果给出的结果增加的是2000，0
        command = 'QS\r'
        try:            
            self.ser.write(command.encode())
            time.sleep(0.01)
            read = self.ser.read_all()
        except OSError:
            read = ''
        return read
    
    def run(self, command):
        self.ser.write(command.encode())
        
    def query_motor_state(self):
        #QS: 查询电机步骤位置，可以利用
        #QM: 查询电机是否在运动，
        #    返回值: QM,CommandStatus, Motor1Status, Motor2Status, FIFOStatus
        #    CommandStatus 若当前在执行任何运动命令，则为1
        #    Motor1Status 若当前电机1在执行运动，则为1
        #    Motor2Status 若当前电机2在执行运动，则为1
        #    FIFOStatus 如果FIFO不为空，则FIFOStatus为1(FIFO缓冲区)
        read = ''
        command = 'QM\r'
        try:            
            self.ser.write(command.encode())
#        if self.ser.in_waiting:
            time.sleep(0.01)
            read = self.ser.read_all()
        except OSError:
            read = ''
        return read
    
    # 查询固件版本号
    def query_motor_version(self):
        read = ''
        command = 'V\r'
        try:            
            self.ser.write(command.encode())
            time.sleep(0.01)
            read = self.ser.read_all()
        except OSError:
            read = ''
        return read
    
    # 关闭接口
    def close(self):
        self.ser.close()
