from ..constants import *

class Fingertip:
    def __init__(self, index, parent, overlook_position, sidelook_position=None):
        self.index = index
        self.parent = parent
        self.overlook_position = overlook_position
        self.sidelook_position = sidelook_position
    
    def get_touch_position(self):
        fingertip_pixel_offset = FINGERTIP_OFFSET * self.parent.parameters["pixel_to_real_ratio"]
        x, y = self.overlook_position
        touch_x, touch_y = x, int(y + fingertip_pixel_offset)
        return (touch_x, touch_y)