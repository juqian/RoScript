# -*- coding: utf-8 -*-
"""
@author: szy
"""

import cv2
import ctypes
from config import Config
from PIL import Image
import math
import numpy as np

MIN_MATCH_COUNT = 5#最低匹配点数
MAX_LOOP_COUNT = 5#最大循环次数

class Algorithm(object):
    """ 算法选择类
    
    Attributes:
        id: string, 算法签名
        relational_operator: 识别结果与阈值之间的关系运算符
        threshold: 算法阈值
    """
    def __init__(self):
        self.id = Config.get_template_match_algorithm()
        self.relational_operator = Config.get_template_match_relation()
        self.threshold = Config.get_template_match_threshold()
        
    def match_result_is_right(self, match_result):
#        print('templateMatch line 30, Match result is:', match_result)
        """根据关系运算符获取获取识别结果是否符合阈值要求"""
        if self.relational_operator == '>':
            return match_result > self.threshold
        elif self.relational_operator == '>=':
            return match_result >= self.threshold
        elif self.relational_operator == '<':
            return match_result < self.threshold
        elif self.relational_operator == '<=':
            return match_result <= self.threshold
        else:
            return False
    
class TemplateMatchResult(object):

    #similarity 为模板匹配算法识别相似度
    #x,y 为模板匹配算法识别后最终结果
    #h,w 为模板匹配区域长宽，可忽略
    def __init__(self, similarity, x, y, h, w):
        self.similarity = similarity
        self.x = x
        self.y = y
        self.h = h
        self.w = w
       
    #返回记录的相似度
    def get_similarity(self):
        return self.similarity
    
    #返回记录的匹配位置
    def get_coordinates(self):
        return self.x, self.y
    
    #返回匹配区域像素大小
    def get_image_size(self):
        return self.h, self.w
    
    #更新数据
    def set_data(self, similarity, x, y):
        self.similarity = similarity
        self.x = x
        self.y = y
    
    #坐标变换
    def add_coordinates(self, dx, dy):
        self.x = self.x + dx
        self.y = self.y + dy
        

#BBS算法根据模板图像计算不同的权重
def __patch_size(size):
    area = size[0] * size[1]
    if area < 2000:
        return 3
    
    elif area < 8000:
        return 5
    
    else:
        return 7
        
def bbs_tempalte_match(screen_image_path, widget_image_path):
    #最佳友好相似度模板匹配
    widget_size = Image.open(widget_image_path).size
    bbsDll = ctypes.WinDLL(Config.get_bbs_lib_path())
    weight = __patch_size(widget_size)
    
    #BBS匹配算法
    #定义用来接收bbsDll返回数据的结构体类
    class MatchResult(ctypes.Structure):  
        _fields_ = [("similarity", ctypes.c_double),
                    ("x", ctypes.c_int),
                    ("y", ctypes.c_int)]
        
    #由于图像数据的传递不方便，所以先将basic和target图像存储成本地文件，以方便bbsDll直接读取
    bbsDll.bbs_template_match.restype = ctypes.POINTER(MatchResult)
    result = bbsDll.bbs_template_match(screen_image_path.encode(),
                                       widget_image_path.encode(),
                                       ctypes.c_int(weight))
    
    template_match_result = TemplateMatchResult(result.contents.similarity,
                                                result.contents.x,
                                                result.contents.y,
                                                widget_size[0],
                                                widget_size[1])
    
    return template_match_result

#分块直方图找相似位置
def __block_difference(hist1, hist2):
    similarity = 0
    
    for i in range(len(hist1)):
        if (hist1[i] == hist2[i]):
            similarity += 1
        else:
            similarity += 1 - float(abs(hist1[i] - hist2[i]))/ max(hist1[i], hist2[i])

    return similarity / len(hist1)

#分块直方图发计算匹配相似度
def __get_bhmatch_similarity(screen_region_image, widget_image):
    #将两张图缩放到统一尺寸
    img1 = screen_region_image.resize((64,64)).convert('RGB')
    img2 = widget_image.resize((64,64)).convert('RGB')  
    #分块直方图法
    similarity = 0;
    for i in range(4):
        for j in range(4):
            hist1 = img1.crop((i*16, j*16, i*16+15, j*16+15)).copy().histogram()
            hist2 = img2.crop((i*16, j*16, i*16+15, j*16+15)).copy().histogram()
            similarity += __block_difference(hist1, hist2)
    
    return similarity/16

