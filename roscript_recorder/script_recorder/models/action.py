import abc
from mako.template import Template
from ..processors import action_processor, group_processor, widget_recognizer, preview_generator
from ..processors.preview_generator import DrawPointMethods, DrawArrowMethods, DrawAreaMethods, DrawNoteMethods
from ..constants import *
from ..models.area import Area


class AbstractAction:
    def __init__(self, index, parent, action_fingertip_group, touch_fingertip_groups, pre_action_frame):
        self.index = index
        self.parent = parent
        self.action_fingertip_group = action_fingertip_group
        self.touch_fingertip_groups = touch_fingertip_groups
        self.pre_action_frame = pre_action_frame
        self.key_touch_positions = None
        self.widget_areas = None
    
    @abc.abstractclassmethod
    def get_instruction_name(cls):
        pass
    
    @abc.abstractmethod
    def get_instruction_parameters(self):
        pass

    @abc.abstractmethod
    def get_preview_image(self):
        pass

    def find_widget_areas(self, touch_positions):
        if WIDGET_RECOGNIZE_METHOD == "fixed_size":
            func = widget_recognizer.recognize_by_fixed_size
        else:
            func = widget_recognizer.recognize_by_mixed_approach
        areas = [func(self.pre_action_frame, pos) for pos in touch_positions]
        return areas

    def get_key_touch_positions(self):
        if self.key_touch_positions is None:
            self.key_touch_positions = [group_processor.get_deepest_from_sidelook(self.touch_fingertip_groups[0]).get_touch_position()]
        return self.key_touch_positions

    def get_widget_areas(self):
        if self.widget_areas is None:
            touch_position = self.get_key_touch_positions()[0]
            self.widget_areas = self.find_widget_areas([touch_position])
        return self.widget_areas


class ClickAction(AbstractAction):
    @classmethod
    def get_instruction_name(cls):
        return "click"

    def get_instruction_parameters(self):
        widget_area = self.get_widget_areas()[0]
        x1, y1 = widget_area.lt
        x2, y2 = widget_area.rb
        widget = self.pre_action_frame.overlook_image[y1:y2, x1:x2]
        return [widget]

    def get_preview_image(self):
        touch_position = self.get_key_touch_positions()[0]
        widget_area = self.get_widget_areas()[0]
        objects = {"points":[touch_position], "areas":[widget_area]}
        draw_methods = {"draw_points":DrawPointMethods.dot,"draw_areas":DrawAreaMethods.widget}
        preview = preview_generator.get_preview(self.pre_action_frame, objects, draw_methods)
        return preview

class DoubleClickAction(AbstractAction):
    @classmethod
    def get_instruction_name(cls):
        return "double_click"

    def get_instruction_parameters(self):
        widget_area = self.get_widget_areas()[0]
        x1, y1 = widget_area.lt
        x2, y2 = widget_area.rb
        widget = self.pre_action_frame.overlook_image[y1:y2, x1:x2]
        return [widget]
    
    def get_preview_image(self):
        touch_position = self.get_key_touch_positions()[0]
        widget_area = self.get_widget_areas()[0]
        objects = {"points":[touch_position], "areas":[widget_area]}
        draw_methods = {"draw_points":DrawPointMethods.tilted_cross,"draw_areas":DrawAreaMethods.widget}
        preview = preview_generator.get_preview(self.pre_action_frame, objects, draw_methods)
        return preview


class LongPressAction(AbstractAction):
    @classmethod
    def get_instruction_name(cls):
        return "long_press"

    def get_instruction_parameters(self):
        widget_area = self.get_widget_areas()[0]
        x1, y1 = widget_area.lt
        x2, y2 = widget_area.rb
        widget = self.pre_action_frame.overlook_image[y1:y2, x1:x2]
        return [widget]
    
    def get_preview_image(self):
        touch_position = self.get_key_touch_positions()[0]
        widget_area = self.get_widget_areas()[0]
        objects = {"points":[touch_position], "areas":[widget_area]}
        draw_methods = {"draw_points":DrawPointMethods.concentric_circles,"draw_areas":DrawAreaMethods.widget}
        preview = preview_generator.get_preview(self.pre_action_frame, objects, draw_methods)
        return preview


