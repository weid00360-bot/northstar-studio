<!-- lang -->**[中文](README.md) | English**

# NorthStar Studio · Content Production Agent

> A short-video content pipeline that runs inside Claude Code: **topic → script → pre-check + forecast → production → review**, with your Douyin backend data pulled in automatically.
> Core design: **shared engine, one profile per person**. You answer a few questions to build your own profile (north-star metric / audience / voice / red lines / visual style), and every stage then runs off *your* profile — not someone else's account rules.

## What it does for you

| Stage | What you get |
|---|---|
| Personalize | Conversational profile setup + auto-pull your last 30 posts to infer "which metric your account should actually track" |
| Topics | Auto-attach info sources by your niche, pull trends, a 5-dimension scored & ranked topic list (re-roll infinitely if unhappy) |
| Script | Voiceover draft + publish kit (title / tags / cover / forecast card); wrong tone? distill a blogger you like, or feed your own past scripts |
| Pre-check + Forecast | Pre-publish red/yellow/green risk list (throttling words / AI-labeling / qualification limits, with minimal edits) + data forecast |
| Production | Cover / slides / shot plan in your visual style (template library, pick & swap) |
| Review | After publishing, auto-pull backend data, judge hit/miss by **your** north star, retention attribution + throttling alerts + Douyin daily report |
| Loop | Validated playbooks get weighted back into your library, so next round's topics get sharper |

Data side: **just stay logged into Douyin in your browser** — the agent reads the session automatically and pulls the full creator backend (completion rate / follower gain / retention curve / traffic source). No manual cookie extraction.

![Daily report example](docs/抖音日报示例.png)

> Above: the profile-driven web daily report — KPI cards by **your** north star, each video judged hit/miss by your profile. Auto-generated and popped open every morning (`bash scripts/install_daily.sh install <your_id>` to schedule it); a CLI version exists too (`daily_report.py`).

## What is a "North-Star metric"?

**North star = the 1-2 metrics your account should watch, and nothing else.** It's set by your business goal. Every stage (topic scoring / forecasting / review judgment) aims at it, and vanity numbers like view count are ignored — so you don't get pulled off course.

| Your goal | North star | What it means |
|---|---|---|
| Grow followers / build persona | **Follow rate** (follows ÷ K-views) | Of every 1,000 people reached, how many follow — is your audience precise |
| Sell products | **GMV / AOV** | How much this video actually converted; high views without sales is nothing |
| Drive to private (consult/community) | **WeChat-add rate** | Comment keyword → WeChat conversion |
| Value/utility account | **Save rate** (saves ÷ likes) | >0.7 means viewers think "useful, keep it" — a precision signal |
| Baseline for every account | **Completion rate** | Clear the floor (e.g. 5%) first; nothing works if completion is bad |

Example: Didi's account is an AI-tools account, north star = follow rate >1 + completion ≥5%, explicitly **not** view count or total follows — because one precise tool-user follower beats a hundred passersby. During onboarding the agent pulls your last 30 posts and compares against what you *said* your goal is; if they conflict, it shows you both and you decide. Full enum & rules in [profiles/_schema/北极星枚举.md](profiles/_schema/北极星枚举.md).

## What onboarding asks you

Setup isn't a form, it's a conversation. 8 core touchpoints, each answer fills one part of your profile:

