---
name: 选题
description: >
  通用选题引擎。给定一个创作者档案(profiles/{id})产出打好分的选题清单。
  当用户说"选题""出选题""今天做什么内容""给我选题清单""这周拍什么"时触发。
  读 profile + 共享机制(九类公式/评分卡) + 赛道热点源,五维打分排序输出。不要 undertrigger。
---

# 选题引擎（通用）

> 对照迪迪版:那版必读写死 `账号北极星.md`、评分卡维度写死"迪迪独家性"、优先级写死 build-in-public。
> 本版**全部读 `profiles/{id}/profile.json`**,机制走共享层。先确认给哪个创作者出题({id})。

## 必读（每次先读）
1. `profiles/{id}/profile.json` —— 定位/受众/北极星/红线/`content_pillars`(定优先级)/`persona.moat`(定独家性)/`sources_track`(定热点源)。**取代写死的北极星.md**。
2. `共享机制/选题评分卡.md` —— 5维框架(2维判据来自上面 profile)。
3. `共享机制/选题公式与钩子.md` —— 九类公式框架 + 钩子机制。
4. 该创作者的套路库样本(对标蒸馏种入的弹药)。
5. (有则)系列规划 —— 编排层,在排系列下一集优先。

## 流程
1. **拉热点**:据 `profile.sources_track` 查 `共享机制/赛道信息源路由表.json` 自动挂源。可直接跑 `python3 engine/resolve_sources.py {id}` 列出该去哪拉、走哪个通道(firsthand/aihot/tikhub/last30days/manual)、哪些 auto 哪些 semi(缺 TikHub Token 自动降级)。一手优先,二手交叉验证;赛道未匹配走 `_默认` 兜底。
2. **(可选)看自家数据**:近期复盘卡,避开刚扑/限流方向。
3. **生成候选**:按 `共享机制/选题公式与钩子.md` 九类公式 × `profile.persona.moat` 独家结合点,出 8-10 个候选。
4. **(可选)深挖验证**:对 top 候选调 `last30days` 扒近30天真实讨论,验证热度真假 + 挖痛点当钩子。
5. **评分卡打分**:用 `共享机制/选题评分卡.md`——北极星匹配读 `profile.north_star`,独家性读 `profile.persona.moat`,加权按 `profile.content_pillars` priority。
6. **排序判定**:≥8 优先 / 6-7 备选 / <6 弃。每条标分项 + 凭什么爆 + 建议钩子 + 📎原始信息源(可溯源,一手优先,二手标注)。
7. **落文件**:`选题清单/{id}/<日期>-第N批.md`。
8. **👤 人工卡点**:选哪条用户拍板,不自动进文案。

## 铁律（机制通用,值来自 profile）
- 收藏率思维:优先高收藏型选题(精准粉),避高分享低收藏的泛流量题。
- 避红线:落在 `profile.redlines`/`anti_metrics`/排除受众 的题直接弃。
- 优先级:按 `profile.content_pillars` 的 priority,**不写死任何赛道**。
- (有活动扶持位)标签带对应活动 tag。

下一步交给「文案」skill。
