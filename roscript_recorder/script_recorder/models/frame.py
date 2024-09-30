from ..processors import device_detector, finger_detector
from .fingertip import Fingertip
import numpy,cv2
from ..constants import *

class Frame:
    def __init__(self, index, parent, overlook_image, sidelook_image=None):
        self.index = index
        self.parent = parent
        self.overlook_image = overlook_image
        self.sidelook_image = sidelook_image

    def is_hand_exist(self):
        fingertip = self.get_fingertip()
        return fingertip.overlook_position != None

    def get_device_location(self):
        return device_detector.detect(self.overlook_image)

    def get_fingertip(self, hand_colors, backgrounds, dev_location, dev_real_measure, pixel_to_real_ration, debug_dir, frame_index):
        overlook_fingertip_position, sidelook_fingertip_position = None, None
        if isinstance(self.overlook_image, numpy.ndarray):
            hand_color_low = hand_colors["overlook_low"]
            hand_color_high = hand_colors["overlook_high"]
            background = backgrounds["overlook"]
            overlook_fingertip_position = finger_detector.YCrCb_overlook_fingertip_detect(self.overlook_image, background,
                        hand_color_low, hand_color_high, dev_location, dev_real_measure, pixel_to_real_ration, debug_dir, frame_index)
            corrected_overlook_fingertip_position = self.correct_overlook_fingertip_position(overlook_fingertip_position)
        if isinstance(self.sidelook_image, numpy.ndarray):
            hand_color_low = hand_colors["sidelook_low"]
            hand_color_high = hand_colors["sidelook_high"]
            background = backgrounds["sidelook"]
            sidelook_fingertip_position = finger_detector.YCrCb_sidelook_fingertip_detect(self.sidelook_image, background,
                        hand_color_low, hand_color_high, dev_real_measure, pixel_to_real_ration, debug_dir, frame_index)
        return Fingertip(self.index, self.parent, corrected_overlook_fingertip_position, sidelook_fingertip_position)
    
    def correct_overlook_fingertip_position(self, overlook_fingertip_position):
        if overlook_fingertip_position == None:
            return None
        pixel_to_real_ratio = self.parent.parameters["pixel_to_real_ratio"]
        horizon_final_pf = HORIZON_PERSPECTIVE_FACTOR * pixel_to_real_ratio
        vertical_final_pf = VERTICAL_PERSPECTIVE_FACTOR * pixel_to_real_ratio
        image_height, image_width = self.overlook_image.shape[:2]
        x, y = overlook_fingertip_position
        corrected_x = int(image_width/2 - (1-horizon_final_pf) * (image_width/2 - x))
        if y > image_height//2:
            corrected_y = y
        else:
            corrected_y = int(image_height/2 - (1-vertical_final_pf) * (image_height/2 - y))
        return (corrected_x, corrected_y)
    
    def get_device_image(self):
        lt = self.parent.parameters["device_location"].lt
        rb = self.parent.parameters["device_location"].rb
        device_image = self.overlook_image[lt[1]:rb[1],lt[0]:rb[0]]
        return device_image