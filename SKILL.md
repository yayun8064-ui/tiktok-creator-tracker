---
name: tiktok-weekly-report
version: 3.1.0
description: "TikTok 创作者追踪助手。支持：初始化配置（引导账号列表/数据维度/自动建表/自动安装脚本）、每日飞书卡片播报（cron驱动，含环比昨日涨跌）、手动触发周报卡片（从多维表格聚合，含环比上期对比）。当用户说：TikTok周报、出周报、创作者日报、配置TikTok追踪、初始化TikTok、帮我追踪这些TikTok账号 时触发。"
metadata:
  requires:
    bins: ["python3", "pip3", "lark-cli"]
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
lark-cli auth status --format json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('userOpenId',''))"
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

### D. 安装脚本

创建脚本目录并安装 Python 依赖：
```bash
mkdir -p ~/.config/tiktok-tracker/scripts
pip3 install requests --quiet
```

写入 `tiktok_vv_tracker.py`：
```bash
cat > ~/.config/tiktok-tracker/scripts/tiktok_vv_tracker.py << 'PYEOF'
"""
TikTok 数据查询工具 — 覆盖 tiktok-api23 所有可用端点

可用模式：
  user      查账号信息 + 视频数据（默认）
  video     查单个视频详情
  hashtag   查话题/挑战信息 + Top 视频
  search    关键词搜索视频
  comments  查视频评论

用法：
  python3 tiktok_vv_tracker.py user account1 account2 --days 2
  python3 tiktok_vv_tracker.py video <video_id>
  python3 tiktok_vv_tracker.py hashtag <hashtag> --top 20
  python3 tiktok_vv_tracker.py search "keyword" --count 20
  python3 tiktok_vv_tracker.py comments <video_id> --count 20
  RAPIDAPI_KEY=xxx python3 tiktok_vv_tracker.py user account1
"""

import argparse
import json
import os
import sys
import time
import requests
from datetime import datetime

def _load_key():
    # 1. 环境变量优先
    if os.environ.get("RAPIDAPI_KEY"):
        return os.environ["RAPIDAPI_KEY"]
    # 2. 本地配置文件
    cfg = os.path.expanduser("~/.config/tiktok-tracker/rapidapi.key")
    if os.path.exists(cfg):
        return open(cfg).read().strip()
    return None

RAPIDAPI_KEY = _load_key()
if not RAPIDAPI_KEY:
    print("❌ 未找到 RapidAPI Key。", file=sys.stderr)
    print("   请前往 https://rapidapi.com/Lundehund/api/tiktok-api23 订阅后，", file=sys.stderr)
    print("   将 Key 写入 ~/.config/tiktok-tracker/rapidapi.key，或设置环境变量 RAPIDAPI_KEY=xxx", file=sys.stderr)
    sys.exit(1)
BASE = "https://tiktok-api23.p.rapidapi.com"
H = {
    "x-rapidapi-host": "tiktok-api23.p.rapidapi.com",
    "x-rapidapi-key": RAPIDAPI_KEY,
}


def get(path: str, params: dict = None) -> dict:
    try:
        r = requests.get(f"{BASE}{path}", headers=H, params=params or {}, timeout=12)
        d = r.json()
        msg = d.get("message", "")
        if "exceeded" in msg and "quota" in msg.lower():
            print(f"❌ API 月度配额已用完，请升级 RapidAPI 套餐或下月再用。\n   {msg}", file=sys.stderr)
            sys.exit(2)
        if "Invalid API key" in msg:
            print(f"❌ API Key 无效，请检查 RAPIDAPI_KEY。", file=sys.stderr)
            sys.exit(2)
        return d.get("data", d)
    except SystemExit:
        raise
    except Exception as e:
        return {"_error": str(e)}


def fmt(n) -> str:
    try:
        n = int(n)
    except Exception:
        return str(n)
    if n >= 100_000_000:
        return f"{n/100_000_000:.1f}亿"
    if n >= 10_000:
        return f"{n/10000:.1f}w"
    return f"{n:,}"


# ──────────────────────────────────────────────
# 各模式实现
# ──────────────────────────────────────────────

def mode_user(accounts: list[str], days: int, count: int = 35) -> dict:
    since_ts = int(time.time()) - days * 86400
    since_str = datetime.fromtimestamp(since_ts).strftime("%Y-%m-%d %H:%M")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    results = []
    for raw_uid in accounts:
        uid = raw_uid.lstrip("@").strip()

        # 获取账号信息
        d = get("/api/user/info", {"uniqueId": uid})
        info = d.get("userInfo", {})
        user = info.get("user", {})
        stats = info.get("stats", {})

        if not user.get("secUid"):
            results.append({"uniqueId": uid, "error": "账号未找到"})
            continue

        sec_uid = user["secUid"]

        # 获取帖子
        pd = get("/api/user/posts", {"secUid": sec_uid, "count": count, "cursor": 0})
        posts = pd.get("itemList", pd.get("item_list", []))

        recent = [p for p in posts if p.get("createTime", 0) >= since_ts]

        videos = []
        for p in recent:
            st = p.get("stats", {})
            videos.append({
                "videoId": p.get("id", ""),
                "time": datetime.fromtimestamp(p["createTime"]).strftime("%m-%d %H:%M"),
                "desc": p.get("desc", "")[:80],
                "vv": st.get("playCount", 0),
                "like": st.get("diggCount", 0),
                "share": st.get("shareCount", 0),
                "comment": st.get("commentCount", 0),
                "collect": int(st.get("collectCount", 0) or 0),
            })

        latest_time = ""
        if posts:
            latest_time = datetime.fromtimestamp(posts[0].get("createTime", 0)).strftime("%Y-%m-%d %H:%M")

        results.append({
            "uniqueId": user.get("uniqueId", uid),
            "nickname": user.get("nickname", ""),
            "secUid": sec_uid,
            "verified": user.get("verified", False),
            "followerCount": stats.get("followerCount", 0),
            "followingCount": stats.get("followingCount", 0),
            "videoCount": stats.get("videoCount", 0),
            "heartCount": stats.get("heartCount", 0),
            "recentVideoCount": len(recent),
            "latestPostTime": latest_time,
            "totalVV": sum(v["vv"] for v in videos),
            "totalLike": sum(v["like"] for v in videos),
            "totalShare": sum(v["share"] for v in videos),
            "totalComment": sum(v["comment"] for v in videos),
            "videos": videos,
        })
        time.sleep(0.3)

    return {
        "mode": "user",
        "period": f"{since_str} ~ {now_str}",
        "days": days,
        "accounts": results,
    }


def mode_video(video_ids: list[str]) -> dict:
    results = []
    for vid in video_ids:
        d = get("/api/post/detail", {"videoId": vid})
        item = d.get("itemInfo", {}).get("itemStruct", {})
        if not item:
            results.append({"videoId": vid, "error": "视频未找到"})
            continue
        st = item.get("stats", {})
        au = item.get("author", {})
        music = item.get("music", {})
        results.append({
            "videoId": vid,
            "desc": item.get("desc", ""),
            "createTime": datetime.fromtimestamp(item.get("createTime", 0)).strftime("%Y-%m-%d %H:%M"),
            "author": {
                "uniqueId": au.get("uniqueId", ""),
                "nickname": au.get("nickname", ""),
                "followerCount": au.get("followerCount", 0),
            },
            "stats": {
                "vv": st.get("playCount", 0),
                "like": st.get("diggCount", 0),
                "share": st.get("shareCount", 0),
                "comment": st.get("commentCount", 0),
                "collect": int(st.get("collectCount", 0) or 0),
            },
            "music": {
                "title": music.get("title", ""),
                "author": music.get("authorName", ""),
                "id": music.get("id", ""),
            },
            "hashtags": [t.get("hashtagName", "") for t in item.get("challenges", [])],
        })
        time.sleep(0.2)
    return {"mode": "video", "videos": results}


def mode_hashtag(names: list[str], top: int = 20) -> dict:
    results = []
    for name in names:
        name = name.lstrip("#").strip()

        # 获取话题信息
        cd = get("/api/challenge/info", {"challengeName": name})
        ch_info = cd.get("challengeInfo", {})
        ch = ch_info.get("challenge", {})
        ch_stats = ch_info.get("stats", {})

        if not ch.get("id"):
            results.append({"name": name, "error": "话题未找到"})
            continue

        ch_id = ch["id"]

        # 获取话题下的视频
        pd = get("/api/challenge/posts", {"challengeId": ch_id, "count": top, "cursor": 0})
        posts = pd.get("itemList", pd.get("item_list", []))

        top_videos = []
        for p in posts:
            st = p.get("stats", {})
            au = p.get("author", {})
            top_videos.append({
                "videoId": p.get("id", ""),
                "time": datetime.fromtimestamp(p.get("createTime", 0)).strftime("%Y-%m-%d"),
                "author": au.get("uniqueId", ""),
                "desc": p.get("desc", "")[:60],
                "vv": st.get("playCount", 0),
                "like": st.get("diggCount", 0),
                "share": st.get("shareCount", 0),
            })

        top_videos.sort(key=lambda x: x["vv"], reverse=True)

        results.append({
            "name": name,
            "challengeId": ch_id,
            "title": ch.get("title", name),
            "desc": ch.get("desc", ""),
            "viewCount": ch_stats.get("viewCount", 0),
            "videoCount": ch_stats.get("videoCount", 0),
            "topVideos": top_videos,
        })
        time.sleep(0.3)

    return {"mode": "hashtag", "hashtags": results}


def mode_search(keyword: str, count: int = 20) -> dict:
    d = get("/api/search/general", {"keyword": keyword, "count": count, "cursor": 0})
    items = d.get("item_list", [])

    videos = []
    for item in items:
        st = item.get("stats", {})
        au = item.get("author", {})
        videos.append({
            "videoId": item.get("id", ""),
            "time": datetime.fromtimestamp(item.get("createTime", 0)).strftime("%Y-%m-%d"),
            "author": au.get("uniqueId", ""),
            "nickname": au.get("nickname", ""),
            "desc": item.get("desc", "")[:80],
            "vv": st.get("playCount", 0),
            "like": st.get("diggCount", 0),
            "share": st.get("shareCount", 0),
            "comment": st.get("commentCount", 0),
        })

    videos.sort(key=lambda x: x["vv"], reverse=True)
    return {"mode": "search", "keyword": keyword, "count": len(videos), "videos": videos}


def mode_comments(video_id: str, count: int = 20) -> dict:
    d = get("/api/post/comments", {"videoId": video_id, "count": count, "cursor": 0})
    raw_comments = d.get("comments", [])

    comments = []
    for c in raw_comments:
        user = c.get("user", {})
        comments.append({
            "author": user.get("uniqueId", ""),
            "nickname": user.get("nickname", ""),
            "text": c.get("text", ""),
            "likeCount": c.get("diggCount", 0),
            "replyCount": c.get("reply_comment_total", 0),
            "time": datetime.fromtimestamp(c.get("createTime", 0)).strftime("%Y-%m-%d %H:%M"),
        })

    return {"mode": "comments", "videoId": video_id, "count": len(comments), "comments": comments}


# ──────────────────────────────────────────────
# 人类可读输出
# ──────────────────────────────────────────────

def print_user(data: dict):
    print(f"\n📊 TikTok 账号数据  |  {data['period']}（{data['days']}天）\n")
    for acc in data["accounts"]:
        if "error" in acc:
            print(f"❌ @{acc['uniqueId']}: {acc['error']}\n")
            continue
        v_mark = "✅" if acc.get("verified") else ""
        print(f"@{acc['uniqueId']} {v_mark}  {acc['nickname']}")
        print(f"   粉丝 {fmt(acc['followerCount'])}  |  关注 {fmt(acc['followingCount'])}  |  总视频 {acc['videoCount']}  |  总获赞 {fmt(acc['heartCount'])}")
        print(f"   过去{data['days']}天: {acc['recentVideoCount']}条  VV {fmt(acc['totalVV'])}  Like {fmt(acc['totalLike'])}  Share {fmt(acc['totalShare'])}")
        if acc["videos"]:
            for v in acc["videos"]:
                print(f"   [{v['time']}] VV {fmt(v['vv']):>8}  Like {fmt(v['like']):>7}  Share {fmt(v['share']):>6}  {v['desc'][:50]}")
        else:
            print(f"   （过去{data['days']}天无发布，最新: {acc['latestPostTime']}）")
        print()


def print_video(data: dict):
    print(f"\n🎬 视频详情\n")
    for v in data["videos"]:
        if "error" in v:
            print(f"❌ {v['videoId']}: {v['error']}\n")
            continue
        print(f"ID: {v['videoId']}")
        print(f"发布: {v['createTime']}  作者: @{v['author']['uniqueId']} ({v['author']['nickname']})")
        print(f"内容: {v['desc']}")
        st = v["stats"]
        print(f"VV {fmt(st['vv'])}  Like {fmt(st['like'])}  Share {fmt(st['share'])}  Comment {fmt(st['comment'])}  Collect {fmt(st['collect'])}")
        if v["hashtags"]:
            print(f"话题: {', '.join('#'+t for t in v['hashtags'])}")
        if v["music"]["title"]:
            print(f"BGM: {v['music']['title']} — {v['music']['author']}")
        print()


def print_hashtag(data: dict):
    print(f"\n🏷️  话题数据\n")
    for h in data["hashtags"]:
        if "error" in h:
            print(f"❌ #{h['name']}: {h['error']}\n")
            continue
        print(f"#{h['title']}  (ID: {h['challengeId']})")
        print(f"   总播放 {fmt(h['viewCount'])}  |  视频数 {fmt(h['videoCount'])}")
        if h["topVideos"]:
            print(f"   Top {len(h['topVideos'])} 视频:")
            for i, v in enumerate(h["topVideos"], 1):
                print(f"   {i:>2}. [{v['time']}] @{v['author']:20}  VV {fmt(v['vv']):>8}  Like {fmt(v['like']):>7}  {v['desc'][:40]}")
        print()


def print_search(data: dict):
    print(f"\n🔍 搜索: {data['keyword']}  (共 {data['count']} 条)\n")
    for i, v in enumerate(data["videos"], 1):
        print(f"{i:>2}. [{v['time']}] @{v['author']:20}  VV {fmt(v['vv']):>8}  Like {fmt(v['like']):>7}  {v['desc'][:45]}")
    print()


def print_comments(data: dict):
    print(f"\n💬 视频 {data['videoId']} 评论 (共 {data['count']} 条)\n")
    for c in data["comments"]:
        print(f"@{c['author']} ({c['nickname']})  [{c['time']}]  👍{fmt(c['likeCount'])}  回复{c['replyCount']}")
        print(f"   {c['text']}")
        print()


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TikTok 数据查询工具")
    sub = parser.add_subparsers(dest="mode")

    # user 模式
    p_user = sub.add_parser("user", help="查账号信息和近期视频数据")
    p_user.add_argument("accounts", nargs="+")
    p_user.add_argument("--days", type=int, default=2)
    p_user.add_argument("--count", type=int, default=35, help="拉取帖子数量上限")

    # video 模式
    p_video = sub.add_parser("video", help="查单个视频详情")
    p_video.add_argument("video_ids", nargs="+")

    # hashtag 模式
    p_tag = sub.add_parser("hashtag", help="查话题信息和Top视频")
    p_tag.add_argument("names", nargs="+")
    p_tag.add_argument("--top", type=int, default=20)

    # search 模式
    p_search = sub.add_parser("search", help="关键词搜索视频")
    p_search.add_argument("keyword")
    p_search.add_argument("--count", type=int, default=20)

    # comments 模式
    p_comments = sub.add_parser("comments", help="查视频评论")
    p_comments.add_argument("video_id")
    p_comments.add_argument("--count", type=int, default=20)

    # 全局参数
    for p in [p_user, p_video, p_tag, p_search, p_comments]:
        p.add_argument("--json", action="store_true", help="只输出 JSON")

    # 兼容旧用法：直接传账号（无子命令）
    if len(sys.argv) > 1 and not sys.argv[1] in ("user", "video", "hashtag", "search", "comments", "-h", "--help"):
        sys.argv.insert(1, "user")

    args = parser.parse_args()
    if not args.mode:
        parser.print_help()
        sys.exit(0)

    raw_json = getattr(args, "json", False)

    if args.mode == "user":
        data = mode_user(args.accounts, args.days, args.count)
        if raw_json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print_user(data)
            print(json.dumps({"summary": data}, ensure_ascii=False))

    elif args.mode == "video":
        data = mode_video(args.video_ids)
        if raw_json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print_video(data)
            print(json.dumps({"summary": data}, ensure_ascii=False))

    elif args.mode == "hashtag":
        data = mode_hashtag(args.names, args.top)
        if raw_json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print_hashtag(data)
            print(json.dumps({"summary": data}, ensure_ascii=False))

    elif args.mode == "search":
        data = mode_search(args.keyword, args.count)
        if raw_json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print_search(data)
            print(json.dumps({"summary": data}, ensure_ascii=False))

    elif args.mode == "comments":
        data = mode_comments(args.video_id, args.count)
        if raw_json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print_comments(data)
            print(json.dumps({"summary": data}, ensure_ascii=False))


if __name__ == "__main__":
    main()

PYEOF
```

