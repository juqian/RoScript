from .area import Area

class PercentArea:
    def __init__(self, x1, y1, x2, y2):
        self.lt = (x1, y1)
        self.rb = (x2, y2)

    def get_pixel_area(self, keyboard_area):
        kb_x1, kb_y1 = keyboard_area.lt
        kb_width = keyboard_area.get_width()
        kb_height = keyboard_area.get_height()
        percent_x1, percent_y1 = self.lt
        percent_x2, percent_y2 = self.rb
        x1 = int(percent_x1 * kb_width) + kb_x1
        y1 = int(percent_y1 * kb_height) + kb_y1
        x2 = int(percent_x2 * kb_width) + kb_x1
        y2 = int(percent_y2 * kb_height) + kb_y1
        return Area(x1, y1, x2, y2)

class Keyboard:
    def __init__(self, keyboard_model):
        self.percent_area = PercentArea(0,0,1,1)
        self.model = keyboard_model
    
    def get_key_distribution(self):
        key_distribution = {}
        kb_x1, kb_y1 = self.percent_area.lt
        kb_x2, kb_y2 = self.percent_area.rb
        keyboard = self.model["keyboard"]
        areas = keyboard["area"]
        for area in areas.values():
            x1 = kb_x1 + area["region"][0] * (kb_x2 - kb_x1)
            y1 = kb_y1 + area["region"][1] * (kb_y2 - kb_y1)
            x2 = kb_x1 + area["region"][2] * (kb_x2 - kb_x1)
            y2 = kb_y1 + area["region"][3] * (kb_y2 - kb_y1)
            kb_area = KBArea(PercentArea(x1,y1,x2,y2), area)
            key_distribution.update(kb_area.get_key_distribution())
        return key_distribution

class KBArea:
    def __init__(self, percent_area, area_model):
        self.percent_area = percent_area
        self.model = area_model

    def get_key_distribution(self):
        key_distribution = {}
        kb_area_x1, kb_area_y1 = self.percent_area.lt
        kb_area_x2, kb_area_y2 = self.percent_area.rb
        rows = self.model["rows"]
        y_unit = (kb_area_y2 - kb_area_y1) / len(rows)
        current_y = kb_area_y1
        for row in rows:
            x1, y1 = kb_area_x1, current_y
            x2, y2 = kb_area_x2, current_y + y_unit
            kb_row = KBRow(PercentArea(x1, y1,x2, y2), row)
            key_distribution.update(kb_row.get_key_distribution())
            current_y += y_unit
        return key_distribution

class KBRow:
    def __init__(self, percent_area, row_model):
        self.percent_area = percent_area
        self.model = row_model
    
    def get_key_distribution(self):
        key_distribution = {}
        kb_row_x1, kb_row_y1 = self.percent_area.lt
        kb_row_x2, kb_row_y2 = self.percent_area.rb
        keys = self.model["keys"]
        x_unit_count = 0
        for key in keys:
            if isinstance(key,dict):
                x_unit_count += list(key.values())[0][0]
            else:
                x_unit_count += 1
        x_unit = (kb_row_x2 - kb_row_x1) / x_unit_count
        y_unit = kb_row_y2 - kb_row_y1
        current_x, current_y = kb_row_x1, kb_row_y1
        for key in keys:
            if isinstance(key,dict):
                width = list(key.values())[0][0] * x_unit
                height = list(key.values())[0][1] * y_unit
                c = list(key.keys())[0]
            else:
                width, height = x_unit, y_unit
                c = key if len(key) == 1 else "[%s]"%key
            x1, y1 = current_x, current_y
            x2, y2 = current_x + width, current_y + height
            key_distribution[c] = PercentArea(x1, y1, x2, y2)
            current_x += width
        return key_distribution