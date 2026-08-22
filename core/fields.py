"""core/fields.py —— 各 CSV 欄位清單

★ 契約三件套之一。v0.4 §4 明定：**Louis 親手寫，Claude Code 只能引用**。
   §11 建造順序第 1 步 —— 尚未完成，本檔目前刻意留空。

本檔需要涵蓋（v0.4 §4 以 v0.3 為基礎，加上 §9 富標籤欄）：

  01_offsets / 02_sheets / 02_exclude / 02_quality
  03_lines / 03_texts / 03_detections / 03_elements
  04_readings / 05_chains / 05_chain_members
  06_verified / 07_walls / 07_columns / 08_conflicts / log

  §9 富標籤新增欄（03_detections、03_elements）：
      conf, evidence, provenance, quality_zone, status
      status ∈ {proposed, adopted, rejected, uncertain}

  幾何欄一律用 WKT（v0.3 原則）。

已由裁決定版、可直接抄進本檔的三份欄位清單（見 docs/程式設計_v0.4.md §1、§3、§5）：

  01_offsets.csv   tile_id,page,x,y,w,h,rotation,upright_file
  04_readings.csv  id,sheet_id,kind,value,unit,conf,status,
                   src_paddle,src_vlm,src_geom,
                   bbox_x,bbox_y,bbox_w,bbox_h,crop,
                   verified_value,verified_by,verified_at,note
  08_conflicts.csv conflict_id,source,kind,severity,sheet_id,description,
                   involved_ids,suggested_fix,resolved,resolved_by

  另：03_texts 需要 region 欄（body/title_block/schedule）、
      03_detections 需要 detector 欄（rule_v1）、
      07_* 的 thickness_src 欄（assumed 時信心 ≤ 0.4）。

匯入本模組的程式會因為找不到符號而 ImportError —— 那是預期行為，
代表建造順序第 1 步還沒做完，不要用 getattr/預設值繞過去。
"""
