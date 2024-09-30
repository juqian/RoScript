import os

from . import script_generator
from ..models.dual_cam_video import DualCamVideo


def record(video_path, device_real_measure, keyboards_dir, export_dir, dev_mode,
           overlook_color_range=None, sidelook_color_range=None, with_hover_calib=False):
    if os.path.exists(export_dir):
        files = os.listdir(export_dir)
        if "debug" in files:
            files.remove("debug")
        if len(files) > 0 and os.path.exists(os.path.join(export_dir, "script.py")):
            raise Exception("Script folder %s already exist. Please remove it before recording!"% export_dir)

    dbg_dir = os.path.join(export_dir, "debug") if dev_mode else None
    vd = DualCamVideo(video_path, device_real_measure,
                      overlook_skin_color_range=overlook_color_range,
                      sidelook_skin_color_range=sidelook_color_range,
                      keyboards_dir=keyboards_dir, debug_dir=dbg_dir, with_hover_calib=with_hover_calib)
    actions = vd.get_actions()
    script_generator.generate(actions, export_dir, True)