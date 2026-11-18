"""產生「示範用」假資料（非真實行情），只用來預覽網頁版面。真實資料請跑 update_data.py。"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
cfg = json.loads((ROOT / "constituents.json").read_text(encoding="utf-8"))
rng = np.random.default_rng(7)
dates = pd.bdate_range(end="2026-11-17", periods=64)

groups = []
for key in ("SOX", "NDX"):
    g = cfg[key]
    vol = 1.8 if key == "SOX" else 1.1
    ir = rng.normal(0.08, vol, len(dates))
    iclose = 1000 * np.cumprod(1 + ir / 100)
    stocks = {}
    for t, name in g["stocks"].items():
        beta = rng.uniform(0.7, 1.6)
        drift = rng.normal(0, 0.15)
        r = beta * ir + drift + rng.normal(0, 1.6, len(dates))
        stocks[t] = {"name": name or t,
                     "close": [round(v, 2) for v in 100 * np.cumprod(1 + r / 100)],
                     "chg": [round(v, 2) for v in r]}
    groups.append({"key": key, "name": g["name"], "index": g["index"],
                   "dates": [d.strftime("%Y-%m-%d") for d in dates],
                   "indexClose": [round(v, 2) for v in iclose],
                   "indexChg": [round(v, 2) for v in ir], "stocks": stocks})

data = {"generated": "2026-11-18T00:00:00Z", "months": 3, "sample": True, "groups": groups}
js = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs" / "data.js").write_text("window.RS_DATA=" + js + ";", encoding="utf-8")
(ROOT / "docs" / "data.json").write_text(js, encoding="utf-8")
print("sample data written")
