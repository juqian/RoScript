# -*- coding: utf-8 -*-
import os
import shutil
import sys
import threading
import mediapipe as mp
import cv2
import numpy as np
from ruamel import yaml
from tkinter import filedialog
import time
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox
import tkinter.simpledialog
import traceback

from script_recorder.processors import single_cam_script_recorder, dual_cam_script_recorder, script_generator
from script_recorder.processors import device_detector


# The physical size of devices, in mm
DEVICE_MEASURE = {
    "SAMSUNG_GALAXY_S5" : (72, 141),
    "SAMSUNG_GALAXY_NOTE4" : (78, 155),
    "IPHONE_5S" : (59, 122),
    "TELCAST_X98_AIR" : (198, 149),
    "RASPBERRY_PI_3B_PLUS" : (143, 102),
    "GOPRO" : (58, 40),
    "SWITCH" : (172, 100),
    "HONOR": (75, 163)
}


SKIN_OPEN_KERNEL = 7
SKIN_CLOSING_KERNEL = 11
SKIN_COLOR_EXTENDS = 15
MASK_AREA_EXTENDS = 40
HAND_MIN_SIZE_RATIO = 0.001
FINGERTIP_CANDIDATE_AREA_LENGTH = 8

MAX_HAND_FRAMES = 10  ##取10帧颜色的中值

DEFAULT_SKIN_COLOR_RANGE = ((35, 133, 100), (165, 160, 146))
RESOLUTIONS = [(1280, 960), (1440, 1080), (1600, 1200), (2560, 1920), (3264, 2448)]


g_camera_ports = []
g_camera_id = 0
g_resolution = (1600, 1200)
g_video_file = None
g_skin_color_range = None
g_use_default_skin_color = False
g_working_thread = None
g_detect_dev = False
g_dev_location = None


g_close_loop = False
g_loop_count = 0


def ensure_range(v, start, end):
    if v < start:
        v = start
    if v >= end:
        v = end - 1
    return v


def collect_yuv_colors(color_image, point, yCrCb_colors, expand_range=5):
    img_YCrCb = cv2.cvtColor(color_image, cv2.COLOR_BGR2YCrCb)
    # print(img_YCrCb.shape)
    Y_ = yCrCb_colors[0]
    Cr_ = yCrCb_colors[1]
    Cb_ = yCrCb_colors[2]

    x, y = point
    x1 = x - expand_range
    x2 = x + expand_range
    y1 = y - expand_range
    y2 = y + expand_range

    height, width = color_image.shape[0], color_image.shape[1]
    x1 = ensure_range(x1, 0, width)
    x2 = ensure_range(x2, 0, width)
    y1 = ensure_range(y1, 0, height)
    y2 = ensure_range(y2, 0, height)

    for x in range(x1, x2+1):
        for y in range(y1, y2+1):
            tmp = img_YCrCb[y, x]
            Y_.append(tmp[0])
            Cr_.append(tmp[1])
            Cb_.append(tmp[2])


def calc_skin_color_range(yCrCb_colors):
    Y_ = yCrCb_colors[0]
    Cr_ = yCrCb_colors[1]
    Cb_ = yCrCb_colors[2]

    if len(Y_)==0 or len(Cr_)==0 or len(Cb_)==0:
        raise Exception("No hand detected. Fail to pick skin color")

    # print("y:{},cr:{},cb:{}".format(Y_,Cr_,Cb_))
    Y_median = int(np.median(Y_))
    Cr_median = int(np.median(Cr_))
    Cb_median = int(np.median(Cb_))
    # print(Y_median,Cr_median,Cb_median)

    a = (Y_median - 50, Cr_median - 15, Cb_median - 15)
    b = (Y_median + 50, Cr_median + 15, Cb_median + 15)
    yuv_skin = (a, b)
    return yuv_skin


def get_2bits_picture(color_image, yuv_skin):
    YCrCb_low = yuv_skin[0]
    YCrCb_high = yuv_skin[1]
    YCrCb_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2YCrCb)
    YCrCb_skin_mask = cv2.inRange(YCrCb_image, YCrCb_low, YCrCb_high)
    YCrCb_skin_mask = cv2.morphologyEx(YCrCb_skin_mask, cv2.MORPH_OPEN,
                                       np.ones((SKIN_OPEN_KERNEL, SKIN_OPEN_KERNEL), np.uint8))
    YCrCb_skin_mask = cv2.morphologyEx(YCrCb_skin_mask, cv2.MORPH_CLOSE,
                                       np.ones((SKIN_CLOSING_KERNEL, SKIN_CLOSING_KERNEL), np.uint8))

    return YCrCb_skin_mask


