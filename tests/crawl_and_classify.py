# -*- coding: utf-8 -*-
"""多页抓取源频道 + 跑过滤，输出判定结果供人工验收。

TG 域名在国内需走代理，脚本默认尝试系统代理 127.0.0.1:7890。
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from classifier import Classifier  # noqa: E402
from parser import parse  # noqa: E402

CHANNEL = "zzzdm"
PROXIES = [None, "http://127.0.0.1:7890", "http://127.0.0.1:7897", "http://127.0.0.1:10809"]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def fetch(url: str, timeout: int = 25) -> str | None:
    for proxy in PROXIES:
        handlers = []
        handlers.append(urllib.request.ProxyHandler(
            {} if proxy is None else {"http": proxy, "https": proxy}))
        opener = urllib.request.build_opener(*handlers)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return opener.open(req, timeout=timeout).read().decode("utf-8", "ignore")
        except Exception:
            continue
    return None


def crawl(pages: int = 4) -> list:
    """翻页抓取历史帖。

    分页要点：t.me/s/<ch> 的 before 参数需传**纯数字消息 ID**，
    传 "zzzdm/379690" 这种带频道前缀的形式会被忽略，导致反复返回同一页。
    """
    seen: dict[str, object] = {}
    before: str | None = None
    for i in range(pages):
        url = f"https://t.me/s/{CHANNEL}"
        if before:
            url += f"?before={before}"
        html_text = fetch(url)
        if not html_text:
            print(f"  第 {i+1} 页抓取失败")
            break
        ps = parse(html_text)
        if not ps:
            print(f"  第 {i+1} 页无帖子")
            break
        new = 0
        for p in ps:
            if p.post_id not in seen:
                seen[p.post_id] = p
                new += 1
        print(f"  第 {i+1} 页：解析 {len(ps)} 条，新增 {new} 条")
        if new == 0:
            break
        # before 只取数字部分
        before = ps[0].post_id.split("/")[-1]
        time.sleep(1.0)
    return list(seen.values())


def main() -> None:
    print("抓取源频道历史帖…")
    posts = crawl(pages=4)
    print(f"合计 {len(posts)} 条\n")
    if not posts:
        sys.exit("未抓到数据")

    clf = Classifier()
    detail = []
    for p in posts:
        v = clf.classify(p.title, p.body)
        detail.append({
            "post_id": p.post_id,
            "title": p.title,
            "verdict": "DROP" if v.drop else "KEEP",
            "category": v.category,
            "matched": v.matched,
            "kept_by": v.kept_by,
            "price": p.price,
            "mall": p.mall,
            "vote_rate": p.vote_rate,
            "link": p.link,
            "buy": p.buy_url,
        })

    drops = [d for d in detail if d["verdict"] == "DROP"]
    keeps = [d for d in detail if d["verdict"] == "KEEP"]
    by_cat: dict[str, int] = {}
    for d in drops:
        by_cat[d["category"]] = by_cat.get(d["category"], 0) + 1

    lines = ["=" * 78,
             f"zzzdm 二次蒸馏 · 真实样本判定结果（{len(detail)} 条）",
             "=" * 78, ""]
    lines.append(f"保留 {len(keeps)} 条 / 剔除 {len(drops)} 条    "
                 f"（信噪比提升：{len(detail)}→{len(keeps)}，"
                 f"剔除率 {len(drops)/len(detail)*100:.0f}%）")
    lines.append("")
    lines.append("剔除分布：")
    for cat, n in sorted(by_cat.items(), key=lambda x: -x[1]):
        lines.append(f"    {cat:<14} {n:>3} 条")
    lines.append("")
    lines.append("-" * 78)
    lines.append("【保留（将推送给你的）】")
    lines.append("-" * 78)
    for d in keeps:
        tag = f"  [{d['kept_by']}]" if d["kept_by"] else ""
        lines.append(f"  · {d['title'][:62]}{tag}")
    lines.append("")
    lines.append("-" * 78)
    lines.append("【剔除】")
    lines.append("-" * 78)
    for d in drops:
        lines.append(f"  ✗ {d['title'][:56]:<56} ← {d['category']}｜{d['matched']}")

    text = "\n".join(lines)
    out = ROOT / "output" / "real_sample_result.txt"
    out.write_text(text, encoding="utf-8")
    print(text)

    (ROOT / "output" / "real_sample_result.json").write_text(
        json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
