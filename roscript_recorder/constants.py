"""
All configuration of the script recorder
"""


import os, sys
from ruamel import yaml

AUTO_HAND_COLOR_DETECT = False

# Global variable declaration
DEVICE_CANNY_LOW = None
DEVICE_CANNY_HIGH = None
DEVICE_CLOSING_KERNEL = None
DEVICE_SIZE_LIMIT_RATIO = None
DEVICE_LEAN_TOLERANCE = None
POWER_LINE_THICKNESS_RATIO = None
####
SKIN_Y_LOW = None
SKIN_CR_LOW = None
SKIN_CB_LOW = None
SKIN_Y_HIGH = None
SKIN_CR_HIGH = None
SKIN_CB_HIGH = None
SKIN_OPEN_KERNEL = None
SKIN_CLOSING_KERNEL = None
 
HAND_MIN_SIZE_RATIO = None
HAND_EDGE_TOLERANCE = None
 
FINGERTIP_CANDIDATE_Y_TOLERANCE = None
 
####
FINGERTIP_OFFSET = None
 
####
HORIZON_PERSPECTIVE_FACTOR = None
VERTICAL_PERSPECTIVE_FACTOR = None
 
####
SIDELOOK_CROP_RATIO = None
 
PRE_ACTION_FRAME_OFFSET = None
 
SIDELOOK_TOUCH_THRESHOLD_FACTOR = None
 
####
ACTION_GAP_FRAME_COUNT_LIMIT = None
ACTION_MIN_FRAME_COUNT_LIMIT = None
 
TOUCH_GAP_FRAME_COUNT_LIMIT = None
TOUCH_MIN_FRAME_COUNT_LIMIT = None
 
####
ACTION_TYPE_MOVE_DISTANCE = None
STAY_TIME_LIMIT = None
SURF_KEYBOARD_MIN_MATCH_COUNT = None
####
WIDGET_MEDIAN_BLUR = None
WIDGET_CANNY_LOW = None
WIDGET_CANNY_HIGH = None
WIDGET_CLOSING_KERNEL = None
WIDGET_MAX_SIZE = None
EXTENSION_SIZE_LIMIT = None
EXTEND_LENGTH = None
 
DEFAULT_SIDE_LENGTH = None
 
EAST_MAX_WORD_SPACE = None
EAST_MAX_WIDTH = None

WIDGET_RECOGNIZE_METHOD = "mixed" #"fixed_size"

####
SAME_ROW_HEIGHT_IOU = None
SCRIPT_TEMPLATE_CONTENT = None
    

