#!/usr/bin/env python3
"""
通用复盘卡装配 —— 完整复盘链路(judge + 留存归因 + 限流预警 + 卡模板),全部读 profile。

对照 ~/新媒体agent/scripts/loop_review.py:那里指标表/命中分母/"不看播放"全焊死迪迪。
本模块:
  · 指标表的行            ← 由 profile.north_star 决定(迪迪显涨粉率/完播,带货号显GMV/完播)
  · "命中 N/M" 的分母 M   ← len(profile.north_star)
  · "不看XX"提示          ← profile.anti_metrics
  · 留存归因/限流预警/2s跳出标尺/小样本护栏 = 通用引擎层(不进 profile,所有人共用)

取数(抖音 cookie API)是平台适配层,不在本模块——本模块吃「已取好的 raw」,
所以换平台只换取数适配器,判定+卡片不变。
"""
from judge import judge, METRIC_REGISTRY


# ── 通用引擎层:这些是机制,不因创作者而变 ──────────────────────────
BOUNCE_2S_STD = 0.4     # 2秒跳出标尺(通用爆款机制)
REC_FLOW_MIN = 0.6      # 推荐流占比合格线(平台机制,后续按平台路由可覆盖)


def retention_hint(curves):
    """留存曲线归因:开头掉=钩子,中段掉=结构。通用机制。"""
    ret = (curves or {}).get("retention", {})
    cur, sim = ret.get("current_item", []), ret.get("similar_author", [])
    if not cur:
        return "（无留存数据）"

    def at(lst, sec):
        for p in lst:
            k = p.get("key", "")
            if k.endswith(f":{sec:02d}") or k == f"00:{sec:02d}":
                return float(p.get("value") or 0)
        return None

    c5, s5 = at(cur, 5), at(sim, 5)
    out = []
    if c5 is not None:
        line = f"5s留存={c5:.0%}"
        if s5 is not None:
            line += f"(同类{s5:.0%},{'低于大盘→钩子偏弱' if c5 < s5 else '不输大盘→钩子OK'})"
        out.append(line)
    return " ｜ ".join(out) if out else "（留存曲线已取,需人工看图）"


def render_card(raw, profile, curves=None, meta_extra=None):
    """装配完整复盘卡 markdown。raw=后台数据, profile=已load档案。"""
    rows, verdict, meta = judge(raw, profile)
    name = profile.get("name", profile.get("id"))
    anti = "、".join(profile.get("anti_metrics", [])) or "无"

    # ① 指标表:行由 profile.north_star 驱动(judge 已算好)
    def _thr(r):
        parts = []
        if r.get("floor"):
            parts.append(f"floor {r['floor']}")
        if r.get("target"):
            parts.append(f"达标 {r['target']}")
        return f" ({' / '.join(parts)})" if parts else ""

    tbl = "\n".join(f"| {r['指标']} | {r['值']}{_thr(r)} | {r['状态']} |" for r in rows)

    # 通用归因信号
    view = raw.get("view_count", 0)
    like = raw.get("like_count", 0)
    bounce2 = raw.get("bounce_rate_2s", 0)
    rec = raw.get("rec_flow_ratio")
    throttled = (view == 0 and raw.get("avg_view_second", 0) > 0)

    throttle_line = ("\n> 🚨 **疑似限流/仅自己可见**:0 播放但有零星留存,且无推荐流。"
                     "先查标签/红线/可见性,别急着归因内容。" if throttled else "")
    bounce_line = (f"- 2s跳出 {bounce2:.1%} → {'钩子偏弱' if bounce2 > BOUNCE_2S_STD else '钩子OK'}"
                   if bounce2 else "- 2s跳出:无数据")
    rec_line = (f"- 推荐流占比 {rec} → "
                f"{'算法几乎没推(限流/降权/标签问题,优先排查)' if (rec or 0) < REC_FLOW_MIN else '算法正常推'}"
                if rec is not None else "- 推荐流占比:无数据")

    return f"""# 复盘卡 · {name}

> 判据来自 {profile.get('id')} 档案的北极星,不看:{anti}

## ① 实际数据(看北极星)

| 指标 | 实际 | 判定 |
|---|---|---|
{tbl}

**总判定:{verdict}**(北极星命中 {meta['n_hit']}/{meta['n_target']}){throttle_line}

## ② 归因(选题 vs 执行)
- 留存:{retention_hint(curves)}
{bounce_line}
{rec_line}
- 初步:▢限流(先排查) ▢选题不行 ▢执行不行 ▢没爆苗 ▢都行

## ③ 这条用了哪些套路(人工回填)
- 选题类型: ｜ 钩子: ｜ 评分卡当初打了 ?分 ｜ 预测卡 vs 实际 diff:

## ④ 更新动作(待 👤 确认)
- [ ] 套路库加权/降权:
- [ ] 预测器校准:
- [ ] 评分卡维度调整:

> ⚠️ 单条不下结论,同类攒 2-3 条再改库。
"""


if __name__ == "__main__":
    import json, sys
    from judge import load_profile
    pid = sys.argv[1] if len(sys.argv) > 1 else "迪迪"
    print(render_card(json.loads(sys.stdin.read()), load_profile(pid)))