def __bh_match_loop(screen_image, widget_image, loop_num):
    #模板匹配循环，原图、控件、循环次数
    #根据模板匹配算法寻找图中是否含有小图片，loop_num代表匹配循环测试
    screen_size = screen_image.size
    template_match_result = TemplateMatchResult(0, 0, 0, 0, 0)
    
    #截取的图片距原图片左边界距离x， 距上边界距离y，距离图片左边界距离+裁剪框宽度x+w，距离图片上边界距离+裁剪框高度y+h
    x, y = 0,0
    [w,h] = widget_image.size
    
    #将切割图片向周围移动距离比例
    #循环次数越多，切分越详细
    proportion = 5 * loop_num
    foot_x, foot_y = 0, 0
    
    #向左右及上下移动次数
    foot_x_all = math.ceil((screen_size[0] - w)*proportion/w)
    foot_y_all = math.ceil((screen_size[1] - h)*proportion/h)
    
    #开始地毯式匹配相似区域
    for foot_x in range(foot_x_all+1):
        y = 0
        for foot_y in range(foot_y_all+1):
            
            #剪切和widget一样大小的图片
            screen_region = screen_image.crop((x, y, x+w, y+h))
            result = __get_bhmatch_similarity(screen_region, widget_image)   #两张同等大小的图像相似度
            if result > template_match_result.get_similarity():
                """寻找最相似的点"""
                template_match_result.save_data(result,x,y)
            
            y = y + h / proportion
            if y + h > screen_size[1]:
                y = screen_size[1] - h
        
        x = x + w / proportion
        if x + w  > screen_size[0]:
            x = screen_size[0] - w
    
    #每次循环都会提高阈值
    if template_match_result.get_similarity() < 1 - loop_num/100:
        # 超出循环次数则结束
        if loop_num > MAX_LOOP_COUNT:
            return template_match_result    
        
        else:
            x, y = template_match_result.get_coordinate()
            #缩小匹配范围
            if x > 0:
                x = x - w / proportion
                if y > 0:
                    y = y - h / proportion
                
                length = min(x + w + 2*w/proportion, screen_size[0])
                height = min(y + h + 2*h/proportion, screen_size[1])
                
                #将下一次查找的区域剪切出来
                screen_region = screen_image.crop((x, y, length, height))
                region_tmr = __bh_match_loop(screen_region, widget_image, loop_num + 1)
                
                #递归查找模板匹配最符合要求的区域
                if template_match_result.get_similarity() > region_tmr.get_similarity():
                    template_match_result.add_coordinate(w/2, h/2)
                
                else:
                    region_x, region_y = region_tmr.get_coordinate()
                    template_match_result.save_data(region_tmr.get_similarity, x + region_x, y + region_y)
                
                return template_match_result
            
    # 比阈值小或者匹配范围已经最小则返回记录的最相似区域
    template_match_result.add_coordinate(w/2, h/2)
    return template_match_result

#分块直方图模板匹配算法
def block_histogram_match(screen_image_path, widget_image_path):
    
    screen_image = Image.open(screen_image_path)
    widget_image = Image.open(widget_image_path)
    return __bh_match_loop(screen_image, widget_image, 0)

#opencv模板匹配算法
def __opencv_template_match(screen_image_path, widget_image_path, opencv_algorithm):
    screen_image = cv2.imread(screen_image_path)
    widget_image = cv2.imread(widget_image_path)
    
    w,h,_ = widget_image.shape
    
    match_result = cv2.matchTemplate(screen_image, widget_image, opencv_algorithm)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match_result)
    if opencv_algorithm in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
        # 对于平方差匹配和归一化平方匹配要结果越小表明匹配成果越好
        template_match_result = TemplateMatchResult(min_val, min_loc[0], min_loc[1], w, h)
    else:
        template_match_result = TemplateMatchResult(max_val, max_loc[0], max_loc[1], w, h)

    template_match_result.image = screen_image_path
    template_match_result.template = widget_image_path
    return template_match_result

# 相关系数匹配
def tm_ccoeff_match(screen_image_path, widget_image_path):
    return __opencv_template_match(screen_image_path, widget_image_path, cv2.TM_CCOEFF)

# 归一化相关系数匹配
def tm_ccoeff_normed_match(screen_image_path, widget_image_path):
    return __opencv_template_match(screen_image_path, widget_image_path, cv2.TM_CCOEFF_NORMED)
    
# 相关匹配
def tm_ccorr_match(screen_image_path, widget_image_path):
    return __opencv_template_match(screen_image_path, widget_image_path, cv2.TM_CCORR)

