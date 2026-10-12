# AIGC X Radar (Demo)
追踪 X 上 AIGC 短片/图像趋势的静态站点。直接双击 `index.html` 即可本地打开。

## 文件
- `index.html` / `assets/style.css` / `assets/app.js` — 页面
- `data.json`（`data.js` 同内容，供 file:// 加载）— 当前数据
- `raw.json` — 抓取原始数据（含引用链）
- `update.py` — 每日更新脚本

## 每日更新
```bash
export X_BEARER_TOKEN=你的_X_API_Bearer_Token   # 必需
export X_API_ENDPOINT=https://api.x.com/2/tweets/search/recent  # 可选；默认 /2/tweets/search/all（需 Pro/学术权限）
export RADAR_DAYS=21   # 可选，检索时间窗（recent 端点最多 7 天）
python3 update.py
# 离线重建: python3 update.py --from-raw raw.json
```
cron 示例（每天 09:00 北京时间）：`0 9 * * * cd /path/aigc-x-radar && X_BEARER_TOKEN=... python3 update.py`

仅依赖 Python 3.9+ 标准库。只追踪内容（作品/梗/连载），不追踪模型。聚类为「一部作品或一种梗格式」的关键词规则（见 `CLUSTERS`，含爆款拆解文案），新梗需手动增补规则；脚本会对热度最高的原帖调用 `/2/tweets/:id/quote_tweets` 拉取真实引用链。