def collect_finger_points(frame_index, frame):
    image1 = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # mp.solutions.drawing_utils用于绘制
    mp_drawing = mp.solutions.drawing_utils
    # 参数：1、颜色，2、线条粗细，3、点的半径
    DrawingSpec_point = mp_drawing.DrawingSpec((0, 255, 0), 3, 3)
    DrawingSpec_line = mp_drawing.DrawingSpec((0, 0, 255), 4, 4)

    # mp.solutions.hands，是人的手
    mp_hands = mp.solutions.hands
    # 参数：1、是否检测静态图片，2、手的数量，3、检测阈值，4、跟踪阈值
    hands_mode = mp_hands.Hands(max_num_hands=1)
    results = hands_mode.process(image1)

    finger_point = None
    image_with_hand = None
    h, w = frame.shape[0], frame.shape[1]

    if results.multi_hand_landmarks:
        hands = len(results.multi_hand_landmarks)
        if hands > 1:
            print("Multiple hands detected in frame %d" % frame_index)
        for hand_landmarks in results.multi_hand_landmarks:
            image_with_hand = frame.copy()
            mp_drawing.draw_landmarks(
                image_with_hand, hand_landmarks, mp_hands.HAND_CONNECTIONS, DrawingSpec_point, DrawingSpec_line)
            #cv2.imshow('hand marks',image_with_hand)
            #cv2.waitKey(0)

            # TODO 选其他的点
            hand_marks = hand_landmarks.landmark
            x_poses = []
            y_poses = []
            for mark in hand_marks:
                x = int(mark.x * w)
                y = int(mark.y * h)
                x_poses.append(x)
                y_poses.append(y)
            hand_width = max(x_poses) - min(x_poses)
            hand_height = max(y_poses) - min(y_poses)
            # 如果手部所占区域不到1/8个屏幕，认为不是有效的手部识别结果
            if hand_height < h/8:
                print("Too small hands detected (height=%d) in frame %d" % (hand_height, frame_index))
                continue

            # 取食指第三个点的坐标
            x1 = int(hand_marks[mp_hands.HandLandmark.INDEX_FINGER_PIP].x * w)
            y1 = int(hand_marks[mp_hands.HandLandmark.INDEX_FINGER_PIP].y * h)
            finger_point = [x1, y1]

    hands_mode.close()
    return finger_point, image_with_hand


def get_and_show_hand_color(frame_index, frame, name, finger_points, yCrCb_colors, max_hand_frames, winfo, wleft, wright):
    global g_skin_color_range, g_close_loop

    finger_point, image_with_hand = collect_finger_points(frame_index, frame)

    if g_close_loop:
        return

    show_hand_image(name, frame_index, frame, image_with_hand, wleft)

    # 如果未到达最大采集的量，则更新手部颜色
    if finger_point is not None and len(finger_points) <= max_hand_frames:
        finger_points.append(finger_point)
        collect_yuv_colors(frame, finger_point, yCrCb_colors)
        g_skin_color_range = calc_skin_color_range(yCrCb_colors)

    if g_skin_color_range is not None:
        show_skin_image(name, frame_index, frame, g_skin_color_range, winfo, wright)



def show_hand_image(name, frame_index, frame, hand_image, wleft):
    global g_detect_dev, g_dev_location

    # 如果有手则显示手
    if hand_image is not None:
        file = "./output/%s/%d_Mp_hands.png" % (name, frame_index)
        folder = os.path.dirname(file)
        os.makedirs(folder, exist_ok=True)
        cv2.imwrite(file, hand_image)
        # mp_img = img_mp_hand[len(finger_points)]
        # tmp_img = cv2.resize(mp_img,(600,1000))
        # cv2.imshow('1111',tmp_img)
        # cv2.waitKey(0)
        left_image = hand_image
    else:
        left_image = frame

        if g_detect_dev:
            g_dev_location, _ = device_detector.simple_detect(left_image)
            g_detect_dev = False

    left_image = cv2.cvtColor(left_image, cv2.COLOR_BGR2RGBA)  # 转换颜色使播放时保持原有色彩

    # 标记上子窗口
    window_w, window_h = 1600, 1200
    image_h, image_w = left_image.shape[0], left_image.shape[1]
    w_gap = int((image_w - window_w)/2)
    h_gap = int((image_h - window_h)/2)
    w_gap = w_gap if w_gap > 0 else 0
    h_gap = h_gap if h_gap > 0 else 0
    cv2.rectangle(left_image, (w_gap, h_gap), (image_w - w_gap, image_h - h_gap), (255, 0, 0), 2)
    cv2.line(left_image, (int(image_w/2), 0),(int(image_w/2), image_h), (0, 255, 0), 3)
    cv2.line(left_image, (0, int(image_h/2)), (image_w, int(image_h/2)), (0, 255, 0), 3)

    cv2.rectangle(left_image, (int(image_w/3), int(image_h/4)), (int(2*image_w/3), int(3*image_h/4)), (255, 0, 0), 2)

    if g_dev_location is not None:
        x1, y1 = g_dev_location.lt
        x2, y2 = g_dev_location.rb
        cv2.rectangle(left_image, (x1, y1), (x2, y2), (255, 0, 0), 2)
    #cv2.imshow('1111',left_image)
    #cv2.waitKey(0)

    resize_height = wleft.winfo_height()
    resize_width = int(left_image.shape[1] * resize_height / left_image.shape[0])

    left_image = Image.fromarray(left_image).resize((resize_width, resize_height))  # 将图像转换成Image对象
    imgtk = ImageTk.PhotoImage(image=left_image)
    wleft.imgtk = imgtk
    wleft.config(image=imgtk)
    wleft.image = imgtk
    #wleft.update()


def show_skin_image(name, frame_index, frame, skin_color_range, winfo, wright):
    global g_use_default_skin_color

    if g_use_default_skin_color:
        skin_color_range = DEFAULT_SKIN_COLOR_RANGE

    info = "Default skin color range: %s, detected skin color range: %s" % (DEFAULT_SKIN_COLOR_RANGE, str(skin_color_range))
    winfo.config(text=info)
    winfo.update()

    YCrCb_skin_mask = get_2bits_picture(frame, skin_color_range)

    file = "./output/%s/%d_mask.png" % (name, frame_index)
    folder = os.path.dirname(file)
    os.makedirs(folder, exist_ok=True)
    cv2.imwrite(file, YCrCb_skin_mask)

    resize_height = wright.winfo_height()
    resize_width = int(frame.shape[1] * resize_height / frame.shape[0])
    mask_img = Image.fromarray(YCrCb_skin_mask).resize((resize_width, resize_height))  # 将图像转换成Image对象
    masktk = ImageTk.PhotoImage(image=mask_img)
    wright.imgtk = masktk
    wright.config(image=masktk)
    wright.image = masktk
    #wright.update()


