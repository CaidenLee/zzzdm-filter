# -*- coding: utf-8 -*-
"""用 zzzdm 真实帖子验证过滤器准确度。

样本来自 t.me/s/zzzdm 近期帖（2026-09-19 抓取），共 20 条。
预期结果由人工标注，与实际判定比对，输出漏杀/误杀清单。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from classifier import Classifier  # noqa: E402

# (标题, 正文摘要, 人工预期 drop 与否)
SAMPLES = [
    ("吴裕泰 茉莉花茶叶（中秋礼盒）", "京东此款目前活动售价129元，下单领取黑五券200-20，plus200-25优惠券，参与满129元减29元", None),
    ("雀巢 怡养益护因子中老年奶粉700g*2（中秋奶粉礼盒）", "凑单到手单件73.75元，返30值得买积分，补贴后低至70.75元", True),
    ("简爱 裸酸奶原味1.08kg×3瓶", "此商品售价89元，下单1件，页面下拉至超级补贴领取满39减6元，88会员到打9.5折", False),
    ("NESPRESSO 奈斯派索胶囊咖啡人气精选120颗", "此款目前活动售价452元，下单领取满400减25元，88VIP消费券 满480减60元优惠券", False),
    ("伊利 欣活中老年高钙补钙奶粉800g*2富硒无蔗糖（中秋礼盒）", "京东此款目前活动售价147.8元，下单领取满99减10元优惠券", True),
    ("瑞幸咖啡 生椰拿铁浓缩咖啡液 18ml*64颗+赠保温杯1个", "主商品加购1件（立减60元，补贴15元，88VIP会员9.5折）+凑单品1件", False),
    ("脉动 +电解质运动饮料 西柚口味整箱600ML*15瓶", "此款目前活动售价89元，下单领取超级补贴领取39-6优惠券，参与88VIP 95折", False),
    ("健力宝 迷你罐柠蜜味运动饮料 200ml*24罐", "此款目前活动售价49.9元，下单领取满10减10元优惠券，参与88VIP 95折", False),
    ("轻上 100%果汁含量含NFC果汁饮品饮料 220ml*10瓶", "京东此款目前活动售价26.9元，满1件减7元，下单领取满26减7元优惠券", False),
    ("沃隆 福果礼 纯坚果礼盒 1220g", "京东售价125元，领取满99减40元优惠卷，满3.1减3元优惠卷，下单实付低至82.0元", True),
    ("邦克仕 适用苹果13-17系列轻砂磁吸手机壳", "拼多多此款目前活动售价56元，拼多多首页搜索ddd进入活动页面，用1张减减卡兑换6折优惠券", False),
    ("妙可蓝多 精制 马苏里拉奶酪 800g", "此款目前活动售价70元，领取淘礼金1.63元，下单领取满1减1元，满70减6元", False),
    ("酷态科 CP12磁吸充电宝电芯10000毫安自带线移动电源", "拼多多此款目前活动售价102元，拼多多百亿补贴→百亿消费券→福袋活动领取7折最高减20元优惠券", False),
    ("品胜 PD20W快充充电器", "拼多多此款目前百亿补贴活动售价23.7元，领取福袋7折券（最高减20）", False),
    ("轩妈 蛋黄酥中秋礼盒660g", "此款目前活动售价129元，领取淘礼金7.98元，下单领取满129减15元，直播间9折券", True),
    ("美心 流心四式招牌月饼 港式经典口味 360g", "此款目前活动售价388元，88VIP下单领取200元减25元消费卷", True),
    ("美心 双白蛋黄莲蓉月饼礼盒 740g", "此款目前活动售价349元，领取淘礼金11.32元，下拉详情超级补贴页面下单", True),
    ("潘祥记 云腿月饼50g*10个", "直播间进入加购，领直播间9折券，详情页下拉进入超级补贴加购主商品和凑单各1", True),
    ("周黑鸭 武汉特产 鸭翅240g约10包/多款可选！", "京东此款目前活动售价16.9元，下单领取满29减10优惠券，下单2件", True),
    ("沃隆 坚果礼盒 万福心意礼 1330g", "京东此款目前活动售价109元，下单领取满99减40元，满3.1-3元优惠券", True),
]


def main() -> None:
    clf = Classifier()
    rows = []
    fp = []   # 误杀：预期保留但被剔除
    fn = []   # 漏杀：预期剔除但保留了

    for title, body, expect_drop in SAMPLES:
        v = clf.classify(title, body)
        rows.append({"title": title, "drop": v.drop, "category": v.category,
                     "matched": v.matched, "kept_by": v.kept_by, "expect": expect_drop})
        if expect_drop is None:
            continue
        if expect_drop and not v.drop:
            fn.append(title)
        if (not expect_drop) and v.drop:
            fp.append((title, v.category, v.matched))

    out = Path(__file__).resolve().parents[1] / "output" / "verify_report.txt"
    lines = []
    lines.append("=" * 78)
    lines.append("zzzdm 二次蒸馏 · 过滤判定验证报告")
    lines.append("=" * 78)
    lines.append("")
    for i, r in enumerate(rows, 1):
        mark = "剔除" if r["drop"] else "保留"
        extra = ""
        if r["drop"]:
            extra = f"  ← {r['category']}｜{r['matched']}"
        elif r["kept_by"]:
            extra = f"  ← 例外保护：{r['kept_by']}"
        flag = ""
        if r["expect"] is not None and r["expect"] != r["drop"]:
            flag = "   ✗ 与预期不符"
        lines.append(f"{i:2d}. [{mark}] {r['title']}{extra}{flag}")

    lines.append("")
    lines.append("-" * 78)
    kept = sum(1 for r in rows if not r["drop"])
    lines.append(f"样本 {len(rows)} 条 → 保留 {kept} 条 / 剔除 {len(rows)-kept} 条")
    lines.append(f"误杀（该留却删）：{len(fp)} 条")
    for t, c, m in fp:
        lines.append(f"    · {t}  ({c}｜{m})")
    lines.append(f"漏杀（该删却留）：{len(fn)} 条")
    for t in fn:
        lines.append(f"    · {t}")
    lines.append("-" * 78)

    text = "\n".join(lines)
    out.write_text(text, encoding="utf-8")
    print(text)

    (out.parent / "verify_detail.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
