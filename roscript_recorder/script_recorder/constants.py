import os
from ruamel import yaml

config_file_path = os.path.join(os.path.dirname(__file__), "../config/data.yaml")
with open(config_file_path,'r') as f:
    constants = yaml.load(f, Loader=yaml.Loader)

AUTO_HAND_COLOR_DETECT = False

DEVICE_CANNY_LOW = constants["device_recognition"]["canny_low"]
DEVICE_CANNY_HIGH = constants["device_recognition"]["canny_high"]
DEVICE_CLOSING_KERNEL = constants["device_recognition"]["closing_kernel"]
DEVICE_SIZE_LIMIT_RATIO = constants["device_recognition"]["device_size_limit_ratio"]
DEVICE_LEAN_TOLERANCE = constants["device_recognition"]["device_lean_tolerance"]
POWER_LINE_THICKNESS_RATIO = constants["device_recognition"]["power_line_thickness_ratio"]
# Overlook color range
OVERLOOK_SKIN_YCrCb_LOW = (constants["finger_recognition"]["YCrCb"]["Y_low"],
                           constants["finger_recognition"]["YCrCb"]["Cr_low"],
                           constants["finger_recognition"]["YCrCb"]["Cb_low"])
OVERLOOK_SKIN_YCrCb_HIGH = (constants["finger_recognition"]["YCrCb"]["Y_high"],
                            constants["finger_recognition"]["YCrCb"]["Cr_high"],
                            constants["finger_recognition"]["YCrCb"]["Cb_high"])
# Sidelook color range
if "side_look_YCrCb" in constants["finger_recognition"]:
    SIDELOOK_SKIN_YCrCb_LOW = (constants["finger_recognition"]["side_look_YCrCb"]["Y_low"],
                               constants["finger_recognition"]["side_look_YCrCb"]["Cr_low"],
                               constants["finger_recognition"]["side_look_YCrCb"]["Cb_low"])
    SIDELOOK_SKIN_YCrCb_HIGH = (constants["finger_recognition"]["side_look_YCrCb"]["Y_high"],
                                constants["finger_recognition"]["side_look_YCrCb"]["Cr_high"],
                                constants["finger_recognition"]["side_look_YCrCb"]["Cb_high"])
else:
    SIDELOOK_SKIN_YCrCb_LOW = OVERLOOK_SKIN_YCrCb_LOW
    SIDELOOK_SKIN_YCrCb_HIGH = OVERLOOK_SKIN_YCrCb_HIGH

SKIN_OPEN_KERNEL = constants["finger_recognition"]["open_kernel"]
SKIN_CLOSING_KERNEL = constants["finger_recognition"]["closing_kernel"]

HAND_MIN_SIZE_RATIO = constants["finger_recognition"]["hand_min_size_ratio"]
HAND_EDGE_TOLERANCE = constants["finger_recognition"]["hand_edge_tolerance"]

FINGERTIP_CANDIDATE_Y_TOLERANCE = constants["finger_recognition"]["fingertip_candidate_y_tolerance"]
####
FINGERTIP_OFFSET = constants["finger_recognition"]["fingertip_offset"]
####
HORIZON_PERSPECTIVE_FACTOR = constants["finger_recognition"]["horizon_perspective_factor"]
VERTICAL_PERSPECTIVE_FACTOR = constants["finger_recognition"]["vertical_perspective_factor"]
####
SIDELOOK_CROP_RATIO = constants["finger_recognition"]["side_look_crop_ratio"]

PRE_ACTION_FRAME_OFFSET = constants["frame_selection"]["pre_action_offset"]

SIDELOOK_TOUCH_THRESHOLD_FACTOR = constants["action_recognition"]["sidelook_touch_threshold_factory"]
####
ACTION_GAP_FRAME_COUNT_LIMIT = constants["frame_selection"]["action_gap_frame_count_limit"]
ACTION_MIN_FRAME_COUNT_LIMIT = constants["frame_selection"]["action_min_frame_count_limit"]

TOUCH_GAP_FRAME_COUNT_LIMIT = constants["frame_selection"]["touch_gap_frame_count_limit"]
TOUCH_MIN_FRAME_COUNT_LIMIT = constants["frame_selection"]["touch_min_frame_count_limit"]
####
ACTION_TYPE_MOVE_DISTANCE = constants["action_recognition"]["action_type_move_distance"]
STAY_TIME_LIMIT = constants["action_recognition"]["stay_time_limit"]
SURF_KEYBOARD_MIN_MATCH_COUNT = constants["action_recognition"]["surf_keyboard_min_match_count"]
####
WIDGET_RECOGNIZE_METHOD = "canny" #"fixed_size"

