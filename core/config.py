"""core/config.py —— 實測校準參數

規格：v0.4 §10。**這組數字是 68 年案實測驗證通過的**，
不要「順手優化」、不要換演算法、不要重新調參。要改先拿新的實測結果來。
"""

UNIT = "cm"                 # 標題欄實證：單位 C.M
SCALE = 100                 # 1:100
DPI = 300                   # 存量掃描實測
PX_PER_CM = DPI / 2.54 / SCALE      # ≈ 1.181 px/實際cm
# 換算範例：牆 24cm ≈ 28px、總寬 806cm ≈ 952px（與實測相符）

ADAPTIVE_BLOCK, ADAPTIVE_C = 31, 12  # 曬圖陰影下存活的那組
HOUGH_THRESHOLD, MIN_LINE_LENGTH, MAX_LINE_GAP = 60, 60, 6
WALL_GAP_PX = (12, 42)              # RC15cm≈18px ~ 磚24cm≈28px 外加餘裕
# 裁決 §6：暫用值，讓程式跑得動。68 年案 **A-2 頁本身就有四個立面圖和側面圖**，
# 上面有標高 —— 量一次就有這件案的真實層高，不必靠預設值。
ASSUMED = {
    "層高cm_1F": 400,    # 店鋪常挑高
    "層高cm_其他": 320,
    "牆厚cm_外": 24,      # 1B 磚牆
    "牆厚cm_內": 12,      # 1/2B
    "板厚cm": 15,
}
# ⚠ 所有由 ASSUMED 導出的值：thickness_src 一律填 "assumed"、信心 ≤ 0.4、
#   輸出檔名帶 _draft。**粗胚 BIM 被誤當精確模型是 v0.3 風險表上的中度風險。**
ASSUMED_SRC = "assumed"
ASSUMED_MAX_CONF = 0.4
DRAFT_SUFFIX = "_draft"
MAX_ITER = 3
