"""
TikTok 数据查询工具 — 覆盖 tiktok-api23 所有可用端点

可用模式：
  user      查账号信息 + 视频数据（默认）
  video     查单个视频详情
  hashtag   查话题/挑战信息 + Top 视频
  search    关键词搜索视频
  comments  查视频评论

用法：
  python3 tiktok_vv_tracker.py user cookierun_en genshinimpact_en --days 2
  python3 tiktok_vv_tracker.py video 7638266780699331848
  python3 tiktok_vv_tracker.py hashtag cookierunkingdom --top 20
  python3 tiktok_vv_tracker.py search "cookie run kingdom" --count 20
  python3 tiktok_vv_tracker.py comments 7638266780699331848 --count 20
  RAPIDAPI_KEY=xxx python3 tiktok_vv_tracker.py user cookierun_en
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
