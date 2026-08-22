"""IFC 匯出器 —— 目前被 §12 擋著，但那個閘門有問題（見下）

IfcOpenShell 純 Python，**needs=file**：不需要目標軟體、不需要授權、不需要網路、
不需要 token。**全清單裡唯一「token 與執行中軟體兩者皆免、又能產原生參數化物件」
的路徑**，也是唯一能在 macOS 上端到端開發並驗收的一條（用免費的 Bonsai / Blender）。

為什麼我們的資料剛好適合 IFC：手上只有「軸線＋厚度」，正好對應
IfcExtrudedAreaSolid —— IFC 裡支援度最好、最沒爭議的表示法。沒有曲面、沒有複雜
boolean，天生避開 IFC 互通性所有著名的地雷。而 extrusion 恰好是 ArchiCAD 判定
「要不要給原生牆」的那條線（非 extruded 的 BREP 會降級成 Object 或 Morph）。

⚠ **IFC 打不進 Revit**（開源碼等級的證據）：Autodesk/revit-ifc 全 repo 沒有任何一處
  Wall.Create、沒有 IFCWall.cs，importer 只建 DirectShape / DirectShapeType /
  Level / Grid。Revit 原廠 Open IFC 不會產生原生 Revit Wall（Level 倒是真的會）。
  Graphisoft 那個免費 Add-In 會不會，只能實測。

## 實作時照抄範例會中的坑

1. **不要用 `create_2pt_wall`** —— 它沒有 offset 參數，把 p1→p2 當牆的**側邊線**，
   而我們的 axis_wkt 是**牆心線**（§11 第 3 步「牆心線壓真牆」）。
   要用 `geometry.add_wall_representation(..., offset=-thickness/2)`。
2. `create_2pt_wall` **不會**幫你 `assign_representation`。忘了補的話
   `wall.Representation` 是 None、牆在任何檢視器裡都不存在，**而且 validate() 不報錯**。
3. numpy 算出來的值要包 `float()` —— 傳 np.float64 進去會在 IFC4 炸掉，
   錯誤訊息提 IfcCartesianPointList2D、完全沒提 numpy，而 IFC2X3 走 IfcPolyline
   不會遇到，於是「2x3 好好的、換 IFC4 就爆」會讓人找錯方向。
4. IFC2X3 **強制要 OwnerHistory**，第一個 create_entity 就會丟
   `Please create a user to continue`。
5. **clippings / booleans 一律留空** —— 一旦傳了，RepresentationType 會從
   'SweptSolid' 變成 'Clipping' + IfcBooleanClippingResult，ArchiCAD 會不會照樣轉
   原生牆沒有文件、沒有把握。開口只走 IfcOpeningElement + IfcRelVoidsElement。
6. GlobalId 從 judgment id 決定性導出，否則兩次產出無法逐筆對照（見 base.py 的確定性）。

## 使用者端有一件我們控制不了的事

ArchiCAD 匯入 Translator 的 Geometry Conversion 必須設成
「Construction elements, otherwise Objects」（或 …otherwise Morphs），且要用
Open 或 Merge、**不要用 Hotlink**（熱連結不可就地編輯）。
這是使用者端設定，檔案裡強迫不了 —— export() 應一併吐出這行提示。

## ⚠ thickness_src == "assumed" 時特別要緊

DXF 是線段，沒人會誤會；**IFC 長得像真 BIM，匯進 ArchiCAD 就是可編輯的真牆** ——
這正好把 v0.3 風險表上「粗胚 BIM 被誤當精確模型」的中度風險兌現。
層高目前一律來自 ASSUMED，所以在 level_line / level_text 能用之前**每一份 IFC 都該帶
`_draft`**，並建議把「層高為假設值、信心 ≤ 0.4」同時寫進 IfcProject 的 Description
或一個 Pset，讓資訊跟著檔案走、不依賴檔名。
"""

from execution.exporters.base import Exporter


class Ifc(Exporter):
    name = "ifc"
    ext = ".ifc"
    needs = "file"
    native_objects = True
    notes = ("唯一 token 免、執行中軟體也免、又能產原生物件的路徑；"
             "但打不進 Revit（原廠 importer 只建 DirectShape）")
    gated = True
    gate_reason = ("§12：等 ArchiCAD 四道牆往返測試通過才實作（§11 第 8 步）。"
                   "⚠ 這個閘門本身有問題 —— ArchiCAD 沒有第二條吃原生牆的路，"
                   "DXF 進去只是線段、往返回來還是線段，驗不到任何跟原生牆有關的事，"
                   "閘門和被擋的東西是同一件事。見 待決事項.md，等負責人裁決。")

    def export(self, plan, out_dir) -> list:
        raise NotImplementedError("IFC 匯出未實作（§12 擋著）")
