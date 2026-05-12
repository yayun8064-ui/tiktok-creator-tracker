# Claude × 飞书全自动追踪TikTok 达人数据 | 运营必备

> 打开飞书机器人作者名单一丢，达人账号数据底表 + 日报 + 周报全出，一行代码都不用写

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)]()
[![Powered by](https://img.shields.io/badge/powered%20by-Claude%20Code-blueviolet.svg)](https://claude.ai)

---

## 🎯 为什么需要这个

如果你在做 TikTok 创作者自孵化、达人运营、内容投放等业务，每天要盯几十个账号的播放、互动数据，手动汇总费时费力还容易漏。

这个工具把整套流程接管：

```
你在飞书里把作者名单发给机器人
        ↓
机器人自动在飞书建好追踪底表（多维表格）
        ↓
每天 10:00 自动推卡片日报到你飞书
        ↓
想看周报时说一声，机器人秒出
```

**全程在飞书里完成，不用打开任何其他工具。**

---

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 💬 **对话式初始化** | 把作者名单发给飞书机器人，机器人自动建好多维表格、配好定时任务 |
| 📊 **飞书作者底表** | 每日视频数据自动写入多维表格，支持筛选、排序、看趋势 |
| 📬 **每日卡片日报** | 每天 10:00 自动推送，含总播放、Top 账号排名、视频明细、停更预警 |
| 📈 **卡片式周报** | 一句话触发，从底表聚合出周报卡片，不额外消耗 API 配额 |
| 🤖 **Claude Skill** | 附带标准 Skill 文件，任意 Claude Code Agent 都能用，每位运营独立配置互不干扰 |

---

## 🖼️ 效果预览

**📬 日报卡片**（每天 10:00 飞书自动推送）

```
┌──────────────────────────────────────────────┐
│  📊 TikTok 日报 · 2026-05-12                  │
├──────────────────────────────────────────────┤
│  共 6 位作者监控｜今日发布 3 条               │
│  总播放 1.54w｜点赞 1,620｜评论 42            │
├──────────────────────────────────────────────┤
│  🏆 今日 Top 播放（新发视频）                  │
│  ─────────────────────────────────────────── │
│  #1  @creator_a    粉丝 66.1w   VV 1.39w     │
│  #2  @creator_b    粉丝  1.2w   VV 1,075     │
│  #3  @creator_c    粉丝  0.1w   VV   427     │
├──────────────────────────────────────────────┤
│  📋 今日视频明细                               │
│  账号 · 时间 · VV · Like · 评论 · 内容摘要    │
├──────────────────────────────────────────────┤
│  ⚠️ 停更预警：@creator_d（最后发布 04-30）     │
├──────────────────────────────────────────────┤
│  [ 📊 查看多维表格明细 → ]                     │
└──────────────────────────────────────────────┘
```

**📈 周报卡片**（说一句「出周报」，机器人秒发）

```
┌──────────────────────────────────────────────┐
│  📊 TikTok 周报 · 05-05 ~ 05-12              │
├──────────────────────────────────────────────┤
│  7天｜发布 13 条｜总VV 6.16w                  │
│  点赞 7,086｜评论 290                         │
├──────────────────────────────────────────────┤
│  📋 本期账号概览                               │
│  账号 · 发布 · 总VV · Like · 评论             │
├──────────────────────────────────────────────┤
│  🔥 爆款 Top 3                                │
│  🥇 @creator_a · 05-06 · VV 1.39w            │
│     "attention 🗣️🗣️"                          │
│  🥈 @creator_a · 05-09 · VV 1.36w            │
│  🥉 @creator_a · 05-05 · VV 0.98w            │
├──────────────────────────────────────────────┤
│  ⚠️ 停更预警：@creator_d · @creator_e        │
├──────────────────────────────────────────────┤
│  [ 📊 查看多维表格明细 → ]                     │
└──────────────────────────────────────────────┘
```

**📊 飞书多维表格底表**（每日自动写入，可筛选任意账号、时段）

```
日期       │ 账号        │ 昵称     │ 发布时间    │ VV     │ Like  │ 评论 │ 视频描述
2026-05-12 │ creator_a  │ Pusa...  │ 05-12 15:56│ 2,679  │  346  │  12  │ man not again...
2026-05-11 │ creator_a  │ Pusa...  │ 05-11 18:35│ 13,900 │ 1,473 │  24  │ attention 🗣️...
2026-05-10 │ creator_b  │ Fudgy... │ 05-10 12:30│  9,693 │ 1,149 │ 122  │ Everyone has...
```

---

## 🏗️ 系统架构

```
飞书对话（丢账号名单给机器人）
        ↓ 一次配置，终身生效
┌─────────────────────────────────┐
│         Claude Code Agent        │
│  SKILL.md 驱动，全程对话式完成    │
│  ① 建飞书多维表格底表             │
│  ② 写入 config，设好 cron        │
└─────────────────────────────────┘
        ↓ 每天 10:00 自动运行
tiktok_daily_report.py
  ├──→ 飞书多维表格（底表累积）
  └──→ 飞书卡片日报（机器人推送）

tiktok_weekly_report.py（说「出周报」触发）
  ├── 从多维表格聚合（0 API 配额消耗）
  └──→ 飞书卡片周报
```

---

## 📦 前置依赖

| 依赖 | 说明 | 安装 |
|------|------|------|
| Python 3.8+ | 运行脚本 | macOS 自带 |
| [lark-cli](https://www.npmjs.com/package/@larksuite/cli) | 飞书命令行工具 | `npm install -g @larksuite/cli` |
| requests | HTTP 库 | `pip3 install requests` |
| [RapidAPI tiktok-api23](https://rapidapi.com/Lundehund/api/tiktok-api23) | TikTok 数据接口 | 注册订阅，免费 500次/月 |

---

## 🚀 快速开始

### 方式一：Claude Code Agent 全自动（推荐）

1. 安装 [Claude Code](https://claude.ai/download) 和 lark-cli
2. 把 `SKILL.md` 的内容复制，发给 Claude，说：
   > 「这是一个 Skill，请按照里面的步骤帮我配置 TikTok 创作者追踪」
3. Claude 会引导你：
   - 输入 RapidAPI Key
   - 给出作者账号名单
   - 选择追踪维度（播放/点赞/评论/转发/粉丝数）
   - **自动在飞书里建好多维表格底表**
   - 设置每日 10:00 定时任务

全程约 15 分钟，之后完全自动运行。

### 方式二：手动配置

```bash
# 1. 写入 RapidAPI Key
mkdir -p ~/.config/tiktok-tracker
echo "你的KEY" > ~/.config/tiktok-tracker/rapidapi.key

# 2. 创建配置文件
cat > ~/.config/tiktok-tracker/config.json << 'EOF'
{
  "accounts": ["账号1", "账号2"],
  "dimensions": ["VV", "Like", "Comment"],
  "bitable_token": "飞书多维表格 token",
  "bitable_table_id": "数据表 ID",
  "feishu_open_id": "你的飞书 open_id",
  "script_dir": "/path/to/scripts"
}
EOF

# 3. 设置每日定时任务
SCRIPT_DIR="/path/to/scripts"
(crontab -l 2>/dev/null; echo "0 10 * * * /usr/bin/python3 $SCRIPT_DIR/tiktok_daily_report.py >> $SCRIPT_DIR/tiktok_daily_report.log 2>&1") | crontab -
```

---

## 📖 日常使用

```bash
# 手动触发日报（测试用）
python3 tiktok_daily_report.py

# 触发周报（指定统计天数）
python3 tiktok_weekly_report.py --days 7

# 直接查询账号数据（不发飞书）
python3 tiktok_vv_tracker.py user creator1 creator2 --days 7

# 查单个视频详情
python3 tiktok_vv_tracker.py video <video_id>

# 关键词搜索
python3 tiktok_vv_tracker.py search "cookie run" --count 20

# 查话题 Top 视频
python3 tiktok_vv_tracker.py hashtag cookierunkingdom --top 20
```

---

## ⚙️ 配置项说明

| 字段 | 说明 |
|------|------|
| `accounts` | TikTok 用户名列表（URL 里的 uniqueId，不带 @） |
| `dimensions` | 追踪维度：VV / Like / Comment / Share / Collect / 粉丝数 |
| `bitable_token` | 飞书多维表格 base token |
| `bitable_table_id` | 数据表 ID |
| `feishu_open_id` | 接收日报/周报的飞书用户 open_id |
| `script_dir` | 三个脚本所在目录的绝对路径 |

---

## 🤖 Claude Code Skill 说明

`SKILL.md` 是标准 Claude Code Skill 文件，可直接交给任意 Agent 使用。

**适合场景：**
- 团队内多位运营各自配置，数据互不干扰
- 新人入职直接跑 Skill，15 分钟搭好全套追踪系统
- 修改账号名单、调整维度，跟机器人说一句即可

**Skill 覆盖的操作：**
- RapidAPI Key 注册引导
- 账号名单录入
- 飞书多维表格自动建表（含字段结构）
- config.json 写入 + crontab 配置
- 周报触发：从多维表格聚合，0 API 消耗

---

## ❓ 常见问题

<details>
<summary>API 配额用完了怎么办？</summary>

脚本会直接提示，前往 RapidAPI 升级套餐后重新运行即可，不需要改任何配置。付费套餐约 $10/月，日报 + 周报长期稳定使用推荐。

</details>

<details>
<summary>账号找不到数据？</summary>

TikTok 用户名区分大小写，填写的是主页 URL 里的 uniqueId，不是昵称。比如主页是 `tiktok.com/@CookieRun_EN`，填 `CookieRun_EN`。

</details>

<details>
<summary>周报显示 0 条数据？</summary>

周报从多维表格聚合历史数据，需要先跑过至少一次日报写入数据后才能生成。

</details>

<details>
<summary>飞书卡片没收到？</summary>

检查 lark-cli bot 权限，运行 `lark-cli auth login --domain im` 重新授权。

</details>

<details>
<summary>想追踪的账号很多，配额够用吗？</summary>

每次日报每个账号消耗约 2 次 API 调用（账号信息 + 帖子列表）。免费套餐 500次/月，约支持 8 个账号跑满 30 天。账号多建议升级付费套餐。

</details>

---

## 📄 License

MIT — 随意使用，欢迎 star ⭐
