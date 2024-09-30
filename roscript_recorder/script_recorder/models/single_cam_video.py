from .frame import Frame
from .action import ClickAction
from ..processors import group_processor
from .abstract_video import AbstractVideo
from ..processors import handcolor

class SingleCamVideo(AbstractVideo):
    def produce_frame(self, index, image):
        return Frame(index, self, image, None)

    def detect_hand_colors(self):
        pixel_to_real_ratio = self.parameters["pixel_to_real_ratio"]
        overlook_low, overlook_high, overlook_median = handcolor.get_single_cam_hand_color(\
            self.path, self.device_real_measure, pixel_to_real_ratio)

        self.hand_colors["overlook_low"] = overlook_low
        self.hand_colors["overlook_high"] = overlook_high
        self.hand_colors["overlook_median"] = overlook_median

    def parse_keyboards_info(self):
        return None
    
    def produce_actions(self, action_fingertip_groups):
        pre_action_frames = self.get_pre_action_frames(action_fingertip_groups)
        actions = []
        for i in range(len(action_fingertip_groups)):
            pre_action_frame = pre_action_frames[i]
            action_fingertip_group = action_fingertip_groups[i]
            touch_fingertip_groups = [[group_processor.get_longest_from_overlook(action_fingertip_group)]]
            action = ClickAction(i+1, self, action_fingertip_group, touch_fingertip_groups, pre_action_frame)
            actions.append(action)
        return actions