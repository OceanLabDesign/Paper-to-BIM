"""perception/detectors/yolo.py —— YOLO 偵測器（空殼）

§12 明令：**現在不要做 YOLO**，等存量配對盤點的數字（§11 建造順序也沒有這一步）。
裁決 §2 再次確認：第一版偵測器是 detectors/rule.py，這支才是空殼佔位。

不要因為「規則式準確率不夠」就提前開這支 —— 那是要拿盤點數字去換的決定，不是實作決定。
"""

DETECTOR_ID = "yolo_v1"


def detect(images) -> list:
    raise NotImplementedError("YOLO 偵測器不在現階段範圍（§12）")
