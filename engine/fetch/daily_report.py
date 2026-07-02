#!/usr/bin/env python3
"""
抖音日报 —— 自动拉底表,按 profile.north_star 出每日数据快照。

  python3 engine/fetch/daily_report.py {id} [--n 10]

账号概览 + 近 n 条逐视频(按该号北极星判命中/未达)+ 北极星趋势。
自动 cookie,不用手抠。判据全读 profile,不写死。
"""
import argparse
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ENGINE)

import fetch_backend as fb
from judge import load_profile, judge, METRIC_REGISTRY


def report(pid, n=10):
    prof = load_profile(pid)
    ns_metrics = [x["metric"] for x in prof.get("north_star", [])]
    s = fb.get_session()
    user = fb.get_user_info(s)
    ids = fb.get_creator_item_ids(s)
    ids.sort(key=lambda v: fb.parse_ct(v.get("create_time")), reverse=True)
    top = ids[:n]
    mm = fb.get_metrics_batch(s, [d["item_id"] for d in top])

    print(f"# 抖音日报 · {user.get('nick_name')} · {datetime.now():%Y-%m-%d %H:%M}")
    print(f"> 粉丝 {user.get('follower_count')} ｜ 总获赞 {user.get('total_favorited')} ｜ 北极星:{'、'.join(ns_metrics)}(不看 {'、'.join(prof.get('anti_metrics',[]))})\n")

    print(f"## 近 {len(top)} 条(按北极星判)")
    print("| 发布 | 标题 | " + " | ".join(ns_metrics) + " | 判定 |")
    print("|---|---|" + "|".join(["---"] * (len(ns_metrics) + 1)) + "|")
    hit = 0
    for d in top:
        m = mm.get(d["item_id"], {})
        _, verdict, meta = judge(m, prof)
        if verdict == "命中":
            hit += 1
        vals = []
        for name in ns_metrics:
            fn = METRIC_REGISTRY.get(name)
            vals.append(f"{fn(m):.3g}" if fn else "?")
        pub = datetime.fromtimestamp(fb.parse_ct(d.get("create_time"))).strftime("%m-%d") if fb.parse_ct(d.get("create_time")) else "?"
        title = (m.get("_description") or d.get("title") or "")[:12]
        print(f"| {pub} | {title} | " + " | ".join(vals) + f" | {verdict} |")

    print(f"\n**近 {len(top)} 条北极星命中 {hit}/{len(top)}**")
    print("> ⚠️ <48h 的新视频数据未稳,别急着判(见复盘铁律)。想看单条详细归因跑 `pull.py review {id} --item-id X`。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--n", type=int, default=10)
    a = ap.parse_args()
    report(a.id, a.n)
