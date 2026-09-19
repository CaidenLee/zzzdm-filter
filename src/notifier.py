# -*- coding: utf-8 -*-
"""图片下载 + Telegram 推送（精简卡片模式：标题 + 价格 + 图片 + 原文链接）。

Leon 2026-09-19 最终定稿：只留标题、价格、原频道链接三段，正文全部丢弃，
以缩短每条消息的行高。图片由 sendPhoto 承载。
Telegram 的 copyMessage 走不通（bot 无读取源频道权限），因此采用：
    下载 telesco CDN 图片 → 用 sendPhoto 上传，caption 放三段式卡片
图片失败时降级为纯文本 sendMessage，不阻塞推送。
"""

from __future__ import annotations

import json
import mimetypes
import re
import urllib.error
import urllib.request
import uuid

API = "https://api.telegram.org/bot{token}/{method}"

# Telegram 单条消息文本上限 4096 字符（含 caption）
MAX_CAPTION = 1024          # sendPhoto 的 caption 上限
MAX_TEXT = 4096


def _opener(proxy: str | None):
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({} if not proxy
                                    else {"http": proxy, "https": proxy}))


def download_photo(url: str, proxy: str | None, timeout: int = 30) -> bytes | None:
    """下载图片。失败返回 None，由调用方降级处理。"""
    if not url:
        return None
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://t.me/"})
        resp = _opener(proxy).open(req, timeout=timeout)
        data = resp.read()
        return data if data and len(data) > 1024 else None
    except Exception as e:
        print(f"    图片下载失败 {type(e).__name__}: {str(e)[:110]}")
        return None


def _multipart(fields: dict, files: dict) -> tuple[bytes, str]:
    """手工构造 multipart/form-data（零第三方依赖）。"""
    boundary = "----zc" + uuid.uuid4().hex
    buf = bytearray()
    for k, v in fields.items():
        buf += f"--{boundary}\r\n".encode()
        buf += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
        buf += str(v).encode("utf-8") + b"\r\n"
    for k, (fname, content) in files.items():
        ctype = mimetypes.guess_type(fname)[0] or "image/jpeg"
        buf += f"--{boundary}\r\n".encode()
        buf += (f'Content-Disposition: form-data; name="{k}"; '
                f'filename="{fname}"\r\n').encode()
        buf += f"Content-Type: {ctype}\r\n\r\n".encode()
        buf += content + b"\r\n"
    buf += f"--{boundary}--\r\n".encode()
    return bytes(buf), f"multipart/form-data; boundary={boundary}"


def _api_call(token: str, method: str, payload: dict,
              proxy: str | None) -> tuple[bool, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API.format(token=token, method=method), data=data,
        headers={"Content-Type": "application/json"})
    try:
        resp = _opener(proxy).open(req, timeout=30)
        body = json.loads(resp.read().decode("utf-8"))
        return bool(body.get("ok")), body.get("description", "")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:200]
        return False, f"HTTP {e.code}: {detail}"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:140]}"


def _api_upload(token: str, method: str, fields: dict, files: dict,
                proxy: str | None) -> tuple[bool, str]:
    body, ctype = _multipart(fields, files)
    req = urllib.request.Request(
        API.format(token=token, method=method), data=body,
        headers={"Content-Type": ctype})
    try:
        resp = _opener(proxy).open(req, timeout=60)
        r = json.loads(resp.read().decode("utf-8"))
        return bool(r.get("ok")), r.get("description", "")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:200]
        return False, f"HTTP {e.code}: {detail}"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:140]}"


def build_caption(post) -> str:
    """精简卡片：标题 + 价格 + 原帖链接，正文丢弃以缩短行高。

    形如：
        脉动 电解质运动饮料 西柚口味整箱600ML*15瓶
        ¥39.43（91天新低）
        https://t.me/zzzdm/379676
    标题缺失时退回正文首行；价格缺失时该行省略。
    """
    title = (post.title or "").strip()
    if not title:
        raw = (post.text or "").strip().replace("------------------------------", "")
        title = next((ln.strip() for ln in raw.splitlines() if ln.strip()), "")
    if len(title) > 180:
        title = title[:179] + "…"

    lines = [title]

    price = (post.price or "").strip()
    if price:
        price = re.sub(r"^[¥￥]\s*", "", price)
        price = re.sub(r"\s*元$", "", price)
        note = (post.price_note or "").strip()
        lines.append(f"¥{price}" + (f"（{note}）" if note else ""))

    if post.link:
        lines.append(post.link)

    return "\n".join(lines)[:MAX_CAPTION]


def send_post(token: str, chat_id: str, post, proxy: str | None = None,
              with_photo: bool = True) -> bool:
    """发送一条帖子：有图则带图，无图或下载失败则发纯文本。"""
    caption = build_caption(post)

    if with_photo and post.photo_url:
        blob = download_photo(post.photo_url, proxy)
        if blob:
            ok, err = _api_upload(
                token, "sendPhoto",
                {"chat_id": chat_id, "caption": caption,
                 "disable_notification": "true"},
                {"photo": ("photo.jpg", blob)}, proxy)
            if ok:
                return True
            print(f"    sendPhoto 失败：{err}")

    # 降级：纯文本（可能超长，截断）
    text = caption if len(caption) <= MAX_TEXT else caption[:MAX_TEXT - 1] + "…"
    ok, err = _api_call(token, "sendMessage",
                        {"chat_id": chat_id, "text": text,
                         "disable_web_page_preview": True,
                         "disable_notification": True}, proxy)
    if not ok:
        print(f"    sendMessage 失败：{err}")
    return ok


def send_message(token: str, chat_id: str, text: str,
                 disable_preview: bool = True, proxy: str | None = None) -> bool:
    """发送纯文本/简易消息（用于测试与提示）。"""
    ok, err = _api_call(token, "sendMessage",
                        {"chat_id": chat_id, "text": text,
                         "disable_web_page_preview": disable_preview}, proxy)
    if not ok:
        print(f"    sendMessage 失败：{err}")
    return ok


def get_me(token: str, proxy: str | None = None) -> dict | None:
    try:
        resp = _opener(proxy).open(
            urllib.request.Request(API.format(token=token, method="getMe")),
            timeout=20)
        return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"getMe 失败：{type(e).__name__} {str(e)[:150]}")
        return None


def get_updates(token: str, proxy: str | None = None) -> list[dict]:
    try:
        resp = _opener(proxy).open(
            urllib.request.Request(API.format(token=token, method="getUpdates")),
            timeout=20)
        body = json.loads(resp.read().decode("utf-8"))
        return body.get("result", []) if body.get("ok") else []
    except Exception:
        return []
