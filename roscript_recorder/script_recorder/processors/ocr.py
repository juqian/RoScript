import sys
import cv2
import os
import json
from typing import List
import numpy
from paddleocr import PaddleOCR, draw_ocr


pd_gpu = None
PADDLE_VER = None


def get_bounds(point_list: list):
    """ bounds: (x, y, w, h) """
    x_min = sys.maxsize
    x_max = 0
    y_min = sys.maxsize
    y_max = 0

    for point in point_list:
        x_min = int(min(x_min, point[0]))
        x_max = int(max(x_max, point[0]))
        y_min = int(min(y_min, point[1]))
        y_max = int(max(y_max, point[1]))

    bounds = (x_min, y_min, x_max - x_min, y_max - y_min)
    return bounds


def annotate_ocr_results(img, ocr_results):
    copy = img.copy()
    for r in ocr_results:
        x, y, w, h = r.bounds
        cv2.rectangle(copy, (x, y), (x + w, y + h), (0, 0, 255), 2)
        copy = cv2.putText(copy, r.text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 1)
        #copy = cv2.putText(copy, str(r.confidence), (x, y), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 1)
    return copy


def bounds_union(bounds1, bounds2):
    x = min(bounds1[0], bounds2[0])
    y = min(bounds1[1], bounds2[1])
    right = max(bounds1[0]+bounds1[2], bounds2[0]+bounds2[2])
    bottom = max(bounds1[1]+bounds1[3], bounds2[1]+bounds2[3])
    return (x, y, right-x, bottom-y)


def get_paddleocr_version():
    try:
        # 2.4以上版本
        from paddleocr import __version__ as __PADDLE_VER
    except:
        from paddleocr.paddleocr import VERSION as __PADDLE_VER
        __PADDLE_VER = str(__PADDLE_VER)
    return __PADDLE_VER


def ensure_paddle_gpu():
    global pd_gpu, PADDLE_VER
    if pd_gpu is None:
        PADDLE_VER = get_paddleocr_version()
        pd_gpu = PaddleOCR(lang="ch", use_gpu=True)  # use_angle_cls=True, gpu_mem=1000
        print("Paddleocr version: %s" % (PADDLE_VER))
    return pd_gpu


def recognize(cv_image):
    pd_ocr = ensure_paddle_gpu()
    paddle_result = pd_ocr.ocr(cv_image)
    if PADDLE_VER.startswith("2.7"):
        assert (len(paddle_result) == 1)
        paddle_result = paddle_result[0]
        if paddle_result is None:
            paddle_result = []

    results = []
    for r in paddle_result:
        bounds = get_bounds(r[0])
        text = r[1][0]
        confidence = r[1][1]
        tb = {"bounds": bounds, "text": text, "confidence": confidence}
        results.append(tb)
    return results


def get_cache_path(cache_root, video_path, video_hash, frame_index):
    video_path = os.path.abspath(video_path)
    video_path = video_path.replace("/", "@")
    video_path = video_path.replace("\\", "@")
    video_path = video_path.replace(":", "@")
    fragments = video_path.split('@')[-4:]
    cache_name = "@".join(fragments) + "@" + video_hash + "@" + str(frame_index) + ".json"
    cache_path = os.path.join(cache_root, cache_name)
    return cache_path


def find_ocr_cache(cache_root, video_path, video_hash, frame_index):
    cache_path = get_cache_path(cache_root, video_path, video_hash, frame_index)
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            ocr_cache = json.load(f)
            return ocr_cache
    return None


def flush_ocr_cache(cache_root, video_path, video_hash, frame_index, ocr_data):
    cache_path = get_cache_path(cache_root, video_path, video_hash, frame_index)
    os.makedirs(cache_root, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(ocr_data, f)


def test_ocr():
    path = r"../../frame7.png"
    path = r"../../test.png"
    img = cv2.imread(path)
    ocr_results = recognize(img)
    print(str(ocr_results))