写入 `tiktok_daily_report.py`：
```bash
cat > ~/.config/tiktok-tracker/scripts/tiktok_daily_report.py << 'PYEOF'
#!/usr/bin/env python3
"""
TikTok 创作者每日播报（卡片版）
- 读取 ~/.config/tiktok-tracker/config.json
- 拉取今日新发视频数据
- 发飞书互动卡片给用户
- 写入多维表格（每条视频一行）
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

CONFIG_PATH = os.path.expanduser("~/.config/tiktok-tracker/config.json")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CST = timezone(timedelta(hours=8))


def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"❌ 配置文件不存在: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def run_tracker(accounts):
    cmd = ["python3", f"{SCRIPT_DIR}/tiktok_vv_tracker.py", "user", *accounts, "--days", "1"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout
    for i, line in enumerate(output.strip().split("\n")):
        if line.strip().startswith('{"summary"'):
            return json.loads("\n".join(output.strip().split("\n")[i:]))
    print("❌ 未找到 JSON 输出", file=sys.stderr)
    print(result.stderr, file=sys.stderr)
    sys.exit(1)


def fmt_num(n):
    if n >= 10000:
        return f"{n/10000:.1f}w"
    return f"{n:,}"


def fmt_pct(curr, prev):
    if not prev:
        return "—"
    pct = (curr - prev) / prev * 100
    if pct >= 0:
        return f"<font color='green'>+{pct:.1f}%</font>"
    return f"<font color='red'>{pct:.1f}%</font>"


def read_bitable_prev_period(base_token, table_id, target_date_str):
    """读取多维表格中指定日期的数据，按账号聚合，返回 {uniqueId: {vv, like, comment}}"""
    if not base_token or not table_id:
        return {}
    cmd = [
        "lark-cli", "base", "+record-list",
        "--base-token", base_token, "--table-id", table_id,
        "--format", "json", "--limit", "200", "--as", "user",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        resp = json.loads(result.stdout)
    except Exception:
        return {}
    if not resp.get("ok"):
        return {}
    data = resp.get("data", {})
    fields = data.get("fields", [])
    stats = {}
    for row in data.get("data", []):
        record = dict(zip(fields, row))
        pub_time = str(record.get("发布时间", "") or "")
        if not pub_time.startswith(target_date_str):
            continue
        uid = record.get("账号", "")
        if not uid:
            continue
        if uid not in stats:
            stats[uid] = {"vv": 0, "like": 0, "comment": 0}
        stats[uid]["vv"] += int(record.get("VV") or 0)
        stats[uid]["like"] += int(record.get("Like") or 0)
        stats[uid]["comment"] += int(record.get("Comment") or 0)
    return stats


def bitable_url(base_token, table_id):
    return f"https://www.feishu.cn/base/{base_token}?table={table_id}"


def build_daily_card(accounts_data, today_str, base_token, table_id, prev_stats=None):
    active = [a for a in accounts_data if not a.get("error") and a.get("recentVideoCount", 0) > 0]
    inactive = [a for a in accounts_data if not a.get("error") and a.get("recentVideoCount", 0) == 0]
    errors = [a for a in accounts_data if a.get("error")]

    total_videos = sum(a.get("recentVideoCount", 0) for a in active)
    total_vv = sum(a.get("totalVV", 0) for a in active)
    total_like = sum(a.get("totalLike", 0) for a in active)
    total_comment = sum(a.get("totalComment", 0) for a in active)

    ranked = sorted(active, key=lambda a: a.get("totalVV", 0), reverse=True)[:10]

    all_videos = []
    for acc in active:
        for v in acc.get("videos", []):
            all_videos.append({
                "account": acc["uniqueId"],
                "time": v.get("time", "")[-5:],
                "vv": fmt_num(v.get("vv", 0)),
                "like": fmt_num(v.get("like", 0)),
                "comment": str(v.get("comment", 0)),
                "desc": v.get("desc", "")[:30],
                "_vv_raw": v.get("vv", 0),
            })
    all_videos.sort(key=lambda v: v["_vv_raw"], reverse=True)

    prev_total_vv = sum(v.get("vv", 0) for v in prev_stats.values()) if prev_stats else 0
    prev_total_like = sum(v.get("like", 0) for v in prev_stats.values()) if prev_stats else 0
    prev_total_comment = sum(v.get("comment", 0) for v in prev_stats.values()) if prev_stats else 0

    elements = [
        {
            "tag": "markdown",
            "content": (
                f"共 **{len(accounts_data)}** 位作者监控｜"
                f"今日发布 **{total_videos}** 条｜"
                f"总播放 **{fmt_num(total_vv)}** {fmt_pct(total_vv, prev_total_vv)}｜"
                f"点赞 **{fmt_num(total_like)}** {fmt_pct(total_like, prev_total_like)}｜"
                f"评论 **{fmt_num(total_comment)}** {fmt_pct(total_comment, prev_total_comment)}"
            )
        },
        {"tag": "hr"},
    ]

    if ranked:
        elements.append({"tag": "markdown", "content": "🏆 **今日 Top 播放（新发视频）**"})
        elements.append({
            "tag": "table",
            "columns": [
                {"name": "rank", "display_name": "排名", "width": "auto"},
                {"name": "account", "display_name": "账号", "width": "auto"},
                {"name": "followers", "display_name": "粉丝", "width": "auto"},
                {"name": "vv", "display_name": "今日 VV", "width": "auto"},
                {"name": "change", "display_name": "环比昨日", "width": "auto"},
            ],
            "rows": [
                {
                    "rank": f"#{i+1}",
                    "account": f"@{acc['uniqueId']}",
                    "followers": fmt_num(acc.get("followerCount", 0)),
                    "vv": fmt_num(acc.get("totalVV", 0)),
                    "change": fmt_pct(
                        acc.get("totalVV", 0),
                        (prev_stats or {}).get(acc["uniqueId"], {}).get("vv", 0),
                    ),
                }
                for i, acc in enumerate(ranked)
            ]
        })
        elements.append({"tag": "hr"})

    if all_videos:
        elements.append({"tag": "markdown", "content": "📋 **今日视频明细**"})
        elements.append({
            "tag": "table",
            "columns": [
                {"name": "account", "display_name": "账号", "width": "auto"},
                {"name": "time", "display_name": "时间", "width": "auto"},
                {"name": "vv", "display_name": "VV", "width": "auto"},
                {"name": "like", "display_name": "Like", "width": "auto"},
                {"name": "comment", "display_name": "评论", "width": "auto"},
                {"name": "desc", "display_name": "内容", "width": "auto"},
            ],
            "rows": [
                {
                    "account": f"@{v['account']}",
                    "time": v["time"],
                    "vv": v["vv"],
                    "like": v["like"],
                    "comment": v["comment"],
                    "desc": v["desc"],
                }
                for v in all_videos
            ]
        })
        elements.append({"tag": "hr"})

    warnings = []
    for a in inactive:
        last = a.get("latestPostTime", "")[:10]
        warnings.append(f"@{a['uniqueId']}（最后发布 {last}）")
    for a in errors:
        warnings.append(f"@{a['uniqueId']}（异常）")
    if warnings:
        elements.append({"tag": "markdown", "content": "⚠️ 停更预警：" + "  ·  ".join(warnings)})
        elements.append({"tag": "hr"})

    if base_token and table_id:
        elements.append({
            "tag": "markdown",
            "content": f"[📊 查看多维表格明细]({bitable_url(base_token, table_id)})"
        })

    return {
        "schema": "2.0",
        "header": {
            "title": {"tag": "plain_text", "content": f"📊 TikTok 日报 · {today_str}"},
            "template": "indigo",
        },
        "body": {"elements": elements},
    }


def send_feishu_card(open_id, card):
    cmd = [
        "lark-cli", "im", "+messages-send",
        "--user-id", open_id,
        "--content", json.dumps(card, ensure_ascii=False),
        "--msg-type", "interactive",
        "--as", "bot",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        if data.get("ok"):
            print("✅ 飞书卡片发送成功")
        else:
            print(f"❌ 飞书卡片发送失败: {data.get('error', {}).get('message', result.stdout)}")
    except Exception:
        print(f"❌ 飞书卡片异常: {result.stdout}{result.stderr}")


def day_ts(date_str):
    if not date_str:
        return int(datetime.now(CST).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d").replace(tzinfo=CST)
        return int(dt.timestamp() * 1000)
    except Exception:
        return int(datetime.now(CST).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)


def build_video_rows(accounts_data, dimensions):
    dim_map = {
        "VV": "vv", "Like": "like", "Share": "share",
        "Comment": "comment", "Collect": "collect",
    }
    fields = ["日期", "账号", "昵称", "发布时间", "视频描述"]
    fields += [d for d in dimensions if d in dim_map]
    if "粉丝数" in dimensions:
        fields.append("粉丝数")

    rows = []
    for acc in accounts_data:
        if acc.get("error") or not acc.get("videos"):
            continue
        for v in acc["videos"]:
            pub_time = v.get("time", "")
            if pub_time and len(pub_time) == 11:
                pub_time = f"2026-{pub_time}"
            row = [
                day_ts(pub_time),
                acc.get("uniqueId", ""),
                acc.get("nickname", ""),
                pub_time,
                v.get("desc", "")[:100],
            ]
            for d in dimensions:
                if d in dim_map:
                    row.append(v.get(dim_map[d], 0))
            if "粉丝数" in dimensions:
                row.append(acc.get("followerCount", 0))
            rows.append(row)
    return fields, rows


def write_to_bitable(base_token, table_id, fields, rows):
    if not rows:
        print("  今日无新视频，跳过写入")
        return
    payload = json.dumps({"fields": fields, "rows": rows}, ensure_ascii=False)
    cmd = [
        "lark-cli", "base", "+record-batch-create",
        "--base-token", base_token,
        "--table-id", table_id,
        "--json", payload,
        "--as", "user",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        if data.get("ok"):
            print(f"✅ 写入多维表格成功，{len(rows)} 条视频记录")
        else:
            print(f"❌ 写入失败: {data.get('error', {}).get('message', result.stdout)}")
    except Exception:
        print(f"❌ 写入异常: {result.stdout}{result.stderr}")


def main():
    cfg = load_config()
    accounts = cfg.get("accounts", [])
    dimensions = cfg.get("dimensions", ["VV", "Like", "Comment"])
    base_token = cfg.get("bitable_token", "")
    table_id = cfg.get("bitable_table_id", "")
    open_id = cfg.get("feishu_open_id", "")

    if not accounts:
        print("❌ 账号列表为空", file=sys.stderr)
        sys.exit(1)

    today_str = datetime.now(CST).strftime("%Y-%m-%d")
    print(f"[{datetime.now(CST).strftime('%Y-%m-%d %H:%M')}] 开始拉取 TikTok 数据...")

    data = run_tracker(accounts)
    accounts_data = data.get("summary", {}).get("accounts", [])
    print(f"  拿到 {len(accounts_data)} 个账号数据")

    yesterday_str = (datetime.now(CST) - timedelta(days=1)).strftime("%Y-%m-%d")
    prev_stats = read_bitable_prev_period(base_token, table_id, yesterday_str) if base_token and table_id else {}
    print(f"  昨日对比数据：{len(prev_stats)} 个账号")

    if base_token and table_id:
        fields, rows = build_video_rows(accounts_data, dimensions)
        write_to_bitable(base_token, table_id, fields, rows)
    else:
        print("  ⚠️ 未配置 bitable_token/table_id，跳过写入")

    if open_id:
        card = build_daily_card(accounts_data, today_str, base_token, table_id, prev_stats=prev_stats)
        send_feishu_card(open_id, card)
    else:
        print("  ⚠️ 未配置 feishu_open_id，跳过发送")


if __name__ == "__main__":
    main()

PYEOF
```

