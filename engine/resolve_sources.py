#!/usr/bin/env python3
"""
信息源路由解析器 —— 给一个档案,据 profile.sources_track 查路由表,吐出该去哪拉热点。
证明选题发现层与迪迪解耦:换赛道自动换源,选题 skill 不改。

匹配:先精确命中赛道 key,再按 aliases 模糊匹配,都不中走 _默认。
报告每个源是否 auto 可跑(dep 缺则提示降级 semi)。
"""
import json
import sys
from pathlib import Path

from judge import load_profile

ROUTE = json.loads((Path(__file__).resolve().parent.parent
                    / "共享机制" / "赛道信息源路由表.json").read_text(encoding="utf-8"))


def match_track(track):
    if not track:
        return "_默认"
    if track in ROUTE:
        return track
    for key, cfg in ROUTE.items():
        if key.startswith("_"):
            continue
        if any(a in track or track in a for a in cfg.get("aliases", [])):
            return key
    return "_默认"


def detect_tikhub():
    """实测 TikHub token 配置是否存在(同 blogger-distiller 的配置位)。"""
    p = Path.home() / ".xiaohongshu" / "tikhub_config.json"
    try:
        return bool(json.loads(p.read_text()).get("tikhub_api_token", "").strip())
    except Exception:
        return False


def resolve(pid, has_tikhub=None):
    if has_tikhub is None:
        has_tikhub = detect_tikhub()
    prof = load_profile(pid)
    track = prof.get("sources_track")
    key = match_track(track)
    out = []
    for s in ROUTE[key]["sources"]:
        mode = s["mode"]
        if s.get("dep") == "TikHub Token" and not has_tikhub:
            mode = "semi(降级·缺TikHub Token)"
        out.append((s["name"], s["channel"], mode, s["role"]))
    return prof.get("name"), track, key, out


if __name__ == "__main__":
    pids = sys.argv[1:] or ["迪迪", "职场琳", "_测试_带货号"]
    for pid in pids:
        name, track, key, srcs = resolve(pid)
        print(f"\n=== {name} ｜ sources_track={track} → 路由[{key}] ===")
        for n, ch, mode, role in srcs:
            print(f"  · {n:<26} [{role}] via {ch} ({mode})")
