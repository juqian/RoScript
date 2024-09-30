"""
Code try to detect hand color (not used, for testing only)
"""
import numpy as np
from . import device_detector
import cv2

# 通过前后两帧图像的对比来定位手的大致位置（这种方式受干扰影响较小），在所得位置基础上，通过和第一张图的对比获得手部的更完整范围
# 在定位到的手部范围内，取颜色中值，在此基础上获得手部颜色范围

# 侧视图在手机位置上半部进行手部范围分析
# 正视图在手机屏幕范围内进行手部范围分析

def get_single_cam_hand_color(video_path, dev_real_measure, pixel_to_real_ratio):
    colors = get_hand_color(video_path, False, False, dev_real_measure, pixel_to_real_ratio)
    return colors


def get_dual_cam_hand_color(video_path, is_sidelook, dev_real_measure, pixel_to_real_ratio):
    colors = get_hand_color(video_path, True, is_sidelook, dev_real_measure, pixel_to_real_ratio)
    return colors


def get_hand_color(video_path, is_mixed_video, is_sidelook, dev_real_measure, pixel_to_real_ratio):
    kerne = 51

    cap = cv2.VideoCapture(video_path)
    index = 0
    background = None
    last = None

    dev_rect = None
    finger_width = 8 * pixel_to_real_ratio

    #y, cr, cb数组，记录每个颜色的出现次数
    hand_colors = [np.zeros(256, dtype=np.int64), np.zeros(256, dtype=np.int64), np.zeros(256, dtype=np.int64)]

    samples = 0
    if is_sidelook:
        max_color_samples = 100      # fps=25, 4 seconds
    else:
        #max_color_samples = 20       # 0.5-1 seconds
        max_color_samples = 10       # 0.5-1 seconds

    while True:
        success, frame = cap.read()
        if not success:
            break
        index += 1

        if samples >= max_color_samples:
            break

        if is_sidelook:
            # 如果是混合视频，则取下半部
            if is_mixed_video:
                height = frame.shape[0]
                frame = frame[int(height*0.5): height, :]

            width = frame.shape[1]
            height = frame.shape[0]
            dev_len = dev_real_measure[1] * pixel_to_real_ratio
            gap = int((width - dev_len)//2)
            # 取设备正上方
            frame = frame[0:int(height * 0.5), gap:(width-gap)]
            pass
        else:
            # 如果是混合视频，则取下半部
            if is_mixed_video:
                height = frame.shape[0]
                frame = frame[0: int(height*0.5), :]

            if dev_rect is None:
                dev_rect = device_detector.detect(frame)
            lt, rb = dev_rect.lt, dev_rect.rb
            frame = frame[lt[1]:rb[1], lt[0]:rb[0]]

        # 对帧进行预处理,先转灰度图,再进行高斯滤波。
        # 用高斯滤波对图像处理,避免亮度、震动等参数微小变化影响效果
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (kerne, kerne), 0)

        # 将第一帧设置为整个输入的背景
        if background is None:
            background = gray
            last = gray
            continue

        # 当前帧和第一帧的不同它可以把两幅图的差的绝对值输出到另一幅图上面来
        backgroundDelta = cv2.absdiff(background, gray)
        lastDelta = cv2.absdiff(last, gray)

        last = gray

        # 相对上一张图进行运动检测，这个检测结果相对准确，基本都是手部
        # 二值化
        thresh = cv2.threshold(lastDelta, 25, 255, cv2.THRESH_BINARY)[1]
        # 腐蚀膨胀
        thresh = cv2.dilate(thresh, None, iterations = 2)

        # 统计白色像素个数
        result = np.sum(thresh == 255)
        if result > 0:
            # 取像素轮廓区域
            points = cv2.findNonZero(thresh)
            # 取轮廓
            rect = cv2.boundingRect(points)

            is_valid_sample = True
            if not is_sidelook:
                rect_width = rect[2]
                if rect_width < finger_width:
                    is_valid_sample = False
            else:
                rect_width = rect[2]
                if rect_width < 20:
                    is_valid_sample = False

            if is_valid_sample:
                samples = samples + 1

                # 二值化，并腐蚀膨胀
                hand_binary = cv2.threshold(backgroundDelta, 25, 255, cv2.THRESH_BINARY)[1]
                hand_binary = cv2.dilate(hand_binary, None, iterations=2)

                pick_sample(dir, index, frame, thresh, hand_binary, rect, hand_colors, pixel_to_real_ratio)
                #print("collect sample on frame %d"%index)

    cap.release()

    color_low, color_high, color_median = get_color_range(video_path, hand_colors, is_sidelook)
    print("Video %s hand color low, high, median: %s, %s, %s"% (video_path, str(color_low), str(color_high), str(color_median)))
    return color_low, color_high, color_median


def get_pixel_to_real_ratio(overlook_video_path, dev_real_measure):
    cap = cv2.VideoCapture(overlook_video_path)
    success, frame = cap.read()
    cap.release()

    if success:
        dev_pixel_rect = device_detector.detect(frame)
        pixel_width = dev_pixel_rect.get_width()
        pixel_height = dev_pixel_rect.get_height()
        pixel_to_real_ratio = 0.5 * (pixel_width / dev_real_measure[0] + pixel_height / dev_real_measure[1])
        return pixel_to_real_ratio
    else:
        return None