def process_frames(cap, video, callback, callback_args):
    global g_close_loop, g_loop_count

    # 等待前一个循环结束
    g_close_loop = True
    while g_loop_count > 0:
        time.sleep(1)

    g_close_loop = False
    g_loop_count += 1

    frame_index = 0

    if not cap.isOpened():
        print("Camera not open")

    print("Enter frame processing loop.")
    exception = None
    try:
        while not g_close_loop and cap.isOpened():
            success, frame = cap.read()
            if not success:
                print("Ignoring empty camera frame.")
                break

            frame_index += 1
            callback(frame_index, frame, *callback_args)

            if video is not None:
                video.write(frame)
    except Exception as e:
        exception = e

    g_loop_count -= 1
    cap.release()
    if video is not None:
        video.release()

    print("Exit frame processing loop.")
    if exception is not None:
        raise exception


def detect_hand_color_in_video(winfo, wleft, wright):
    global g_video_file
    root = tk.Tk()
    root.withdraw()
    g_video_file = filedialog.askopenfilename()
    root.destroy()

    if g_video_file == "":
        return

    print("Video:", g_video_file)
    name, ext = os.path.splitext(os.path.basename(g_video_file))

    finger_points = []
    yCrCb_colors = [[],[],[]]

    cap = cv2.VideoCapture(g_video_file)
    t = threading.Thread(target=process_frames, args=(cap, None, get_and_show_hand_color, (name, finger_points, yCrCb_colors, MAX_HAND_FRAMES, winfo, wleft, wright)))
    t.start()

    #process_frames(cap, None, get_and_show_hand_color, (name, finger_points, yCrCb_colors, MAX_HAND_FRAMES, winfo, wleft, wright))


def detect_hand_color_in_camera_internal(winfo, wleft, wright):
    global g_camera_id, g_resolution, g_close_loop, g_loop_count, g_video_file

    g_close_loop = True
    while g_loop_count > 0:
        time.sleep(1)

    camera_id = g_camera_id  # 1
    resolution = g_resolution

    #cap = cv2.VideoCapture(camera_id)
    cap = cv2.VideoCapture(camera_id + cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
    size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))

    # 如果启用cv2.CAP_DSHOW，则获得的fps为0。如果不启用，则相机设置对话框无法打开，且一个程序不能以两种方式启用同一个摄像头
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps==0.0:
        fps = 15.0

    # 设置相机参数, 需要与cv2.CAP_DSHOW配合使用
    #cap.set(cv2.CAP_PROP_SETTINGS, 1)

    # dscap只有摄像头支持的分辨率才能正常工作
    # import dscap
    # cap = dscap.DsVideoCapture(camera_id, resolution[0], resolution[1])
    # size = resolution
    # fps = 15

    save_dir = r"./output"
    name = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())
    g_video_file = os.path.join(save_dir, "%s.mp4" % name)

    print("Camera shooting resolution=%s, fps=%d, save to %s" % (str(size), fps, g_video_file))

    video = cv2.VideoWriter(g_video_file, cv2.VideoWriter_fourcc('m', 'p', '4', 'v'), fps, size)

    finger_points = []
    yCrCb_colors = [[], [], []]

    # t = threading.Thread(target=process_frames, args=(cap, video, get_and_show_hand_color, (name, finger_points, yCrCb_colors, MAX_HAND_FRAMES, winfo, wleft, wright)))
    # t.start()
    process_frames(cap, video, get_and_show_hand_color, (name, finger_points, yCrCb_colors, MAX_HAND_FRAMES, winfo, wleft, wright))

    #     if cv2.waitKey(1) & 0xFF == ord('q'):#键盘输入q 停止程序运行并保存视频


def detect_hand_color_in_camera(winfo, wleft, wright):
    global g_working_thread
    g_working_thread = threading.Thread(target=detect_hand_color_in_camera_internal, args=(winfo, wleft, wright))
    #g_working_thread.setDaemon(True)
    g_working_thread.start()


def calc_hand_color(frame_index, frame, name, frames, hand_images, finger_points, yCrCb_colors, max_hand_frames, dump_hand_image):
    global g_skin_color_range

    if frame_index % 100 ==0:
        print()
    print('+', end='')

    frames.append(frame)
    finger_point, image_with_hand = collect_finger_points(frame_index, frame)

    # 如果有手则显示手
    if image_with_hand is not None:
        hand_images.append(image_with_hand)

        if dump_hand_image:
            file = "./output/%s/%d_Mp_hands.png" % (name, frame_index)
            folder = os.path.dirname(file)
            os.makedirs(folder, exist_ok=True)
            cv2.imwrite(file, image_with_hand)
            # mp_img = img_mp_hand[len(finger_points)]
            # tmp_img = cv2.resize(mp_img,(600,1000))
            # cv2.imshow('1111',tmp_img)
            # cv2.waitKey(0)
    else:
        hand_images.append(frame)

    # 如果未到达最大采集的量，则更新手部颜色
    if finger_point is not None and len(finger_points) <= max_hand_frames:
        finger_points.append(finger_point)
        collect_yuv_colors(frame, finger_point, yCrCb_colors)


def offline_detect(winfo, wleft, wright):
    global g_video_file, g_skin_color_range
    root = tk.Tk()
    root.withdraw()
    g_video_file = filedialog.askopenfilename()
    root.destroy()
    print("Video:", g_video_file)

    name, ext = os.path.splitext(os.path.basename(g_video_file))

    max_hand_frames = 10  ##取10帧颜色的中值
    frames = []
    hand_images = []
    finger_points = []
    yCrCb_colors = [[],[],[]]

    # 处理视频得到颜色
    print("Process frames: ")
    cap = cv2.VideoCapture(g_video_file)
    process_frames(cap, None, calc_hand_color, (name, frames, hand_images, finger_points, yCrCb_colors, max_hand_frames, True))

    print("Calculating YUV color range ...")
    g_skin_color_range = calc_skin_color_range(yCrCb_colors)
    #g_skin_color_range = ((35, 133, 100), (165, 160, 146))

    print("Showing hand detection results  ...")
    for i in range(len(hand_images)):
        frame = frames[i]
        hand_img = hand_images[i]
        show_hand_image(name, i, frame, hand_img, wleft)
        show_skin_image(name, i, frame, g_skin_color_range, winfo, wright)
        #time.sleep(2)
    print("Done")


