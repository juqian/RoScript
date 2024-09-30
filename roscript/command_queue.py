# -*- coding: utf-8 -*-
"""
A singleton command queue
@author: szy
"""
import threading
import time
from queue import Queue
import re

from robot_communicate import RobotCommunicate

BLOCK_COMMAND = ['click', 'drag', 'double click', 'press drag',
                 'press keyboard', 'long press', 'release', 'reset'
                 'detour', 'match']

#rc = RobotCommunicate()# 机器通信

command_wait_queue = Queue(maxsize=3)#等待执行指令队列
command_history_queue = Queue(maxsize=0)#已经结束执行的指令队列

cmd_push_event = threading.Event()  # 指令上传阻塞
cmd_exec_end_event = threading.Event()  # 指令队列执行完毕阻塞
script_end_event = threading.Event()  # 脚本执行结束事件阻塞


class RobotCommand(object):
    #指令参数
    # 机器指令字符串‘’
    # text: 指令信息
    # id: 指令编号
    # push_time: 推到机器上的时间
    # estimate_start_time: 指令预计执行时间
    # exec_time: 指令理论运行时间
    
    def __init__(self, command_text, command_id, estimate_start_time):
        self.text = command_text
        self.id = command_id
        self.push_time = time.time()
        self.estimate_start_time = estimate_start_time
        self.exec_time = 0
        self.__extract_exec_time()
        #预估运行时间
    
    # 分析指令执行时间
    def __extract_exec_time(self):
        if 'XM' in self.text:
            self.exec_time = int(self.text.split(',')[1])
        elif 'SP' in self.text:
            if len(self.text.split(',')) == 3:
                self.exec_time = int(self.text.split(',')[2])
            else:
                self.exec_time = 0.1
        else:
            self.exec_time = 0
         
#    # 记录推送时间
#    def record_cmd_push_time(self, push_time):
#        self.push_time = push_time
    
    def print_command(self):
        print('text: ',self.text)
        print('id: ',self.id)
        print('push_time: ',self.push_time)
        print('estimate_start_time: ',self.estimate_start_time)
        print('exec_time: ',self.exec_time)
        
    #执行脚本指令
    def run(self, rc):
        rc.run('{}\r'.format(self.text))
    
#    # 记录指令开始时间
#    def record_command_start_time(self, start_time):
#        self.estimate_start_time = start_time
    
    # 获取指令运行持续时间
    def get_exec_time(self):
#        command_end_time = self.start_time + self.duration_time
        return float(self.exec_time / 1000)


class CommandQueue(object):
    #设置指令编号、指令队列最终执行时间
    def __init__(self):
        self.command_index = 0
        self.estimated_queue_end_time = 0
        self.is_closed = False
        self.rc = RobotCommunicate()
        self.__start()
        
    #开启指令队列线程
    def __start(self):
        t = threading.Thread(target=self.run)
        t.setDaemon(True)
        t.start()
        t.join(1)
    
    # 将指令加入队列中
    def put(self, action_commands):
        # 记录指令执行时间
        # 若之前等待过指令队列执行结束，则更新当前时间为指令队列执行结束时间
        if self.estimated_queue_end_time < time.time():
            self.estimated_queue_end_time = time.time()
        
        # 获取指令集中的各条指令
        for atom_command in action_commands:
            if not atom_command == '':
                self.command_index += 1
                command = RobotCommand(atom_command, 
                                       self.command_index, 
                                       self.estimated_queue_end_time)
                command_exec_time = command.get_exec_time()
                # 记录指令队列结束时间
                self.estimated_queue_end_time += command_exec_time
                # 将指令加入到等待队列中
                command_wait_queue.put(command)
                # 设置入队事件，用于队列为空时的等待响应
                cmd_push_event.set()
                self.is_closed = False
                
    # 线程中按队列执行指令
    def run(self):
        #当程序正在执行时
        while 1:
            if command_wait_queue.empty():
                # 机器指令队列为空则等待指令上传
                if self.__check_robot_cmds_finish():
                    # 用于所有机器指令结束等待（用于拍摄等需要机器指令执行完毕的时候）
                    if not cmd_push_event.is_set():
                        cmd_exec_end_event.set()
                    # 机器指令队列为空，
                    # 若脚本执行结束，则跳出循环，不进入下面的入队事件等待
                    # （否则会因没有新的指令入队，陷入无限等待）
                    if self.is_closed:
                        break
                    
                    # 等待新的指令入队，wait结束后clear掉
                    cmd_push_event.wait()
                    cmd_push_event.clear()
                    cmd_exec_end_event.clear()
                else:
                    # 固定时间查询
                    # 等待最后指令的时间，
                    # 时间密度
                    time.sleep(0.1)
                    
            elif not self.__query_robot_cmd_que():
                # 如果队列指令没有阻塞
                # 即机器缓冲区能够接收新的指令，
                command = command_wait_queue.get()
                # 将进入缓冲区的指令记录到历史指令队列中
                command_history_queue.put(command)
                command.run(self.rc)
