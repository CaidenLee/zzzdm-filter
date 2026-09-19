# -*- coding: utf-8 -*-
"""zzzdm 二次蒸馏 · 主服务

职责：轮询源频道 → 过滤掉不喜欢的品类 → Bot 推送精简卡片到私聊。

设计要点：
- 纯标准库，零第三方依赖，可直接扔到任意免费云函数/小机器上跑。
- 状态用本地 JSON 文件去重，重启不重复推送。
- 本机不参与运行，只在部署时用一次。

部署形态建议（按省事程度排序）：
  1. 免费云函数 + 定时触发器（如腾讯云 SCF、阿里云 FC，最低几分钟一次）
  2. 任意 1 核小服务器 systemd 常驻
  3. GitHub Actions 定时任务（完全免费，最省事，缺点是最小间隔 5 分钟）
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from classifier import Classifier  # noqa: E402
from notifier import get_me, get_updates, send_post  # noqa: E402
from parser import parse  # noqa: E402

CHANNEL = os.environ.get("SRC_CHANNEL", "zzzdm")
PROXIES = [None, "http://127.0.0.1:7890", "http://127.0.0.1:7897",
           "http://127.0.0.1:10809"]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

STATE_PATH = ROOT / "output" / "state.json"
CONFIG_PATH = ROOT / "config.json"


# ---------------------------------------------------------------------------
# 配置 / 状态
# ---------------------------------------------------------------------------

def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {
        "bot_token": os.environ.get("TG_BOT_TOKEN", ""),
        "chat_id": os.environ.get("TG_CHAT_ID", ""),
        "proxy": os.environ.get("TG_PROXY", ""),
        "max_push_per_run": 20,
        "dry_run": False,
    }


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"pushed": [], "last_post_id": None}


def save_state(state: dict) -> None:
    state["pushed"] = state["pushed"][-800:]
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                          encoding="utf-8")


# ---------------------------------------------------------------------------
# 抓取
# ---------------------------------------------------------------------------

def fetch(url: str, proxy: str | None, timeout: int = 25) -> str | None:
    import urllib.request
    chain = [proxy] if proxy else []
    chain += [p for p in PROXIES if p and p != proxy]
    chain.append(None)          # 最后兜底：完全直连
    errors: list[str] = []
    for px in chain:
        label = px or "直连"
        try:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler(
                    {} if not px else {"http": px, "https": px}))
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            resp = opener.open(req, timeout=timeout)
            body = resp.read().decode("utf-8", "ignore")
            if "tgme_widget_message" not in body:
                errors.append(f"{label}: 页面无消息结构（len={len(body)}）")
                continue
            return body
        except Exception as e:
            errors.append(f"{label}: {type(e).__name__} {str(e)[:80]}")
            continue
    # 全部通道失败：打印出来，否则云端日志只有「抓到 0 条」无从排查
    print("  fetch 全部通道失败：")
    for e in errors:
        print(f"    - {e}")
    return None


def fetch_latest(proxy: str | None, pages: int = 1) -> list:
    """抓最近若干页帖子（默认 1 页约 20 条，足够覆盖两次轮询间隔）。"""
    seen: dict[str, object] = {}
    before: str | None = None
    for i in range(pages):
        url = f"https://t.me/s/{CHANNEL}"
        if before:
            url += f"?before={before}"
        html_text = fetch(url, proxy)
        if not html_text:
            break
        ps = parse(html_text)
        if not ps:
            break
        for p in ps:
            seen.setdefault(p.post_id, p)
        before = ps[0].post_id.split("/")[-1]
        time.sleep(0.6)
    return list(seen.values())


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_once(config: dict, state: dict, verbose: bool = True) -> dict:
    clf = Classifier()
    proxy = config.get("proxy") or None
    token = config.get("bot_token", "")
    chat_id = config.get("chat_id", "")
    dry = config.get("dry_run", False)
    cap = int(config.get("max_push_per_run", 20))

    posts = fetch_latest(proxy, pages=config.get("pages", 1))
    if verbose:
        print(f"抓到 {len(posts)} 条帖子")
    if not posts:
        # 抓取完全失败（网络问题或频道页面结构变化），必须显式报错，
        # 否则云端会「成功」地什么都不做，问题被静默吞掉。
        raise RuntimeError("抓取失败：未取到任何帖子，请检查网络通道或页面结构")

    pushed = set(state.get("pushed", []))
    new_kept, new_dropped = [], []

    for p in sorted(posts, key=lambda x: int(x.post_id.split("/")[-1])):
        if p.post_id in pushed:
            continue
        v = clf.classify(p.title, p.body, p.price)
        if v.drop:
            new_dropped.append((p, v))
            pushed.add(p.post_id)      # 被剔除的立即记账，无需重试
        else:
            new_kept.append((p, v))

    if verbose:
        print(f"新增：保留 {len(new_kept)} 条，剔除 {len(new_dropped)} 条")
        for p, v in new_dropped:
            print(f"    ✗ {p.title[:44]} ← {v.category}｜{v.matched}")

    sent = 0
    if not dry and token and chat_id:
        for p, v in new_kept[:cap]:
            ok = send_post(token, chat_id, p,
                           proxy=proxy if proxy else None,
                           with_photo=config.get("with_photo", True))
            if ok:
                # 关键：只有发送成功才记账。否则被限流截断的帖子会永久丢失
                pushed.add(p.post_id)
                sent += 1
            else:
                print(f"    推送失败，下轮重试：{p.title[:40]}")
            time.sleep(1.5)
    elif verbose:
        if dry:
            print("[dry_run] 未实际发送。示例内容：")
            if new_kept:
                from notifier import build_caption
                print(build_caption(new_kept[0][0])[:400])
        elif not token or not chat_id:
            print("缺少 bot_token 或 chat_id，跳过推送")

    state["pushed"] = list(pushed)
    if posts:
        state["last_post_id"] = max(
            (p.post_id for p in posts), key=lambda x: int(x.split("/")[-1]))
    save_state(state)

    return {"fetched": len(posts), "new_kept": len(new_kept),
            "new_dropped": len(new_dropped), "sent": sent}


def main() -> None:
    loop = os.environ.get("LOOP", "").lower() in ("1", "true", "yes")
    interval = int(os.environ.get("INTERVAL", "300"))
    config = load_config()
    state = load_state()

    if not loop:
        try:
            r = run_once(config, state)
        except RuntimeError as e:
            print(f"运行失败：{e}")
            sys.exit(1)
        print(json.dumps(r, ensure_ascii=False))
        return

    print(f"进入常驻模式，每 {interval}s 轮询一次（Ctrl+C 退出）")
    while True:
        try:
            r = run_once(config, state)
            print(f"[{time.strftime('%H:%M:%S')}] "
                  f"抓 {r['fetched']} / 推 {r['sent']} / 剔 {r['new_dropped']}")
        except KeyboardInterrupt:
            print("已退出")
            break
        except Exception as e:
            print(f"轮询异常：{type(e).__name__} {str(e)[:200]}")
        time.sleep(interval)


if __name__ == "__main__":
    main()
