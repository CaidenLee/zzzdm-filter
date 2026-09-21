# -*- coding: utf-8 -*-
"""飞书自建应用推送（零第三方依赖，纯 urllib）。

用法：
    feishu = FeishuNotifier(app_id, app_secret)
    feishu.send_post(receive_id, post)      # 默认推群聊（receive_id_type=chat_id）
    feishu.send_post(open_id, post, "open_id")  # 推私聊
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request


TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
SEND_URL = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={rid_type}"

# tenant_access_token 有效期 2 小时，提前 60 秒刷新
TOKEN_REFRESH_SKEW = 60


class FeishuNotifier:
    """飞书自建应用推送器，自动缓存 tenant_access_token。"""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: str | None = None
        self._token_expires_at: float = 0

    # ---- tenant_access_token ----

    def _refresh_token(self) -> bool:
        """用 app_id + app_secret 换 tenant_access_token，成功返回 True。"""
        payload = json.dumps({
            "app_id": self.app_id,
            "app_secret": self.app_secret,
        }).encode("utf-8")
        req = urllib.request.Request(
            TOKEN_URL, data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            body = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"    飞书 token 刷新失败：{type(e).__name__} {str(e)[:140]}")
            return False
        if body.get("code") != 0:
            print(f"    飞书 token 刷新错误：{body.get('msg')}")
            return False
        self._token = body["tenant_access_token"]
        self._token_expires_at = time.time() + int(body.get("expire", 7200)) - TOKEN_REFRESH_SKEW
        return True

    def _get_token(self) -> str | None:
        """返回可用的 tenant_access_token，必要时自动刷新。"""
        if self._token and time.time() < self._token_expires_at:
            return self._token
        return self._refresh_token() and self._token or None

    # ---- 卡片构建 ----

    def _build_card(self, post) -> dict:
        """把帖子对象组装成飞书 interactive 卡片 JSON。"""
        title = (post.title or "").strip()
        if not title:
            raw = (post.text or "").strip().replace("------------------------------", "")
            title = next((ln.strip() for ln in raw.splitlines() if ln.strip()), "")
        if len(title) > 180:
            title = title[:179] + "…"

        elements = [
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**{title}**"}},
        ]

        price = (post.price or "").strip()
        if price:
            price = re.sub(r"^[¥￥]\s*", "", price)
            price = re.sub(r"\s*元$", "", price)
            note = (post.price_note or "").strip()
            price_line = f"¥{price}" + (f"（{note}）" if note else "")
            elements.append(
                {"tag": "div", "text": {"tag": "lark_md", "content": price_line}})

        if post.photo_url:
            # 用 lark_md 嵌入远程图片，避免必须先上传拿 img_key
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"![商品图]({post.photo_url})",
                },
            })

        if post.link:
            elements.append({
                "tag": "action",
                "actions": [{
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "查看原帖"},
                    "url": post.link,
                    "type": "primary",
                }],
            })

        # interactive 卡片：card 内容必须 JSON 字符串化后放 content 字段
        card_body = {
            "header": {
                "title": {"tag": "plain_text", "content": "zzzdm 精选"},
            },
            "elements": elements,
        }
        return {
            "msg_type": "interactive",
            "content": json.dumps(card_body, ensure_ascii=False),
        }

    # ---- 发送 ----

    def _send_raw(self, receive_id: str, receive_id_type: str,
                  payload: dict) -> tuple[bool, str]:
        token = self._get_token()
        if not token:
            return False, "无有效 tenant_access_token"
        url = SEND_URL.format(rid_type=receive_id_type)
        # 新 API 模式：receive_id 必须放 body
        body = dict(payload)
        body["receive_id"] = receive_id
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {token}",
            })
        try:
            resp = urllib.request.urlopen(req, timeout=20)
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("code") == 0:
                return True, ""
            return False, f"飞书 API {body.get('code')}: {body.get('msg')}"
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:200]
            return False, f"HTTP {e.code}: {detail}"
        except Exception as e:
            return False, f"{type(e).__name__}: {str(e)[:140]}"

    def send_post(self, receive_id: str, post,
                  receive_id_type: str = "chat_id") -> bool:
        """发送一条帖子卡片。receive_id_type 可选 chat_id / open_id / user_id。"""
        card = self._build_card(post)
        ok, err = self._send_raw(receive_id, receive_id_type, card)
        if not ok:
            print(f"    飞书推送失败：{err}")
        return ok

    def send_text(self, receive_id: str, text: str,
                  receive_id_type: str = "chat_id") -> bool:
        """发送纯文本消息（用于测试）。"""
        payload = {
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        }
        ok, err = self._send_raw(receive_id, receive_id_type, payload)
        if not ok:
            print(f"    飞书文本发送失败：{err}")
        return ok
