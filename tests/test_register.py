"""tests/test_register.py —— 對位的真值迴歸測試

`python3 tests/test_register.py`

用 tests/fixtures/scattered 的合成測資（位移已知）量三件事：
  1. 兩兩對位：解對幾對、誤差多少
  2. 全域求解：每片的絕對座標與真值差多少
  3. 誠實度：解不出來的有沒有據實回報，而不是給一個看起來很有信心的錯答案

第 3 項才是重點。對位這種東西，**錯得理直氣壯比明說不知道危險得多** ——
拼歪的圖看起來是完整的，只是尺寸全錯，要量過才發現。
"""

import csv
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
sys.dont_write_bytecode = True

import cv2                                                        # noqa: E402
from perception.s01c_register import (register_pair, solve_global,   # noqa: E402
                                      closure_errors)
import make_scattered                                              # noqa: E402

TOL_PX = 3


def main() -> int:
    fx = make_scattered.build()
    truth = {r["tile_id"]: (int(r["x"]), int(r["y"]))
             for r in csv.DictReader((fx / "ground_truth.csv").open(encoding="utf-8"))}
    gray = {t: cv2.imread(str(fx / f"{t}.png"), cv2.IMREAD_GRAYSCALE) for t in truth}
    tiles = sorted(truth)

    print(f"測資：{len(tiles)} 片，各 {gray[tiles[0]].shape[1]}×{gray[tiles[0]].shape[0]} px\n")
    print(f"{'配對':<11}{'真值 dx,dy':<15}{'解出':<15}{'誤差':<8}{'一致度':<8}"
          f"{'獨特性':<8}{'狀態'}")
    print("─" * 78)

    edges, correct, honest, wrong = [], 0, 0, 0
    for a, b in itertools.combinations(tiles, 2):
        tdx, tdy = truth[b][0] - truth[a][0], truth[b][1] - truth[a][1]
        r = register_pair(gray[a], gray[b])
        r["tile_a"], r["tile_b"] = a, b
        edges.append(r)
        err = ((r["dx"] - tdx) ** 2 + (r["dy"] - tdy) ** 2) ** 0.5
        ok = err <= TOL_PX
        if r["status"] == "ok":
            correct += ok
            wrong += not ok
        else:
            honest += 1
        mark = "✓" if ok else ("· 已回報" if r["status"] != "ok" else "★ 錯而不自知")
        print(f"{a}-{b:<7}({tdx:>5},{tdy:>5})  ({r['dx']:>5},{r['dy']:>5})  {err:>6.1f}  "
              f"{r['agree']:.3f}   {r['distinct']:>6.2f}  {r['status']:<22}{mark}")

    placement, used, unplaced = solve_global(edges, tiles)
    print(f"\n全域求解：用了 {len(used)} 條邊，定位 {len(placement)}/{len(tiles)} 片")
    if unplaced:
        print(f"  無法定位（誠實回報，不猜）：{unplaced}")

    # 真值也平移到左上角原點，才能比
    if placement:
        mx = min(truth[t][0] for t in placement)
        my = min(truth[t][1] for t in placement)
        print(f"\n{'片':<8}{'真值':<16}{'解出':<16}{'誤差 px'}")
        print("─" * 48)
        worst = 0.0
        for t in sorted(placement):
            tx, ty = truth[t][0] - mx, truth[t][1] - my
            px, py = placement[t]
            e = ((px - tx) ** 2 + (py - ty) ** 2) ** 0.5
            worst = max(worst, e)
            print(f"{t:<8}({tx:>5},{ty:>5})  ({px:>5},{py:>5})  {e:>7.1f}"
                  f"{'' if e <= TOL_PX else '   ★'}")
    else:
        worst = float("inf")

    cl = closure_errors(placement, edges)
    if cl:
        print(f"\n回路閉合（多餘的邊拿來驗證，與尺寸鏈閉合同一個道理）："
              f"最大殘差 {max(c[2] for c in cl):.1f} px")

    print(f"\n兩兩對位：{correct} 對正確、{honest} 對據實回報證據不足、"
          f"**{wrong} 對錯而不自知**")
    print(f"全域定位：{len(placement)}/{len(tiles)} 片，最大誤差 {worst:.1f} px")

    fail = []
    if wrong:
        fail.append(f"{wrong} 對給出高信心的錯答案 —— 這比解不出來嚴重")
    if len(placement) < len(tiles):
        fail.append(f"{len(unplaced)} 片無法定位")
    if worst > TOL_PX:
        fail.append(f"全域最大誤差 {worst:.1f} px 超過容差 {TOL_PX} px")
    if fail:
        print("\n✗ " + "；".join(fail))
        return 1
    print("\n✓ 全部片定位正確，且沒有錯而不自知的配對")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
