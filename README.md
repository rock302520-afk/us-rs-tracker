# 每日美股強弱股（SOX・NDX 成分股 vs 指數）

每天美股收盤後自動抓資料，比較費城半導體指數（^SOX）、納斯達克100（^NDX）成分股與指數的當日漲跌幅，
分出強勢 / 弱勢股，並用網頁呈現排行與曲線圖。

**判斷規則**：強弱差 = 個股當日漲跌% − 指數當日漲跌%。> 0 強勢、< 0 弱勢。
例：2026/11/17 MRVL +2.33%、SOX +0.34% → 強弱差 +1.99 → 強勢。

## 網頁功能
- 費半 / 那指 切換，可選 3 個月內任一交易日回看
- 依強弱差由強到弱排序（也可改用近5日、近20日、3個月相對強度排序；點表頭可正反排序）
- 強勢 / 弱勢篩選、代號或中文名稱搜尋
- 每檔：近5日強弱燈號、20日與3個月相對強度、3個月相對強度走勢小圖
- 點個股：累積漲跌幅 vs 指數曲線、每日強弱差柱狀圖（紅＝強、綠＝弱）
- 每日強勢股比例曲線（點圖可直接切換日期）
- 手機、深色模式都可用

## 檔案
| 檔案 | 用途 |
|---|---|
| `update_data.py` | 從 Yahoo Finance 抓 3 個月收盤價、計算、輸出 `docs/data.json` 與 `docs/data.js` |
| `constituents.json` | 成分股清單與中文名稱（SOX 依 Nasdaq 2026/11/02 權重檔；NDX 每次執行會先嘗試從維基百科自動更新） |
| `docs/index.html` | 儀表板網頁（純 HTML/JS，無外部套件） |
| `.github/workflows/update.yml` | GitHub Actions：每週一～五 22:30 UTC（台灣 06:30）自動更新並推送 |
| `make_sample_data.py` | 產生示範假資料，只用來預覽版面 |

## 方式 A：放上 GitHub，每天自動更新（推薦）
1. 在 GitHub 建一個新 repository（可設 Private，但 Pages 免費版需 Public），把整個資料夾內容上傳。
2. 第一次先手動跑一次：repo → **Actions** → 「每日更新美股強弱資料」→ **Run workflow**。
3. 開啟網頁：repo → **Settings → Pages** → Source 選 **Deploy from a branch**，Branch 選 `main`、資料夾選 `/docs` → Save。
   約 1 分鐘後網址會出現在同一頁（`https://<帳號>.github.io/<repo名>/`），手機加到主畫面即可。
4. 之後每個交易日台灣早上 06:30 左右會自動更新（GitHub 排程偶爾延遲 5～30 分鐘屬正常）。

## 方式 B：在自己電腦跑
```bash
pip install -r requirements.txt
python update_data.py          # 約 1 分鐘
# 直接雙擊 docs/index.html 開啟
```
Windows 可用「工作排程器」、Mac 用 `crontab` 每天早上 6:30 執行 `python update_data.py`。

## 維護
- SOX 成分股每季可能調整：更新 `constituents.json` 的 `SOX` 區塊即可（Nasdaq 官方權重檔：nasdaq.com/docs/global-indexes/SOX）。
- 想看更長區間：`python update_data.py --months 6`（workflow 裡同樣加參數）。
- 價格用 Yahoo Finance 收盤價（已調整分割、未調整股息），漲跌幅會和看盤軟體一致。
- 想核對某天的原始資料：`python update_data.py --check MRVL 2026-11-17`，會印出個股與指數前後幾天的收盤價、漲跌%與強弱差算式。
