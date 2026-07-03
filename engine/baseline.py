#!/usr/bin/env python3
"""
北极星基线反推 —— onboarding Step2A 的核心逻辑。
拉创作者自己近 N 条数据 → 算真实基线 → 反推「该看哪个北极星」,比用户嘴说的准。

分两层(同 review.py 的设计):
  · 取数      = 平台适配器(复用现成通道,见文件尾 fetch_posts),不重造轮子。
  · 算基线+反推 = 纯逻辑(本文件主体),喂一组 posts 就能算,可离线测。

铁律2:数据反推优先于用户自述,但冲突要告诉用户、让 TA 拍板(见 onboarding SKILL.md)。
"""
import json
import statistics
import sys


# 商业目标 → 默认北极星(对齐 profiles/_schema/北极星枚举.md)
GOAL_DEFAULT = {
    "涨粉":   ["涨粉率", "完播率"],
    "带货":   ["GMV/客单", "完播率", "收藏率"],
    "导私域": ["加微率", "完播率"],
    "立人设": ["涨粉率", "互动率", "完播率"],
    "接广":   ["涨粉率", "互动率", "完播率"],
    "干货":   ["收藏率", "完播率", "涨粉率"],
}
# 同义词兜底:用户随口说"卖货""粉丝"也能对上;全不中返回 None 走数据信号
GOAL_ALIAS = {
    "涨粉": ["涨粉", "粉丝", "起号", "做大"],
    "带货": ["带货", "卖货", "卖东西", "电商", "gmv", "成交", "橱窗"],
    "导私域": ["私域", "导私", "加微", "微信", "社群", "咨询"],
    "立人设": ["人设", "ip", "个人品牌", "影响力"],
    "接广": ["接广", "广告", "商单", "恰饭"],
    "干货": ["干货", "工具", "教程", "知识", "收藏"],
}


def normalize_goal(stated):
    """自由文本 → 标准目标 key;不中返回 None(交给数据信号)。"""
    if not stated:
        return None
    if stated in GOAL_DEFAULT:
        return stated
    low = stated.lower()
    for key, words in GOAL_ALIAS.items():
        if any(w in low for w in words):
            return key
    return None


def _med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 4) if xs else None


def compute_baselines(posts):
    """posts: [{view_count,like_count,favorite_count,comment_count,share_count,
               subscribe_count?,completion_rate?}] → 各指标中位数基线。
    公开数据(对标/TikHub)只有 view/like/fav/comment/share;
    完播率/涨粉率是后台口径,只有自己账号(cookie)才有 → 缺则为 None。"""
    fav_like, sub_pk, comp, inter, fwd_like = [], [], [], [], []
    for p in posts:
        v, like = p.get("view_count", 0), p.get("like_count", 0)
        fav, sh = p.get("favorite_count", 0), p.get("share_count", 0)
        cm = p.get("comment_count", 0)
        if like:
            fav_like.append(fav / like)
            fwd_like.append(sh / like)
        if v:
            inter.append((like + cm + sh) / v)
            if p.get("subscribe_count") is not None:
                sub_pk.append(p["subscribe_count"] / v * 1000)
        if p.get("completion_rate") is not None:
            comp.append(p["completion_rate"])
    return {
        "n": len(posts),
        "收藏率(藏/赞)": _med(fav_like),
        "涨粉率(涨粉/千播)": _med(sub_pk),
        "完播率": _med(comp),
        "互动率": _med(inter),
        "转赞(转/赞)": _med(fwd_like),
        "_后台指标缺失": sub_pk == [] or comp == [],
    }


def recommend_northstar(baselines, stated_goal=None):
    """据基线反推北极星 + 与用户自述对比。返回 (推荐list, 提示list)。"""
    fl = baselines.get("收藏率(藏/赞)")
    fwd = baselines.get("转赞(转/赞)")
    notes, data_signal = [], None

    # 数据信号判型(套路库§0:收藏率=赛道匹配器)
    if fl is not None and fl > 0.7:
        data_signal = "干货"
        notes.append(f"收藏率基线 {fl} >0.7 → 受众精准/干货型,真实强项是收藏。")
    elif fwd is not None and fwd > 0.4 and (fl or 0) < 0.2:
        notes.append(f"转赞 {fwd} 高而收藏 {fl} 低 → 泛流量信号⚠️,慎把互动当北极星。")
    elif fl is not None:
        notes.append(f"收藏率基线 {fl},未达精准线 0.7,需结合目标定。")

    if baselines.get("_后台指标缺失"):
        notes.append("完播率/涨粉率缺(公开数据取不到,只有自己账号cookie有)→ 这两项基线待补测。")

    goal_key = normalize_goal(stated_goal)
    if stated_goal and not goal_key:
        notes.append(f"没听懂目标「{stated_goal}」(可选:{'/'.join(GOAL_DEFAULT)}),按数据信号走。")
    stated = GOAL_DEFAULT.get(goal_key) if goal_key else None
    rec = GOAL_DEFAULT.get(data_signal) if data_signal else None

    if stated and rec and set(stated) != set(rec):
        notes.append(f"⚠️冲突:你说目标是「{stated_goal}」(→{stated}),"
                     f"但数据显示更像干货型(→{rec})。铁律:数据优先,但请你拍板。")
        recommend = rec
    else:
        recommend = rec or stated or ["完播率"]
        if stated and not rec:
            notes.append(f"数据无强信号,采用你自述目标「{stated_goal}」→ {stated}。")

    return recommend, notes


def fetch_posts(account, platform, n=30):
    """取数适配器(平台特定)。抖音自己账号走 engine/fetch/pull.py(自动cookie,含完播/涨粉);
    对标/公开(小红书/抖音)走 blogger-distiller 的 TikHub 采集(需 token)。
    其他平台暂无适配 → 用户手动贴数据。返回 posts list 喂给 compute_baselines。"""
    raise NotImplementedError("抖音用 engine/fetch/pull.py onboarding {id};其他平台手动喂数据")


if __name__ == "__main__":
    goal = sys.argv[1] if len(sys.argv) > 1 else None
    posts = json.loads(sys.stdin.read())
    b = compute_baselines(posts)
    rec, notes = recommend_northstar(b, goal)
    print("基线:")
    for k, v in b.items():
        if not k.startswith("_"):
            print(f"  {k}: {v}")
    print(f"\n反推北极星: {rec}")
    for n in notes:
        print(f"  · {n}")