写入 `tiktok_weekly_report.py`：
```bash
cat > ~/.config/tiktok-tracker/scripts/tiktok_weekly_report.py << 'PYEOF'
#!/usr/bin/env python3
"""
TikTok 创作者周报（卡片版）
- 从多维表格读取过去 N 天数据聚合
- 发飞书互动卡片（不生成文档）
用法：python3 tiktok_weekly_report.py [--days 7]
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

CONFIG_PATH = os.path.expanduser("~/.config/tiktok-tracker/config.json")
CST = timezone(timedelta(hours=8))


def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"❌ 配置文件不存在: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def fmt_num(n):
    if n >= 10000:
        return f"{n/10000:.1f}w"
    return f"{n:,}"


def fmt_pct(curr, prev):
    if not prev:
        return "—"
    pct = (curr - prev) / prev * 100
    if pct >= 0:
        return f"<font color='green'>+{pct:.1f}%</font>"
    return f"<font color='red'>{pct:.1f}%</font>"


def bitable_url(base_token, table_id):
    return f"https://www.feishu.cn/base/{base_token}?table={table_id}"


def read_bitable_records(base_token, table_id):
    """分页读取多维表格全量记录，返回 list[dict]"""
    records = []
    offset = 0
    limit = 200
    while True:
        cmd = [
            "lark-cli", "base", "+record-list",
            "--base-token", base_token,
            "--table-id", table_id,
            "--format", "json",
            "--limit", str(limit),
            "--offset", str(offset),
            "--as", "user",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        try:
            resp = json.loads(result.stdout)
        except Exception:
            print(f"❌ 读取多维表格失败: {result.stdout}{result.stderr}", file=sys.stderr)
            sys.exit(1)

        if not resp.get("ok"):
            print(f"❌ 读取失败: {resp.get('error', {}).get('message', result.stdout)}", file=sys.stderr)
            sys.exit(1)

        data = resp.get("data", {})
        fields = data.get("fields", [])
        rows = data.get("data", [])

        for row in rows:
            records.append(dict(zip(fields, row)))

        if not data.get("has_more"):
            break
        offset += limit

    return records


def parse_date(record):
    """从记录中提取日期，返回 date 对象"""
    val = record.get("发布时间") or record.get("日期") or ""
    if not val:
        return None
    try:
        # 格式可能是 "2026-05-11 00:00:00" 或 "2026-05-11 15:56"
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def aggregate(records, days, all_accounts, since=None, until=None):
    """按账号聚合指定日期范围的数据"""
    if since is None:
        since = (datetime.now(CST) - timedelta(days=days)).date()
    if until is None:
        until = datetime.now(CST).date()

    filtered = [r for r in records if parse_date(r) and since <= parse_date(r) <= until]

    # 按账号聚合
    account_stats = {}
    for r in filtered:
        uid = r.get("账号", "")
        if not uid:
            continue
        if uid not in account_stats:
            account_stats[uid] = {
                "uniqueId": uid,
                "nickname": r.get("昵称", uid),
                "vv": 0, "like": 0, "comment": 0, "share": 0,
                "video_count": 0,
                "videos": [],
            }
        s = account_stats[uid]
        s["vv"] += int(r.get("VV") or 0)
        s["like"] += int(r.get("Like") or 0)
        s["comment"] += int(r.get("Comment") or 0)
        s["share"] += int(r.get("Share") or 0)
        s["video_count"] += 1
        s["videos"].append({
            "date": str(parse_date(r)),
            "desc": str(r.get("视频描述", ""))[:40],
            "vv": int(r.get("VV") or 0),
        })

    # 停更账号（在 all_accounts 里但没数据）
    inactive = [uid for uid in all_accounts if uid not in account_stats]

    # Top 3 视频（跨账号）
    all_videos = []
    for s in account_stats.values():
        for v in s["videos"]:
            all_videos.append({"account": s["uniqueId"], **v})
    top3 = sorted(all_videos, key=lambda v: v["vv"], reverse=True)[:3]

    return account_stats, inactive, top3


def build_weekly_card(account_stats, inactive, top3, days, base_token, table_id, prev_stats=None):
    now = datetime.now(CST)
    end_str = now.strftime("%m-%d")
    start_str = (now - timedelta(days=days)).strftime("%m-%d")
    period = f"{start_str} ~ {end_str}"

    total_videos = sum(s["video_count"] for s in account_stats.values())
    total_vv = sum(s["vv"] for s in account_stats.values())
    total_like = sum(s["like"] for s in account_stats.values())
    total_comment = sum(s["comment"] for s in account_stats.values())

    ranked = sorted(account_stats.values(), key=lambda s: s["vv"], reverse=True)

    prev_total_vv = sum(s.get("vv", 0) for s in prev_stats.values()) if prev_stats else 0
    prev_total_like = sum(s.get("like", 0) for s in prev_stats.values()) if prev_stats else 0
    prev_total_comment = sum(s.get("comment", 0) for s in prev_stats.values()) if prev_stats else 0

    elements = [
        {
            "tag": "markdown",
            "content": (
                f"统计周期 **{period}**（{days}天）｜"
                f"发布 **{total_videos}** 条｜"
                f"总VV **{fmt_num(total_vv)}** {fmt_pct(total_vv, prev_total_vv)}｜"
                f"点赞 **{fmt_num(total_like)}** {fmt_pct(total_like, prev_total_like)}｜"
                f"评论 **{fmt_num(total_comment)}** {fmt_pct(total_comment, prev_total_comment)}"
            )
        },
        {"tag": "hr"},
        {"tag": "markdown", "content": "📋 **本期账号概览**"},
        {
            "tag": "table",
            "columns": [
                {"name": "account", "display_name": "账号", "width": "auto"},
                {"name": "videos", "display_name": "发布", "width": "auto"},
                {"name": "vv", "display_name": "总VV", "width": "auto"},
                {"name": "vv_change", "display_name": "环比", "width": "auto"},
                {"name": "like", "display_name": "Like", "width": "auto"},
                {"name": "comment", "display_name": "评论", "width": "auto"},
            ],
            "rows": [
                {
                    "account": f"@{s['uniqueId']}",
                    "videos": str(s["video_count"]),
                    "vv": fmt_num(s["vv"]),
                    "vv_change": fmt_pct(s["vv"], (prev_stats or {}).get(s["uniqueId"], {}).get("vv", 0)),
                    "like": fmt_num(s["like"]),
                    "comment": fmt_num(s["comment"]),
                }
                for s in ranked
            ]
        },
        {"tag": "hr"},
    ]

    if top3:
        medals = ["🥇", "🥈", "🥉"]
        top3_lines = "\n".join(
            f"{medals[i]} **@{v['account']}** · {v['date'][5:]} · VV **{fmt_num(v['vv'])}**\n> {v['desc']}"
            for i, v in enumerate(top3)
        )
        elements.append({"tag": "markdown", "content": f"🔥 **爆款 Top 3**\n\n{top3_lines}"})
        elements.append({"tag": "hr"})

    if inactive:
        names = "  ·  ".join(f"@{uid}" for uid in inactive)
        elements.append({"tag": "markdown", "content": f"⚠️ **停更预警**：{names}\n本周期内无发布内容"})
        elements.append({"tag": "hr"})

    elements.append({
        "tag": "markdown",
        "content": f"[📊 查看多维表格明细]({bitable_url(base_token, table_id)})"
    })

    return {
        "schema": "2.0",
        "header": {
            "title": {"tag": "plain_text", "content": f"📊 TikTok 周报 · {period}"},
            "template": "green",
        },
        "body": {"elements": elements},
    }


def send_feishu_card(open_id, card):
    cmd = [
        "lark-cli", "im", "+messages-send",
        "--user-id", open_id,
        "--content", json.dumps(card, ensure_ascii=False),
        "--msg-type", "interactive",
        "--as", "bot",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        if data.get("ok"):
            print("✅ 周报卡片发送成功")
        else:
            print(f"❌ 发送失败: {data.get('error', {}).get('message', result.stdout)}")
    except Exception:
        print(f"❌ 发送异常: {result.stdout}{result.stderr}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()

    cfg = load_config()
    base_token = cfg.get("bitable_token", "")
    table_id = cfg.get("bitable_table_id", "")
    open_id = cfg.get("feishu_open_id", "")
    all_accounts = cfg.get("accounts", [])

    if not base_token or not table_id:
        print("❌ 未配置 bitable_token/table_id", file=sys.stderr)
        sys.exit(1)

    print(f"📖 读取多维表格数据（过去 {args.days} 天）...")
    records = read_bitable_records(base_token, table_id)
    print(f"  共读取 {len(records)} 条记录")

    today = datetime.now(CST).date()
    current_since = today - timedelta(days=args.days)
    prev_since = current_since - timedelta(days=args.days)
    prev_until = current_since - timedelta(days=1)

    account_stats, inactive, top3 = aggregate(records, args.days, all_accounts, since=current_since, until=today)
    prev_stats, _, _ = aggregate(records, args.days, all_accounts, since=prev_since, until=prev_until)
    print(f"  聚合完成：{len(account_stats)} 个账号有数据，{len(inactive)} 个停更")

    card = build_weekly_card(account_stats, inactive, top3, args.days, base_token, table_id, prev_stats=prev_stats)

    if open_id:
        send_feishu_card(open_id, card)
    else:
        print("❌ 未配置 feishu_open_id", file=sys.stderr)


if __name__ == "__main__":
    main()

PYEOF
```

