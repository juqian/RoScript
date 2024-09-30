# -*- coding: utf-8 -*-
"""
Created on Mon Sep 23 20:31:49 2019

@author: 29965
"""

from __future__ import print_function
import numpy as np
import cv2 
import os
import pandas as pd
from config import Config


class Camera_Calibration_API(object):
    def __init__(self,
                 pattern_rows,  # int: Number of pattern points along row (No default)
                 pattern_columns,  # int: Number of pattern points along column (No default)
                 distance_in_world_units,  # float: The distance between pattern points in any world unit. (No default)
                 figsize = (8,8),  # To set the figure size of the matplotlib.pyplot (Default (8,8))
                 term_criteria = (cv2.TERM_CRITERIA_EPS + 
                                  cv2.TERM_CRITERIA_COUNT, 
                                  30, 0.001)  # The termination criteria for the subpixel refinement
                 ):
        
        self.pattern_rows = pattern_rows
        self.pattern_columns = pattern_columns
        self.distance_in_world_units = distance_in_world_units
        self.figsize = figsize
        self.debug_dir = Config.get_output_dir()#存储校准结果
        self.term_criteria = term_criteria
        self.blobParams = cv2.SimpleBlobDetector_Params()#斑点检测函数，设置斑点参数
        # Change thresholds
        self.blobParams.minThreshold = 8
        self.blobParams.maxThreshold = 255
        # Filter by Area.
        self.blobParams.filterByArea = True
        self.blobParams.minArea = 20     # minArea may be adjusted to suit for your experiment
        self.blobParams.maxArea = 10e5   # maxArea may be adjusted to suit for your experiment
        # Filter by Circularity
        self.blobParams.filterByCircularity = True
        self.blobParams.minCircularity = 0.8
        # Filter by Convexity
        self.blobParams.filterByConvexity = True
        self.blobParams.minConvexity = 0.87
        # Filter by Inertia
        self.blobParams.filterByInertia = True
        self.blobParams.minInertiaRatio = 0.01
            
        if self.debug_dir and not os.path.isdir(self.debug_dir):
            os.mkdir(self.debug_dir)
    
    def __symmetric_world_points(self):
        x,y = np.meshgrid(range(self.pattern_columns),range(self.pattern_rows))#生成网格点坐标矩阵
        prod = self.pattern_rows * self.pattern_columns
        pattern_points=np.hstack((x.reshape(prod,1),y.reshape(prod,1),np.zeros((prod,1)))).astype(np.float32)#hstack水平方向叠加数组
        return(pattern_points)
    
    def __circulargrid_image_points(self,img,flags,blobDetector):
        found, corners = cv2.findCirclesGrid(img, (self.pattern_columns, self.pattern_rows),
                                             flags=flags,
                                             blobDetector=blobDetector
                                             )  # opencv圆形标志点检测算法
        return(found,corners)#返回结果和中心点

    def __cal_pixel_to_physical(self):
        """计算物理距离与像素距离的转换比例关系
        Return: 像素与物理距离的转换比例
        """
        length = [np.linalg.norm(self.calibration_df.img_points[0][num] - self.calibration_df.img_points[0][num + 1]) for num in range(self.pattern_rows*self.pattern_columns - 1)]
        # 计算每两个相邻点之间的像素距离
        
        # 移除每一行最后一个点到下一行第一个点的像素距离
        for num in range(self.pattern_rows -1):
            length.pop((self.pattern_columns - 1) * num + self.pattern_columns - 1)
        
        # 计算公式 距离总量/距离数量/标定点之间的实际距离
        return 10 * sum(length)/(len(length) * self.distance_in_world_units)

    def calibrate_camera(self,
                         image_path = Config.get_calibration_image(),#图片路径
                         custom_world_points_function=None,#自定义标定点参数，默认为None
                         custom_image_points_function=None,
                         ):
        # initialize place holders
        img_points = []
        obj_points = []
        working_images = []
        pattern_points = self.__symmetric_world_points() * self.distance_in_world_units
        blobDetector = cv2.SimpleBlobDetector_create(self.blobParams)#斑点检测
        flags = cv2.CALIB_CB_SYMMETRIC_GRID + cv2.CALIB_CB_CLUSTERING
        h, w = cv2.imread(image_path, 0).shape[:2]#读取图片距离
        
        def process_single_image(img_path):
#            print("Processing {}".format(img_path))
            img = cv2.imread(img_path,0) # gray scale
            if img is None:
                print("Failed to load {}".format(img_path))
                return (None)
            
            found,corners = self.__circulargrid_image_points(img,flags,blobDetector)#返回查找结果和位置
            if found:
                if self.debug_dir:
                    vis = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                    cv2.drawChessboardCorners(vis, (self.pattern_columns,self.pattern_rows), corners, found)
                    outfile = os.path.join(self.debug_dir, 'calibration_pts_vis.png')
                    cv2.imwrite(outfile, vis)
                    print("Save circle grids to calibration_pts_vis.png")
            else:
                print("Failed to found calibration board {}".format(img_path))
                return(None)
            
            return(img_path,corners,pattern_points)
                
        calibrationBoards = process_single_image(image_path)
        if calibrationBoards is (None):
            return False
        working_images.append(calibrationBoards[0])
        img_points.append(calibrationBoards[1])  # 每个标点坐标
        obj_points.append(calibrationBoards[2])
            
        # combine it to a dataframe
        self.calibration_df = pd.DataFrame({"image_names":working_images,
                                       "img_points":img_points,
                                       "obj_points":obj_points,
                                       })  # 将数据转换为二维表，类似于excel
        self.calibration_df.sort_values("image_names")  # 按名称排序
        self.calibration_df = self.calibration_df.reset_index(drop=True)
        
        #返回摄像机矩阵，畸变系数，旋转和变换向量
        self.rms, self.camera_matrix, self.dist_coefs, rvecs, tvecs = cv2.calibrateCamera(self.calibration_df.obj_points, self.calibration_df.img_points, (w, h), None, None)        
        self.calibration_df['rvecs'] = pd.Series(rvecs)
        self.calibration_df['tvecs'] = pd.Series(tvecs)
        result_dictionary = {
                             "rms":self.rms,
                             "intrinsic_matrix":self.camera_matrix.tolist(),
                             "distortion_coefficients":self.dist_coefs.tolist(),
                             }
        result_dictionary['pixel_to_physical'] = self.__cal_pixel_to_physical()
        Config.update_calibration_result(result_dictionary)  # 记录相机数据
        print("Find pixel to physical scale rate: " + str(result_dictionary['pixel_to_physical']))
        return True
    