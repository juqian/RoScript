# -*- coding: utf-8 -*-
"""

@author: szy
"""

import cv2
from config import Config

# 为保存视频做准备
# 视频帧率，正常速度，小于20慢，大了快
fps = 20
# 获取旋转参数
# getRotationMatrix2D有三个参数，第一个为旋转中心，第二个为旋转角度，第三个为缩放比例
rotation_angle = Config.get_rotation_angle()
M = cv2.getRotationMatrix2D((512, 384),rotation_angle,1)
width,height = 1024,768
if rotation_angle % 180 != 0:
    width,height = 768,1024

def record_video():
    """ Record video when the script is running. """
    global width,height 
#    cameraCapture = cv2.VideoCapture(Config.get_capture() + cv2.CAP_DSHOW)
    cameraCapture = cv2.VideoCapture(0 + cv2.CAP_DSHOW)
#    camera_number = 0
#    cameraCapture = cv2.VideoCapture(camera_number + cv2.CAP_DSHOW)
#    _, capture, _, [width, hight], _, _ = Config.get_config()
#    cameraCapture = cv2.VideoCapture(capture)
    # 检测摄像设备是否与计算机相连
    if not cameraCapture.isOpened:
        print(False)
    
    #设置分辨率
    cameraCapture.set(cv2.CAP_PROP_FRAME_WIDTH, 1024)
    cameraCapture.set(cv2.CAP_PROP_FRAME_HEIGHT, 768)
    
    cameraCapture.set(cv2.CAP_PROP_SETTINGS, 1)
    
    #video 视频存放路径
#    file = Config.acquire_video_data_dir()
#    num = len(os.listdir(file))+1
#    video_name = os.path.join(file, 'output'+str(num)+'.avi')
#    #设置视频存放路径
#    size = (int(cameraCapture.get(cv2.CAP_PROP_FRAME_WIDTH)),
#            int(cameraCapture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
#    videoWriter = cv2.VideoWriter(
#        video_name, cv2.VideoWriter_fourcc('I','4','2','0'), fps, size)
    
    #写视频
    while 1:
        
        # 当无法接收视频帧时，抛出异常
        try:
            ret, frame = cameraCapture.read()
        except:
            raise Exception('Cannot Read Focus From Capture!')
            
        if ret == True:
            #是否接收到图像
            frame = cv2.warpAffine(frame, M, (width, height))
#            videoWriter.write(frame)
            # 显示结果帧
            cv2.imshow(r"Enter 'q' to QUIT", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                
                break
        else:
            print('Cannot get photo')
            break
        
    cameraCapture.release()
#    videoWriter.release()
    cv2.destroyAllWindows()
    
#    
if __name__ == "__main__":
    
    record_video()