def list_camera_ports():
    """
    Test the ports and returns a tuple with the available ports and the ones that are working.
    """
    non_working_ports = []
    dev_port = 0
    working_ports = []
    available_ports = []
    while len(non_working_ports) < 1: # if there are more than 5 non working ports stop the testing.
        #camera = cv2.VideoCapture(dev_port)
        camera = cv2.VideoCapture(dev_port + cv2.CAP_DSHOW)
        if not camera.isOpened():
            non_working_ports.append(dev_port)
            print("Port %s is not working." %dev_port)
        else:
            is_reading, img = camera.read()
            w = camera.get(3)
            h = camera.get(4)
            if is_reading:
                print("Port %s is working and reads images (%s x %s)" %(dev_port,h,w))
                working_ports.append(dev_port)
            else:
                print("Port %s for camera ( %s x %s) is present but does not reads." %(dev_port,h,w))
                available_ports.append(dev_port)
        camera.release()
        dev_port +=1
    return working_ports




def set_camera_id(id):
    global g_camera_id
    g_camera_id = id


def set_resolution(resolution):
    global g_resolution
    g_resolution = resolution


def set_camera_props():
    global g_camera_id, g_resolution

    stop_camera_capture()

    # cap = cv2.VideoCapture(camera_id)
    cap = cv2.VideoCapture(g_camera_id + cv2.CAP_DSHOW)
    # 设置相机参数, 需要与cv2.CAP_DSHOW配合使用
    # 设置后会持久生效
    cap.set(cv2.CAP_PROP_SETTINGS, 1)
    cap.release()


def stop_camera_capture():
    global g_close_loop
    g_close_loop = True


def get_color_file(reference_video):
    video_name = os.path.basename(reference_video)
    name, ext = os.path.splitext(video_name)
    config_file = os.path.join(os.path.dirname(reference_video), name + ".yaml")
    if not os.path.exists(config_file) and name.endswith("_action"):
        file = os.path.join(os.path.dirname(reference_video), name[:-len("_action")] + ".yaml")
        if os.path.exists(file):
            config_file = file
    return config_file


def save_skin_color_to_file(reference_video, overlook_color_range=None, sidelook_color_range=None):
    video_name = os.path.basename(reference_video)
    name, ext = os.path.splitext(video_name)
    config_file = get_color_file(reference_video)

    if os.path.exists(config_file):
        mt = os.path.getmtime(config_file)
        timestamp = time.strftime('%Y%m%d-%H%M%S', time.localtime(mt))
        backup_file = os.path.join(os.path.dirname(reference_video), name + "_" + timestamp + ".yaml")
        shutil.copyfile(config_file, backup_file)

    default_color_file = os.path.join(os.path.dirname(__file__), "config/data.yaml")
    with open(default_color_file, 'r') as f:
        constants = yaml.load(f, Loader=yaml.RoundTripLoader)

    if overlook_color_range is not None:
        color = constants['finger_recognition']['YCrCb']
        color['Y_low'] = overlook_color_range[0][0]
        color['Y_high'] = overlook_color_range[1][0]
        color['Cr_low'] = overlook_color_range[0][1]
        color['Cr_high'] = overlook_color_range[1][1]
        color['Cb_low'] = overlook_color_range[0][2]
        color['Cb_high'] = overlook_color_range[1][2]

    if sidelook_color_range is not None:
        if 'side_look_YCrCb' in constants['finger_recognition']:
            color = constants['finger_recognition']['side_look_YCrCb']
        else:
            color = {}
            constants['finger_recognition']['side_look_YCrCb'] = color

        color['Y_low'] = sidelook_color_range[0][0]
        color['Y_high'] = sidelook_color_range[1][0]
        color['Cr_low'] = sidelook_color_range[0][1]
        color['Cr_high'] = sidelook_color_range[1][1]
        color['Cb_low'] = sidelook_color_range[0][2]
        color['Cb_high'] = sidelook_color_range[1][2]

    constants['finger_recognition']['reference_video'] = reference_video

    with open(config_file, 'w') as f:
        yaml.dump(constants, f, indent=4, Dumper=yaml.RoundTripDumper)

    return config_file


def save_skin_color():
    global g_skin_color_range, g_video_file

    if g_skin_color_range is None:
        tk.messagebox.showerror(title='Export Color', message='Error: no hand color detected')
        return

    color_file = save_skin_color_to_file(g_video_file, overlook_color_range=g_skin_color_range, sidelook_color_range=None)
    tk.messagebox.showinfo(title='Export Color', message='Hand color:%s\nVideo file: %s\nColor file: %s'
                           % (str(g_skin_color_range), g_video_file, color_file))


def load_skin_color_from_file(config_file):
    with open(config_file, 'r') as f:
        constants = yaml.load(f, Loader=yaml.RoundTripLoader)
        color = constants['finger_recognition']['YCrCb']
        color_range = (color['Y_low'], color['Cr_low'], color['Cb_low']), (color['Y_high'], color['Cr_high'], color['Cb_high'])
        return color_range


def load_skin_color():
    global DEFAULT_SKIN_COLOR_RANGE
    default_color_file = os.path.join(os.path.dirname(__file__), "config/data.yaml")

    root = tk.Tk()
    root.withdraw()
    initialdir = os.path.dirname(default_color_file)
    initialfile = os.path.basename(default_color_file)
    color_file_path = filedialog.askopenfilename(initialdir=initialdir, initialfile=initialfile)
    root.destroy()

    DEFAULT_SKIN_COLOR_RANGE = load_skin_color_from_file(color_file_path)