| # | What it asks | What it sets |
|---|---|---|
| 0 | Account name | Profile id |
| 1 | What kind of account? Goal — followers / sales / private / ads / persona? | **North star** + positioning + monetization |
| 2 | Who's your target audience? Who to exclude? | Info sources + playbook weighting |
| 3 | Your exclusive experience / moat (what others can't copy)? | The "exclusivity" scoring dimension |
| 4 | Main platform? Where do you receive private traffic? | Throttling rules + funnel |
| 5 | Give 3 benchmark accounts you envy | Auto-distilled → seeds your playbook library |
| 6 | Paste 2 of your own scripts you're happy with | Voice samples (so copy sounds like you, not AI) |
| 7 | What visual style? On-camera cover or not? | Cover / slide color templates |

Not done after asking: if you provide your account, the agent **auto-pulls your last 30 posts** and computes your real save/follow/completion baselines — when what you said conflicts with the data, it lays both out and lets you decide (data usually beats gut).

## Install

Prereqs: macOS + [Claude Code](https://claude.com/claude-code) + Python 3.10+ + Chrome/Edge (logged into Douyin).

```bash
git clone https://github.com/weid00360-bot/northstar-studio.git
cd northstar-studio
python3 -m venv .venv
.venv/bin/pip install -r engine/fetch/requirements.txt
```

Then open this folder in Claude Code and tell it "help me build my profile" to start onboarding.

> The first time it auto-reads browser cookies, macOS pops a keychain prompt ("access Chrome Safe Storage") → click Allow.

## Quick start (3 commands to verify install)

```bash
# 1. Validate the sample profile (engine runs)
cd engine && python3 validate_profile.py 迪迪

# 2. Auto-pull your last 30 posts, infer your north star (needs browser logged into Douyin)
../.venv/bin/python fetch/pull.py onboarding 迪迪 --n 30 --goal 涨粉

# 3. Daily report: last 10 posts judged by north star (CLI)
../.venv/bin/python fetch/daily_report.py 迪迪 --n 10
```

Once it runs, replace "迪迪" with your own profile id (onboarding creates it).

Want the **web daily report that pops up every morning**:
```bash
bash scripts/install_daily.sh install your_id 8   # generate & open in browser daily at 08:00
bash scripts/daily_run.sh your_id                 # run once now
```

## User journey (8 levels)

![User journey map](docs/用户旅程地图.png)

```
LV0 Install+Detect → LV1 Personalize → LV2 Topics (♻️ re-roll)
→ LV3 Script (tone off → distill blogger / feed your own) → LV4 Pre-check+Forecast (forecast low → back to script, fix the hook)
→ LV5 Production (visual off → swap template / distill style) → LV6 Publish → BOSS Review
→ Loop: weight validated playbooks → back to topics, sharper each lap
```

## Full agent workflow

```
        ┌─────────────────────────────────────────────────────┐
        │  Onboarding (one-time setup)                         │
        │  8 questions + auto-pull last 30 posts → infer NS    │
        │  → profiles/{you}/profile.json (valid = built)       │
        │  → distill benchmarks into your playbook library     │
        └─────────────────────────────────────────────────────┘
                          │ profile built, run daily below
                          ▼
   ┌──► ① Topics    reads your profile + scorecard + niche source router
   │       pull trends → 9 viral formulas × your moat → 5-dim score → list (you pick)
   │          │
   │          ▼
   │    ② Script    reads your voice samples + hook/structure/human-voice mechanics
   │       voiceover (iterated in chat, saved only when final) → publish kit
   │          │
   │          ▼
   │    ③ Pre-check+Forecast   3-layer red-line scan (generic + platform-official + your positioning)
   │       red/yellow/green with minimal edits · AI-labeling/qualification · forecast low → back to ②
   │          │
   │          ▼
   │    ④ Production   cover/slides/shot-plan in your visual style → final cut
   │          │
   │          ▼
   │    ⑤ Publish (manual)
   │          │
   │          ▼
   │    ⑥ Review   auto-pull backend → judge hit/miss by your north star
   │       retention attribution (early drop=hook / mid drop=structure) · throttling alert · daily report
   │          │
   └──────────┘  Loop: validated playbooks weighted back → next round sharper
```

Which profile fields each stage reads, and which mechanics it uses — see [工作流.md](工作流.md).

## Directory structure

```
profiles/          Profile layer: one profile.json per creator (north star / audience / red lines / visual…)
  ├─ 迪迪/         Sample #1 (AI-tools account, Douyin)
  ├─ 职场琳/       Sample #2 (career account, Xiaohongshu — proves "swap niche, no code change")
  └─ _schema/      Field table + north-star enum + playbook structure
engine/            Engine: judge / review (review card) / baseline (metric inference)
  └─ fetch/        Auto data pull: get_cookie / pull / daily_report / daily_report_html
scripts/           daily_run.sh (morning run) · install_daily.sh (schedule it)
skills/            Claude Code skills: onboarding / topics / script / pre-check / review
共享机制/           Shared mechanics: scorecard / 14 hooks / human-voice writing / red-line library / source router
视频生产/模板库/     Cover templates / slide styles / shot plans (colors follow your profile)
工作流.md           Full-chain SOP
```

## Design principles (why it's "universal")

1. **The engine reads profiles, hardcodes no one.** Feed the same data to different profiles and the review verdict / topic scores / info sources / visual style all differ — guarded by a regression test (`engine/test_judge.py`).
2. **Mechanics vs samples are separated.** Viral *mechanics* (14 hooks / scorecard framework / 2-second bounce ruler) are shared; viral *samples* (your niche's ammo) are distilled into your own playbook.
3. **You can change anything.** North star / sources / scoring weights / voice / red lines all live in your `profile.json`, with validation as a safety net (`validate_profile.py`).
4. **Data beats claims.** You say you want followers, but the data shows your strength is saves — the agent surfaces the conflict and lets you decide.

## Dependencies & graceful degradation

| Dependency | Required? | If missing |
|---|---|---|
| Claude Code | ✅ | skills won't run |
| Python 3.10+ / venv | ✅ | fetch/judge scripts won't run |
| Browser logged into Douyin | for data pull | completion/follows/retention unavailable; fallback: save cookie to `~/.douyin_cookie` |
| TikHub Token (paid 3rd-party) | optional | benchmark distill / Xiaohongshu sources degrade to manual paste |

## Privacy

- Cookies are read and used only on your machine, uploaded nowhere.
- Your real profile (`profiles/your_id/`) is **not tracked by git** by default (.gitignore set); the repo ships sample profiles only.
- Raw data JSON pulled during review is likewise not committed.

## Known limits (the honest version)

- Backend data pull currently supports **Douyin** only; adapters for Xiaohongshu etc. are TODO (the judging engine itself is platform-agnostic).
- Douyin red lines come from the official Creator Academy; the Xiaohongshu red-line library is general operational knowledge.
- Voice can't be fully automated: to make scripts sound like you, you must feed your own past scripts (onboarding Q6).
- The daily report pulls per-video and can be slow with many videos (platform rate limits).

---

Maintained by generalizing the author's own content-production engine; iterating with a small hands-on cohort. Issues / feedback welcome.
