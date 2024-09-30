from ..constants import *

class Area:
    def __init__(self, x1, y1, x2, y2):
        self.lt = (x1, y1)
        self.rb = (x2, y2)
    
    def get_width(self):
        return self.rb[0] - self.lt[0]
    
    def get_height(self):
        return self.rb[1] - self.lt[1]
    
    def get_size(self):
        return self.get_width() * self.get_height()
    
    def contain_position(self, position):
        return self.lt[0] <= position[0] < self.rb[0] and self.lt[1] <= position[1] < self.rb[1]

    def get_pre_offset_area(self, offset):
        return Area(self.lt[0]+offset[0], self.lt[1]+offset[1], self.rb[0]+offset[0], self.rb[1]+offset[1])

    def expand(self, expand_size):
        return Area(int(self.lt[0] - expand_size),
                    int(self.lt[1] - expand_size),
                    int(self.rb[0] + expand_size),
                    int(self.rb[1] + expand_size))

    @staticmethod
    def merge(area1, area2):
        x1 = min(area1.lt[0], area2.lt[0])
        y1 = min(area1.lt[1], area2.lt[1])
        x2 = min(area1.rb[0], area2.rb[0])
        y2 = min(area1.rb[1], area2.rb[1])
        return Area(x1, y1, x2, y2)

    @staticmethod
    def is_in_same_row(area1, area2):
        height_intersection = min(area1.rb[1], area2.rb[1]) - max(area1.lt[1], area2.lt[1])
        height_union = max(area1.rb[1], area2.rb[1]) - min(area1.lt[1], area2.lt[1])
        height_IoU = height_intersection / height_union
        return height_IoU > SAME_ROW_HEIGHT_IOU

    @staticmethod
    def is_overlapped(area1, area2):
        x1 = max(area1.lt[0], area2.lt[0])
        y1 = max(area1.lt[1], area2.lt[1])
        x2 = min(area1.rb[0], area2.rb[0])
        y2 = min(area1.rb[1], area2.rb[1])
        return x1 < x2 and y1 < y2