#!/usr/bin/env python3
"""
回归验证: 证明通用 judge 引擎确实读 profile,而非写死迪迪。

断言两件事:
  ① 喂迪迪 profile → 用迪迪的北极星(涨粉率/完播率)判定。
  ② 同一条原始数据,只换成带货号 profile(GMV/客单+完播)→ 判定结果不同,
     且全程不改一行引擎代码。
"""
from judge import judge, load_profile
from review import render_card

# 一条真实形态的后台原始数据(同一条视频,喂给不同档案)
RAW = {
    "view_count": 8000, "like_count": 300, "favorite_count": 240,
    "subscribe_count": 12, "completion_rate": 0.16, "comment_count": 40,
    "share_count": 20, "bounce_rate_2s": 0.32, "rec_flow_ratio": 0.7,
    "gmv": 500,            # 带货维度:这条只成交了 500
}


def show(pid):
    prof = load_profile(pid)
    rows, verdict, _ = judge(RAW, prof)
    print(f"\n=== {prof['name']} ===")
    for r in rows:
        print(f"  {r['指标']:<16} = {r['值']}  [{r['状态']}]")
    print(f"  总判定: {verdict}")
    return {r["指标"]: r["状态"] for r in rows}, verdict


didi_rows, didi_v = show("迪迪")
test_rows, test_v = show("_测试_带货号")

print("\n--- 回归断言 ---")

# ① 迪迪: 涨粉率=12/8000*1000=1.5 (>1 达标), 完播16%>15% 达标 → 命中
assert "涨粉率" in didi_rows, "迪迪档案应按涨粉率判定"
assert didi_rows["涨粉率"] == "✅达标", f"涨粉率1.5应达标, 实际{didi_rows['涨粉率']}"
assert didi_rows["完播率"] == "✅达标", f"完播16%应达标, 实际{didi_rows['完播率']}"
assert didi_v == "命中", f"迪迪应命中, 实际{didi_v}"
print("① 迪迪 profile → 按涨粉率+完播率判定 = 命中 ✓")

# ② 带货号: 同一条数据, GMV=500 < 2000 平庸/不达标, 完播16%>10%达标 → 平庸
#    且引擎此时根本不看涨粉率(它在带货号的 anti_metrics 里)
assert "GMV/客单" in test_rows, "带货档案应按GMV判定"
assert "涨粉率" not in test_rows, "带货号不应出现涨粉率(证明判据来自档案而非写死)"
assert test_rows["GMV/客单"] == "平庸", f"GMV500未达2000应平庸, 实际{test_rows['GMV/客单']}"
assert test_v == "平庸", f"带货号应平庸, 实际{test_v}"
print("② 换带货号 profile(不改代码)→ 改按GMV判定, 不再看涨粉率 = 平庸 ✓")

# ③ 完整复盘卡也是 profile 驱动:卡里的指标行/命中分母/"不看"提示随档案变
didi_card = render_card(RAW, load_profile("迪迪"))
test_card = render_card(RAW, load_profile("_测试_带货号"))
assert "涨粉率" in didi_card and "命中 2/2" in didi_card, "迪迪卡应显涨粉率+分母2"
assert "GMV/客单" in test_card and "涨粉率" not in test_card.split("不看")[0], \
    "带货卡应显GMV、不显涨粉率"
assert "不看:播放量、总涨粉" in didi_card, "迪迪卡应据 anti_metrics 标'不看播放量'"
assert "不看:涨粉率" in test_card, "带货卡的'不看'应是涨粉率"
print("③ 完整复盘卡(含归因/限流/护栏)整张随 profile 变, 不只 judge ✓")

print("\n✅ 回归通过: 引擎已与迪迪解耦,judge + 整张复盘卡都由 profile 驱动。")