def use_default_color(use_default_color):
    global g_use_default_skin_color
    use_default = use_default_color.get()
    g_use_default_skin_color = use_default


def show_record_frame(frame_index, frame, name, winfo, wleft, wright):
    global g_skin_color_range, g_close_loop

    if g_close_loop:
        return

    if g_skin_color_range is None:
        g_skin_color_range = DEFAULT_SKIN_COLOR_RANGE

    show_hand_image(name, frame_index, frame, None, wleft)
    show_skin_image(name, frame_index, frame, g_skin_color_range, winfo, wright)


def open_camera(camera_id, resolution, test_fps):
    #cap = cv2.VideoCapture(camera_id)
    cap = cv2.VideoCapture(camera_id + cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
    size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))

    # 如果启用cv2.CAP_DSHOW，则获得的fps为0。如果不启用，则相机设置对话框无法打开，且一个程序不能以两种方式启用同一个摄像头
    fps = cap.get(cv2.CAP_PROP_FPS)
    test_frames = []
    if fps==0.0:
        t1 = time.time()
        # 读取5帧，检测fps
        for i in range(10):
            if cap.isOpened():
                success, frame = cap.read()
                if success:
                    test_frames.append(frame)
        t2 = time.time()
        fps1 = len(test_frames)/(t2 - t1)
        fps = int(fps1/5) * 5
        #fps = 15.0

    # 设置相机参数, 需要与cv2.CAP_DSHOW配合使用
    #cap.set(cv2.CAP_PROP_SETTINGS, 1)

    # dscap只有摄像头支持的分辨率才能正常工作
    # import dscap
    # cap = dscap.DsVideoCapture(camera_id, resolution[0], resolution[1])
    # size = resolution
    # fps = 15

    if test_fps:
        return cap, size, fps, test_frames
    else:
        return cap, size, fps


def record_single_cam_video_internal(winfo, wleft, wright):
    global g_camera_id, g_resolution, g_close_loop, g_loop_count, g_video_file

    # 先关闭正在读取的线程
    g_close_loop = True
    while g_loop_count > 0:
        time.sleep(1)

    camera_id = g_camera_id  # 1
    resolution = g_resolution

    cap, size, fps, test_frames = open_camera(camera_id, resolution, True)
    save_dir = r"./output"
    name = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())
    g_video_file = os.path.join(save_dir, "%s.mp4" % name)

    print("Camera shooting resolution=%s, fps=%d, save to %s" % (str(size), fps, g_video_file))

    video = cv2.VideoWriter(g_video_file, cv2.VideoWriter_fourcc('m', 'p', '4', 'v'), fps, size)
    for f in test_frames:
        video.write(f)

    process_frames(cap, video, show_record_frame, (name, winfo, wleft, wright))
    #     if cv2.waitKey(1) & 0xFF == ord('q'):#键盘输入q 停止程序运行并保存视频


def record_single_cam_video(winfo, wleft, wright):
    global g_working_thread
    g_working_thread = threading.Thread(target=record_single_cam_video_internal, args=(winfo, wleft, wright))
    g_working_thread.start()


def record_dual_cam_video_internal(overlook_cam_id, sidelook_cam_id, winfo, wleft, wright):
    global g_camera_id, g_resolution, g_close_loop, g_loop_count, g_video_file

    # 先关闭正在读取的线程
    g_close_loop = True
    while g_loop_count > 0:
        time.sleep(1)

    cap1, size1, fps1, test_frames1 = open_camera(overlook_cam_id, g_resolution, True)
    cap2, size2, fps2, test_frames2 = open_camera(sidelook_cam_id, g_resolution, True)

    save_dir = r"./output"
    name = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())
    g_video_file = os.path.join(save_dir, "%s.mp4" % name)

    fps = min(fps1, fps2)
    print("Camera shooting resolution=%s, fps=%d, save to %s" % (str(g_resolution), fps, g_video_file))
    combined_size = (g_resolution[0], 2*g_resolution[1])
    video = cv2.VideoWriter(g_video_file, cv2.VideoWriter_fourcc('m', 'p', '4', 'v'), fps, combined_size)

    g_close_loop = False
    g_loop_count += 1

    frame_index = 0

    print("Enter frame processing loop.")
    exception = None
    try:
        while not g_close_loop and cap1.isOpened() and cap2.isOpened():
            success1, frame1 = cap1.read()
            success2, frame2 = cap2.read()
            if not success1 or not success2:
                print("Ignoring empty camera frame.")
                break

            frame_index += 1

            top = cv2.resize(frame1, (g_resolution[0], g_resolution[1]))
            bottom = cv2.resize(frame2, (g_resolution[0], g_resolution[1]))
            combined = np.vstack((top, bottom))
            video.write(combined)

            show_hand_image(name, frame_index, frame1, None, wleft)
            show_hand_image(name, frame_index, frame2, None, wright)
    except Exception as e:
        exception = e

    g_loop_count -= 1
    cap1.release()
    cap2.release()
    if video is not None:
        video.release()

    print("Exit frame processing loop.")
    if exception is not None:
        raise exception


def record_dual_cam_video(win, overlook_cam, sidelook_cam, winfo, wleft, wright):
    global g_working_thread

    overlook_cam_id = int(overlook_cam.get())
    sidelook_cam_id = int(sidelook_cam.get())

    g_working_thread = threading.Thread(target=record_dual_cam_video_internal,
                                        args=(overlook_cam_id, sidelook_cam_id, winfo, wleft, wright))
    g_working_thread.start()

    win.destroy()


