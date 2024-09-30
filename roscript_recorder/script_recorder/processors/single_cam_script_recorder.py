import os

from . import script_generator
from ..models.single_cam_video import SingleCamVideo

def record(video_path, device_real_measure, export_dir, dev_mode, overlook_color_range=None):
    dbg_dir = os.path.join(export_dir, "debug") if dev_mode else None
    vd = SingleCamVideo(video_path, device_real_measure, overlook_skin_color_range=overlook_color_range, debug_dir=dbg_dir)
    actions = vd.get_actions()
    script_generator.generate(actions, export_dir, True)