WIDGET_MEDIAN_BLUR = constants["widget_recognition"]["canny"]["median_blur"]
WIDGET_CANNY_LOW = constants["widget_recognition"]["canny"]["canny_low"]
WIDGET_CANNY_HIGH = constants["widget_recognition"]["canny"]["canny_high"]
WIDGET_CLOSING_KERNEL = constants["widget_recognition"]["canny"]["closing_kernel"]
WIDGET_MAX_SIZE = constants["widget_recognition"]["canny"]["widget_max_size"]
EXTENSION_SIZE_LIMIT = constants["widget_recognition"]["canny"]["extension_size_limit"]
EXTEND_LENGTH = constants["widget_recognition"]["canny"]["extend_length"]

DEFAULT_SIDE_LENGTH = constants["widget_recognition"]["fixed_size"]["default_side_length"]

PRODUCE_SWIPE_REGION = True


config_dir = os.path.dirname(config_file_path)
script_template_path = os.path.join(config_dir, constants["script_generation"]["template_path"])
with open(script_template_path,'r') as f:
    SCRIPT_TEMPLATE_CONTENT = f.read()


def load_config(config_file_path):
    global AUTO_HAND_COLOR_DETECT
    global DEVICE_CANNY_LOW
    global DEVICE_CANNY_HIGH
    global DEVICE_CLOSING_KERNEL
    global DEVICE_SIZE_LIMIT_RATIO
    global DEVICE_LEAN_TOLERANCE
    global POWER_LINE_THICKNESS_RATIO
    global OVERLOOK_SKIN_YCrCb_LOW
    global OVERLOOK_SKIN_YCrCb_HIGH
    global SIDELOOK_SKIN_YCrCb_LOW
    global SIDELOOK_SKIN_YCrCb_HIGH
    global SKIN_OPEN_KERNEL
    global SKIN_CLOSING_KERNEL
    global HAND_MIN_SIZE_RATIO
    global HAND_EDGE_TOLERANCE
    global FINGERTIP_CANDIDATE_Y_TOLERANCE
    global FINGERTIP_OFFSET
    global HORIZON_PERSPECTIVE_FACTOR
    global VERTICAL_PERSPECTIVE_FACTOR
    global SIDELOOK_CROP_RATIO
    global PRE_ACTION_FRAME_OFFSET
    global SIDELOOK_TOUCH_THRESHOLD_FACTOR
    global ACTION_GAP_FRAME_COUNT_LIMIT
    global ACTION_MIN_FRAME_COUNT_LIMIT
    global TOUCH_GAP_FRAME_COUNT_LIMIT
    global TOUCH_MIN_FRAME_COUNT_LIMIT
    global ACTION_TYPE_MOVE_DISTANCE
    global STAY_TIME_LIMIT
    global SURF_KEYBOARD_MIN_MATCH_COUNT
    global WIDGET_RECOGNIZE_METHOD
    global WIDGET_MEDIAN_BLUR
    global WIDGET_CANNY_LOW
    global WIDGET_CANNY_HIGH
    global WIDGET_CLOSING_KERNEL
    global WIDGET_MAX_SIZE
    global EXTENSION_SIZE_LIMIT
    global EXTEND_LENGTH
    global DEFAULT_SIDE_LENGTH
    global PRODUCE_SWIPE_REGION
    global SCRIPT_TEMPLATE_CONTENT

    with open(config_file_path, 'r') as f:
        constants = yaml.load(f, Loader=yaml.Loader)

    AUTO_HAND_COLOR_DETECT = False

    DEVICE_CANNY_LOW = constants["device_recognition"]["canny_low"]
    DEVICE_CANNY_HIGH = constants["device_recognition"]["canny_high"]
    DEVICE_CLOSING_KERNEL = constants["device_recognition"]["closing_kernel"]
    DEVICE_SIZE_LIMIT_RATIO = constants["device_recognition"]["device_size_limit_ratio"]
    DEVICE_LEAN_TOLERANCE = constants["device_recognition"]["device_lean_tolerance"]
    POWER_LINE_THICKNESS_RATIO = constants["device_recognition"]["power_line_thickness_ratio"]
    # Overlook color range
    OVERLOOK_SKIN_YCrCb_LOW = (constants["finger_recognition"]["YCrCb"]["Y_low"],
                               constants["finger_recognition"]["YCrCb"]["Cr_low"],
                               constants["finger_recognition"]["YCrCb"]["Cb_low"])
    OVERLOOK_SKIN_YCrCb_HIGH = (constants["finger_recognition"]["YCrCb"]["Y_high"],
                                constants["finger_recognition"]["YCrCb"]["Cr_high"],
                                constants["finger_recognition"]["YCrCb"]["Cb_high"])
    # Sidelook color range
    if "side_look_YCrCb" in constants["finger_recognition"]:
        SIDELOOK_SKIN_YCrCb_LOW = (constants["finger_recognition"]["side_look_YCrCb"]["Y_low"],
                                   constants["finger_recognition"]["side_look_YCrCb"]["Cr_low"],
                                   constants["finger_recognition"]["side_look_YCrCb"]["Cb_low"])
        SIDELOOK_SKIN_YCrCb_HIGH = (constants["finger_recognition"]["side_look_YCrCb"]["Y_high"],
                                    constants["finger_recognition"]["side_look_YCrCb"]["Cr_high"],
                                    constants["finger_recognition"]["side_look_YCrCb"]["Cb_high"])
    else:
        SIDELOOK_SKIN_YCrCb_LOW = OVERLOOK_SKIN_YCrCb_LOW
        SIDELOOK_SKIN_YCrCb_HIGH = OVERLOOK_SKIN_YCrCb_HIGH

    SKIN_OPEN_KERNEL = constants["finger_recognition"]["open_kernel"]
    SKIN_CLOSING_KERNEL = constants["finger_recognition"]["closing_kernel"]

    HAND_MIN_SIZE_RATIO = constants["finger_recognition"]["hand_min_size_ratio"]
    HAND_EDGE_TOLERANCE = constants["finger_recognition"]["hand_edge_tolerance"]

    FINGERTIP_CANDIDATE_Y_TOLERANCE = constants["finger_recognition"]["fingertip_candidate_y_tolerance"]
    ####
    FINGERTIP_OFFSET = constants["finger_recognition"]["fingertip_offset"]
    ####
    HORIZON_PERSPECTIVE_FACTOR = constants["finger_recognition"]["horizon_perspective_factor"]
    VERTICAL_PERSPECTIVE_FACTOR = constants["finger_recognition"]["vertical_perspective_factor"]
    ####
    SIDELOOK_CROP_RATIO = constants["finger_recognition"]["side_look_crop_ratio"]

    PRE_ACTION_FRAME_OFFSET = constants["frame_selection"]["pre_action_offset"]

    SIDELOOK_TOUCH_THRESHOLD_FACTOR = constants["action_recognition"]["sidelook_touch_threshold_factory"]
    ####
    ACTION_GAP_FRAME_COUNT_LIMIT = constants["frame_selection"]["action_gap_frame_count_limit"]
    ACTION_MIN_FRAME_COUNT_LIMIT = constants["frame_selection"]["action_min_frame_count_limit"]

    TOUCH_GAP_FRAME_COUNT_LIMIT = constants["frame_selection"]["touch_gap_frame_count_limit"]
    TOUCH_MIN_FRAME_COUNT_LIMIT = constants["frame_selection"]["touch_min_frame_count_limit"]
    ####
    ACTION_TYPE_MOVE_DISTANCE = constants["action_recognition"]["action_type_move_distance"]
    STAY_TIME_LIMIT = constants["action_recognition"]["stay_time_limit"]
    SURF_KEYBOARD_MIN_MATCH_COUNT = constants["action_recognition"]["surf_keyboard_min_match_count"]
    ####
    WIDGET_RECOGNIZE_METHOD = "canny"  # "fixed_size"

    WIDGET_MEDIAN_BLUR = constants["widget_recognition"]["canny"]["median_blur"]
    WIDGET_CANNY_LOW = constants["widget_recognition"]["canny"]["canny_low"]
    WIDGET_CANNY_HIGH = constants["widget_recognition"]["canny"]["canny_high"]
    WIDGET_CLOSING_KERNEL = constants["widget_recognition"]["canny"]["closing_kernel"]
    WIDGET_MAX_SIZE = constants["widget_recognition"]["canny"]["widget_max_size"]
    EXTENSION_SIZE_LIMIT = constants["widget_recognition"]["canny"]["extension_size_limit"]
    EXTEND_LENGTH = constants["widget_recognition"]["canny"]["extend_length"]
    DEFAULT_SIDE_LENGTH = constants["widget_recognition"]["fixed_size"]["default_side_length"]
