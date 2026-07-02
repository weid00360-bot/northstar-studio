#!/usr/bin/env python3
"""抖音创作者数据抓取脚本

抓取内容：
  - 用户基础信息
  - 全量视频列表（仅公开视频）+ 详细 metrics（mget）
  - 每条视频的「比往期」诊断数据（item_compare）
    口径：前5条视频各自发布后同等小时数内的均值
  - 每条视频的逐小时播放 / 涨粉趋势（metrics_trend）
  - 留存曲线（逐秒）+ 同类作品基准线 + 低谷时间段（realtime/analysis）
  - 跳出分析（逐秒跳出率 + 同类作品基准线）
  - 流量来源分布 + vs往期差值（play/source）
  - 章节点击率（item/chapter）
  - 搜索关键词（search/keyword）

用法：
  python3 fetch_douyin.py --cookie "..." --output /tmp/douyin_data.json
  python3 fetch_douyin.py --cookie-file ~/.douyin_cookie --recent 7
  python3 fetch_douyin.py --cookie-file ~/.douyin_cookie --recent 7 --skip-trend
"""

import argparse, json, time, sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print("pip install requests", file=sys.stderr)
    sys.exit(1)

CREATOR_BASE = "https://creator.douyin.com"
JANUS_BASE   = "https://creator.douyin.com/janus/douyin/creator/data"

# ── Session ────────────────────────────────────────────────────────────────

def make_session(cookie: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://creator.douyin.com/",
    })
    return s

def get_session(cookie: str = None):
    """自动 cookie 建 session:不传 cookie 就从浏览器自动读(用户只需登录抖音)。"""
    if cookie is None:
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from get_cookie import get_cookie
        cookie = get_cookie()
    return make_session(cookie)


import re as _re
from datetime import datetime as _dt

def parse_ct(v) -> float:
    """create_time 可能是 epoch 数字,也可能是"发布于2026年06月28日 13:18"显示串 → 统一转时间戳。"""
    if v in (None, ""):
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        pass
    m = _re.search(r'(\d{4})\D+(\d{1,2})\D+(\d{1,2})\D+(\d{1,2}):(\d{2})', str(v))
    if m:
        try:
            return _dt(*map(int, m.groups())).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def recent_posts_metrics(session, n: int = 30) -> list:
    """拉近 n 条视频的底表指标(按发布时间倒序),喂 baseline 反推北极星。"""
    ids = get_creator_item_ids(session)
    ids.sort(key=lambda v: parse_ct(v.get("create_time")), reverse=True)
    top = [d["item_id"] for d in ids[:n]]
    mm = get_metrics_batch(session, top)
    return [mm[i] for i in top if i in mm]


def _get(session, url, params=None, label="") -> dict:
    try:
        r = session.get(url, params=params, timeout=20)
        if r.status_code in (401, 403):
            print(f"  ⚠️  {label} → Cookie失效 (HTTP {r.status_code})", file=sys.stderr)
            return {}
        return r.json()
    except Exception as e:
        print(f"  ✗ {label} → {e}", file=sys.stderr)
        return {}

# ── User info ──────────────────────────────────────────────────────────────

def get_user_info(session) -> dict:
    data = _get(session, f"{CREATOR_BASE}/aweme/v1/creator/user/info/", label="user_info")
    p = data.get("user_profile", {})
    return {
        "nick_name":       p.get("nick_name", ""),
        "follower_count":  p.get("follower_count", 0),
        "total_favorited": p.get("total_favorited", 0),
        "uid":             p.get("unique_id", ""),
    }

# ── Video list + metrics ───────────────────────────────────────────────────

def get_creator_item_ids(session) -> list[dict]:
    """从创作者后台拿全量视频 item_id_plain（含私密视频，用于后续 mget）"""
    ids = []
    cursor = 0
    while True:
        data = _get(session, f"{CREATOR_BASE}/aweme/v1/creator/item/list/",
                    params={"count": 20, "cursor": cursor}, label="creator_item_list")
        # API returns item_info_list (not item_list)
        items = data.get("item_info_list") or data.get("item_list", [])
        if not items:
            break
        for item in items:
            ids.append({
                "item_id":    item.get("item_id_plain") or item.get("item_id", ""),
                "title":      item.get("title", ""),
                "create_time":item.get("create_time", ""),
                "duration":   item.get("duration", 0),
                # privacy determined later via mget view_count == 0
                "is_private": False,
            })
        if not data.get("has_more", False):
            break
        cursor = data.get("cursor", 0)
        time.sleep(0.3)
    return ids

