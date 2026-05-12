---
name: tiktok-weekly-report
version: 3.0.0
description: "TikTok 创作者追踪助手。支持：初始化配置（引导账号列表/数据维度/自动建表）、每日飞书卡片播报（cron驱动）、手动触发周报卡片（从多维表格聚合，不消耗API配额）。当用户说：TikTok周报、出周报、创作者日报、配置TikTok追踪、初始化TikTok、帮我追踪这些TikTok账号 时触发。"
metadata:
  requires:
    bins: ["python3", "lark-cli"]
---

# TikTok 创作者追踪

## 入口判断（每次必做）

### Step 1：检查 RapidAPI Key

```bash
ls ~/.config/tiktok-tracker/rapidapi.key 2>/dev/null && echo "KEY_EXISTS" || echo "KEY_MISSING"
```

KEY_MISSING → 告知用户：
> 需要先配置 RapidAPI Key。步骤：
> 1. 打开 https://rapidapi.com/Lundehund/api/tiktok-api23
> 2. 注册/登录，选套餐订阅（免费 500次/月，6~8个账号约够用3周；付费套餐约$10/月不限量）
> 3. 订阅后页面右侧复制 `X-RapidAPI-Key`
> 4. 把 Key 告诉我，我帮你写入

拿到 Key 后：
```bash
mkdir -p ~/.config/tiktok-tracker
echo "<用户的KEY>" > ~/.config/tiktok-tracker/rapidapi.key
```
然后重新执行入口判断。

### Step 2：检查配置文件

```bash
cat ~/.config/tiktok-tracker/config.json 2>/dev/null || echo "CONFIG_MISSING"
```

- CONFIG_MISSING 或文件不完整 → 进入 **Setup 流程**
- 配置完整 → 根据用户意图跳转：
  - 用户说"出周报" / "周报" → **周报模式**
  - 其他 → 显示当前配置摘要，询问需要做什么

---

## Setup 流程（首次配置）

### A. 收集账号列表

问用户：
> 请把要追踪的 TikTok 账号用户名给我（每行一个，或空格分隔，不需要带@）

等待用户输入后继续。

### B. 选择追踪数据维度

展示可选维度，让用户选择：

| 维度 | 说明 | 推荐 |
|------|------|------|
| VV（播放量） | 统计周期内发布视频的总播放 | ✅ 必选 |
| Like（点赞） | 统计周期内总点赞 | ✅ 推荐 |
| Comment（评论） | 统计周期内总评论 | ✅ 推荐 |
| Share（转发） | 统计周期内总转发 | 可选 |
| Collect（收藏） | 统计周期内总收藏 | 可选 |
| 粉丝数 | 当前账号总粉丝数 | 可选 |

> 直接说"全要"或列出需要的维度（默认推荐三项：VV/Like/Comment）

### C. 创建飞书多维表格

获取用户 open_id：
```bash
lark-cli auth status 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('userOpenId',''))"
```

创建多维表格：
```bash
lark-cli base +base-create --name "TikTok 创作者数据" --time-zone "Asia/Shanghai" --as user 2>&1
```
记录返回的 `base_token`。

创建数据表（根据选择的维度动态拼接 fields）：

基础字段（固定，按此顺序）：
```json
[
  {"field_name": "日期", "type": "datetime"},
  {"field_name": "账号", "type": "text"},
  {"field_name": "昵称", "type": "text"},
  {"field_name": "发布时间", "type": "text"},
  {"field_name": "视频描述", "type": "text"}
]
```

维度字段（按用户选择追加，均为 number 类型）：
- VV → `{"field_name":"VV","type":"number"}`
- Like → `{"field_name":"Like","type":"number"}`
- Comment → `{"field_name":"Comment","type":"number"}`
- Share → `{"field_name":"Share","type":"number"}`
- Collect → `{"field_name":"Collect","type":"number"}`
- 粉丝数 → `{"field_name":"粉丝数","type":"number"}`

