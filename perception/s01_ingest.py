"""s01_ingest —— PDF 拆片（免拼接）

規格：v0.4 §8、裁決 §1、§11 第 2 步
輸入：{case}/00_raw/*.pdf
輸出：{case}/01_tiles/*.png（各片**原始解析度、未轉正**）、{case}/01_offsets.csv

要點：**用 PyMuPDF 讀每個影像 XObject 的放置矩陣** —— Illustrator 拼的檔案，
      偏移量就寫在 PDF 裡，**不用重新對位**（規格 §8 原文如此）。

      ⚠ 規格說的是「不用」，不是「不准」。輸入若是沒有放置矩陣的單張影像，
        或多張分次掃描，對位要另尋來源 —— 見 docs/adr/0008-輸入格式.md。

01_offsets.csv 欄位（裁決 §1 定版，正式清單見 core/fields.py）：
    tile_id,page,x,y,w,h,rotation,upright_file
    p01_t01,1,0,0,3507,4960,180,01_tiles_upright/p01_t01.png

**本步 `rotation` 與 `upright_file` 兩欄留空** —— 那是 s01b 的事。

禁：不要在這裡轉正、不要降解析度。01_tiles/ 是可追溯的原始版，永不就地覆蓋。
"""

import csv
from pathlib import Path

from core import case, fields

# rotation 是「影像被轉了幾度，要轉回來」。np.rot90 是逆時針，所以要補回 360-rotation。
# ⚠ 這裡寫錯過一次（270 對到 k=2 ＝ 180°），線段數從 392 變 445 才發現。
ROTATIONS = {0: None, 90: 3, 180: 2, 270: 1}


def run(case_dir: Path, rotation: int = 0) -> int:
    """PDF → 01_tiles/ ＋ 01_tiles_upright/ ＋ 01_offsets.csv。回傳片數。

    用 PyMuPDF 抽出每頁的影像 XObject。**不重新編碼、不降解析度** ——
    抽的是 PDF 裡原本那份位元組。

    rotation：整批旋轉角度（0/90/180/270）。實務上由 s01b 偵測，
    這裡先接受外部給定 —— 79 年案實測整批 270°（影像直式、頁面橫式）。

    ⚠ x/y 留空：這批掃描一頁一張完整 A3、PDF 裡沒有拼版偏移量可讀，
      而且我們不做像素對位（ADR 0009）。整頁座標系並不存在，tile_id 就是座標系。
    """
    import fitz
    import cv2
    import numpy as np

    case_dir = Path(case_dir)
    pdfs = sorted((case_dir / "00_raw").glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"{case_dir}/00_raw/ 沒有 PDF")
    raw_dir = case.dir_path(case_dir, "01_tiles")
    up_dir = case.dir_path(case_dir, "01_tiles_upright")
    raw_dir.mkdir(parents=True, exist_ok=True)
    up_dir.mkdir(parents=True, exist_ok=True)

    k = ROTATIONS.get(rotation)
    rows, n = [], 0
    for pdf in pdfs:
        doc = fitz.open(pdf)
        for i in range(doc.page_count):
            imgs = doc[i].get_images(full=True)
            if not imgs:
                continue
            n += 1
            tid = f"p{n:02d}"
            blob = doc.extract_image(imgs[0][0])
            (raw_dir / f"{tid}.{blob['ext']}").write_bytes(blob["image"])
            arr = cv2.imdecode(np.frombuffer(blob["image"], np.uint8), cv2.IMREAD_GRAYSCALE)
            up = arr if k is None else np.rot90(arr, k).copy()
            cv2.imwrite(str(up_dir / f"{tid}.png"), up)
            rows.append({"tile_id": tid, "page": i + 1, "x": "", "y": "",
                         "w": up.shape[1], "h": up.shape[0], "rotation": rotation,
                         "upright_file": f"01_tiles_upright/{tid}.png"})
    with case.path(case_dir, "offsets").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields.OFFSETS); w.writeheader(); w.writerows(rows)
    return n