# configuration should always be made before recording test scripts
def load_config(file):
    with open(file,'r') as f:
        constants = yaml.load(f, Loader=yaml.Loader)
       
    # Global variable declaration
    global DEVICE_CANNY_LOW
    global DEVICE_CANNY_HIGH
    global DEVICE_CLOSING_KERNEL
    global DEVICE_SIZE_LIMIT_RATIO
    global DEVICE_LEAN_TOLERANCE
    global POWER_LINE_THICKNESS_RATIO
    ####
    global SKIN_Y_LOW
    global SKIN_CR_LOW
    global SKIN_CB_LOW
    global SKIN_Y_HIGH
    global SKIN_CR_HIGH
    global SKIN_CB_HIGH
    global SKIN_OPEN_KERNEL
    global SKIN_CLOSING_KERNEL

    global HAND_MIN_SIZE_RATIO
    global HAND_EDGE_TOLERANCE

    global FINGERTIP_CANDIDATE_Y_TOLERANCE
    ####
    global FINGERTIP_OFFSET
    ####
    global HORIZON_PERSPECTIVE_FACTOR
    global VERTICAL_PERSPECTIVE_FACTOR
    ####
    global SIDELOOK_CROP_RATIO

    global PRE_ACTION_FRAME_OFFSET

    global SIDELOOK_TOUCH_THRESHOLD_FACTOR
    ####
    global ACTION_GAP_FRAME_COUNT_LIMIT
    global ACTION_MIN_FRAME_COUNT_LIMIT

    global TOUCH_GAP_FRAME_COUNT_LIMIT
    global TOUCH_MIN_FRAME_COUNT_LIMIT
    ####
    global ACTION_TYPE_MOVE_DISTANCE
    global STAY_TIME_LIMIT
    global SURF_KEYBOARD_MIN_MATCH_COUNT
    ####
    global WIDGET_MEDIAN_BLUR
    global WIDGET_CANNY_LOW
    global WIDGET_CANNY_HIGH
    global WIDGET_CLOSING_KERNEL
    global WIDGET_MAX_SIZE
    global EXTENSION_SIZE_LIMIT
    global EXTEND_LENGTH

    global DEFAULT_SIDE_LENGTH

    global EAST_MAX_WORD_SPACE
    global EAST_MAX_WIDTH
    ####
    global SAME_ROW_HEIGHT_IOU
    global SCRIPT_TEMPLATE_CONTENT
        
    # Global variable initialization ===============================================================    
    DEVICE_CANNY_LOW = constants["device_recognition"]["canny_low"]
    DEVICE_CANNY_HIGH = constants["device_recognition"]["canny_high"]
    DEVICE_CLOSING_KERNEL = constants["device_recognition"]["closing_kernel"]
    DEVICE_SIZE_LIMIT_RATIO = constants["device_recognition"]["device_size_limit_ratio"]
    DEVICE_LEAN_TOLERANCE = constants["device_recognition"]["device_lean_tolerance"]
    POWER_LINE_THICKNESS_RATIO = constants["device_recognition"]["power_line_thickness_ratio"]
    ####
    SKIN_Y_LOW = constants["finger_recognition"]["YCrCb"]["Y_low"]
    SKIN_CR_LOW =constants["finger_recognition"]["YCrCb"]["Cr_low"]
    SKIN_CB_LOW = constants["finger_recognition"]["YCrCb"]["Cb_low"]
    SKIN_Y_HIGH = constants["finger_recognition"]["YCrCb"]["Y_high"]
    SKIN_CR_HIGH = constants["finger_recognition"]["YCrCb"]["Cr_high"]
    SKIN_CB_HIGH = constants["finger_recognition"]["YCrCb"]["Cb_high"]
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
    WIDGET_MEDIAN_BLUR = constants["widget_recognition"]["canny"]["median_blur"]
    WIDGET_CANNY_LOW = constants["widget_recognition"]["canny"]["canny_low"]
    WIDGET_CANNY_HIGH = constants["widget_recognition"]["canny"]["canny_high"]
    WIDGET_CLOSING_KERNEL = constants["widget_recognition"]["canny"]["closing_kernel"]
    WIDGET_MAX_SIZE = constants["widget_recognition"]["canny"]["widget_max_size"]
    EXTENSION_SIZE_LIMIT = constants["widget_recognition"]["canny"]["extension_size_limit"]
    EXTEND_LENGTH = constants["widget_recognition"]["canny"]["extend_length"]

    DEFAULT_SIDE_LENGTH = constants["widget_recognition"]["fixed_size"]["default_side_length"]

    EAST_MAX_WORD_SPACE = constants["widget_recognition"]["east"]["east_max_word_space"]
    EAST_MAX_WIDTH = constants["widget_recognition"]["east"]["east_max_width"]
    ####
    SAME_ROW_HEIGHT_IOU = constants["widget_recognition"]["east"]["same_row_height_iou"]
    
    #### 
    script_template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "script-template.mako"))
    with open(script_template_path,'r') as f:
        SCRIPT_TEMPLATE_CONTENT = f.read()
        

# in default, try to load the config file from the current directory 
default_config_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "config.yaml"))
if os.path.exists(default_config_file):
    load_config(default_config_file)    
        

