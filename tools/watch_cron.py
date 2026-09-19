# -*- coding: utf-8 -*-
"""盯住 GitHub Actions 的定时任务是否真的自动触发（部署验收用）。

用法：
    python tools/watch_cron.py [最长等待分钟数]

GitHub 的 cron 对新仓库有 10~30 分钟的"上电"延迟，属正常现象。
本脚本轮询运行记录，一旦发现 event=schedule 的运行就报告结果并退出。
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "leondellee/zzzdm-filter"
GIT_CRED = (r"C:/Users/leon/.workbuddy/binaries/PortableGit/versions/1.2.0"
            r"/mingw64/bin/git-credential-wincred.exe")
PROXY = "http://127.0.0.1:7890"


def token() -> str:
    p = subprocess.run([GIT_CRED, "get"],
                       input="protocol=https\nhost=github.com\n\n",
                       capture_output=True, text=True)
    for line in p.stdout.splitlines():
        if line.startswith("password="):
            return line[9:]
    raise SystemExit("未取到 GitHub 凭据")


def main() -> None:
    minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    # 沙箱环境会注入失效代理，先清掉
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.pop(k, None)

    tok = token()
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    headers = {"Authorization": "token " + tok, "User-Agent": "zzzdm",
               "Accept": "application/vnd.github+json"}
    base = f"https://api.github.com/repos/{REPO}"

    log_path = ROOT / "output" / "cron_watch.txt"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fh = log_path.open("w", encoding="utf-8")

    def log(msg: str) -> None:
        print(msg)
        fh.write(msg + "\n")
        fh.flush()

    log(f"等待定时任务触发（最多 {minutes} 分钟）…")
    for i in range(minutes * 2):
        try:
            url = base + "/actions/runs?per_page=20"
            runs = json.loads(opener.open(
                urllib.request.Request(url, headers=headers),
                timeout=30).read().decode()).get("workflow_runs", [])
        except Exception as e:
            log(f"查询异常：{type(e).__name__} {e}")
            time.sleep(30)
            continue

        sched = [r for r in runs if r["event"] == "schedule"]
        done = [r for r in sched if r["status"] == "completed"]
        if done:
            r = done[0]
            log(f"定时任务完成 #{r['run_number']} → {r['conclusion']}")
            log(f"URL {r['html_url']}")
            if r["conclusion"] == "success":
                try:
                    data = opener.open(urllib.request.Request(
                        f"{base}/actions/runs/{r['id']}/logs", headers=headers),
                        timeout=60).read()
                    z = zipfile.ZipFile(io.BytesIO(data))
                    for n in z.namelist():
                        if "filter & push" in n:
                            log("--- 运行日志 ---")
                            for line in z.read(n).decode(
                                    "utf-8", "ignore").splitlines()[-12:]:
                                log("   " + line.split("Z ", 1)[-1])
                except Exception as e:
                    log(f"日志拉取失败：{e}")
            break
        log(f"  [{(i + 1) * 30}s] 尚无定时运行"
            + (f"（已有 {len(sched)} 条排队中）" if sched else ""))
        time.sleep(30)
    else:
        log("未在限定时间内观察到定时运行")

    fh.close()


if __name__ == "__main__":
    main()