class DragAction(AbstractAction):
    @classmethod
    def get_instruction_name(cls):
        return "drag"
    
    def get_key_touch_positions(self):
        start_touch_position = self.touch_fingertip_groups[0][0].get_touch_position()
        end_touch_position = self.touch_fingertip_groups[0][-1].get_touch_position()
        return [start_touch_position, end_touch_position]

    def get_widget_areas(self):
        if self.widget_areas is None:
            start_touch_position, end_touch_position = self.get_key_touch_positions()
            start_widget_area = widget_recognizer.recognize_by_mixed_approach(self.pre_action_frame, start_touch_position)
            end_widget_area = widget_recognizer.recognize_by_fixed_size(self.pre_action_frame, end_touch_position)
            self.widget_areas = [start_widget_area, end_widget_area]
        return self.widget_areas


    def get_instruction_parameters(self):
        start_widget_area, end_widget_area = self.get_widget_areas()
        widgets = []
        for widget_area in [start_widget_area, end_widget_area]:
            x1, y1 = widget_area.lt
            x2, y2 = widget_area.rb
            widget = self.pre_action_frame.overlook_image[y1:y2, x1:x2]
            widgets.append(widget)
        return widgets
    
    def get_preview_image(self):
        start_touch_position, end_touch_position = self.get_key_touch_positions()
        widget_areas = self.get_widget_areas()
        objects = {"points":[start_touch_position, end_touch_position], "areas":widget_areas}
        draw_methods = {"draw_points":DrawPointMethods.dot,"draw_areas":DrawAreaMethods.widget,"draw_arrows":DrawArrowMethods.default}
        preview = preview_generator.get_preview(self.pre_action_frame, objects, draw_methods)
        return preview


class SwipeAction(AbstractAction):
    @classmethod
    def get_instruction_name(cls):
        return "swipe"

    def get_key_touch_positions(self):
        start_touch_position = self.touch_fingertip_groups[0][0].get_touch_position()
        #end_touch_position = self.touch_fingertip_groups[0][-1].get_touch_position()
        end_touch_position = self.touch_fingertip_groups[-1][-1].get_touch_position()
        return [start_touch_position, end_touch_position]

    def get_instruction_parameters(self):
        start_touch_position, end_touch_position = self.get_key_touch_positions()
        horizon_move = end_touch_position[0] - start_touch_position[0]
        vertical_move = end_touch_position[1] - start_touch_position[1]
        if abs(horizon_move) > abs(vertical_move):
            direction = "right" if horizon_move > 0 else "left"
        else:
            direction = "down" if vertical_move > 0 else "up"

        if not PRODUCE_SWIPE_REGION:
            return [direction]
        else:
            region_x0 = min(start_touch_position[0], end_touch_position[0])
            region_x1 = max(start_touch_position[0], end_touch_position[0])
            region_y0 = min(start_touch_position[1], end_touch_position[1])
            region_y1 = max(start_touch_position[1], end_touch_position[1])

            # 根据机器人的执行要求，扩大region（机器人只在指定滑动区域的中心 2/3 范围滑动
            dx = region_x1 - region_x0
            dy = region_y1 - region_y0

            swipe_dc = 2/3
            if direction=="up" or direction=="down":
                expand = (dy/swipe_dc - dy) / 2
                region_x0 = start_touch_position[0] - dx / 2
                region_x1 = start_touch_position[0] + dx / 2
                region_y0 -= expand
                region_y1 += expand
            else:
                expand = (dx / swipe_dc - dx) / 2
                region_x0 -= expand
                region_x1 += expand
                region_y0 = start_touch_position[1] - dy / 2
                region_y1 = start_touch_position[1] + dy / 2

            # 获得相对屏幕的位置
            device_location = self.parent.parameters["device_location"]
            device_x1, device_y1 = device_location.lt
            dev_rx0, dev_ry0 = region_x0 - device_x1, region_y0 - device_y1
            dev_rx1, dev_ry2 = region_x1 - device_x1, region_y1 - device_y1

            dev_width = device_location.rb[0] - device_location.lt[0]
            dev_height = device_location.rb[1] - device_location.lt[1]

            r_x0 = dev_rx0 / dev_width
            r_x1 = dev_rx1 / dev_width
            r_y0 = dev_ry0 / dev_height
            r_y1 = dev_ry2 / dev_height
            region = [r_x0, r_y0, r_x1, r_y1]
            return [direction, region]

    def get_preview_image(self):
        start_touch_position = self.touch_fingertip_groups[0][0].get_touch_position()
        end_touch_position = self.touch_fingertip_groups[0][-1].get_touch_position()
        params = self.get_instruction_parameters()
        note = "direction:%s"%params[0]
        objects = {"points":[start_touch_position, end_touch_position], "notes":[note]}
        draw_methods = {"draw_points":DrawPointMethods.dot,"draw_arrows":DrawArrowMethods.default,"draw_notes":DrawNoteMethods.default}
        if PRODUCE_SWIPE_REGION:
            draw_methods["draw_areas"] = DrawAreaMethods.widget
            region = params[1]
            device_location = self.parent.parameters["device_location"]
            dev_width = device_location.rb[0] - device_location.lt[0]
            dev_height = device_location.rb[1] - device_location.lt[1]
            x0 = int(region[0] * dev_width) + device_location.lt[0]
            y0 = int(region[1] * dev_height) + device_location.lt[1]
            x1 = int(region[2] * dev_width) + device_location.lt[0]
            y1 = int(region[3] * dev_height) + device_location.lt[1]
            objects["areas"] = [Area(x0, y0, x1, y1)]

        preview = preview_generator.get_preview(self.pre_action_frame, objects, draw_methods)
        return preview


