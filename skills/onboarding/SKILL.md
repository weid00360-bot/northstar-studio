---
name: onboarding
description: >
  给一个新创作者建专属内容档案(profile.json),让通用内容引擎能为 TA 服务而非只服务迪迪。
  当用户说"帮我建个号档案""我要做个新号""onboarding""配一下我的账号""给我做个 profile"
  "我想做XX赛道的号怎么配""新创作者入驻"时触发。
  产出一份引擎可消费的 profiles/{id}/profile.json,并种好套路库弹药。
---

# 创作者 Onboarding（建档案#N）

> 把"谁都能用"落地。引擎(选题/文案/复盘)读 `profiles/{id}/profile.json` 运转,
> 本 skill 负责把一个新创作者**问 + 抓**成那份档案。
> 字段定义见 `profiles/_schema/profile.schema.md`,北极星枚举见 `北极星枚举.md`。

## 铁律（优先级最高）

1. **不替用户编答案**。北极星、受众、壁垒、红线这些填错,整个引擎都歪。问清楚再填。
2. **能抓就别只问**。多数人说不清自己北极星——给账号 URL 时,**用真实近 30 条数据反推** 优先于用户嘴说的(§自动抓)。两者冲突时以数据为准,但要把冲突告诉用户、让 TA 拍板。
3. **写完必校验**。生成 profile.json 后**必须**跑 `engine/validate_profile.py`,过了才算建成。不过就回去补。
4. **改库要人工确认**。对标蒸馏出的套路、反推的北极星,落库前给用户看。

---

## 流程

### Step 0 · 定身份
问账号名 → 定 `id`(英文/拼音短名,做目录)和 `name`(展示名)。输出落 `profiles/{id}/`。

### Step 1 · 6 问（每问填一块档案）

| # | 问什么 | 填进 profile 的 | 字段 |
|---|---|---|---|
| 1 | 做什么号?商业目标是涨粉/带货/导私域/接广/立人设里的哪个? | 定**北极星**(查枚举表给推荐) | `north_star` `anti_metrics` `positioning` `monetization` `content_pillars` |
| 2 | 目标受众是谁?明确排除谁? | 定信息源+套路权重 | `audience.want` `.exclude` |
| 3 | 你的独家经历/壁垒是什么?(别人抄不走的) | §8 独家结合点 | `persona.moat` |
| 4 | 主战哪个平台?私域承接在哪? | 限流模块+发现源 | `platforms` |
| 5 | 给 3 个你眼红的对标账号(平台+名字) | → Step 2 自动蒸馏 | `benchmark_accounts` |
| 6 | 贴 2 条你自己满意的旧文案(路径或正文) | 语气样本 | `tone_samples` |

> 第1问最关键:拿到商业目标后,**查 `北极星枚举.md` 的"目标→默认北极星"映射**给推荐,
> 让用户确认指标和阈值。别直接抄迪迪的"涨粉率+完播"。

### Step 2 · 自动抓（关键升级,别省）

**A. 反推北极星(自动取数,一步到位)** —— 跑 `engine/fetch/pull.py`
- **用户只要在浏览器(Chrome/Edge)登录抖音**,一条命令自动拿全量底表反推北极星:
  ```bash
  .venv/bin/python engine/fetch/pull.py onboarding {id} --goal {商业目标}
  ```
- 自动读浏览器 cookie(`get_cookie.py`)→ 自包含取数(`fetch_backend.py`,含完播/涨粉/留存全量底表)→ `baseline.py` 算基线 + 反推,**自动标"自述 vs 数据"冲突**(铁律2:数据优先,让用户拍板)。
- 首次读 Chrome 可能弹一次钥匙串授权,点允许。没装依赖先 `pip install -r engine/fetch/requirements.txt`。
- 不依赖任何私有 repo;自己账号的完播/涨粉都能拿(走登录态,不是公开数据)。

**B. 对标蒸馏 → 种套路库(第5问的 3 个账号)**
- 对每个对标账号跑 `blogger-distiller`(`~/.claude/skills/blogger-distiller`,走 TikHub 公开 API 自动扒,不靠登录态)。
- 模式 A(拆对标),采集量默认 30。
- 蒸馏出的选题公式/钩子/标题模板 → 作该赛道的套路库样本(人工确认后落库)。
- ⚠️ TikHub 额度用尽或接口变 → 退回让用户手动贴内容。

**C. 自动挂信息源(选赛道后)**
- 据受众判赛道 → 填 `sources_track` → 挂赛道→信息源路由表(路由表完整版待建,先填赛道名)。

### Step 3 · 组装 profile.json
按 `profile.schema.md` 字段表填。`presentation_rule` 用通用默认("结果先行")可让用户改。
不确定的 onboarding 项留 `{"_待填": "..."}` 占位,别瞎填。

### Step 4 · 校验（焊点,必跑）
```bash
python3 ~/通用内容agent/engine/validate_profile.py {id}
```
- ❌ 硬错误(缺字段/北极星指标不在引擎里/阈值解析不了)→ 回去补,不过不算建成。
- ⚠️ 警告(无对标/无语气样本)→ 告诉用户缺什么,可后补。

### Step 5 · 验证档案真能跑
拿一条样本数据跑一下复盘,确认引擎按新档案的北极星判定:
```bash
echo '<一条raw json>' | python3 ~/通用内容agent/engine/review.py {id}
```
卡片里的指标行/命中分母应是**这个号**的北极星,不是迪迪的。

---

## 产出物
1. `profiles/{id}/profile.json` — 校验通过的档案。
2. 套路库种子(对标蒸馏,人工确认后落库)。
3. 一段给用户的话:这个号的北极星定成了啥、为什么(尤其数据反推和嘴说冲突时)。

## 三层提醒（别越界）
- 只往 profile 填**第一层字段**(问出来的)。
- **第二层通用机制**(打分卡/钩子14招/2秒跳出/人味儿原则)不进 profile,引擎自带。
- **第三层样本**(套路库弹药)由对标蒸馏种入,不手抄迪迪的样本。

## 参考
- 字段表 `profiles/_schema/profile.schema.md`
- 北极星枚举+判定 `profiles/_schema/北极星枚举.md`
- 校验器 `engine/validate_profile.py` ｜ 复盘引擎 `engine/review.py` `judge.py`
- 对标蒸馏 `~/.claude/skills/blogger-distiller`