赋予执行权限：
```bash
chmod +x ~/.config/tiktok-tracker/scripts/*.py
```

验证安装：
```bash
python3 ~/.config/tiktok-tracker/scripts/tiktok_vv_tracker.py --help 2>&1 | head -3
```

### E. 保存配置文件

```bash
cat > ~/.config/tiktok-tracker/config.json << 'EOF'
{
  "accounts": ["<账号1>", "<账号2>"],
  "dimensions": ["VV", "Like", "Comment"],
  "bitable_token": "<base_token>",
  "bitable_table_id": "<table_id>",
  "feishu_open_id": "<用户 open_id>",
  "script_dir": "$HOME/.config/tiktok-tracker/scripts"
}
EOF
```

### F. 设置每日定时任务

检查是否已有 cron：
```bash
crontab -l 2>/dev/null | grep tiktok_daily_report
```

没有则添加（使用 $HOME 绝对路径，crontab 不展开 ~）：
```bash
(crontab -l 2>/dev/null; echo "0 10 * * * /usr/bin/python3 $HOME/.config/tiktok-tracker/scripts/tiktok_daily_report.py >> $HOME/.config/tiktok-tracker/tiktok_daily_report.log 2>&1") | crontab -
```

### G. 告知用户配置完成

```
✅ TikTok 追踪配置完成！

📋 追踪账号：X 个
📊 追踪维度：VV / Like / Comment
📅 每天 10:00 自动推送飞书卡片日报（含环比昨日涨跌，绿色 +% / 红色 -%）
📊 多维表格：https://www.feishu.cn/base/<base_token>

想看周报时，直接说「出周报」就行，卡片含环比上期对比。
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
python3 $HOME/.config/tiktok-tracker/scripts/tiktok_weekly_report.py --days <天数>
```

脚本自动完成：读取多维表格全量记录 → 按账号聚合（含上期对比）→ 提取 Top 3 爆款 → 识别停更账号 → 构建卡片推送到飞书。

卡片内容（绿色主题）：
- 统计周期 / 发布条数 / 总VV / 点赞 / 评论，含环比上期涨跌
- 本期账号概览表（含 VV 环比列，绿色 +% / 红色 -%）
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
