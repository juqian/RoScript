import abc
import cv2
import json
import os
import numpy as np
import hashlib
from ..processors import group_processor
from ..constants import *


class AbstractVideo:
    def __init__(self, video_path, device_real_measure,
                 overlook_skin_color_range=None, sidelook_skin_color_range=None,
                 keyboards_dir=None, debug_dir=None):
        self.path = video_path

        hash_md5 = hashlib.md5()
        with open(video_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        self.video_hash = hash_md5.hexdigest()

        self.debug_dir = debug_dir
        self.device_real_measure = device_real_measure
        self.keyboards_dir = keyboards_dir
        self.parameters = {}
        self.overlook_skin_color_range = overlook_skin_color_range if overlook_skin_color_range is not None \
                                         else (OVERLOOK_SKIN_YCrCb_LOW, OVERLOOK_SKIN_YCrCb_HIGH)
        self.sidelook_skin_color_range = sidelook_skin_color_range if sidelook_skin_color_range is not None \
                                         else (SIDELOOK_SKIN_YCrCb_LOW, SIDELOOK_SKIN_YCrCb_HIGH)
    
    def get_actions(self):
        video_info = self.get_info()
        self.parameters.update(video_info)

        device_location = self.get_device_location()
        self.parameters["device_location"] = device_location
        pixel_to_real_ratio = self.get_pixel_to_real_ratio()
        self.parameters["pixel_to_real_ratio"] = pixel_to_real_ratio

        # 自动识别手指颜色范围（废弃）
        self.hand_colors = {}
        if AUTO_HAND_COLOR_DETECT:
            find_color_in_file = False
            if os.path.exists("./handcolors.json"):
                with open("./handcolors.json", "r") as f:
                    s = "[" + f.read() + "{}]"
                    array = json.loads(s)
                    for data in array:
                        for key in data:
                            if key == self.path:
                                self.hand_colors = data[key]
                                find_color_in_file = True
                                break
                        if find_color_in_file:
                            break
                if find_color_in_file:
                    print("%s: Find hand color in file" % self.path)
                    self.hand_colors["overlook_low"] = self.color_array_to_tuple(self.hand_colors["overlook_low"])
                    self.hand_colors["overlook_high"] = self.color_array_to_tuple(self.hand_colors["overlook_high"])
                    self.hand_colors["sidelook_low"] = self.color_array_to_tuple(self.hand_colors["sidelook_low"])
                    self.hand_colors["sidelook_high"] = self.color_array_to_tuple(self.hand_colors["sidelook_high"])
            if not find_color_in_file:
                print("%s: Auto detecting hand colors" % self.path)
                self.detect_hand_colors()
        else:
            print("Use default hand colors")
            self.hand_colors["overlook_low"] = self.overlook_skin_color_range[0]
            self.hand_colors["overlook_high"] = self.overlook_skin_color_range[1]
            self.hand_colors["sidelook_low"] = self.sidelook_skin_color_range[0]
            self.hand_colors["sidelook_high"] = self.sidelook_skin_color_range[1]

        print(self.hand_colors)

        fingertips = self.get_fingertips()
        action_fingertip_groups = self.group_by_action(fingertips)
        actions = self.produce_actions(action_fingertip_groups)
        return actions

    def color_array_to_tuple(self, array):
        return (array[0], array[1], array[2])

    def find_hand_colors(self):
        video_info = self.get_info()
        self.parameters.update(video_info)
        self.parameters["device_location"] = self.get_device_location()
        self.parameters["pixel_to_real_ratio"] = self.get_pixel_to_real_ratio()
        self.hand_colors = {}
        self.detect_hand_colors()
        return self.hand_colors

    def get_info(self):
        cap = cv2.VideoCapture(self.path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        return {"fps": fps, "width": width, "height": height}
    
    def get_device_location(self):
        cap = cv2.VideoCapture(self.path)
        index = 0
        frame = None
        while True:
            success, image = cap.read()
            if not success:
                break
            frame = self.produce_frame(index, image)
            # if not frame.is_hand_exist():
            #     break
            break
            index += 1
        cap.release()
        assert frame != None
        device_location = frame.get_device_location()
        return device_location

    def get_pixel_to_real_ratio(self):
        device_location = self.parameters["device_location"]
        device_pixel_width = device_location.get_width()
        device_pixel_height = device_location.get_height()
        pixel_to_real_ratio = 0.5 * (device_pixel_width/self.device_real_measure[0] + device_pixel_height/self.device_real_measure[1])
        return pixel_to_real_ratio

    def get_fingertips(self):
        fingertips = []

        dev_location = self.parameters["device_location"]
        pixel_to_real_ratio = self.parameters["pixel_to_real_ratio"]

        cap = cv2.VideoCapture(self.path)
        index = 0
        background_frame = None
        while True:
            success, image = cap.read()
            if not success:
                break
            frame = self.produce_frame(index, image)

            if index==0:
                backgrounds = {}
                kerne = 51
                gray1 = cv2.cvtColor(frame.overlook_image, cv2.COLOR_BGR2GRAY)
                gray1 = cv2.GaussianBlur(gray1, (kerne, kerne), 0)
                backgrounds["overlook"] = gray1

                if frame.sidelook_image is not None:
                    gray2 = cv2.cvtColor(frame.sidelook_image, cv2.COLOR_BGR2GRAY)
                    gray2 = cv2.GaussianBlur(gray2, (kerne, kerne), 0)
                    backgrounds["sidelook"] = gray2

            fingertip = frame.get_fingertip(self.hand_colors, backgrounds, dev_location, self.device_real_measure,
                                            pixel_to_real_ratio, self.debug_dir, index)
            fingertips.append(fingertip)
            index += 1
        cap.release()

        return fingertips

    def group_by_action(self, fingertips):
        return group_processor.group_by_action(fingertips)

    @abc.abstractmethod
    def produce_actions(self, action_fingertip_groups):
        pass

    @abc.abstractmethod
    def produce_frame(self, index, image):
        pass

    def get_pre_action_frames(self, action_fingertip_groups):
        pre_action_frame_indexes = [group[0].index - PRE_ACTION_FRAME_OFFSET for group in action_fingertip_groups]
        frames = []
        index = 0
        cap = cv2.VideoCapture(self.path)
        while True:
            success, image = cap.read()
            if not success:
                break
            if index in pre_action_frame_indexes:
                frame = self.produce_frame(index, image)
                frames.append(frame)
            index += 1
        cap.release()
        return frames