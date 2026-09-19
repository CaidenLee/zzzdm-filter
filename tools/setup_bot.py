# -*- coding: utf-8 -*-
"""首次配置助手：验证 Bot Token 并自动获取 chat_id。

用法：
    python tools/setup_bot.py <BOT_TOKEN>

流程：
    1. 校验 token 是否有效（调 getMe）
    2. 提示你给 bot 发一条消息
    3. 从 getUpdates 自动读出你的 chat_id
    4. 写回 config.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from notifier import get_me, get_updates  # noqa: E402

PROXY = "http://127.0.0.1:7890"


def main() -> None:
    if len(sys.argv) < 2:
        print("用法：python tools/setup_bot.py <BOT_TOKEN>")
        sys.exit(1)
    token = sys.argv[1].strip()

    print("① 校验 Bot Token…")
    me = get_me(token, proxy=PROXY)
    if not me or not me.get("ok"):
        # 云端/直连重试
        me = get_me(token, proxy=None)
    if not me or not me.get("ok"):
        print("   Token 无效，请检查是否复制完整（形如 7712xxxxx:AAHxxxx）")
        sys.exit(1)
    bot = me["result"]
    print(f"   有效 ✓  Bot 名称：@{bot.get('username')}（{bot.get('first_name')}）")

    print("\n② 请在 Telegram 里找到这个 bot，给它发送任意一条消息（例如 hi）")
    print("   发送后按回车继续…")
    input()

    print("③ 读取 chat_id…")
    chat_id = None
    for attempt in range(6):
        updates = get_updates(token, proxy=PROXY) or get_updates(token, proxy=None)
        for u in reversed(updates):
            msg = u.get("message") or u.get("edited_message") or {}
            chat = msg.get("chat") or {}
            if chat.get("id"):
                chat_id = str(chat["id"])
                print(f"   找到 chat_id = {chat_id}"
                      f"（{chat.get('first_name', '')} {chat.get('username', '')}）")
                break
        if chat_id:
            break
        print(f"   第 {attempt+1} 次未读到，等待 3 秒…")
        time.sleep(3)

    if not chat_id:
        print("   未读到 chat_id。请确认已给 bot 发消息后重跑本脚本。")
        sys.exit(1)

    cfg_path = ROOT / "config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    cfg.update({"bot_token": token, "chat_id": chat_id})
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"\n④ 已写入 {cfg_path}")
    print("   下一步：设为 dry_run=false 即可正式推送。")

    # 发一条测试消息验证
    print("\n⑤ 发送测试消息…")
    from notifier import escape_md, send_message
    test = (f"*zzzdm 二次蒸馏已就绪*\n"
            f"过滤规则生效，后续只推送你关注的品类。\n"
            f"chat\\_id \\= {escape_md(chat_id)}")
    ok = send_message(token, chat_id, test, proxy=PROXY) or \
        send_message(token, chat_id, test, proxy=None)
    print("   测试消息已送达 ✓" if ok else "   测试消息发送失败，请检查网络")


if __name__ == "__main__":
    main()
