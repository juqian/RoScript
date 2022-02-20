import cv2
import os
from ruamel import yaml
from .frame import Frame
from .action import ClickAction, DoubleClickAction, LongPressAction, DragAction, SwipeAction, PressKeyboardAction, UnknownAction
from .abstract_video import AbstractVideo
from .keyboard import Keyboard
from roscript_recorder.processors import group_processor, action_processor
from roscript_recorder.constants import *

class DualCamVideo(AbstractVideo):
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
        sidelook_hover_y = group_processor.get_deepest_from_sidelook(action_fingertip_groups[0]).sidelook_position[1]
        sidelook_screen_y = min([group_processor.get_deepest_from_sidelook(action_fingertip_group).sidelook_position[1] for action_fingertip_group in action_fingertip_groups[1:]])
        if sidelook_hover_y >= sidelook_screen_y:
            print("Please ensure a calibaration step is conducted before perform GUI actions")
        assert sidelook_hover_y < sidelook_screen_y
        sidelook_touch_threshold = sidelook_screen_y - (sidelook_screen_y - sidelook_hover_y) * SIDELOOK_TOUCH_THRESHOLD_FACTOR
        return sidelook_touch_threshold
    
    def get_action_type(self, touch_fingertip_groups, pre_action_frame):
        action_type = action_processor.get_action_type(touch_fingertip_groups, pre_action_frame, self.parameters["keyboards"])
        return action_type

    def produce_actions(self, action_fingertip_groups):
        self.parameters["keyboards"] = self.parse_keyboards_info()
        pre_action_frames = self.get_pre_action_frames(action_fingertip_groups)
        self.parameters["sidelook_touch_threshold"] = self.get_sidelook_touch_threshold(action_fingertip_groups)
        actions = []
        for i in range(1, len(action_fingertip_groups)):
            pre_action_frame = pre_action_frames[i]
            action_fingertip_group = action_fingertip_groups[i]
            touch_fingertip_groups = group_processor.group_by_touch(action_fingertip_group, self.parameters["sidelook_touch_threshold"])
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
                print("Find unknown action. Please check whether you hand is hover up to enough height between GUI actions")
                action = UnknownAction(i, self, action_fingertip_group, touch_fingertip_groups, pre_action_frame)
            actions.append(action)
        return actions
