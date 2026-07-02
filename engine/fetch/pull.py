#!/usr/bin/env python3
"""
一步到位取数入口 —— 用户在浏览器登录抖音后,一条命令自动拿底表并出结果。

  python3 engine/fetch/pull.py onboarding {id}          # 拉近30条→反推北极星基线
  python3 engine/fetch/pull.py review {id} --latest      # 拉最新一条底表→出复盘卡
  python3 engine/fetch/pull.py review {id} --item-id X   # 指定视频复盘
  python3 engine/fetch/pull.py raw --n 30                 # 只导出原始底表json

自动 cookie(get_cookie)→ 自包含取数(fetch_backend)→ 喂 baseline/review。
不依赖任何私有 repo。需先 pip install(见 requirements.txt)。
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ENGINE)

import fetch_backend as fb
from judge import load_profile
import baseline as bl
import review as rv


def cmd_onboarding(args):
    s = fb.get_session()
    posts = fb.recent_posts_metrics(s, args.n)
    print(f"拉到 {len(posts)} 条底表", file=sys.stderr)
    b = bl.compute_baselines(posts)
    rec, notes = bl.recommend_northstar(b, args.goal)
    print("基线:")
    for k, v in b.items():
        if not k.startswith("_"):
            print(f"  {k}: {v}")
    print(f"\n反推北极星: {rec}")
    for note in notes:
        print(f"  · {note}")


def cmd_review(args):
    s = fb.get_session()
    if args.latest:
        ids = fb.get_creator_item_ids(s)
        ids.sort(key=lambda v: fb.parse_ct(v.get("create_time")), reverse=True)
        item_id = ids[0]["item_id"]
    else:
        item_id = args.item_id
    m = fb.get_metrics_batch(s, [item_id]).get(item_id, {})
    time.sleep(0.2)
    curves = fb.get_retention_curves(s, item_id)
    psource = fb.get_play_source(s, item_id)
    # 播放来源:推荐流占比塞进 raw 供复盘归因
    rec_flow = next((p.get("value") for p in psource if p.get("key") == "homepage_hot"), None)
    if rec_flow is not None:
        m["rec_flow_ratio"] = rec_flow
    prof = load_profile(args.id)
    print(rv.render_card(m, prof, curves=curves))


def cmd_raw(args):
    s = fb.get_session()
    print(json.dumps(fb.recent_posts_metrics(s, args.n), ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("onboarding"); o.add_argument("id"); o.add_argument("--n", type=int, default=30); o.add_argument("--goal")
    r = sub.add_parser("review"); r.add_argument("id")
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument("--latest", action="store_true"); g.add_argument("--item-id")
    ra = sub.add_parser("raw"); ra.add_argument("--n", type=int, default=30)
    args = ap.parse_args()
    {"onboarding": cmd_onboarding, "review": cmd_review, "raw": cmd_raw}[args.cmd](args)


if __name__ == "__main__":
    main()
