#!/usr/bin/env python3
"""
评分卡判据解析器 —— 证明「选题评分卡」的两个 🔵 维度确实从 profile 取,不写死迪迪。

共享机制/选题评分卡.md 里:
  · 北极星匹配  ← profile.north_star / audience / positioning
  · 创作者独家性 ← profile.persona.moat
  · 优先级加权  ← profile.content_pillars
  · 自动弃      ← profile.anti_metrics / redlines / audience.exclude
本工具把这些维度对某个档案「解析成具体判据」,换档案判据就变,卡的框架不变。
"""
import sys
from judge import load_profile


def resolve(pid):
    p = load_profile(pid)
    moat = p.get("persona", {}).get("moat", [])
    pillars = [f"{c['name']}(P{c.get('priority','?')})" for c in p.get("content_pillars", [])]
    ns = [n["metric"] for n in p.get("north_star", [])]
    aud = p.get("audience", {})
    return {
        "档案": p.get("name"),
        "北极星匹配·命中标准": f"正中「{p.get('positioning','')[:24]}…」+ 受众「{aud.get('want','')[:18]}」",
        "北极星匹配·看哪些指标": ns,
        "创作者独家性·2分=": moat or ["(未填 moat)"],
        "优先级加权·按支柱": pillars or ["(未填 pillars)"],
        "自动弃·排除": (p.get("anti_metrics", []) + [aud.get("exclude", "")]),
    }


if __name__ == "__main__":
    pids = sys.argv[1:] or ["迪迪", "职场琳"]
    for pid in pids:
        r = resolve(pid)
        print(f"\n=== {r['档案']} ===")
        for k, v in list(r.items())[1:]:
            print(f"  {k}: {v}")
