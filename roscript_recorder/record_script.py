from processors import single_cam_script_recorder, dual_cam_script_recorder
from processors import widget_recognizer, device_detector
import os, argparse
from ruamel import yaml
import cv2
import roscript_recorder.constants as rconfig


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--src", help = "The source video path or image path.")
    parser.add_argument("--export", help = "The export directory path.")
    parser.add_argument("--measure", nargs = 2, help = "The measure of the device.(width height)")
    parser.add_argument("--vtype", default = "singleCamera", help = "The type of the video.(singleCamera/dualCamera)")
    parser.add_argument("--keyboards", default = None, help = "The keyboards directory path.")
    parser.add_argument("--position", default = None, nargs = 2, help = "The touch position in the image.(x y)")
    args = parser.parse_args()

    dev_mode = False

    device_real_width, device_real_height = int(args.measure[0]), int(args.measure[1])
    device_real_measure = (device_real_width, device_real_height)
    
    #rconfig.load_config(__find_RoScript_recorder_config())

    if args.position == None:
        video_path = args.src
        video_type = args.vtype
        result_dir = args.export
        if video_type.lower() == "singlecamera":
            single_cam_script_recorder.record(video_path, device_real_measure, result_dir, False)
        elif video_type.lower() == "dualcamera":
            keyboards_dir = args.keyboards
            dual_cam_script_recorder.record(video_path, device_real_measure, keyboards_dir, result_dir, False)
        else:
            print("无法识别的视频类型！")
        print("视频解析完成！")
    else:
        touch_position = (int(args.position[0]), int(args.position[1]))
        image = cv2.imread(args.src)
        device_location = device_detector.simple_detect(image)
        device_pixel_width = device_location.get_width()
        device_pixel_height = device_location.get_height()
        pixel_to_real_ratio = 0.5 * (device_pixel_width/device_real_measure[0] + device_pixel_height/device_real_measure[1])
        x1, y1, x2, y2 = widget_recognizer.recognize_by_mixed_approach0(image, touch_position, pixel_to_real_ratio)
        widget = image[y1:y2, x1:x2]

        # 保存widget图片
        image_name = os.path.splitext(os.path.basename(args.src))[0]
        widget_name_template = image_name + "_widget{0}.png"
        i = 1
        while True:
            widget_save_path = os.path.join(args.export, widget_name_template.format(i))
            if not os.path.exists(widget_save_path):
                cv2.imwrite(widget_save_path, widget)
                print(os.path.abspath(widget_save_path))
                break
            i += 1