```bash
lark-cli base +table-create \
  --base-token <base_token> \
  --name "视频数据" \
  --fields '<拼好的 JSON 数组>' \
  --as user 2>&1
```
记录返回的 `table_id`。

### D. 检测脚本路径

定位三个脚本的实际位置：
```bash
find ~ -name "tiktok_vv_tracker.py" 2>/dev/null | head -1
find ~ -name "tiktok_daily_report.py" 2>/dev/null | head -1
find ~ -name "tiktok_weekly_report.py" 2>/dev/null | head -1
```

若找不到，告知用户：
> 未找到脚本文件，请告诉我 tiktok_vv_tracker.py / tiktok_daily_report.py / tiktok_weekly_report.py 放在哪个目录下。

记录三者共同的父目录为 `<script_dir>`。

### E. 保存配置文件

```bash
cat > ~/.config/tiktok-tracker/config.json << 'EOF'
{
  "accounts": ["<账号1>", "<账号2>"],
  "dimensions": ["VV", "Like", "Comment"],
  "bitable_token": "<base_token>",
  "bitable_table_id": "<table_id>",
  "feishu_open_id": "<用户 open_id>",
  "script_dir": "<script_dir>"
}
EOF
```

### F. 设置每日定时任务

检查是否已有 cron：
```bash
crontab -l 2>/dev/null | grep tiktok_daily_report
```

没有则添加（从 config 读路径，写入 10:00 定时任务）：
```bash
SCRIPT_DIR=$(python3 -c "import json,os; print(json.load(open(os.path.expanduser('~/.config/tiktok-tracker/config.json')))['script_dir'])")
(crontab -l 2>/dev/null; echo "0 10 * * * /usr/bin/python3 $SCRIPT_DIR/tiktok_daily_report.py >> $SCRIPT_DIR/tiktok_daily_report.log 2>&1") | crontab -
```

### G. 告知用户配置完成

```
✅ TikTok 追踪配置完成！

📋 追踪账号：X 个
📊 追踪维度：VV / Like / Comment
📅 每天 10:00 自动推送飞书卡片日报
📊 多维表格：https://www.feishu.cn/base/<base_token>

想看周报时，直接说「出周报」就行。
```

---

## 周报模式

### 触发条件
用户说"出周报"、"TikTok 周报"、"帮我出一期周报"等。

### 询问时间范围

问用户：
> 要出哪段时间的周报？比如"过去7天"、"上周一到周日"、"5月1日到5月7日"

换算为天数，记为 `<天数>`（向上取整）。

### 执行

从多维表格聚合数据，发飞书卡片（不调用 TikTok API，不消耗配额）：

```bash
SCRIPT_DIR=$(python3 -c "import json,os; print(json.load(open(os.path.expanduser('~/.config/tiktok-tracker/config.json')))['script_dir'])")
python3 $SCRIPT_DIR/tiktok_weekly_report.py --days <天数>
```

脚本自动完成：读取多维表格全量记录 → 按账号聚合 → 提取 Top 3 爆款 → 识别停更账号 → 构建卡片推送到飞书。

卡片内容（绿色主题）：
- 统计周期 / 发布条数 / 总VV / 点赞 / 评论
- 本期账号概览表
- 爆款 Top 3（含描述摘要）
- 停更预警账号列表
- 多维表格跳转链接

完成后告知用户"周报卡片已发送到你的飞书"。

---

## 修改账号列表

用户说"加账号"、"删账号"、"修改追踪列表"等：

1. 读取当前 config.json 显示现有账号
2. 按用户指示更新 accounts 列表
3. 写回 config.json
4. 告知更新结果，下次日报生效

---

## 注意事项

- **绝对不能**在任何输出中打印 RapidAPI Key 内容
- 日报和周报均以飞书互动卡片推送，不生成文档
- 多维表格是唯一数据底表，每日日报写入，卡片内附跳转链接
- 周报从多维表格聚合，不消耗 RapidAPI 配额
- 账号未找到时备注标注，不中断流程
- 配额耗尽时明确告知，引导用户升级套餐