class PressKeyboardAction(AbstractAction):
    @classmethod
    def get_instruction_name(cls):
        return "press_keyboard"

    def get_info(self):
        keyboard_name, keyboard_area = action_processor.get_keyboard_info(self.pre_action_frame, self.parent.parameters["keyboards"])
        key_distribution = self.parent.parameters["keyboards"][keyboard_name]["key_distribution"]
        key_area_mapping = self.get_key_area_mapping(keyboard_area, key_distribution)
        return [keyboard_name, keyboard_area, key_area_mapping]
    
    def get_key_touch_positions(self):
        touch_positions = [group_processor.get_deepest_from_sidelook(group).get_touch_position() for group in self.touch_fingertip_groups]
        return touch_positions

    def get_pressed_keys(self, touch_positions, key_area_mapping):
        pressed_keys = ""
        for touch_position in touch_positions:
            pressed_key = None
            for c, area in key_area_mapping.items():
                if area.contain_position(touch_position):
                    pressed_key = c
                    break
            if pressed_key == None:
                pressed_key = "*"
            if len(pressed_key) > 1 and not pressed_key.startswith("["):
                pressed_key = "[%s]"%pressed_key
            pressed_keys += pressed_key
        return pressed_keys

    def get_instruction_parameters(self):
        keyboard_name, _keyboard_area, key_area_mapping = self.get_info()
        touch_positions = self.get_key_touch_positions()
        pressed_keys = self.get_pressed_keys(touch_positions, key_area_mapping)
        return [keyboard_name, pressed_keys]

    def get_key_area_mapping(self, keyboard_area, key_distribution):
        key_area_mapping = {}
        for c in key_distribution.keys():
            key_area_mapping[c] = key_distribution[c].get_pixel_area(keyboard_area)
        return key_area_mapping

    def get_preview_image(self):
        keyboard_name, keyboard_area, key_area_mapping = self.get_info()
        touch_positions = self.get_key_touch_positions()
        pressed_keys = self.get_pressed_keys(touch_positions, key_area_mapping)
        areas = [keyboard_area]
        areas.extend(key_area_mapping.values())
        note1 = "keyboard:%s"%keyboard_name
        note2 = "keys:%s"%pressed_keys
        objects = {"points":touch_positions, "areas":areas, "notes":[note1, note2]}
        draw_methods = {"draw_points":DrawPointMethods.dot, "draw_areas":DrawAreaMethods.keyboard, "draw_notes":DrawNoteMethods.default}
        preview = preview_generator.get_preview(self.pre_action_frame, objects, draw_methods)
        return preview


class UnknownAction(AbstractAction):
    @classmethod
    def get_instruction_name(cls):
        return "unknown"
    
    def get_instruction_parameters(self):
        return []
    
    def get_preview_image(self):
        objects = {"notes":["Unknown"]}
        draw_methods = {"draw_notes":DrawNoteMethods.default}
        preview = preview_generator.get_preview(self.pre_action_frame, objects, draw_methods)
        return preview