def select_dual_cameras(winfo, wleft, wright):
    global g_camera_ports

    win = tk.Toplevel()
    win.attributes("-topmost", 1)
    win.title('Select cameras for dual-camera recording')
    screenwidth = win.winfo_screenwidth()
    screenheight = win.winfo_screenheight()
    width = 300
    height = 100
    x = int((screenwidth - width) / 2)
    y = int((screenheight - height) / 2)
    win.geometry('{}x{}+{}+{}'.format(width, height, x, y))  # 大小以及位置

    overlook_cam = tk.StringVar()
    sidelook_cam = tk.StringVar()

    ports = [str(x) for x in g_camera_ports]

    lb1 = tk.Label(win, text="Overlook camera:")
    lb1.grid(row=0, column=0, padx=(10, 0))

    combobox1 = ttk.Combobox(
        master=win,  # 父容器
        state='readonly',  # 设置状态 normal(可选可输入)、readonly(只可选)、 disabled
        cursor='arrow',  # 鼠标移动时样式 arrow, circle, cross, plus...
        textvariable=overlook_cam,  # 通过StringVar设置可改变的值
        values=ports,  # 设置下拉框的选项
    )
    combobox1.grid(row=0, column=1)
    combobox1.current(0)

    lb2 = tk.Label(win, text="Sidelook camera:")
    lb2.grid(row=1, column=0, padx=(10, 0))

    combobox2 = ttk.Combobox(
        master=win,  # 父容器
        state='readonly',  # 设置状态 normal(可选可输入)、readonly(只可选)、 disabled
        cursor='arrow',  # 鼠标移动时样式 arrow, circle, cross, plus...
        textvariable=sidelook_cam,  # 通过StringVar设置可改变的值
        values=ports,  # 设置下拉框的选项
    )
    combobox2.grid(row=1, column=1, pady=5)
    combobox2.current(1)

    b = tk.Button(win, text='OK', width=10, command=lambda: record_dual_cam_video \
                 (win, overlook_cam, sidelook_cam, winfo, wleft, wright))
    b.grid(row=2, columnspan=2, pady=5)

    win.protocol('WM_DELETE_WINDOW', win.destroy)
    #win.mainloop()


def select_device(parent):
    win = tk.Toplevel()
    win.attributes("-topmost", 1)
    win.title('Select device model')
    screenwidth = win.winfo_screenwidth()
    screenheight = win.winfo_screenheight()
    width = 350
    height = 70
    x = int((screenwidth - width) / 2)
    y = int((screenheight - height) / 2)
    win.geometry('{}x{}+{}+{}'.format(width, height, x, y))  # 大小以及位置
    dev_var = tk.StringVar()
    ok_var = []

    values = [x for x in DEVICE_MEASURE.keys()]
    unknown_dev = "<Unknown and Quit>"
    values.append(unknown_dev)
    combobox = ttk.Combobox(
        master=win,  # 父容器
        height=10,
        width=40,  # 宽度
        state='readonly',  # 设置状态 normal(可选可输入)、readonly(只可选)、 disabled
        cursor='arrow',  # 鼠标移动时样式 arrow, circle, cross, plus...
        textvariable=dev_var,  # 通过StringVar设置可改变的值
        values=values,  # 设置下拉框的选项
    )
    combobox.pack(side='top')

    b = tk.Button(win, text='OK', width=10, command=lambda : (win.destroy(), ok_var.append(1)))
    b.pack(side='bottom')

    win.transient(parent)
    win.grab_set()
    win.protocol("WM_DELETE_WINDOW", win.destroy)
    parent.wait_window(win)
    if len(ok_var)>0:
        dev = dev_var.get()
        return dev if dev != unknown_dev and len(dev)>0 else None
    else:
        return None


def record_script(video_path, device_name, is_dual_mode, result_dir, color_file):
    try:
        dev_mode = True

        with open(color_file, 'r') as f:
            constants = yaml.load(f, Loader=yaml.RoundTripLoader)

        color = constants['finger_recognition']['YCrCb']
        overlook_color_range = (color['Y_low'], color['Cr_low'], color['Cb_low']), (color['Y_high'], color['Cr_high'], color['Cb_high'])

        if is_dual_mode:
            color = constants['finger_recognition']['side_look_YCrCb']
            sidelook_color_range = (color['Y_low'], color['Cr_low'], color['Cb_low']), (color['Y_high'], color['Cr_high'], color['Cb_high'])

        if is_dual_mode:
            device_real_measure = DEVICE_MEASURE[device_name]
            # 设置键盘模型的路径，用于识别键盘输入操作
            keyboards_dir = os.path.join("./keyboards", device_name)
            dual_cam_script_recorder.record(video_path, device_real_measure, keyboards_dir, result_dir, dev_mode,
                            overlook_color_range=overlook_color_range, sidelook_color_range=sidelook_color_range)
        else:
            device_real_measure = DEVICE_MEASURE[device_name]
            single_cam_script_recorder.record(video_path, device_real_measure, result_dir, dev_mode,
                            overlook_color_range=overlook_color_range)

        html = script_generator.create_script_html(result_dir)
        print("Script recorded to %s" % result_dir)

        # create sut.yaml
        sut_file = os.path.join(result_dir, "sut.yaml")
        dev_info = {'DEVICE': device_name}
        with open(sut_file, 'w') as f:
            yaml.dump(dev_info, f, indent=4, Dumper=yaml.RoundTripDumper)

        import webbrowser
        webbrowser.open(html)
    except Exception as e:
        traceback.print_exc()
        message = "Fail to generate test script: %s" % (str(e))
        tk.messagebox.showerror(title='Fail to generate test script', message=message)