# 归一化相关匹配
def tm_ccorr_normed_match(screen_image_path, widget_image_path):
    return __opencv_template_match(screen_image_path, widget_image_path, cv2.TM_CCORR_NORMED)

# 平方差匹配
def tm_sqdiff_match(screen_image_path, widget_image_path):
    return __opencv_template_match(screen_image_path, widget_image_path, cv2.TM_SQDIFF)

# 归一化平方差匹配
def tm_sqdiff_normed_match(screen_image_path, widget_image_path):
    return __opencv_template_match(screen_image_path, widget_image_path, cv2.TM_SQDIFF_NORMED)


# FlannBasedMatcher算法实现
def __flann_based_matcher(screen_image_path, widget_image_path, fbm_algorithm):
    
    screen_image = cv2.imread(screen_image_path, 1)#读取模板图片，大图
    widget_image = cv2.imread(widget_image_path, 0)#目标控件，小图
    #找出图像中的关键点
    kp1, des1 = fbm_algorithm.detectAndCompute(widget_image, None)
    kp2, des2 = fbm_algorithm.detectAndCompute(screen_image, None)
  
    FLANN_INDEX_KDTREE = 0
    index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)#KTreeIndex配置索引，指定待处理核密度树的数量
    search_params = dict(checks = 60)#指定递归遍历的次数。值越高结果越准确
    
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    matches = flann.knnMatch(des1, des2, k=2)#进行匹配，
    good_dot = []
    for m,n in matches:
        if m.distance < 0.6 * n.distance:
            """
            ratio=0. 4：对于准确度要求高的匹配； 
            ratio=0. 6：对于匹配点数目要求比较多的匹配；
            ratio=0. 5：一般情况下。
            """
            good_dot.append(m)
            
#    print('good dot count:{}'.format(len(good_dot)))
    
    if len(good_dot) < MIN_MATCH_COUNT:
        # 匹配到的点数不符合要求
        template_match_result = TemplateMatchResult(0, 0, 0, 0, 0)
        template_match_result.image = screen_image_path
        template_match_result.template = widget_image_path
        print("Not enough matches")
        return template_match_result
    
    # trainIdx    是匹配之后所对应关键点的序号，大图片的匹配关键点序号
    screen_pts = np.float32([kp2[m.trainIdx].pt for m in good_dot]).reshape(-1, 1, 2)
    # queryIdx  是匹配之后所对应关键点的序号，控件图片的匹配关键点序号
    widget_pts = np.float32([kp1[m.queryIdx].pt for m in good_dot]).reshape(-1, 1, 2)
    #计算变换矩阵和MASK
    M, mask = cv2.findHomography(widget_pts, screen_pts, cv2.RANSAC, 5.0)
    
    h,w = widget_image.shape
    try:     
        pts = np.float32([[0, 0], [0, h-1], [w-1, h-1], [w-1, 0]]).reshape(-1, 1, 2)
        dst = cv2.perspectiveTransform(pts, M)
    except:
        # 出现数据错误
        return TemplateMatchResult(0, 0, 0, 0, 0)
    x,y = [],[]
    for i in range(len(dst)):
        x.append(int(dst[i][0][0]))
        y.append(int(dst[i][0][1]))
    
    template_match_result = TemplateMatchResult(1, min(x), min(y), 
                                                max(y) - min(y), 
                                                max(x) - min(x))
    template_match_result.image = screen_image_path
    template_match_result.template = widget_image_path
    return template_match_result
    
    

# 基于FlannBasedMatcher的SIFT实现模板匹配
def sift_match(screen_image_path, widget_image_path):
    sift = cv2.xfeatures2d.SIFT_create()
    return __flann_based_matcher(screen_image_path, widget_image_path, sift)

# 基于FlannBasedMatcher的SURF实现
def surf_match(screen_image_path, widget_image_path):
    surf = cv2.xfeatures2d.SURF_create(400)
    return __flann_based_matcher(screen_image_path, widget_image_path, surf)


TEMPLATE_MATCHERS = {
            'bbs': bbs_tempalte_match,
            'tcf': tm_ccoeff_match,
            'tcfn':tm_ccoeff_normed_match,
            'tcr': tm_ccorr_match,
            'tcrn':tm_ccorr_normed_match,
            'ts' : tm_sqdiff_match,
            'tsn': tm_sqdiff_normed_match,
            'bhm': block_histogram_match,
            'sift':sift_match,
            'surf':surf_match
        }