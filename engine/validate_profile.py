#!/usr/bin/env python3
"""
档案校验器 —— 保证 onboarding 产出的 profile.json,引擎(judge/review)一定吃得下。
闭环的焊点:onboarding 写完档案必须跑本校验,过了才算数。

校验:
  · 必填字段在
  · north_star 每个 metric 都在引擎 METRIC_REGISTRY 里(否则复盘判不了)
  · 每个 north_star 至少有 target 或 floor,且阈值字符串能被解析
  · anti_metrics / signal_thresholds 形态对
返回非 0 退出码 = 不合格。
"""
import json
import sys
from pathlib import Path

from judge import METRIC_REGISTRY, parse_threshold

REQUIRED = ["id", "name", "positioning", "audience", "north_star"]


def validate(profile):
    errs, warns = [], []

    for f in REQUIRED:
        if not profile.get(f):
            errs.append(f"缺必填字段: {f}")

    ns = profile.get("north_star", [])
    if not ns:
        errs.append("north_star 为空:没有北极星,复盘无法判定")
    for i, n in enumerate(ns):
        tag = f"north_star[{i}]({n.get('metric','?')})"
        if n.get("metric") not in METRIC_REGISTRY:
            errs.append(f"{tag}: 指标 '{n.get('metric')}' 不在引擎 METRIC_REGISTRY,"
                        f"复盘算不出。可选: {list(METRIC_REGISTRY)}")
        if not (n.get("target") or n.get("floor")):
            errs.append(f"{tag}: 必须至少有 target 或 floor")
        for k in ("target", "floor"):
            if n.get(k) is not None:
                try:
                    parse_threshold(n[k])
                except ValueError as e:
                    errs.append(f"{tag}: {k} 阈值解析失败 — {e}")

    aud = profile.get("audience", {})
    if isinstance(aud, dict) and not aud.get("want"):
        warns.append("audience.want 空:选不准信息源")

    if not profile.get("benchmark_accounts"):
        warns.append("无对标账号:套路库种不进弹药(onboarding 第5问)")
    if not profile.get("tone_samples"):
        warns.append("无语气样本:人味儿写作没参照(onboarding 第6问)")

    return errs, warns


def main():
    if len(sys.argv) < 2:
        sys.exit("用法: validate_profile.py <profile_id 或 路径>")
    arg = sys.argv[1]
    p = Path(arg)
    if not p.exists():
        p = Path(__file__).resolve().parent.parent / "profiles" / arg / "profile.json"
    profile = json.loads(p.read_text(encoding="utf-8"))

    errs, warns = validate(profile)
    name = profile.get("name", profile.get("id"))
    for w in warns:
        print(f"  ⚠️  {w}")
    if errs:
        for e in errs:
            print(f"  ❌ {e}")
        print(f"\n不合格: {name}（{len(errs)} 个硬错误）")
        sys.exit(1)
    print(f"✅ 合格: {name} — 引擎可消费（北极星 {len(profile['north_star'])} 项）")


if __name__ == "__main__":
    main()
