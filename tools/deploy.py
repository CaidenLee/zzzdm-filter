# -*- coding: utf-8 -*-
"""一键部署到 GitHub（在已有 git 仓库上推送，并提示填写 Secrets）。

用法：
    python tools/deploy.py <仓库地址>

仓库地址形如：
    https://github.com/<用户名>/zzzdm-filter.git
    git@github.com:<用户名>/zzzdm-filter.git

前置：
    - 已跑过 tools/setup_bot.py，config.json 里有有效 token 和 chat_id
    - 本机已配置 GitHub 凭据（或走代理）

注意：config.json 含 token，已在 .gitignore 中排除，不会被推上去。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIT = r"C:/Users/leon/.workbuddy/binaries/PortableGit/versions/1.2.0/cmd/git.exe"
PROXY = "http://127.0.0.1:7890"


def run(args: list[str], check: bool = True) -> tuple[int, str]:
    proc = subprocess.run([GIT] + args, cwd=str(ROOT),
                          capture_output=True, text=True, encoding="utf-8",
                          errors="ignore")
    out = (proc.stdout or "") + (proc.stderr or "")
    if check and proc.returncode != 0:
        print(f"  命令失败：git {' '.join(args)}")
        print(f"  {out.strip()[:400]}")
    return proc.returncode, out


def main() -> None:
    if len(sys.argv) < 2:
        print("用法：python tools/deploy.py <仓库地址>")
        sys.exit(1)
    remote = sys.argv[1].strip()

    cfg_path = ROOT / "config.json"
    if not cfg_path.exists():
        sys.exit("未找到 config.json，请先跑 tools/setup_bot.py")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    if not cfg.get("bot_token") or not cfg.get("chat_id"):
        sys.exit("config.json 缺少 bot_token 或 chat_id，请先跑 tools/setup_bot.py")

    print("① 检查 git 状态…")
    if not (ROOT / ".git").exists():
        run(["init"])
        run(["branch", "-M", "main"])
        print("   已初始化仓库")
    else:
        print("   仓库已存在")

    print("② 校验 config.json 已被忽略（防止 token 泄露）…")
    code, out = run(["check-ignore", "config.json"], check=False)
    if code != 0:
        sys.exit("  ✗ config.json 未被 .gitignore 忽略，中止部署以防 token 泄露！")
    print("   ✓ 已忽略")

    print("③ 提交…")
    run(["add", "-A"])
    code, out = run(["commit", "-m", "deploy: zzzdm 二次蒸馏"], check=False)
    if "nothing to commit" in out:
        print("   无新改动")
    else:
        print("   已提交")

    print("④ 设置远程…")
    code, _ = run(["remote", "get-url", "origin"], check=False)
    if code == 0:
        run(["remote", "set-url", "origin", remote])
        print("   已更新 origin")
    else:
        run(["remote", "add", "origin", remote])
        print("   已添加 origin")

    print("⑤ 走代理推送…")
    for key in ("http.proxy", "https.proxy"):
        run(["config", "--local", key, PROXY], check=False)
    # 状态文件必须强制加入（output/ 通常被部分忽略）
    run(["add", "-f", "output/state.json"], check=False)
    code, out = run(["commit", "-m", "deploy: include state"], check=False)
    code, out = run(["push", "-u", "origin", "main"], check=False)
    if code != 0:
        print("   推送失败，请检查仓库地址与凭据。输出：")
        print(out[:500])
        sys.exit(1)
    print("   ✓ 已推送")

    print("\n" + "=" * 60)
    print("最后一步：去 GitHub 填 Secrets")
    print("=" * 60)
    print(f"  仓库 → Settings → Secrets and variables → Actions")
    print(f"\n  TG_BOT_TOKEN = {cfg['bot_token']}")
    print(f"  TG_CHAT_ID   = {cfg['chat_id']}")
    print("\n  填完到 Actions 标签页点 Run workflow 即可。")
    print("  之后每 5 分钟云端自动运行，本机无需开机。")


if __name__ == "__main__":
    main()
