# 📊 TikTok Creator Tracker

> 用 AI Agent 自动追踪 TikTok 创作者数据，每日飞书卡片播报 + 周报一键生成

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)]()
[![Powered by](https://img.shields.io/badge/powered%20by-Claude%20Code-blueviolet.svg)](https://claude.ai)

---

## ✨ 能做什么

| 功能 | 说明 |
|------|------|
| 📡 **多账号追踪** | 同时监控任意数量 TikTok 创作者 |
| 📬 **每日卡片日报** | 每天 10:00 自动推送飞书互动卡片，含 Top 排名 + 视频明细 |
| 📊 **数据底表** | 每日视频数据自动写入飞书多维表格，可筛选、排序、分析 |
| 📈 **零配额周报** | 从多维表格聚合历史数据，出周报不额外消耗 API |
| 🤖 **Agent Skill** | 附带 Claude Code Skill，新用户对话式完成全套配置 |

---

## 🖼️ 效果预览

**日报卡片**（每天 10:00 自动推送）

```
┌─────────────────────────────────────────┐
│ 📊 TikTok 日报 · 2026-05-12             │
├─────────────────────────────────────────┤
│ 共 6 位作者监控｜今日发布 3 条｜         │
│ 总播放 1.54w｜点赞 1,620｜评论 42       │
├─────────────────────────────────────────┤
│ 🏆 今日 Top 播放                         │
│  #1  @creator_a    粉丝66.1w  VV 1.39w  │
│  #2  @creator_b    粉丝 1.2w  VV 1,075  │
│  #3  @creator_c    粉丝 0.1w  VV   427  │
├─────────────────────────────────────────┤
│ 📋 今日视频明细                           │
│  账号 / 时间 / VV / Like / 评论 / 内容   │
├─────────────────────────────────────────┤
│ ⚠️ 停更预警：@creator_d（最后发布04-30） │
├─────────────────────────────────────────┤
│  [📊 查看多维表格明细]                    │
└─────────────────────────────────────────┘
```

**周报卡片**（手动触发，从多维表格聚合）

```
┌─────────────────────────────────────────┐
│ 📊 TikTok 周报 · 05-05 ~ 05-12          │
├─────────────────────────────────────────┤
│ 7天｜发布 13 条｜总VV 6.16w｜点赞 7,086  │
├─────────────────────────────────────────┤
│ 📋 本期账号概览                           │
│  账号 / 发布 / 总VV / Like / 评论        │
├─────────────────────────────────────────┤
│ 🔥 爆款 Top 3                            │
│  🥇 @creator_a · 05-06 · VV 1.39w      │
│  🥈 @creator_a · 05-09 · VV 1.36w      │
│  🥉 @creator_a · 05-05 · VV 0.98w      │
├─────────────────────────────────────────┤
│  [📊 查看多维表格明细]                    │
└─────────────────────────────────────────┘
```

---

## 🏗️ 架构

```
TikTok API (RapidAPI)
       ↓ 每天 10:00 拉取
tiktok_daily_report.py
       ├──→ 飞书多维表格（底表，每条视频一行）
       └──→ 飞书卡片日报（懒羊羊 bot 推送）

tiktok_weekly_report.py（手动触发）
       ├── 读多维表格历史数据（不消耗 API 配额）
       └──→ 飞书卡片周报
```

---

## 📦 前置依赖

- **Python 3.8+**
- **[lark-cli](https://www.npmjs.com/package/@larksuite/cli)**：飞书命令行工具

  ```bash
  npm install -g @larksuite/cli
  ```

- **[RapidAPI tiktok-api23](https://rapidapi.com/Lundehund/api/tiktok-api23)**：TikTok 数据接口
  - 免费套餐：500次/月，6~8个账号约够用3周
  - 付费套餐：约 $10/月，不限量

- **Python 依赖**

  ```bash
  pip3 install requests
  ```

---

## 🚀 快速开始

### 方式一：用 Claude Code Agent 自动配置（推荐）

1. 安装 [Claude Code](https://claude.ai/download)
2. 安装 Skill：把 `SKILL.md` 的内容复制发给 Claude，说：
   > 「这是一个 Skill，请按照里面的步骤帮我配置 TikTok 创作者追踪」
3. Claude 会全程对话式引导你完成配置，约 15 分钟

### 方式二：手动配置

**1. 写入 RapidAPI Key**

```bash
mkdir -p ~/.config/tiktok-tracker
echo "你的KEY" > ~/.config/tiktok-tracker/rapidapi.key
```

**2. 创建配置文件**

```bash
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
```

**3. 设置每日定时任务**

```bash
SCRIPT_DIR="/path/to/scripts"
(crontab -l 2>/dev/null; echo "0 10 * * * /usr/bin/python3 $SCRIPT_DIR/tiktok_daily_report.py >> $SCRIPT_DIR/tiktok_daily_report.log 2>&1") | crontab -
```

---

## 📖 使用说明

### 手动触发日报

```bash
python3 tiktok_daily_report.py
```

### 触发周报（指定天数）

```bash
python3 tiktok_weekly_report.py --days 7
```

### 直接查询数据（不发飞书）

```bash
# 查账号近7天数据
python3 tiktok_vv_tracker.py user creator1 creator2 --days 7

# 查单个视频
python3 tiktok_vv_tracker.py video 7638266780699331848

# 搜索关键词
python3 tiktok_vv_tracker.py search "cookie run kingdom" --count 20

# 查话题 Top 视频
python3 tiktok_vv_tracker.py hashtag cookierunkingdom --top 20
```

---

## ⚙️ 配置说明

| 字段 | 说明 |
|------|------|
| `accounts` | 要追踪的 TikTok 用户名列表（不带@） |
| `dimensions` | 追踪维度：VV / Like / Comment / Share / Collect / 粉丝数 |
| `bitable_token` | 飞书多维表格 base token |
| `bitable_table_id` | 数据表 ID |
| `feishu_open_id` | 接收日报的飞书用户 open_id |
| `script_dir` | 脚本所在目录的绝对路径 |

---

## 🤖 Claude Code Skill

`SKILL.md` 是一个可直接交给任意 Claude Code Agent 的 Skill 文件。

**功能覆盖：**
- 引导新用户注册 RapidAPI 并写入 Key
- 引导输入追踪账号列表和数据维度
- 自动创建飞书多维表格并建表
- 检测脚本路径，写入 config.json
- 设置 crontab 定时任务
- 周报模式：从多维表格聚合发卡片

**使用方式：** 把 `SKILL.md` 内容发给 Claude，然后说「帮我配置 TikTok 追踪」即可。

---

## ❓ 常见问题

<details>
<summary>API 配额用完了怎么办？</summary>

脚本会直接提示配额耗尽，前往 RapidAPI 升级套餐后重新运行即可，配置文件不需要修改。

</details>

<details>
<summary>账号找不到数据？</summary>

TikTok 用户名区分大小写，确认填写的是 URL 里的 uniqueId（不是昵称）。

</details>

<details>
<summary>飞书卡片没收到？</summary>

检查 lark-cli 的 bot 权限，运行 `lark-cli auth login --domain im` 重新授权。

</details>

<details>
<summary>周报只有 0 条数据？</summary>

周报从多维表格聚合数据，需要先跑过至少一次日报写入数据后才能生成周报。

</details>

---

## 📄 License

MIT — 随意使用，欢迎 star ⭐
