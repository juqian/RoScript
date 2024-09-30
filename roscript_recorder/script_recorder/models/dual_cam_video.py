import statistics

import cv2
import os
from ruamel import yaml
from .frame import Frame
from .action import ClickAction, DoubleClickAction, LongPressAction, DragAction, SwipeAction, PressKeyboardAction, UnknownAction
from .abstract_video import AbstractVideo
from .keyboard import Keyboard
from ..processors import group_processor, action_processor
from ..processors import handcolor
from ..constants import *

class DualCamVideo(AbstractVideo):
    def __init__(self, video_path, device_real_measure, overlook_skin_color_range=None, sidelook_skin_color_range=None,
                 keyboards_dir=None, debug_dir=None, with_hover_calib=False):
        super().__init__(video_path, device_real_measure, overlook_skin_color_range, sidelook_skin_color_range,
                 keyboards_dir, debug_dir)
        self.with_hover_calib = with_hover_calib

    def produce_frame(self, index, image):
        sub_image_height = image.shape[0] // 2
        overlook_image = image[:sub_image_height,:]
        sidelook_image = image[sub_image_height:, :]
        cropped_sidelook_image = sidelook_image[int(sub_image_height * SIDELOOK_CROP_RATIO):int(sub_image_height * (1-SIDELOOK_CROP_RATIO)), :]
        return Frame(index, self, overlook_image, cropped_sidelook_image)

    def detect_hand_colors(self):
        pixel_to_real_ratio = self.parameters["pixel_to_real_ratio"]
        overlook_low, overlook_high, overlook_median = handcolor.get_dual_cam_hand_color(\
            self.path, False, self.device_real_measure, pixel_to_real_ratio)
        self.hand_colors["overlook_low"] = overlook_low
        self.hand_colors["overlook_high"] = overlook_high
        self.hand_colors["overlook_median"] = overlook_median

        sidelook_low, sidelook_high, sidelook_median = handcolor.get_dual_cam_hand_color(\
            self.path, True, self.device_real_measure, pixel_to_real_ratio)
        self.hand_colors["sidelook_low"] = sidelook_low
        self.hand_colors["sidelook_high"] = sidelook_high
        self.hand_colors["sidelook_median"] = sidelook_median
    
    def parse_keyboards_info(self):
        if self.keyboards_dir is None or not os.path.exists(self.keyboards_dir):
            return None
        keyboards = {}
        for keyboard_name in os.listdir(self.keyboards_dir):
            keyboard_dir = os.path.join(self.keyboards_dir, keyboard_name)
            keyboard_image_path = os.path.join(keyboard_dir, "keyboard.png")
            keyboard_model_path = os.path.join(keyboard_dir, "keyboard.yaml")
            if not (os.path.exists(keyboard_image_path) and os.path.exists(keyboard_model_path)):
                continue
            keyboard_image = cv2.imread(keyboard_image_path)
            with open(keyboard_model_path,'r') as f:
                keyboard_model = yaml.load(f, Loader=yaml.Loader)
            key_distribution = Keyboard(keyboard_model).get_key_distribution()
            keyboards[keyboard_name] = {"image":keyboard_image, "key_distribution":key_distribution}
        return keyboards if len(keyboards) > 0 else None
    
    def get_sidelook_touch_threshold(self, action_fingertip_groups):
        if self.with_hover_calib:
            # 前置校准操作得到的y坐标
            hover_fingertip = group_processor.get_deepest_from_sidelook(action_fingertip_groups[0])
            sidelook_hover_y = hover_fingertip.sidelook_position[1]
            # 后续手指的触控深度y坐标
            touch_finger_tips = [group_processor.get_deepest_from_sidelook(action_fingertip_group) for action_fingertip_group in action_fingertip_groups[1:]]
            side_look_poses = []
            for f in touch_finger_tips:
                if f.sidelook_position is not None:
                    side_look_poses.append(f.sidelook_position[1])
            sidelook_screen_y = min(side_look_poses)

            # for action_fingertip_group in action_fingertip_groups[1:]:
            #     h = group_processor.get_deepest_from_sidelook(action_fingertip_group).sidelook_position[1]
            #     print("%d" % h)

            if sidelook_hover_y >= sidelook_screen_y:
                print("Please ensure a calibaration step is conducted before perform GUI actions")
            #assert sidelook_hover_y < sidelook_screen_y

            #sidelook_touch_threshold = sidelook_screen_y - (sidelook_screen_y - sidelook_hover_y) * SIDELOOK_TOUCH_THRESHOLD_FACTOR
            action_beigin_index = 1
        else:
            action_beigin_index = 0

        fingertip_depths = []
        gaps = set()
        for action_fingertip_group in action_fingertip_groups[action_beigin_index:]:
            depths = []
            for fingertip in action_fingertip_group:
                d = fingertip.sidelook_position[1] if fingertip and fingertip.sidelook_position else 0
                depths.append(d)
            max_depth = max(depths)
            fingertip_depths.append(max_depth)
            frame_gaps = []
            for i in range(len(depths)):
                if i > 0:
                    #gap = abs(depths[i]-depths[i-1])
                    gap = depths[i] - depths[i - 1]
                    if gap>0:
                        frame_gaps.append(gap)
                if depths[i]==max_depth:
                    break

            recent_gaps = set()
            for g in reversed(frame_gaps):
                if len(recent_gaps)>=5:
                    break
                recent_gaps.add(g)
            gaps.update(recent_gaps)

        delta = statistics.median(gaps)

        #sidelook_touch_threshold = sidelook_screen_y - delta
        #return sidelook_touch_threshold
        return delta
    
    def get_action_type(self, touch_fingertip_groups, pre_action_frame):
        action_type = action_processor.get_action_type(touch_fingertip_groups, pre_action_frame, self.parameters["keyboards"])
        return action_type

    def produce_actions(self, action_fingertip_groups):
        self.parameters["keyboards"] = self.parse_keyboards_info()
        pre_action_frames = self.get_pre_action_frames(action_fingertip_groups)
        self.parameters["sidelook_touch_threshold"] = self.get_sidelook_touch_threshold(action_fingertip_groups)
        actions = []
        first_action_index = 1 if self.with_hover_calib else 0
        for i in range(first_action_index, len(action_fingertip_groups)):
            pre_action_frame = pre_action_frames[i]
            action_fingertip_group = action_fingertip_groups[i]

            deepest_fingertip = group_processor.get_deepest_from_sidelook(action_fingertip_group)
            if deepest_fingertip.sidelook_position is None:
                touch_fingertip_groups = []
            else:
                deepest_fingertip_depth = deepest_fingertip.sidelook_position[1]
                touch_threshold = deepest_fingertip_depth - self.parameters["sidelook_touch_threshold"]

                touch_fingertip_groups = group_processor.group_by_touch(action_fingertip_group, touch_threshold)

            # smooth
            if len(touch_fingertip_groups) > 1:
                smooth_groups = []
                for ti in range(1, len(touch_fingertip_groups)):
                    grp = touch_fingertip_groups[ti - 1]
                    next_grp = touch_fingertip_groups[ti]
                    if next_grp[0].index - grp[-1].index <= 2:
                        grp.extend(next_grp)
                        touch_fingertip_groups[ti] = grp
                        next_grp = grp
                    else:
                        smooth_groups.append(grp)
                smooth_groups.append(next_grp)
                touch_fingertip_groups = smooth_groups

            if len(touch_fingertip_groups)==0:
                print("Warning: No touch between frames %d-%d" % (action_fingertip_group[0].index, action_fingertip_group[-1].index))
                action_type = None
            else:
                action_type = self.get_action_type(touch_fingertip_groups, pre_action_frame)

            if action_type == "click":
                action = ClickAction(i, self, action_fingertip_group, touch_fingertip_groups, pre_action_frame)
            elif action_type == "double_click":
                action = DoubleClickAction(i, self, action_fingertip_group, touch_fingertip_groups, pre_action_frame)
            elif action_type == "long_press":
                action = LongPressAction(i, self, action_fingertip_group, touch_fingertip_groups, pre_action_frame)
            elif action_type == "swipe":
                action = SwipeAction(i, self, action_fingertip_group, touch_fingertip_groups, pre_action_frame)
            elif action_type == "drag":
                action = DragAction(i, self, action_fingertip_group, touch_fingertip_groups, pre_action_frame)
            elif action_type == "press_keyboard":
                action = PressKeyboardAction(i, self, action_fingertip_group, touch_fingertip_groups, pre_action_frame)
            else:
                print("Warning: Find unknown action between frames %d-%d. Please check whether you hand is hover up to enough height between GUI actions"
                      % (action_fingertip_group[0].index, action_fingertip_group[-1].index))
                action = UnknownAction(i, self, action_fingertip_group, touch_fingertip_groups, pre_action_frame)
            actions.append(action)
        return actions
