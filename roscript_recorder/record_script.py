"""
Entry of the test script recorder
"""
import os
import argparse
from ruamel import yaml
from script_recorder.processors import single_cam_script_recorder, dual_cam_script_recorder, script_generator
import script_recorder.constants as rconfig


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--i", help="The input video path.")
    parser.add_argument("--dev", nargs=2, help="The physical size of the device: (width height).")
    parser.add_argument("--mode", default="singleCamera", help="The recording mode: (singleCamera/dualCamera)")
    parser.add_argument("--o", default=None, help="The output directory.")
    parser.add_argument("--keyboards", default=None, help="The keyboards directory path.")
    parser.add_argument("--color_file", default=None, help="The color file for hand detection.")
    parser.add_argument("--config", default=None, help="The config file path.")
    args = parser.parse_args()

    video_path = args.i
    result_dir = args.o

    dev_mode = False

    device_real_width, device_real_height = int(args.dev[0]), int(args.dev[1])
    device_real_measure = (device_real_width, device_real_height)

    if not os.path.exists(video_path):
        raise Exception("Video not found: " + video_path)

    if args.config is not None:
        rconfig.load_config(args.config)

    if result_dir is None:
        video_name = os.path.basename(video_path)
        name, ext = os.path.splitext(video_name)
        result_dir = r"./output/" + name

    if os.path.exists(result_dir):
        raise Exception("Please remove the existing result in %s first" % result_dir)

    os.makedirs(result_dir, exist_ok=True)

    color_file = args.color_file
    overlook_color_range, sidelook_color_range = None, None
    if color_file is not None and os.path.exists(color_file):
        with open(color_file, 'r') as f:
            data = yaml.load(f, Loader=yaml.Loader)
        color_block = data["finger_recognition"]["YCrCb"]
        overlook_color_low = (color_block["Y_low"], color_block["Cr_low"], color_block["Cb_low"])
        overlook_color_high = (color_block["Y_high"], color_block["Cr_high"], color_block["Cb_high"])
        if "side_look_YCrCb" in data["finger_recognition"]:
            color_block = data["finger_recognition"]["side_look_YCrCb"]
            sidelook_color_low = (color_block["Y_low"], color_block["Cr_low"], color_block["Cb_low"])
            sidelook_color_high = (color_block["Y_high"], color_block["Cr_high"], color_block["Cb_high"])
        else:
            sidelook_color_low = overlook_color_low
            sidelook_color_high = overlook_color_high
        overlook_color_range = (overlook_color_low, overlook_color_high)
        sidelook_color_range = (sidelook_color_low, sidelook_color_high)

    if args.mode.lower() == "singlecamera":
        video_name = os.path.basename(video_path)
        single_cam_script_recorder.record(video_path, device_real_measure, result_dir, dev_mode, overlook_color_range)
        script_generator.create_script_html(result_dir)
    elif args.mode.lower() == "dualcamera":
        keyboards_dir = args.keyboards
        dual_cam_script_recorder.record(video_path, device_real_measure, keyboards_dir, result_dir,
                                        dev_mode, overlook_color_range, sidelook_color_range)
        script_generator.create_script_html(result_dir)
    else:
        raise Exception("Unsupported recording mode: " + args.mode)
    print("Done!")