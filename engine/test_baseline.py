#!/usr/bin/env python3
"""验证基线反推:数据反推优于用户自述(onboarding 铁律2)。"""
from baseline import compute_baselines, recommend_northstar


def make_posts(fav_like, fwd_like=0.1, n=30):
    """造 n 条:藏/赞=fav_like, 转/赞=fwd_like。"""
    return [{"view_count": 5000, "like_count": 200,
             "favorite_count": int(200 * fav_like),
             "share_count": int(200 * fwd_like),
             "comment_count": 20} for _ in range(n)]


# 场景①:用户说要"涨粉",但近30条收藏率基线=0.9(高,干货型)
posts_hi_fav = make_posts(fav_like=0.9)
b1 = compute_baselines(posts_hi_fav)
rec1, notes1 = recommend_northstar(b1, stated_goal="涨粉")
print("场景① 自述涨粉 / 数据高收藏:")
print(f"  收藏率基线={b1['收藏率(藏/赞)']} 反推={rec1}")
assert b1["收藏率(藏/赞)"] == 0.9
assert "收藏率" in rec1, "高收藏应反推干货型北极星(含收藏率)"
assert any("冲突" in x for x in notes1), "应标出自述vs数据冲突"
print("  ✓ 数据反推=干货型,并标冲突让用户拍板(数据优先)")

# 场景②:泛流量信号(转赞高、收藏低)→ 预警
posts_viral = make_posts(fav_like=0.1, fwd_like=0.5)
b2 = compute_baselines(posts_viral)
rec2, notes2 = recommend_northstar(b2, stated_goal="立人设")
print("\n场景② 转赞高收藏低(泛流量):")
assert any("泛流量" in x for x in notes2), "应给泛流量预警"
print(f"  ✓ 预警泛流量,采用自述目标={rec2}")

# 场景③:公开数据无完播/涨粉 → 标缺失,不瞎给基线
b3 = compute_baselines(posts_hi_fav)
assert b3["完播率"] is None and b3["_后台指标缺失"], "公开数据应标后台指标缺失"
print("\n场景③ 公开数据缺完播/涨粉:")
print("  ✓ 不编基线,标'待补测'")

print("\n✅ 基线反推通过:嘴说不准时数据纠偏,缺数据不硬编。")
