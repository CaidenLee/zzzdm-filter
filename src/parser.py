# -*- coding: utf-8 -*-
"""从 t.me/s/<channel> 的 HTML 页面解析帖子。

Telegram 公开预览页结构：
    <div class="tgme_widget_message" data-post="zzzdm/379670">
      <div class="tgme_widget_message_text ...">正文</div>
      <a class="tgme_widget_message_date" href="...">

zzzdm 的正文固定模板（实测 2026-09）：
    第1行  商品标题（可带运营标签前缀，如「今日必买、中秋送好礼：」）
    第2行  优惠说明（凑单/领券流水账）
    价格：59.53元  (价格低于618)
    商家：[京东]
    值率：值: 8 不值: 1
    领券：[无需领券]
    ------------------------------
    【🛒 立即购买】【💬 查看评论】

结构化字段（价格/商家/值率/领券）可直接用于生成精简卡片。

注意：TG 域名在国内需走代理，取页面时请显式指定 ProxyHandler。
"""

from __future__ import annotations

import html as html_mod
import re
from dataclasses import dataclass, field


@dataclass
class Post:
    post_id: str
    text: str
    title: str
    body: str
    link: str
    price: str = ""
    price_note: str = ""
    mall: str = ""
    vote_value: int = 0
    vote_bad: int = 0
    coupon: str = ""
    buy_url: str = ""
    photo_url: str = ""

    @property
    def vote_rate(self) -> float | None:
        total = self.vote_value + self.vote_bad
        return round(self.vote_value / total * 100, 1) if total else None

    @property
    def msg_id(self) -> int:
        try:
            return int(self.post_id.split("/")[-1])
        except Exception:
            return 0


_MSG_BLOCK = re.compile(
    r'<div class="tgme_widget_message[^"]*"\s+data-post="([^"]+)"(.*?)'
    r'(?=<div class="tgme_widget_message[^"]*"\s+data-post=|$)',
    re.S,
)
_TEXT_DIV = re.compile(
    r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S
)
_DATE_LINK = re.compile(r'class="tgme_widget_message_date"[^>]*href="([^"]+)"')
_OUT_LINKS = re.compile(r'<a[^>]+href="(https?://[^"]+)"[^>]*>', re.S)

# 帖子配图：公开预览页用 background-image 方式内联，URL 指向 telesco CDN
_PHOTO = re.compile(
    r'tgme_widget_message_photo_wrap[^>]*background-image:url\([\'"]?'
    r'(https://[^\'")]+)', re.S
)
# 兜底：任何出现在 photo_wrap 区域的 telesco 直链
_PHOTO_ALT = re.compile(
    r'background-image:url\([\'"]?(https://cdn\d*\.telesco\.pe/[^\'")]+)', re.S
)

# 运营标签前缀（判定会误伤，需剥离）
_TITLE_TAGS = [
    "今日必买", "中秋送好礼", "中秋", "春节送好礼", "年货节", "双11", "双十一",
    "618", "黑五", "开学季", "女神节", "38节", "母亲节", "父亲节", "端午送好礼",
    "纯净无添加", "88VIP", "PLUS会员", "超级补贴", "百亿补贴", "今日爆款",
    "历史新低", "绝对值", "手慢无", "限时", "限量", "京东", "天猫", "淘宝",
    "拼多多", "唯品会", "抖音", "小编推荐",
]

_FIELD = {
    "price": re.compile(r'价格[：:]\s*([^\n(（]*)'),
    "price_note": re.compile(r'价格[：:][^\n(（]*[\(（]([^)）]*)'),
    "mall": re.compile(r'商家[：:]\s*\[?([^\]\n]*)'),
    "coupon": re.compile(r'领券[：:]\s*\[?([^\]\n]*)'),
}
_VOTE = re.compile(r'值率[：:]\s*值[:：]\s*(\d+)\s*不值[:：]\s*(\d+)')


def _strip_tags(fragment: str) -> str:
    fragment = re.sub(r'<br\s*/?>', '\n', fragment)
    fragment = re.sub(r'<[^>]+>', '', fragment)
    fragment = html_mod.unescape(fragment)
    return fragment.replace('\u200b', '').replace('\xa0', ' ').strip()


def clean_title(title: str) -> str:
    """剥离运营标签前缀，返回真实商品名。

    「今日必买、中秋送好礼：雀巢 怡养中老年奶粉700g*2」
    → 「雀巢 怡养中老年奶粉700g*2」
    """
    if not title:
        return ""
    for sep in ("：", ":"):
        if sep in title:
            title = title.split(sep)[-1]
            break
    parts = [p.strip() for p in re.split(r"[、,，]", title) if p.strip()]
    while parts and parts[0] in _TITLE_TAGS:
        parts.pop(0)
    if parts:
        head = parts[0]
        for tag in sorted(_TITLE_TAGS, key=len, reverse=True):
            if head.startswith(tag) and len(head) > len(tag) + 2:
                parts[0] = head[len(tag):].lstrip("：: 、,，")
                break
    return "、".join(parts) if parts else title.strip()


def split_title_body(text: str) -> tuple[str, str]:
    """取首行作为商品标题，其余为正文。"""
    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
    if not lines:
        return "", ""
    return lines[0], '\n'.join(lines[1:])


def parse(html_text: str) -> list[Post]:
    posts: list[Post] = []
    for m in _MSG_BLOCK.finditer(html_text):
        post_id, block = m.group(1), m.group(2)
        tm = _TEXT_DIV.search(block)
        if not tm:
            continue
        text = _strip_tags(tm.group(1))
        if not text:
            continue

        raw_title, body = split_title_body(text)
        title = clean_title(raw_title)

        dm = _DATE_LINK.search(block)
        link = dm.group(1) if dm else f"https://t.me/{post_id}"

        full = text
        price = (m1.group(1).strip() if (m1 := _FIELD["price"].search(full)) else "")
        note = (m1.group(1).strip() if (m1 := _FIELD["price_note"].search(full)) else "")
        mall = (m1.group(1).strip() if (m1 := _FIELD["mall"].search(full)) else "")
        coupon = (m1.group(1).strip() if (m1 := _FIELD["coupon"].search(full)) else "")
        vm = _VOTE.search(full)
        vv, vb = (int(vm.group(1)), int(vm.group(2))) if vm else (0, 0)

        out = [u for u in _OUT_LINKS.findall(block)
               if 't.me' not in u and 'telegram' not in u]

        photo = ""
        pm = _PHOTO.search(block) or _PHOTO_ALT.search(block)
        if pm:
            photo = pm.group(1).replace('&amp;', '&')

        posts.append(Post(
            post_id=post_id, text=text, title=title, body=body, link=link,
            price=price, price_note=note, mall=mall, coupon=coupon,
            vote_value=vv, vote_bad=vb, buy_url=out[0] if out else "",
            photo_url=photo,
        ))
    return posts


if __name__ == "__main__":
    import sys
    from pathlib import Path
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/raw_page.html")
    ps = parse(src.read_text(encoding="utf-8"))
    print(f"解析到 {len(ps)} 条帖子\n")
    for p in ps[:8]:
        print(f"[{p.post_id}] {p.title}")
        print(f"    价格={p.price}  商家={p.mall}  值率={p.vote_value}/{p.vote_bad}"
              f" ({p.vote_rate}%)")
        print()