def create_script(win, is_dual_mode):
    root = tk.Tk()
    root.withdraw()
    if g_video_file is not None:
        initialdir = os.path.dirname(g_video_file)
        initialfile = os.path.basename(g_video_file)
        video_path = filedialog.askopenfilename(title='Select action video (after color splitting)', initialdir=initialdir, initialfile=initialfile)
    else:
        video_path = filedialog.askopenfilename(title='Select action video (after color splitting)', )
    root.destroy()

    if len(video_path) == 0:
        return

    device_name = select_device(win)
    if device_name is None:
        return

    color_file = get_color_file(video_path)
    if not os.path.exists(color_file):
        message = 'Fail to get a specific color file: %s,\nUsing the default color in file config/data.yaml' % (video_path, device_name, color_file)
        tk.messagebox.showinfo(title='Test Script Generation', message=message)
        color_file = os.path.join(os.path.dirname(__file__), "config/data.yaml")

    message = 'Ready to record test script. \nPlease close this window and wait until the record result is shown.\n  Source Video：%s\n  Device：%s\n  Color file：%s' \
              % (video_path, device_name, color_file)
    tk.messagebox.showinfo(title='Test Script Generation', message=message)

    # dev_mode用于生成预览图等信息，正式版中可设置为False
    video_name = os.path.basename(video_path)
    video_name, ext = os.path.splitext(video_name)
    result_dir = os.path.join(os.path.dirname(video_path), video_name)
    os.makedirs(result_dir, exist_ok=True)

    #record_script(video_path, device_name, is_dual_mode, result_dir)

    from multiprocessing import Process
    p = Process(target=record_script, args=(video_path, device_name, is_dual_mode, result_dir, color_file))
    p.start()
    p.join()


def pick_hand_color_from_video(video_path, max_hand_frames=10):
    # max_hand_frames 取10帧颜色的中值
    frames = []
    hand_images = []
    finger_points = []
    yCrCb_colors = [[], [], []]

    video_name, ext = os.path.splitext(os.path.basename(video_path))

    # 处理视频得到颜色
    print("Process frames: ")
    cap = cv2.VideoCapture(video_path)
    process_frames(cap, None, calc_hand_color,
                   (video_name, frames, hand_images, finger_points, yCrCb_colors, max_hand_frames, False))

    print("Calculating YUV color range ...")
    skin_color_range = calc_skin_color_range(yCrCb_colors)
    return skin_color_range


def split_video(is_dual_camera):
    # Download Ffmpeg and add its binaries into the environment variable PATH
    # https://www.gyan.dev/ffmpeg/builds/
    # There are many python bindings for ffmpeg. Make sure to download the right version
    # pip install ffmpeg-python
    import ffmpeg

    root = tk.Tk()
    root.withdraw()
    if g_video_file is not None:
        initialdir = os.path.dirname(g_video_file)
        initialfile = os.path.basename(g_video_file)
        video_path = filedialog.askopenfilename(initialdir=initialdir, initialfile=initialfile)
    else:
        video_path = filedialog.askopenfilename()
    root.destroy()

    video_dir = os.path.dirname(video_path)
    video_name, ext = os.path.splitext(os.path.basename(video_path))
    color_video = os.path.join(video_dir, video_name + "_color" + ext)
    action_video = os.path.join(video_dir, video_name + "_action" + ext)

    color_duration = 10
    s = tk.simpledialog.askstring(title='Please input the time duration to pick color (in seconds)',
                                  prompt='If nothing is input, the default time duration is 10s.\n' +
                                         'A too long duration may cause screen detection error and action lost')
    if s is not None and len(s) > 0:
        color_duration = int(s)

    # 取前10s的帧
    (
        ffmpeg.input(video_path)
        .output(
            color_video,
            t="00:00:%d.0" % color_duration,##结束时间:start-10s
        )
        .overwrite_output()
        .run()
    )

    # 取10s后的帧
    (
        ffmpeg.input(video_path)
        .output(
            action_video,
            ss="00:00:%d.0" % color_duration,##ss为开始时间: 10s-end
        )
        .overwrite_output()
        .run()
    )

    split_file = os.path.join(video_dir, video_name + ".split")
    split_info = {'CALIBRATE_TIME': color_duration}
    with open(split_file, 'w') as f:
        yaml.dump(split_info, f, indent=4, Dumper=yaml.RoundTripDumper)

    if is_dual_camera:
        overlook_color_video = os.path.join(video_dir, video_name + "_overlook_color" + ext)
        sidelook_color_video = os.path.join(video_dir, video_name + "_sidelook_color" + ext)
        # 按上半部分画面切分
        (
            ffmpeg.input(color_video)
            .filter('crop', 'in_w', 'in_h/2', '0', '0')
            .output(overlook_color_video)
            .overwrite_output()
            .run()
        )

        # 按下半部分画面切分
        (
            ffmpeg.input(color_video)
            .filter('crop', 'in_w', 'in_h/2', '0', 'in_h/2')
            .output(sidelook_color_video)
            .overwrite_output()
            .run()
        )

        os.remove(color_video)

        try:
            overlook_color_range = pick_hand_color_from_video(overlook_color_video)
            sodelook_color_range = pick_hand_color_from_video(sidelook_color_video)
            color_file = save_skin_color_to_file(video_path, overlook_color_range=overlook_color_range, sidelook_color_range=sodelook_color_range)

            message = 'Split video and pick color succeed.\nSource video: %s\nColor file: %s' % (video_path, color_file)
            tk.messagebox.showinfo(title='Split Video', message=message)
        except Exception as e:
            message = 'Split video and pick color fail.\nSource video: %s\nError: %s' % (video_path, str(e))
            tk.messagebox.showinfo(title='Split Video', message=message)
            traceback.print_exc()
    else:
        try:
            skin_color_range = pick_hand_color_from_video(color_video)
            color_file = save_skin_color_to_file(video_path, overlook_color_range=skin_color_range, sidelook_color_range=None)

            message = 'Split video and pick color succeed.\nSource video: %s\nColor file: %s' % (video_path, color_file)
            tk.messagebox.showinfo(title='Split Video', message=message)
        except Exception as e:
            message = 'Split video and pick color fail.\nSource video: %s\nError: %s' % (video_path, str(e))
            tk.messagebox.showinfo(title='Split Video', message=message)
            traceback.print_exc()


