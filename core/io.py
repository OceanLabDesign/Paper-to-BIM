"""core/io.py —— 讀寫層

規格：裁決 §3（v0.4 §1 補上定義，**不再依賴 v0.3**）
v0.4 §0.2：「讀值一律用 `io.final()`」。
"""


def num(v):
    """把 CSV 欄位轉成數字；空字串／None／轉不動 → None。"""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def final(row: dict):
    """人工修正優先於 AI 判讀。下游一律用這個，不要直接讀 value 欄。

    語意（裁決 §3）：
      verified_value（人在校對介面確認的）優先；沒有才用 value（系統採信的）。
      兩者皆空 → 回 None，代表這個值未定，**不准往下游傳**。

    ⚠ 用 `or` 串接的副作用：verified_value 若真的是 0，會落到 value。
      尺寸讀數不會是 0，實務上無害；哪天有可能為 0 的欄位要走這支，先改成 is None 判斷。
    """
    return num(row.get("verified_value")) or num(row.get("value"))
