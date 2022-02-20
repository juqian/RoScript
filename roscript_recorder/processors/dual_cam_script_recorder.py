from . import script_generator
from roscript_recorder.models.dual_cam_video import DualCamVideo

def record(video_path, device_real_measure, keyboards_dir, export_dir, dev_mode):
    actions = DualCamVideo(video_path, device_real_measure, keyboards_dir).get_actions()
    script_generator.generate(actions, export_dir, dev_mode)