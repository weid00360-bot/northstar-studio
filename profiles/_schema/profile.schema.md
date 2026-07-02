# profile.json 字段表（v0.1）

> 通用内容 agent 的「档案层」定义。每个创作者一份 `profiles/{id}/profile.json`,引擎读它运转。
> 本表说明:每个字段是什么、引擎怎么用、onboarding 怎么填。
> 第一份实例见 `profiles/迪迪/profile.json`(从硬编码抽出,验证解耦)。

---

## 填法三类（决定字段怎么来）

| 标记 | 含义 |
|---|---|
| 🟢 问 | onboarding 一问一答,用户直接给 |
| 🔵 自动 | 引擎/脚本自动生成或反推(用户不手填) |
| 🟡 半自动 | 用户给原料(账号名/旧文案),脚本加工 |

---

## 字段表

| 字段 | 类型 | 含义 | 引擎怎么读 | 来源 | onboarding |
|---|---|---|---|---|---|
| `id` `name` `version` | str | 档案标识 | — | — | 🟢 第1问 |
| `positioning` | str | 一句话定位 | 文案/选题注入人设 | 北极星§定位 | 🟢 第1问 |
| `persona.carrier` | str | 账号载体/转型话术 | 文案语气背景 | 北极星§定位 | 🟢 第1问 |
| `persona.moat` | str[] | 独家壁垒(§8 等价) | 文案找独家结合点 | 北极星§关系 | 🟢 第3问 |
| `audience.want` / `.exclude` | str | 目标受众 / 排除谁 | 选信息源 + 套路权重 | 北极星§受众 | 🟢 第2问 |
| `north_star` | obj[] | 北极星指标+阈值(枚举见下) | **复盘判定读这个**(核心) | 北极星§指标 | 🟢 第1问 + 🔵 数据反推 |
| `anti_metrics` | str[] | 明确不看的指标 | 复盘排除项 | 北极星§指标 | 🟢 第1问 |
| `monetization` | obj | 变现模型 + 红线 | 预审红线、选题加权 | 北极星§变现 | 🟢 第1问 |
| `content_pillars` | obj[] | 内容支柱+优先级 | 选题打分加权 | 北极星§支柱 | 🟢 第1问 + 🔵 反推 |
| `presentation_rule` | str | 呈现铁律 | 文案结构约束 | 北极星§支柱 | 🔵 通用默认,可改 |
| `platforms` | obj[] | 平台+漏斗角色 | 限流模块 + 漏斗设计 | 北极星§漏斗 | 🟢 第4问 |
| `redlines` | str[] | 红线 | 预审 | 北极星§红线 | 🟢 第1问 + 🔵 平台默认 |
| `signal_thresholds` | obj | 收藏率等信号阈值 | 复盘归因 | 套路库§0 | 🔵 数据反推(赛道特定) |
| `sources_track` | str | 赛道(挂信息源路由表) | 发现层拉源 | 派生自受众 | 🔵 自动(选赛道) |
| `transition` | obj | 转型/阶段策略 | 选题阶段约束 | 北极星§转型 | 🟢 可选 |
| `benchmark_accounts` | obj[] | 对标账号 | 🟡 blogger-distiller 自动蒸馏种套路库 | onboarding | 🟡 第5问(用户报名,脚本扒) |
| `tone_samples` | path[] | 满意旧文案 | 喂人味儿写作 | onboarding | 🟡 第6问 |

---

## 不进档案的东西（通用引擎,所有人共用,别写进 profile）

- 选题打分卡 5 维框架、钩子14招、2秒跳出标尺
- 人味儿写作原则、复盘"判定→归因→沉淀"逻辑
- 九类选题公式(A–I)的**框架**(具体样本才进套路库,由蒸馏种入)
- 发现层管线、blogger-distiller 机制

> 这些是「机制」,引擎读 profile 字段来运转,不因人而变。

---

## 待补（下个迭代）

- `signal_thresholds` 的数据反推脚本(给账号 URL → 拉近 30 条 → 算基线)
- ~~`sources_track` → 信息源路由表完整版~~ ✅ 已建 `共享机制/赛道信息源路由表.json` + `engine/resolve_sources.py`
- profile.json 的正式 JSON Schema(校验用),现先用本表 + 实例约束
