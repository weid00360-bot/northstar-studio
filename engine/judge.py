#!/usr/bin/env python3
"""
通用复盘判定引擎 —— 读 profile.north_star,不写死任何创作者的指标。

对照: ~/新媒体agent/scripts/loop_review.py 的 judge() 把
  涨粉/千播>1、完播>0.05、收藏>0.5、n_hit>=3 命中  全焊在代码里(=迪迪的北极星)。
本引擎把判据外置到 profile.json,换创作者只换档案、不改代码。

分两层:
  METRIC_REGISTRY  = 通用引擎层。每个指标「怎么从后台原始数据算出来」,所有人共用。
  profile.north_star = 档案层。这个号「看哪些指标、阈值多少」,每人一份。
"""
import json
import re
import sys
from pathlib import Path


# ── 通用引擎层:指标定义(怎么从原始后台数据算) ────────────────────────
# 新增赛道指标只在这里加一行,profile 引用名字即可。
def _ratio(a, b):
    return (a / b) if b else 0.0

METRIC_REGISTRY = {
    "涨粉率":   lambda r: _ratio(r.get("subscribe_count", 0), r.get("view_count", 0)) * 1000,  # 涨粉/千播
    "完播率":   lambda r: r.get("completion_rate", 0.0),
    "收藏率":   lambda r: _ratio(r.get("favorite_count", 0), r.get("like_count", 0)),           # 藏/赞
    "GMV/客单": lambda r: r.get("gmv", 0.0),
    "加微率":   lambda r: _ratio(r.get("wechat_add", 0), r.get("view_count", 0)),
    "互动率":   lambda r: _ratio(
        r.get("like_count", 0) + r.get("comment_count", 0) + r.get("share_count", 0),
        r.get("view_count", 0)),
}


def parse_threshold(s):
    """'>1' / '>=2000' / '5%' / '15%' → (op, float). 纯数字默认 >=。"""
    if s is None:
        return None
    s = str(s).strip()
    m = re.match(r"^(>=|<=|>|<)?\s*([\d.]+)(%)?$", s)
    if not m:
        raise ValueError(f"看不懂的阈值: {s!r}")
    op, num, pct = m.group(1) or ">=", float(m.group(2)), m.group(3)
    if pct:
        num /= 100.0
    return op, num


def _cmp(v, thr):
    op, num = thr
    return {">": v > num, ">=": v >= num, "<": v < num, "<=": v <= num}[op]


def judge(raw, profile, min_view=500):
    """
    raw     : 后台原始数据 dict(view_count/like_count/completion_rate/gmv...)
    profile : 已 load 的 profile.json dict
    返回 (逐指标结果 list, 总判定 str, meta dict{n_hit,n_target})
    """
    view = raw.get("view_count", 0)
    rows, n_target, n_hit, below_floor = [], 0, 0, False

    for ns in profile.get("north_star", []):
        name = ns["metric"]
        fn = METRIC_REGISTRY.get(name)
        if fn is None:
            rows.append({"指标": name, "值": None, "状态": "⚠️引擎无此指标定义"})
            continue
        v = fn(raw)
        floor = parse_threshold(ns.get("floor"))
        target = parse_threshold(ns.get("target"))
        if floor and not _cmp(v, floor):
            status, below_floor = "未过合格线", True
        elif target and _cmp(v, target):
            status, n_hit, n_target = "✅达标", n_hit + 1, n_target + 1
        else:
            status = "平庸"
            if target:
                n_target += 1
        rows.append({"指标": name, "值": round(v, 3), "floor": ns.get("floor"),
                     "target": ns.get("target"), "状态": status})

    # 通用判定规则(对照 loop_review 的 n_hit>=3 命中,这里按本号指标数归一)
    if view < min_view:
        verdict = f"⚠️样本太小(播放<{min_view})·比率不可信,别判"
    elif below_floor:
        verdict = "扑(未过合格线)"
    elif n_target == 0:
        verdict = "无可判指标"
    elif n_hit == n_target:
        verdict = "命中"
    elif n_hit > 0:
        verdict = "平庸"
    else:
        verdict = "扑"

    # signal_thresholds 作归因辅助报告(非北极星,不进总判定)
    sig = profile.get("signal_thresholds", {})
    if sig:
        fl = METRIC_REGISTRY["收藏率"](raw)
        rows.append({"指标": "收藏率(归因辅助)", "值": round(fl, 3),
                     "状态": f"参照 {sig.get('精准', '?')}"})

    return rows, verdict, {"n_hit": n_hit, "n_target": n_target}


def load_profile(profile_id):
    p = Path(__file__).resolve().parent.parent / "profiles" / profile_id / "profile.json"
    return json.loads(p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    pid = sys.argv[1] if len(sys.argv) > 1 else "迪迪"
    prof = load_profile(pid)
    raw = json.loads(sys.stdin.read())
    rows, verdict, _ = judge(raw, prof)
    print(f"档案: {prof['name']}")
    for r in rows:
        print(f"  {r['指标']:<16} = {r['值']}  [{r['状态']}]")
    print(f"总判定: {verdict}")
