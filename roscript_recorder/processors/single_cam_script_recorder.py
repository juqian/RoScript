from . import script_generator
from roscript_recorder.models.single_cam_video import SingleCamVideo

def record(video_path, device_real_measure, export_dir, dev_mode):
    actions = SingleCamVideo(video_path, device_real_measure).get_actions()
    script_generator.generate(actions, export_dir, dev_mode)