def get_metrics_batch(session, item_ids: list[str]) -> dict:
    """mget 接口批量拉取详细指标，返回 {item_id: metrics_dict}"""
    result = {}
    # 逐条查询更稳定（批量时部分视频可能返回空）
    for iid in item_ids:
        data = _get(session,
                    f"{CREATOR_BASE}/web/api/creator/item/mget",
                    params={"ids": iid, "fields": "metrics,review,play_info"},
                    label=f"mget:{iid[:10]}")
        items = data.get("items", [])
        if items:
            item = items[0]
            m = item.get("metrics", {})
            result[iid] = {k: float(v) if v not in ("", None) else None
                           for k, v in m.items()}
            result[iid]["_duration"]    = item.get("video_info", {}).get("duration")
            result[iid]["_create_time"] = item.get("create_time")
            result[iid]["_description"] = item.get("description", "")
        time.sleep(0.2)
    return result

# ── item_compare ───────────────────────────────────────────────────────────

def get_item_compare(session, item_id: str) -> dict:
    """
    拉取「比往期」诊断数据。
    返回结构：
      {
        "compare_hour": 25,
        "compare_item_ids": [...],
        "metrics": [
          { "name": "completion_rate", "name_desc": "完播率",
            "self_value": 0.018, "compare_value": 0.021,
            "diff_value": -0.003, "change_ratio": -0.11,
            "change_type": 2,   # 0=好 1=差 2=中性
            "suggestion": "..." }
        ],
        "view_count_metric": { "self_value":1555, "compare_value":763,
                               "diff_value":792, "change_ratio":1.04 }
      }
    """
    data = _get(session,
                f"{JANUS_BASE}/diagnose/item_compare",
                params={"item_id": item_id, "selected_metric_count": 2},
                label=f"item_compare:{item_id[:10]}")
    if not data:
        return {}
    return {
        "compare_hour":      data.get("compare_hour"),
        "compare_item_ids":  data.get("compare_item_ids", []),
        "metrics":           data.get("metrics", []),
        "view_count_metric": data.get("view_count_metric", {}),
    }

# ── metrics_trend ──────────────────────────────────────────────────────────

TREND_METRICS = ["view_count", "subscribe_count", "like_count", "share_count"]

# ── Retention + bounce curve (留存/跳出分析) ──────────────────────────────

def get_retention_curves(session, item_id: str) -> dict:
    """
    拉取留存曲线和跳出分析，包含同类作品（大盘）基准线。

    抖音用两次相同接口请求返回不同 type 的数据：
      type=1 → 留存分析：current_item 从1.0开始逐秒下降（还有多少比例的人在看）
      type=2 → 跳出分析：current_item 每秒的跳出人数占比分布

    返回结构：
      {
        "retention": {
          "current_item":   [{"key": "00:05", "value": 0.38}, ...],  # 当前视频
          "similar_author": [{"key": "00:05", "value": 0.42}, ...],  # 同类作品基准
          "valley_list":    {"1": [{"start":"27","end":"28"}, ...]}   # 低谷时间段
        },
        "bounce": {
          "current_item":   [...],   # 每秒跳出率
          "similar_author": [...]    # 同类作品每秒跳出率
        }
      }
    """
    result = {}
    # analysis_type=1 → 留存曲线（current_item[0].value==1.0，逐秒还剩多少人在看）
    # analysis_type=7 → 跳出分析（每秒跳出人数分布）
    for analysis_type, label in [("1", "retention"), ("7", "bounce")]:
        data = _get(session,
                    f"{JANUS_BASE}/realtime/analysis/data_center",
                    params={"user_id": "", "item_id": item_id, "analysis_type": analysis_type},
                    label=f"retention_{label}:{item_id[:10]}")
        if not data:
            continue
        trend = data.get("analysis_trend", {})
        result[label] = {
            "current_item":   trend.get("current_item", []),
            "similar_author": trend.get("similar_author", []),  # 同类作品大盘
            "valley_list":    data.get("valley_list", {}),       # 自动识别的低谷
        }
        time.sleep(0.2)
    return result