#                time.sleep(max(0.01, command.get_exec_time()-0.05))
                # 清除机器指令队列为空的事件
                
            else:
                # 固定周期去等待
                time.sleep(0.1)
            
        print('Close the Command Queue')
        script_end_event.set()

    def is_empty(self):
        """判断队列中是否有还在执行的指令，
        首先判断指定队列是否为空
        然后判断机器人缓冲区是否为空
        """
        # TODO暂时没用
        if command_wait_queue.empty():
            if self.__query_robot_cmd_que():
                return True
        return False
    
    def get_ebb_version(self):
        """
        查询固件版本号
        Return: version, EBB固件版本号
        """
        query_answer = str(self.rc.query_motor_version())
        version = query_answer[query_answer.find('Version')+8: 
                                query_answer.rfind('\\r\\n')]
        return str(version)
    
    # 判断机器指令缓冲区是否为空
    # 查询电机是否在运动，返回值: QM,CommandStatus,Motor1Status,Motor2Status,FIFOStatus
    #   CommandStatus 若当前在执行任何运动命令，则为非0
    #   Motor1Status 若当前电机1在执行运动，则为非0
    #   Motor2Status 若当前电机2在执行运动，则为非0
    #   FIFOStatus 如果FIFO不为空，则FIFOStatus为非0(FIFO缓冲区)(仅在2.4.4以上版本中存在)
    #              即当最后一位为1时，缓冲区存在指令，不能继续插入机器指令
    # 此指令查询的是缓冲区状态，不需要进入机器指令的队列中
    def __query_robot_cmd_que(self):
        # 版本号不同导致的查询函数和结果不同
        version = self.get_ebb_version()
        if version >= '2.4.4':
            # 2.4.4以上版本
            motor_block = re.compile(r"QM,([0-1]),([0-1]),([0-1]),1")
        elif version >= '2.2.6':
            # 2.2.6以上版本
            motor_block = re.compile(r"QM,1,([0-1]),([0-1])")
        else:
            # 再老的版本不支持此指令
            return True
        
        motor_state = str(self.rc.query_motor_state())
        # 若motor_search_result为None， 则代表FIFO缓冲区不为空，否则为空
        motor_search_result = motor_block.search(motor_state)
        if motor_state == '':
            return True
        # 若motor_search_result为None，则代表FIFO缓冲区为0，可以入队，否则，阻塞
        return motor_search_result is not None
    
    # 判断机器指令是否执行结束
    def __check_robot_cmds_finish(self):
        version = self.get_ebb_version()
        if version >= '2.4.4':
            # 2.4.4以上版本
            motor_block = re.compile(r"QM,0,0,0,0")
        else:
            # 其他版本
            motor_block = re.compile(r"QM,0,0,0")
        motor_state = str(self.rc.query_motor_state())
#        motor_block = re.compile(r"QM,0,0,0")
        motor_search_result = motor_block.search(motor_state)
        # 若motor_search_result为None， 则代表FIFO缓冲区不为空，否则为空
        if motor_state == '':
            return True
#        print('version:', rc.query_motor_version())
        return motor_search_result is not None
    
    # 等待队列阻塞
    # 有部分脚本动作需要机器停止后才能继续进行
    def do_necessary_wait(self, action_name):
        # 部分指令需要等待所有机器指令执行完毕，主要用于拍照，
        # click等指令是需要机械臂停止，否则会导致机器移动点击
        if action_name in BLOCK_COMMAND:
            #等待sleep、查询机器和waitqueue，固定间隔等待
#            print('do necessary wait')
            cmd_exec_end_event.wait()
#            time.sleep(0.5)
#            print(cmd_exec_end_event.is_set())
#        return True
    
    # 关闭队列（主要是关闭线程）
    def close(self):
#        push_command.set()
        # 等待关键
        self.do_necessary_wait('release')
        # 脚本结束设置为True，线程执行结束
        estimated_wait_time = self.estimated_queue_end_time - time.time() + 0.1
        if estimated_wait_time > 0:      
            time.sleep(estimated_wait_time)
            
        self.is_closed = True
        cmd_push_event.set()
        script_end_event.wait()
        self.rc.close()