def detect_device():
    global g_detect_dev

    g_detect_dev = True


def create_ui_window():
    global g_camera_ports, g_resolution, port_var, resolution_var

    window = tk.Tk()
    window.title('Calibration Tool for Test Script Recording')
    window.geometry('1200x700')

    def close_exit():
        global g_close_loop
        g_close_loop = True

        def exit_window():
            # 等待后台任务完成
            global g_working_thread
            if g_working_thread is not None:
                g_working_thread.join()
            print("Exit Program")
            window.quit()
            #window.destroy()
            #sys.exit()

        t = threading.Thread(target=exit_window)
        t.start()

    window.protocol('WM_DELETE_WINDOW', close_exit)

    winfo = tk.Label(window, text="Hand color range:")
    winfo.pack(side='top')
    wleft = tk.Label(window,width=600, height=800)
    wleft.pack(side='left')
    wright = tk.Label(window,width=600,  height=800)
    wright.pack(side='right')

    menubar = tk.Menu(window, tearoff=0)
    video_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Read Video", menu=video_menu)
    video_menu.add_command(label="Detect color online", compound=tk.LEFT, command=lambda: detect_hand_color_in_video(winfo, wleft, wright))
    video_menu.add_command(label="Detect color offline", compound=tk.LEFT, command=lambda: offline_detect(winfo, wleft, wright))

    camera_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label='Read Camera', menu=camera_menu)

    cam_select_menu = tk.Menu(camera_menu, tearoff=0)
    camera_menu.add_cascade(label="Pick camera", menu=cam_select_menu)
    g_camera_ports = list_camera_ports()
    #camera_ports = [0]
    port_var = tk.IntVar()
    for p in g_camera_ports:
        cam_select_menu.add_radiobutton(label=str(p), var=port_var, value=p, command=lambda x=p:set_camera_id(x))
    port_var.set(0)

    resolution_menu = tk.Menu(camera_menu, tearoff=0)
    resolution_var = tk.StringVar()
    camera_menu.add_cascade(label="Set resolution", menu=resolution_menu)
    for w, h in RESOLUTIONS:
        rname = "%dx%d" % (w, h)
        resolution_menu.add_radiobutton(label=rname, var=resolution_var, value=rname, command=lambda r=(w,h): set_resolution(r))
    resolution_var.set("%dx%d" % (g_resolution[0], g_resolution[1]))

    camera_menu.add_command(label="Set camera parameters", compound=tk.LEFT, command=set_camera_props)
    camera_menu.add_separator()
    camera_menu.add_command(label="Start capturing", compound=tk.LEFT, command=lambda: detect_hand_color_in_camera(winfo, wleft, wright))
    camera_menu.add_separator()
    camera_menu.add_command(label="Stop capturing", compound=tk.LEFT, command=stop_camera_capture)

    menubar.add_command(label='Device Location', compound=tk.LEFT, command=detect_device)

    default_color = tk.BooleanVar()
    default_color.set(False)
    default_color_menu = tk.Menu(menubar, tearoff=False)
    menubar.add_cascade(label="Default Color", menu=default_color_menu)
    default_color_menu.add_checkbutton(label='Use default color', command=lambda: use_default_color(default_color), onvalue=True, offvalue=False, variable=default_color)
    default_color_menu.add_command(label='Reload default color for file', command=lambda: load_skin_color())

    menubar.add_command(label="Re-pick Color", compound=tk.LEFT, command=lambda: detect_hand_color_in_camera(winfo, wleft, wright))
    menubar.add_command(label="Export Color", compound=tk.LEFT, command=save_skin_color)

    single_cam_record = tk.Menu(menubar, tearoff=False)
    menubar.add_cascade(label="Single-Camera Recording", menu=single_cam_record)
    single_cam_record.add_command(label="Start recording", compound=tk.LEFT, command=lambda: record_single_cam_video(winfo, wleft, wright))
    single_cam_record.add_command(label="Stop recording", compound=tk.LEFT, command=stop_camera_capture)

    dual_cam_record = tk.Menu(menubar, tearoff=False)
    menubar.add_cascade(label="Dual-Camera Recording", menu=dual_cam_record)
    dual_cam_record.add_command(label="Start recording", compound=tk.LEFT, command=lambda: select_dual_cameras(winfo, wleft, wright))
    dual_cam_record.add_command(label="Stop recording", compound=tk.LEFT, command=stop_camera_capture)

    split_video_menu = tk.Menu(menubar, tearoff=False)
    menubar.add_cascade(label="Spit Video and Pick Color", menu=split_video_menu)
    split_video_menu.add_command(label="Single Camera", compound=tk.LEFT, command=lambda: split_video(False))
    split_video_menu.add_command(label="Dual Camera", compound=tk.LEFT, command=lambda: split_video(True))

    script_gen_menu = tk.Menu(menubar, tearoff=False)
    menubar.add_cascade(label="Generate Script", menu=script_gen_menu)
    script_gen_menu.add_command(label="Single Camera", compound=tk.LEFT, command=lambda: create_script(window, False))
    script_gen_menu.add_command(label="Dual Camera", compound=tk.LEFT, command=lambda: create_script(window, True))

    window.config(menu=menubar)

    return window


if __name__ == '__main__':
    g_working_thread = None

    window = create_ui_window()
    window.mainloop()
    cv2.destroyAllWindows()
    #sys.exit()