# ── Play source (流量来源) ─────────────────────────────────────────────────

def get_play_source(session, item_id: str) -> list:
    """
    拉取流量来源分布。
    返回: [{"key": "homepage_hot", "value": 0.945, "history_difference": 0.024}, ...]

    key 含义:
      homepage_hot  推荐流（首页热门）
      homepage      主页
      follow        关注页
      search        搜索
      message       私信/通知
      familiar      熟人推荐
      other         其他
    """
    data = _get(session,
                f"{JANUS_BASE}/item/play/source",
                params={"item_id": item_id},
                label=f"play_source:{item_id[:10]}")
    return data.get("play_source", [])

# ── Chapter click rate (章节点击率) ───────────────────────────────────────

def get_chapter(session, item_id: str) -> dict:
    """
    拉取视频章节点击率（仅在视频有设置章节时有数据）。
    返回: {
      "chapters": [{"desc": "引言", "timestamp_ms": 2000, "click_rate": 0.4}, ...]
    }
    """
    data = _get(session,
                f"{JANUS_BASE}/item/chapter",
                params={"item_id": item_id},
                label=f"chapter:{item_id[:10]}")
    top = data.get("chapter_top_data", [])
    return {
        "chapters": [
            {
                "desc":         c.get("chapter_detail", {}).get("Desc", ""),
                "detail":       c.get("chapter_detail", {}).get("Detail", ""),
                "timestamp_ms": c.get("chapter_detail", {}).get("Timestamp", 0),
                "click_rate":   c.get("click_rate", 0),
            }
            for c in top
        ]
    }

# ── Search keywords (搜索关键词) ──────────────────────────────────────────

def get_search_keywords(session, item_id: str) -> list:
    """
    拉取引导用户搜索的关键词及占比。
    返回: [{"keyword": "AI U盘下乡风险", "percent": 0.334}, ...]
    """
    data = _get(session,
                f"{JANUS_BASE}/item_analysis/search/keyword",
                params={"item_id": item_id},
                label=f"keywords:{item_id[:10]}")
    return data.get("inspire_search", [])


def get_metrics_trend(session, item_id: str) -> dict:
    """
    拉取逐小时播放趋势。
    返回 { "view_count": [{"date_time": "2026-06-02 11:00:00", "value": 442}, ...], ... }
    """
    result = {}
    for metric in TREND_METRICS:
        data = _get(session,
                    f"{JANUS_BASE}/item_analysis/metrics_trend",
                    params={
                        "aid": "2906",
                        "app_name": "aweme_creator_platform",
                        "device_platform": "web",
                        "item_id": item_id,
                        "metrics_group": "0,1,3",
                        "metrics": metric,
                    },
                    label=f"trend:{metric[:8]}:{item_id[:10]}")
        points = data.get("trend_map", {}).get(metric, {}).get("0", [])
        if points:
            result[metric] = [
                {"date_time": p["date_time"], "value": float(p["value"])}
                for p in points
            ]
        time.sleep(0.2)
    return result

# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="抖音创作者数据抓取")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--cookie", help="直接传入 Cookie 字符串")
    grp.add_argument("--cookie-file", help="从文件读取 Cookie（默认 ~/.douyin_cookie）")
    parser.add_argument("--output",  default="/tmp/douyin_data.json", help="输出 JSON 路径")
    parser.add_argument("--recent",  type=int, default=0,
                        help="只抓最近 N 条公开视频的 compare/trend（0=全部，节省时间）")
    parser.add_argument("--skip-trend", action="store_true",
                        help="跳过 metrics_trend（速度更快）")
    args = parser.parse_args()

    cookie = args.cookie or Path(args.cookie_file or "~/.douyin_cookie").expanduser().read_text().strip()
    session = make_session(cookie)

    # 1. 用户信息
    print("① 获取用户信息...", file=sys.stderr)
    user = get_user_info(session)
    print(f"   账号: {user['nick_name']} | 粉丝: {user['follower_count']}", file=sys.stderr)

    # 2. 全量视频 ID（含私密）
    print("② 获取视频列表...", file=sys.stderr)
    all_ids = get_creator_item_ids(session)
    print(f"   共 {len(all_ids)} 条（含私密）", file=sys.stderr)

    public_ids = all_ids  # privacy filtered later via mget (view_count==0 = private)
    print(f"   将通过 mget view_count 过滤私密视频", file=sys.stderr)

    # 3. mget 详细指标（全量视频）
    print("③ 拉取详细 metrics（mget）...", file=sys.stderr)
    public_item_ids = [v["item_id"] for v in public_ids if v["item_id"]]
    metrics_map = get_metrics_batch(session, public_item_ids)
    print(f"   拿到 {len(metrics_map)} 条 metrics", file=sys.stderr)

    # 4. 组装视频列表，按发布时间排序
    videos = []
    for v in public_ids:
        iid = v["item_id"]
        m   = metrics_map.get(iid, {})
        create_ts = m.pop("_create_time", None)
        duration  = m.pop("_duration", None)
        desc      = m.pop("_description", "") or v.get("title", "")
        ts = int(create_ts) if create_ts else 0
        view_count = int(m.get("view_count") or 0)
        videos.append({
            "item_id":     iid,
            "title":       desc[:60],
            "create_ts":   ts,
            "create_time": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else v.get("create_time",""),
            "duration":    int(duration) if duration else v.get("duration", 0),
            "view_count":  view_count,
            "is_private":  view_count == 0,   # private videos show 0 views in mget
            "metrics":          m,
            "compare":          {},
            "trend":            {},
            "retention_curves": {},
            "play_source":      [],
            "chapter":          {},
            "search_keywords":  [],
        })
    videos.sort(key=lambda v: v["create_ts"], reverse=True)
    public_count = sum(1 for v in videos if not v["is_private"])
    print(f"   公开视频: {public_count} 条，私密/限流: {len(videos)-public_count} 条", file=sys.stderr)

    # 5. item_compare + metrics_trend（只抓有播放量的视频）
    with_play = [v for v in videos if not v["is_private"]]
    target = with_play[:args.recent] if args.recent > 0 else with_play

    print(f"④ 拉取「比往期」对比数据（{len(target)} 条）...", file=sys.stderr)
    for v in target:
        iid = v["item_id"]
        print(f"   compare: {v['create_time']} {v['title'][:25]}...", file=sys.stderr)
        v["compare"] = get_item_compare(session, iid)
        time.sleep(0.5)

    if not args.skip_trend:
        print(f"⑤ 拉取逐小时趋势（{len(target)} 条）...", file=sys.stderr)
        for v in target:
            iid = v["item_id"]
            print(f"   trend:   {v['create_time']} {v['title'][:25]}...", file=sys.stderr)
            v["trend"] = get_metrics_trend(session, iid)
            time.sleep(0.5)
    else:
        print("⑤ 已跳过 metrics_trend", file=sys.stderr)

    print(f"⑥ 拉取留存/跳出曲线 + 同类大盘（{len(target)} 条）...", file=sys.stderr)
    for v in target:
        iid = v["item_id"]
        print(f"   retention: {v['create_time']} {v['title'][:25]}...", file=sys.stderr)
        v["retention_curves"] = get_retention_curves(session, iid)
        time.sleep(0.5)

    print(f"⑦ 拉取流量来源（{len(target)} 条）...", file=sys.stderr)
    for v in target:
        iid = v["item_id"]
        v["play_source"] = get_play_source(session, iid)
        time.sleep(0.3)

    print(f"⑧ 拉取章节点击率（{len(target)} 条）...", file=sys.stderr)
    for v in target:
        iid = v["item_id"]
        v["chapter"] = get_chapter(session, iid)
        time.sleep(0.3)

    print(f"⑨ 拉取搜索关键词（{len(target)} 条）...", file=sys.stderr)
    for v in target:
        iid = v["item_id"]
        v["search_keywords"] = get_search_keywords(session, iid)
        time.sleep(0.3)

    # 6. 输出
    result = {
        "fetch_time": datetime.now().isoformat(),
        "user":       user,
        "videos":     videos,
    }
    out_path = Path(args.output)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n✅ 已保存到 {out_path}  ({len(videos)} 条公开视频)", file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