def pick_sample(dir, index, frame, motion, hand_binary, rect, hand_colors, pixel_to_real_ratio):
    frame_YCrCb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)

    (x, y, w, h) = rect

    # 从和初始背景的差异图中裁切出疑似手部的区域[y1:y2, x1:x2]
    mask = np.zeros([frame.shape[0], frame.shape[1]], dtype=np.uint8)
    mask[y:y+h, x:x+w] = 255
    hand_area = cv2.bitwise_and(hand_binary, hand_binary, mask=mask)
    # 取得手部区域点
    pixelpoints = cv2.findNonZero(hand_area)

    # 收缩手部区域，找出不在手部的边缘，将其改成黑的
    if pixelpoints is not None and pixel_to_real_ratio is not None:
        pixelpoints = shrink_area(hand_area, pixelpoints, pixel_to_real_ratio)

    # 在收缩后的范围内进行取色
    if pixelpoints is not None:
        if pixel_to_real_ratio is not None:
            for [px, py] in pixelpoints:
                pick_color(frame_YCrCb, px, py, hand_colors)
        else:
            for [[px, py]] in pixelpoints:
                pick_color(frame_YCrCb, px, py, hand_colors)


def pick_color(frame, x, y, hand_colors):
    y, Cr, Cb = frame[y, x]
    hand_colors[0][y] += 1
    hand_colors[1][Cr] += 1
    hand_colors[2][Cb] += 1
    # print('(' + str(y) + ',' + str(Cr) + ',' + str(Cb) + ')')

# 默认收缩物理尺寸x毫米，只取核心区域
def shrink_area(hand_area, pixelpoints, pixel_to_real_ratio, shrink=3):
    shrink_size = int(shrink * pixel_to_real_ratio)
    min_y = pixelpoints[0][0,1]
    # 扫描线算法处理所有像素
    shrinked_pixels = []
    start_y = min_y + shrink_size
    row = None
    row_y = 0
    for pixel in pixelpoints:
        [[x, y]] = pixel
        if y < start_y:
            hand_area[y, x] = 0
            continue

        # 如果切入新行，则处理旧行
        if y!=row_y:
            if row is not None:
                shrinked = shrink_row(hand_area, row, pixel_to_real_ratio, shrink)
                shrinked_pixels.extend(shrinked)

            row = []
            row_y = y

        row.append((x, y))

    return shrinked_pixels


def shrink_row(hand_area, row, pixel_to_real_ratio, shrink):
    shrink_size = int(shrink * pixel_to_real_ratio)
    last_x = -5
    row_y = row[0][1]
    part_start = -1
    points = []

    # 将一行切分成多个段
    for [x, y] in row:
        if x-last_x > 1:
            # 切换新的段
            if part_start >= 0:
                shrink_part(hand_area, row_y, part_start, last_x, shrink_size, points)
            part_start = x

        last_x = x

    shrink_part(hand_area, row_y, part_start, x, shrink_size, points)
    return points


def shrink_part(hand_area, y, part_start, part_end, shrink_size, points):
    # 掐头去尾
    start = part_start + shrink_size
    end = part_end - shrink_size
    if start <= end:
        for i in range(start, end+1):
            points.append((i, y))
        for i in range(part_start, start):
            hand_area[y, i] = 0
        for i in range(end+1, part_end+1):
            hand_area[y, i] = 0
    else:
        for i in range(part_start, part_end+1):
            hand_area[y, i] = 0


def get_color_range(video_path, hand_colors, is_sidelook):
    y_median = get_median(hand_colors[0])
    Cr_median = get_median(hand_colors[1])
    Cb_median = get_median(hand_colors[2])
    YCrCb_median = (y_median, Cr_median, Cb_median)

    # 侧面的颜色变化更大，正面颜色变化相对小
    if is_sidelook:
        y_radius = 60
        Cr_left_radius = 5
        Cr_right_radius = 20
        Cb_left_radius = 20
        Cb_right_radius = 20
    else:
        y_radius = 50
        Cr_left_radius = 10
        Cr_right_radius = 20
        Cb_left_radius = 10
        Cb_right_radius = 15

    y_low = y_median - y_radius if (y_median - y_radius)>=20 else 20
    YCrCb_low = ( y_low, Cr_median - Cr_left_radius, Cb_median - Cb_left_radius)
    YCrCb_high = (y_median + y_radius, Cr_median + Cr_right_radius, Cb_median + Cb_right_radius)
    return YCrCb_low, YCrCb_high, YCrCb_median


def get_median(hand_colors):
    samples = 0
    for i in range(256):
        count = hand_colors[i]
        samples += count

    half = samples//2

    num = 0
    for i in range(256):
        count = hand_colors[i]
        if num<=half and half<num+count:
            median = i
            break
        else:
            num += count

    return median

