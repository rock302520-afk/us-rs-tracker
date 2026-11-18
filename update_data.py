"""
每日美股強弱股 — 資料更新程式

抓取 費城半導體指數(^SOX)、納斯達克100(^NDX) 與其成分股近 3 個月的日收盤價，
計算每檔股票「當日漲跌幅 − 指數漲跌幅」(強弱差，百分點)，
強弱差 > 0 為強勢股、< 0 為弱勢股，輸出給網頁使用：
    docs/data.json   (純資料)
    docs/data.js     (window.RS_DATA = ...，讓 index.html 直接雙擊開啟也能用)

用法：
    pip install -r requirements.txt
    python update_data.py            # 預設 3 個月
    python update_data.py --months 6
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "docs"
CONSTITUENTS = ROOT / "constituents.json"


def refresh_ndx_list(fallback: dict[str, str]) -> dict[str, str]:
    """嘗試從維基百科抓最新 Nasdaq-100 成分股；失敗就沿用 constituents.json。"""
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100", attrs={"id": "constituents"})
        df = tables[0]
        tcol = next(c for c in df.columns if str(c).lower() in ("ticker", "symbol"))
        ncol = next(c for c in df.columns if "company" in str(c).lower())
        fresh = {}
        for t, n in zip(df[tcol], df[ncol]):
            t = str(t).strip().replace(".", "-")
            fresh[t] = fallback.get(t) or str(n).strip()
        if len(fresh) >= 90:
            print(f"[NDX] 已從維基百科更新成分股：{len(fresh)} 檔")
            return fresh
    except Exception as e:  # noqa: BLE001
        print(f"[NDX] 自動抓成分股失敗，使用 constituents.json：{e}")
    return fallback


def download_closes(tickers: list[str], months: int) -> pd.DataFrame:
    # 多抓 15 天，確保第一天也算得出漲跌幅
    period_days = months * 31 + 15
    df = yf.download(
        tickers,
        period=f"{period_days}d",
        interval="1d",
        auto_adjust=False,   # 用 Yahoo 的 Close（已調整分割、未調整股息）= 看盤軟體顯示的收盤價
        progress=False,
        group_by="column",
        threads=True,
    )
    closes = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df[["Close"]].rename(columns={"Close": tickers[0]})
    closes.index = pd.to_datetime(closes.index).tz_localize(None)
    return closes.sort_index()


def r2(x) -> float | None:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return round(float(x), 2)


def build_group(key: str, cfg: dict, months: int) -> dict:
    stocks: dict[str, str] = cfg["stocks"]
    idx = cfg["index"]
    tickers = [idx] + list(stocks)
    closes = download_closes(tickers, months)

    # 只保留指數有開盤的日子
    closes = closes[closes[idx].notna()]
    chg = closes.pct_change(fill_method=None) * 100

    start = closes.index.max() - pd.DateOffset(months=months)
    keep = closes.index >= start
    closes, chg = closes[keep], chg[keep]

    out = {
        "key": key,
        "name": cfg["name"],
        "index": idx,
        "dates": [d.strftime("%Y-%m-%d") for d in closes.index],
        "indexClose": [r2(v) for v in closes[idx]],
        "indexChg": [r2(v) for v in chg[idx]],
        "stocks": {},
    }
    missing = []
    for t, name in stocks.items():
        if t not in closes.columns or closes[t].notna().sum() < 2:
            missing.append(t)
            continue
        out["stocks"][t] = {
            "name": name or t,
            "close": [r2(v) for v in closes[t]],
            "chg": [r2(v) for v in chg[t]],
        }
    if missing:
        print(f"[{key}] 無資料、已略過：{', '.join(missing)}")
    print(f"[{key}] {len(out['stocks'])} 檔，{out['dates'][0]} ~ {out['dates'][-1]}")
    return out


def check(ticker: str, date: str) -> int:
    """印出個股與所屬指數在指定日附近的原始收盤價，方便和看盤軟體逐筆比對。"""
    cfg = json.loads(CONSTITUENTS.read_text(encoding="utf-8"))
    idxs = [cfg[k]["index"] for k in ("SOX", "NDX") if ticker in cfg[k]["stocks"]] or ["^SOX", "^NDX"]
    closes = download_closes([ticker] + idxs, 1)
    chg = closes.pct_change(fill_method=None) * 100
    d = pd.Timestamp(date)
    win = closes.loc[d - pd.Timedelta(days=7): d + pd.Timedelta(days=1)]
    print(f"\n原始收盤價（Yahoo Finance）：")
    print(pd.concat({"收盤": win, "漲跌%": chg.loc[win.index].round(2)}, axis=1).to_string())
    if d in chg.index:
        for ix in idxs:
            print(f"\n{date} 強弱差 {ticker} − {ix} = {chg.at[d, ticker]:.2f} − {chg.at[d, ix]:.2f} = {chg.at[d, ticker]-chg.at[d, ix]:+.2f}")
    else:
        print(f"\n{date} 不是交易日或尚無資料")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=3)
    ap.add_argument("--no-refresh", action="store_true", help="不自動更新 NDX 成分股")
    ap.add_argument("--check", nargs=2, metavar=("TICKER", "DATE"),
                    help="只核對原始資料，例：--check MRVL 2026-11-17")
    args = ap.parse_args()

    if args.check:
        return check(args.check[0].upper(), args.check[1])

    cfg = json.loads(CONSTITUENTS.read_text(encoding="utf-8"))
    if not args.no_refresh:
        cfg["NDX"]["stocks"] = refresh_ndx_list(cfg["NDX"]["stocks"])

    data = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "months": args.months,
        "sample": False,
        "groups": [build_group(k, cfg[k], args.months) for k in ("SOX", "NDX")],
    }

    OUT_DIR.mkdir(exist_ok=True)
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    (OUT_DIR / "data.json").write_text(js, encoding="utf-8")
    (OUT_DIR / "data.js").write_text("window.RS_DATA=" + js + ";", encoding="utf-8")
    print(f"已輸出 {OUT_DIR/'data.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
