"""execution/exporters/base.py —— 匯出器介面

s07_execute 只認這個介面。**每個匯出器都只讀 plan，不讀任何 03/04 檔**
（§8 腦手分離鐵則）—— 加新匯出器不會鬆動這條。

存取方式（`needs`）—— 這比「有沒有 API token」更貼近實情：
    file        純檔案輸出，不需要任何外部程式。DXF、3DM、IFC 屬此類。
    live_app    需要目標軟體正在本機執行，透過它的腳本介面下指令。
                ArchiCAD 的 JSON/Python 介面、Revit 的 pyRevit、
                VisualARQ（Rhino 外掛）都屬此類。**不需要 token，需要授權與安裝。**
    cloud_token 需要雲端服務憑證。目前只有 Autodesk Platform Services 屬此類。

`gated` = True 代表規格明令現在不准做（§12），registry 會擋下來。
"""

NEEDS = ("file", "live_app", "cloud_token")


class Exporter:
    name = "base"
    ext = ""
    needs = "file"
    gated = False           # True 代表 §12 明令現在不准做
    gate_reason = ""

    def export(self, plan: dict, out_dir) -> list:
        """把 plan 落地，回傳產出的檔案路徑 list。

        紀律（§8、裁決 §6）：
          - **只讀 plan**，不讀 03/04
          - 同一份 plan 跑兩次要得到同一份輸出（確定性，不准有隨機、不准有 LLM）
          - plan 裡由 core.config.ASSUMED 導出的值（thickness_src == "assumed"）
            → 檔名帶 core.config.DRAFT_SUFFIX
        """
        raise NotImplementedError(f"{type(self).__name__}.export 未實作")

    def available(self) -> tuple:
        """回傳 (可用嗎, 說明)。給 registry 在選之前先問，不要等到 export 才炸。"""
        return (False, f"{self.name} 尚未實作")
