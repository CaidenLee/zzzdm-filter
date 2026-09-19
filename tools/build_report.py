# -*- coding: utf-8 -*-
"""生成 HTML 验收报告：把真实样本判定结果可视化，便于人工确认。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "output" / "real_sample_result.json"
OUT = ROOT / "output" / "验收报告.html"

CSS = """
* { box-sizing: border-box; }
body { font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
       margin: 0; padding: 32px; background: #F7F6F3; color: #2C2C2A;
       font-size: 14px; line-height: 1.6; }
h1 { font-size: 20px; font-weight: 500; margin: 0 0 6px; }
.sub { color: #888780; font-size: 13px; margin-bottom: 24px; }
.stats { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 24px; }
.stat { background: #fff; border-radius: 12px; padding: 14px 20px; min-width: 130px;
        border: 0.5px solid rgba(0,0,0,.1); }
.stat .lbl { font-size: 12px; color: #888780; }
.stat .val { font-size: 24px; font-weight: 500; margin-top: 2px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
.panel { background: #fff; border-radius: 12px; padding: 18px 20px;
         border: 0.5px solid rgba(0,0,0,.1); }
.panel h2 { font-size: 14px; font-weight: 500; margin: 0 0 14px;
            padding-bottom: 10px; border-bottom: 0.5px solid rgba(0,0,0,.1); }
.item { padding: 9px 0; border-bottom: 0.5px solid rgba(0,0,0,.06); }
.item:last-child { border-bottom: none; }
.name { font-size: 13px; margin-bottom: 3px; }
.meta { font-size: 12px; color: #888780; }
.tag { display: inline-block; font-size: 11px; padding: 1px 7px; border-radius: 4px;
       margin-left: 6px; background: #F1EFE8; color: #5F5E5A; }
.drop .name { color: #791F1F; }
.drop .tag { background: #FCEBEB; color: #A32D2D; }
.keep .tag { background: #E1F5EE; color: #0F6E56; }
.bars { margin-bottom: 24px; }
.bar { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; font-size: 12px; }
.bar .cn { width: 90px; color: #5F5E5A; text-align: right; }
.bar .track { flex: 1; background: #F1EFE8; border-radius: 3px; height: 16px; overflow: hidden; }
.bar .fill { height: 100%; background: #E24B4A; border-radius: 3px; }
.bar .num { width: 30px; color: #888780; }
"""


def main() -> None:
    if not DATA.exists():
        raise SystemExit("请先运行 tests/crawl_and_classify.py")
    rows = json.loads(DATA.read_text(encoding="utf-8"))
    keeps = [r for r in rows if r["verdict"] == "KEEP"]
    drops = [r for r in rows if r["verdict"] == "DROP"]

    by_cat: dict[str, int] = {}
    for r in drops:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
    by_cat = dict(sorted(by_cat.items(), key=lambda x: -x[1]))
    mx = max(by_cat.values()) if by_cat else 1

    rate = len(drops) / len(rows) * 100 if rows else 0

    def item(r, cls):
        meta = []
        if r.get("price"):
            meta.append(r["price"])
        if r.get("mall"):
            meta.append(r["mall"])
        if r.get("vote_rate") is not None:
            meta.append(f"值率 {r['vote_rate']}%")
        tag = ""
        if cls == "drop":
            tag = f'<span class="tag">{r["category"]}｜{r["matched"]}</span>'
        elif r.get("kept_by"):
            tag = f'<span class="tag">例外：{r["kept_by"]}</span>'
        m = "  ·  ".join(meta)
        return (f'<div class="item {cls}"><div class="name">{r["title"]}{tag}</div>'
                f'<div class="meta">{m}</div></div>')

    bars = "".join(
        f'<div class="bar"><div class="cn">{cat}</div>'
        f'<div class="track"><div class="fill" style="width:{n/mx*100:.0f}%"></div></div>'
        f'<div class="num">{n}</div></div>'
        for cat, n in by_cat.items()
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>zzzdm 二次蒸馏 · 验收报告</title><style>{CSS}</style></head>
<body>
<h1>zzzdm 二次蒸馏 · 验收报告</h1>
<div class="sub">真实样本 {len(rows)} 条，抓取自 https://t.me/s/zzzdm （2026-09-19）</div>

<div class="stats">
  <div class="stat"><div class="lbl">样本总数</div><div class="val">{len(rows)}</div></div>
  <div class="stat"><div class="lbl">保留（推送给你）</div><div class="val" style="color:#0F6E56">{len(keeps)}</div></div>
  <div class="stat"><div class="lbl">剔除</div><div class="val" style="color:#A32D2D">{len(drops)}</div></div>
  <div class="stat"><div class="lbl">剔除率</div><div class="val">{rate:.0f}%</div></div>
</div>

<div class="panel" style="margin-bottom:20px">
  <h2>剔除品类分布</h2>
  <div class="bars">{bars}</div>
</div>

<div class="grid">
  <div class="panel">
    <h2>保留 · 将推送给你（{len(keeps)} 条）</h2>
    {"".join(item(r, "keep") for r in keeps)}
  </div>
  <div class="panel">
    <h2>剔除 · 已过滤（{len(drops)} 条）</h2>
    {"".join(item(r, "drop") for r in drops)}
  </div>
</div>
</body></html>"""

    OUT.write_text(html, encoding="utf-8")
    print(f"已生成 {OUT}")


if __name__ == "__main__":
    main()
