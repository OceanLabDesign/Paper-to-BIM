# 案件資料夾範本

複製這個資料夾並改名為 `<案號>_<地段>`，例如 `68-01782_某某街`（案號＋地段）。
結構定義在 `docs/程式設計_v0.4.md` §3，路徑常數在 `core/case.py`
（`core.case.ensure_case(case_dir)` 可直接建出這個骨架）。

| 資料夾 | 誰寫 | 內容 |
|---|---|---|
| `00_raw/` | 人 | 原始掃描 PDF（唯讀，不要就地修改） |
| `01_tiles/` | s01_ingest | 拆出的片，**原始解析度、未轉正**，可追溯用 |
| `01_tiles_upright/` | s01b_orient | 轉正後的片 —— **s02 以後一律吃這個** |
| `01_rectified/` | s01b_orient | 轉正後整頁，僅供人看；程式吃 tiles＋offsets |
| `04_crops/` | s04_read | 讀數用的局部截圖 |
| `plans/` | 中樞 | 思考史：`plan_vN.yaml` / `residuals_vN.csv` |
| `out/` | s07_execute | DXF 輸出；由 ASSUMED 導出的值檔名帶 `_draft` |

同層的 CSV（`01_offsets` / `02_sheets` / … / `08_conflicts` / `log`）不在此列，
檔名一律引 `core/case.py` 的 `FILES`，不要自行拼字串。

**案件資料不進版控**（見根目錄 `.gitignore`）：`00_raw` 可能含個資與著作權，
其餘都能從 `00_raw` 重生。只有各資料夾的 `.gitkeep` 與本檔會進 git。
