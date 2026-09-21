# zzzdm 二次蒸馏

把 [真正值得买](https://t.me/zzzdm) 频道按你的口味再筛一遍，只把想看的推到你 Telegram 私聊。
**部署后不在你电脑上运行，不消耗任何 token。**

---

## 它做什么

```
源频道 zzzdm → 抓最新帖子（含图片）→ 按黑名单剔除不喜欢的品类 → Bot 精简卡片 → 你的私聊
```

**精简卡片模式**：每条消息只有三行——标题、价格、原频道链接，正文全部丢弃，
以缩短消息行高，方便快速扫读。图片保留。

实际效果：

```
脉动 +电解质运动饮料 西柚口味整箱600ML*15瓶
¥39.43（91天新低）
https://t.me/zzzdm/379676
        ← 上方是原帖商品图
```

> 技术说明：Bot 无法使用 Telegram 原生转发（没有读取源频道权限，`copyMessage`
> 会报 `message to copy not found`）。因此采用「下载 telesco CDN 图片 → 用
> `sendPhoto` 上传，三段式卡片作为 caption」，效果等同转发。
> 图片下载失败时自动降级为纯文本，不阻塞推送。

---

## 剔除清单

| 品类 | 说明 |
|---|---|
| 生鲜 | 肉类、蛋类、海鲜水产 |
| 酒类 | 白酒、啤酒、红酒等 |
| 服装 | 成人服装鞋袜；**婴幼儿服装保留** |
| 纸品 | 抽纸、卷纸、湿厕纸等 |
| 米面粮油 | 米、面、油、调味品 |
| 洗衣液 | 洗衣液、凝珠、消毒液等 |
| 成人奶粉 | 中老年/孕妇/全脂脱脂；**婴幼儿奶粉保留** |
| 零食 | 坚果、饼干、糕点、月饼、粽子等 |
| 牛奶 | 纯牛奶、鲜奶盒装奶 |
| 眼镜镜片 | 镜片、镜架、墨镜、隐形眼镜 |
| ETC | ETC 设备与办理 |
| 流量卡 | 流量卡、上网卡、随身 wifi |
| 浴巾毛巾 | 浴巾、毛巾、干发帽 |
| 茶叶 | 绿茶、红茶、普洱、茶包等 |
| 方便食品 | 方便面、速食、自热、速冻、预制菜 |
| 手机壳 | 手机壳、保护套 |
| 酸奶及冷链 | 酸奶、乳酸菌饮品、雪糕冰淇淋 |
| **开通类/虚拟服务** | 入会红包、开卡、年卡、京豆积分、话费充值等 |
| **美妆个护** | 面膜、面霜、精华、口红、香水、防晒等 |
| **零价格活动** | 价格=0 元的一切帖（入会送豆、抽奖、返红包凑单等） |
| **水果** | 苹果、石榴、芒果、车厘子、榴莲等鲜果 |
| **礼盒礼品** | 礼盒、大礼包、伴手礼、商务礼品 |
| **床上用品** | 四件套、被芯、枕芯、毛毯、凉席、床垫 |
| **宠物用品** | 猫粮狗粮、罐头猫条、冻干、猫砂、猫窝狗窝、猫爬架、玩具、牵引绳、航空箱、喂食器、宠物保健 |

**保留**：数码、家电、日化（洗发水/沐浴露/牙膏/洗洁精）、饮料、咖啡、奶酪、
真正的婴幼儿用品（服装/奶粉/辅食/纸尿裤/婴儿护理），以及不在上表的一切。

> 易混项已做例外处理：奶酪、酸奶机、钢化膜、镜头、存储卡、茶饮料、奶茶、
> 洗发水、沐浴露、剃须刀、苹果手机、鼠标垫、猫爪杯、番茄酱、柠檬味洗洁精、
> 婴儿隔尿垫、会员价促销的实物品，都不会被误剔。
>
> **婴幼儿例外与零食的边界**：真正的婴幼儿用品一律保留；但出现
> 「儿童/宝宝 + 零食语义」（如"儿童休闲零食""宝宝磨牙饼干"）时不适用例外——
> 它的本质是零食。
>
> **零价格规则说明**：价格字段解析为 `0` 的一律剔除，不设例外。实测 157 条样本中，
> 9 条零价格帖有 8 条是虚拟活动（入会送豆/抽奖/关注/加购/超市卡），
> 另 1 条是「返红包后实付 0 元」的凑单帖 —— 同属应剔除之列。
> 价格字段**为空**（未抓到）不触发该规则。

---

## 部署状态

**已上线** → https://github.com/leondellee/zzzdm-filter

- GitHub Actions 定时任务已启用，每 5 分钟自动运行
- Secrets（`TG_BOT_TOKEN` / `TG_CHAT_ID`）已配置
- 去重状态 `output/state.json` 自动提交回仓库
- **本机不需要开机，也不消耗任何 token**

查看运行记录：仓库 → Actions 标签页。

---

## 从零部署（如需重来）

### 第 1 步：创建 Bot

1. Telegram 里搜 `@BotFather`
2. 发 `/newbot`
3. 依次起两个名字（显示名随意，用户名必须以 `bot` 结尾）
4. 复制它返回的 Token，形如 `7712345678:AAHxxxxxxxxxxxxxxxx`

> 这一步必须你亲自做——Telegram 规定 Bot 只能由账号主人创建。

**然后必须给 bot 发一条消息**（搜到它，点 START），否则 bot 无法给你推送。

### 第 2 步：跑配置助手

```bash
python tools/setup_bot.py <你的BOT_TOKEN>
```

脚本会校验 Token、自动读出你的 chat_id、发一条测试消息。

### 第 3 步：推到 GitHub

```bash
python tools/deploy.py https://github.com/<用户名>/zzzdm-filter.git
```

脚本会初始化仓库、校验 `config.json` 已被忽略（防 token 泄露）、提交并推送，
最后把要填的 Secrets 值打印出来。

### 第 4 步：填两个 Secrets

仓库 → Settings → Secrets and variables → Actions → New repository secret：

| 名称 | 值 |
|---|---|
| `TG_BOT_TOKEN` | 第 1 步拿到的 Token |
| `TG_CHAT_ID` | 第 2 步脚本输出的数字 ID |

### 第 5 步：启用

Actions 标签页 → 若提示则点「I understand my workflows, go ahead and enable them」。
也可以直接点 `zzzdm-filter` → Run workflow 手动跑一次验证。

**完成。** 之后每 5 分钟自动检查一次，有新帖且通过筛选就推给你。

> 两个易踩的坑：
> 1. 工作流必须有 `permissions: contents: write`，否则回写 state 时会 403。
> 2. 抓取完全失败时脚本会**报错退出**（而不是静默空跑），便于在 Actions 里发现问题。

---

## 本地测试（可选）

```bash
# 只看判定结果，不推送
python src/service.py

# 单条帖子判定
python -c "import sys; sys.path.insert(0,'src'); from classifier import Classifier; c=Classifier(); print(c.classify('伊利 中老年高钙奶粉800g'))"

# 回归测试（159 条边界用例）
python tests/test_regression.py

# 抓真实样本跑判定
python tests/crawl_and_classify.py
```

---

## 调整口味

改 `src/classifier.py` 里的 `DROP_RULES`：

- **想保留某类** → 删掉对应的规则块
- **想多加一类** → 复制一个规则块改 `keywords`
- **发现误杀** → 把词加进该规则的 `exclude` 列表
- **品牌词污染** → 用 `exclude_re` 加正则

> 零价格规则不走关键词表，由 `is_zero_price()` 单独判定，位于白名单之前。
> 若要放开（比如允许 0 元商品），改 `Classifier.classify()` 里那一段即可。

改完必须跑 `python tests/test_regression.py` 确认没改坏。

---

## 文件结构

```
zzzdm-filter/
├── src/
│   ├── classifier.py    品类判定引擎（核心，改口味在这）
│   ├── parser.py        t.me 页面解析 + 结构化字段抽取
│   ├── notifier.py      精简卡片渲染 + TG 推送
│   └── service.py       主流程（抓 → 筛 → 推）
├── tools/
│   ├── setup_bot.py     首次配置助手
│   ├── deploy.py        一键推 GitHub
│   └── build_report.py  生成验收报告
├── tests/
│   ├── test_regression.py     159 条边界回归测试
│   ├── verify_samples.py      原始 20 条人工标注验证
│   └── crawl_and_classify.py  真实样本批量判定
├── .github/workflows/filter.yml
└── config.json          本地配置（token/chat_id/代理，已 gitignore）
```

---

## 常见问题

**为什么不用 Bot 直接读源频道？**
Bot 无法读取它不在其中的频道，而 `t.me/zzzdm` 是别人的频道，你加不进去 bot。
所以走「轮询公开预览页」的方式，不需要任何账号授权。

**为什么选 GitHub Actions？**
你要求不占本机、不烧 token。Actions 云端免费跑，本机零占用。
如果嫌 5 分钟延迟长，可以改到云函数（1 分钟）或自备服务器（常驻）。

**会重复推送吗？**
不会。已推送的帖 ID 记在 `output/state.json`，工作流会自动提交回仓库。

**TG 域名在国内打不开？**
本地测试需走代理（`config.json` 的 `proxy` 字段）。
云端（GitHub Actions）直连即可，无需代理。

---

## CaidenLee Fork · 飞书自建应用推送支持

> 本 Fork 在原作者代码基础上新增 **飞书自建应用推送通道**，零第三方依赖，
> 与原 Telegram 推送并存——配置飞书凭证自动走飞书，没配则走 Telegram。
> 原作者 README 内容完整保留，以下为本 Fork 的增量改动。

### 改了什么

| 操作 | 文件 | 说明 |
|---|---|---|
| **新增** | `src/notifier_feishu.py` | 飞书自建应用推送器（约 130 行），零依赖，纯 `urllib` |
| **修改** | `src/service.py` | 推送路由加飞书优先判断（+30 行/-15 行），原 TG 逻辑不动 |

核心设计：
- **tenant_access_token** 自动缓存 + 提前 60 秒刷新，不重复换 token
- **interactive 卡片** 渲染：标题（加粗）+ 价格 + 商品图（lark_md 内嵌远程 URL，避免先上传拿 img_key）+ 「查看原帖」按钮
- **receive_id_type** 同时支持 `chat_id`（群聊）/ `open_id`（私聊）/ `user_id`

### 文件结构（Fork 更新版）

```
src/
├── classifier.py        # 未改动
├── parser.py            # 未改动
├── notifier.py          # 未改动（原 Telegram 推送）
├── notifier_feishu.py   # [新增] 飞书自建应用推送
└── service.py           # [修改] 加推送路由判断
```

### GitHub Secrets（Fork 新增 3 个）

| 名称 | 用途 |
|---|---|
| `FEISHU_APP_ID` | 飞书自建应用 App ID，形如 `cli_xxxxxxxx` |
| `FEISHU_APP_SECRET` | 飞书自建应用 App Secret |
| `FEISHU_CHAT_ID` | 推送目标 chat_id，形如 `oc_xxxxxxxx`（飞书群设置里可见） |

原 TG 的两个 Secrets（`TG_BOT_TOKEN` / `TG_CHAT_ID`）仍可用，优先级低于飞书。

### 飞书自建应用配置步骤

1. **创建应用**：打开 https://open.feishu.cn/app → 创建「企业自建应用」
2. **开通权限**（应用身份权限，发布后生效）：
   - `im:chat:readonly` （可选，查已加入的群列表用）
   - `im:message` / `im:message:send_as_bot` （必加，发消息用）
3. **发布版本**：权限加完后到「版本管理与发布」创建版本并发布
4. **加应用进群**：飞书群 → 设置 → 群机器人/应用 → 添加自建应用
5. **拿 chat_id**：群设置拉到底，找到 Chat ID 字段（`oc_` 开头）

### config.json 字段（Fork 新增）

```json
{
  "feishu_app_id": "cli_a743f3cfee6b900b",
  "feishu_app_secret": "xxxxxx",
  "feishu_chat_id": "oc_fa6f4c66d666c48b15e0157425f0c5f6",
  "proxy": "",
  "max_push_per_run": 20,
  "dry_run": false
}
```

三个飞书字段任意缺失则自动回退到 Telegram 推送。

### 推送效果

群内收到一张 interactive 卡片：

```
┌─ zzzdm 精选 ─────────────────────────┐
│                                       │
│ **脉动 +电解质运动饮料 西柚口味...**   │
│                                       │
│ ¥39.43（91天新低）                    │
│                                       │
│  [商品图]                             │
│                                       │
│  [ 查看原帖 ]                         │
└───────────────────────────────────────┘
```

### 本地测试（飞书推送）

```bash
# 方式 A：直接用 GitHub Secrets 里的值（需本地 git 仓库状态正常）
python src/service.py

# 方式 B：dry_run 只看不推
python -c "
import sys; sys.path.insert(0,'src')
from service import load_config, load_state, run_once
cfg = load_config(); cfg['dry_run'] = True
run_once(cfg, load_state())
"

# 方式 C：单独测飞书推送器
python -c "
import sys; sys.path.insert(0,'src')
from notifier_feishu import FeishuNotifier
f = FeishuNotifier('你的APP_ID', '你的APP_SECRET')
ok = f.send_text('oc_xxx', '测试消息')
print('OK' if ok else 'FAIL')
"
```

### 踩坑记录（Fork 踩过）

| 坑 | 原因 | 解决 |
|---|---|---|
| HTTP 403 `im:chat:readonly` 权限缺失 | 飞书权限加了但没「发布版本」 | 加完权限必须到「版本管理与发布」创建并发布版本 |
| HTTP 400 `invalid receive_id` | `receive_id_type` 默认 `open_id`，但传的是 `chat_id` | URL 里显式带 `?receive_id_type=chat_id` |
| HTTP 400 `field validation failed` / `content is required` | interactive 卡片的 card JSON 必须放 `content` 字段（字符串化），不是顶层 `card` | 改为 `{"msg_type":"interactive","content": json.dumps(card_body)}` |
| HTTP 400 `img element must contain img_key` | 飞书卡片 `img` 元素不支持远程 URL，必须先上传拿 img_key | 改用 `lark_md` 的 `![](url)` 语法内嵌图片，免上传 |

### 更新日志

| 日期 | 版本 | 说明 |
|---|---|---|
| 2026-09-21 | Fork 初始版 | 新增 `notifier_feishu.py`，`service.py` 加飞书优先路由；本地 py_compile ✓，卡片推送测试 ✓，GitHub Actions 端到端 SUCCESS |
