import abc
from mako.template import Template
from roscript_recorder.processors import action_processor, group_processor, widget_recognizer, preview_generator
from roscript_recorder.processors.preview_generator import DrawPointMethods, DrawArrowMethods, DrawAreaMethods, DrawNoteMethods
from roscript_recorder.constants import *

class AbstractAction:
    def __init__(self, index, parent, action_fingertip_group, touch_fingertip_groups, pre_action_frame):
        self.index = index
        self.parent = parent
        self.action_fingertip_group = action_fingertip_group
        self.touch_fingertip_groups = touch_fingertip_groups
        self.pre_action_frame = pre_action_frame
    
    @abc.abstractclassmethod
    def get_instruction_name(cls):
        pass
    
    @abc.abstractmethod
    def get_instruction_parameters(self):
        pass

    @abc.abstractmethod
    def get_preview_image(self):
        pass


class ClickAction(AbstractAction):
    @classmethod
    def get_instruction_name(cls):
        return "click"
    
    def get_key_touch_positions(self):
        return [group_processor.get_deepest_from_sidelook(self.touch_fingertip_groups[0]).get_touch_position()]
    
    def get_widget_areas(self, touch_positions):
        if WIDGET_RECOGNIZE_METHOD=="fixed_size":
            return [widget_recognizer.recognize_by_fixed_size(self.pre_action_frame, touch_positions[0])]
        else:
            return [widget_recognizer.recognize_by_mixed_approach(self.pre_action_frame, touch_positions[0])]

    def get_instruction_parameters(self):
        touch_position = self.get_key_touch_positions()[0]
        widget_area = self.get_widget_areas([touch_position])[0]
        x1, y1 = widget_area.lt
        x2, y2 = widget_area.rb
        widget = self.pre_action_frame.overlook_image[y1:y2, x1:x2]
        return [widget]

    def get_preview_image(self):
        touch_position = self.get_key_touch_positions()[0]
        widget_area = self.get_widget_areas([touch_position])[0]
        objects = {"points":[touch_position], "areas":[widget_area]}
        draw_methods = {"draw_points":DrawPointMethods.dot,"draw_areas":DrawAreaMethods.widget}
        preview = preview_generator.get_preview(self.pre_action_frame, objects, draw_methods)
        return preview

class DoubleClickAction(AbstractAction):
    @classmethod
    def get_instruction_name(cls):
        return "double_click"

    def get_key_touch_positions(self):
        return [group_processor.get_deepest_from_sidelook(self.touch_fingertip_groups[0]).get_touch_position()]

    def get_widget_areas(self, touch_positions):
        return [widget_recognizer.recognize_by_mixed_approach(self.pre_action_frame, touch_positions[0])]

    def get_instruction_parameters(self):
        touch_position = self.get_key_touch_positions()[0]
        widget_area = self.get_widget_areas([touch_position])[0]
        x1, y1 = widget_area.lt
        x2, y2 = widget_area.rb
        widget = self.pre_action_frame.overlook_image[y1:y2, x1:x2]
        return [widget]
    
    def get_preview_image(self):
        touch_position = self.get_key_touch_positions()[0]
        widget_area = self.get_widget_areas([touch_position])[0]
        objects = {"points":[touch_position], "areas":[widget_area]}
        draw_methods = {"draw_points":DrawPointMethods.tilted_cross,"draw_areas":DrawAreaMethods.widget}
        preview = preview_generator.get_preview(self.pre_action_frame, objects, draw_methods)
        return preview

class LongPressAction(AbstractAction):
    @classmethod
    def get_instruction_name(cls):
        return "long_press"

    def get_key_touch_positions(self):
        return [group_processor.get_deepest_from_sidelook(self.touch_fingertip_groups[0]).get_touch_position()]

    def get_widget_areas(self, touch_positions):
        return [widget_recognizer.recognize_by_mixed_approach(self.pre_action_frame, touch_positions[0])]

    def get_instruction_parameters(self):
        touch_position = self.get_key_touch_positions()[0]
        widget_area = self.get_widget_areas([touch_position])[0]
        x1, y1 = widget_area.lt
        x2, y2 = widget_area.rb
        widget = self.pre_action_frame.overlook_image[y1:y2, x1:x2]
        return [widget]
    
    def get_preview_image(self):
        touch_position = self.get_key_touch_positions()[0]
        widget_area = self.get_widget_areas([touch_position])[0]
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

    def get_widget_areas(self, touch_positions):
        start_touch_position = touch_positions[0]
        end_touch_position = touch_positions[1]
        start_widget_area = widget_recognizer.recognize_by_mixed_approach(self.pre_action_frame, start_touch_position)
        end_widget_area = widget_recognizer.recognize_by_fixed_size(self.pre_action_frame, end_touch_position)
        return [start_widget_area, end_widget_area]

    def get_instruction_parameters(self):
        start_touch_position, end_touch_position = self.get_key_touch_positions()
        start_widget_area, end_widget_area = self.get_widget_areas([start_touch_position, end_touch_position])
        widgets = []
        for widget_area in [start_widget_area, end_widget_area]:
            x1, y1 = widget_area.lt
            x2, y2 = widget_area.rb
            widget = self.pre_action_frame.overlook_image[y1:y2, x1:x2]
            widgets.append(widget)
        return widgets
    
    def get_preview_image(self):
        start_touch_position = self.touch_fingertip_groups[0][0].get_touch_position()
        end_touch_position = self.touch_fingertip_groups[0][-1].get_touch_position()
        widget_areas = self.get_widget_areas([start_touch_position, end_touch_position])
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
        return [direction]
    
    def get_preview_image(self):
        start_touch_position = self.touch_fingertip_groups[0][0].get_touch_position()
        end_touch_position = self.touch_fingertip_groups[0][-1].get_touch_position()
        note = "direction:%s"%self.get_instruction_parameters()[0]
        objects = {"points":[start_touch_position, end_touch_position], "notes":[note]}
        draw_methods = {"draw_points":DrawPointMethods.dot,"draw_arrows":DrawArrowMethods.default,"draw_notes":DrawNoteMethods.default}
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