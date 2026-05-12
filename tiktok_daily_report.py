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


def bitable_url(base_token, table_id):
    return f"https://www.feishu.cn/base/{base_token}?table={table_id}"


def build_daily_card(accounts_data, today_str, base_token, table_id):
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

    elements = [
        {
            "tag": "markdown",
            "content": (
                f"共 **{len(accounts_data)}** 位作者监控｜"
                f"今日发布 **{total_videos}** 条｜"
                f"总播放 **{fmt_num(total_vv)}**｜"
                f"点赞 **{fmt_num(total_like)}**｜"
                f"评论 **{fmt_num(total_comment)}**"
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
            ],
            "rows": [
                {
                    "rank": f"#{i+1}",
                    "account": f"@{acc['uniqueId']}",
                    "followers": fmt_num(acc.get("followerCount", 0)),
                    "vv": fmt_num(acc.get("totalVV", 0)),
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

    if base_token and table_id:
        fields, rows = build_video_rows(accounts_data, dimensions)
        write_to_bitable(base_token, table_id, fields, rows)
    else:
        print("  ⚠️ 未配置 bitable_token/table_id，跳过写入")

    if open_id:
        card = build_daily_card(accounts_data, today_str, base_token, table_id)
        send_feishu_card(open_id, card)
    else:
        print("  ⚠️ 未配置 feishu_open_id，跳过发送")


if __name__ == "__main__":
    main()
