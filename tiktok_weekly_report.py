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


def aggregate(records, days, all_accounts):
    """按账号聚合过去 days 天的数据"""
    since = (datetime.now(CST) - timedelta(days=days)).date()

    filtered = [r for r in records if parse_date(r) and parse_date(r) >= since]

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


def build_weekly_card(account_stats, inactive, top3, days, base_token, table_id):
    now = datetime.now(CST)
    end_str = now.strftime("%m-%d")
    start_str = (now - timedelta(days=days)).strftime("%m-%d")
    period = f"{start_str} ~ {end_str}"

    total_videos = sum(s["video_count"] for s in account_stats.values())
    total_vv = sum(s["vv"] for s in account_stats.values())
    total_like = sum(s["like"] for s in account_stats.values())
    total_comment = sum(s["comment"] for s in account_stats.values())

    ranked = sorted(account_stats.values(), key=lambda s: s["vv"], reverse=True)

    elements = [
        {
            "tag": "markdown",
            "content": (
                f"统计周期 **{period}**（{days}天）｜"
                f"发布 **{total_videos}** 条｜"
                f"总VV **{fmt_num(total_vv)}**｜"
                f"点赞 **{fmt_num(total_like)}**｜"
                f"评论 **{fmt_num(total_comment)}**"
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
                {"name": "like", "display_name": "Like", "width": "auto"},
                {"name": "comment", "display_name": "评论", "width": "auto"},
            ],
            "rows": [
                {
                    "account": f"@{s['uniqueId']}",
                    "videos": str(s["video_count"]),
                    "vv": fmt_num(s["vv"]),
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

    account_stats, inactive, top3 = aggregate(records, args.days, all_accounts)
    print(f"  聚合完成：{len(account_stats)} 个账号有数据，{len(inactive)} 个停更")

    card = build_weekly_card(account_stats, inactive, top3, args.days, base_token, table_id)

    if open_id:
        send_feishu_card(open_id, card)
    else:
        print("❌ 未配置 feishu_open_id", file=sys.stderr)


if __name__ == "__main__":
    main()
