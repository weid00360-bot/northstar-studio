#!/usr/bin/env python3
"""
网页版抖音日报 —— 每早自动弹出的仪表盘。profile 驱动,不写死任何号。

  python3 engine/fetch/daily_report_html.py {id} [--n 10]

自动读浏览器 cookie → 拉底表 → 按 profile.north_star 判定 → 生成自包含 HTML(内联CSS/SVG,
无 CDN 依赖)→ 写 reports/抖音日报_YYYYMMDD.html,打印路径。daily_run.sh 负责打开+通知。

对照迪迪变美版 generate_report.py(943行,写死变美分类/建议):本版不搬那些,
KPI/判定全读档案,分类建议交给「选题」「复盘」skill。
"""
import argparse, html, os, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ENGINE)

import fetch_backend as fb
from judge import load_profile, judge, METRIC_REGISTRY

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,'PingFang SC',sans-serif;background:#EEF2F7;color:#1C1E24;padding:32px}
.wrap{max-width:1080px;margin:0 auto}
.hd{background:linear-gradient(120deg,#1F4ED8,#3E6BE6);color:#fff;border-radius:18px;padding:26px 30px;margin-bottom:22px}
.hd h1{font-size:26px;margin-bottom:6px}.hd .sub{opacity:.85;font-size:14px}
.hd .ns{margin-top:12px;font-size:14px;background:rgba(255,255,255,.16);display:inline-block;padding:6px 14px;border-radius:20px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:22px}
.kpi{background:#fff;border-radius:16px;padding:20px 22px;box-shadow:0 2px 10px rgba(30,40,80,.06)}
.kpi .lbl{font-size:13px;color:#7A8598;margin-bottom:8px}
.kpi .val{font-size:30px;font-weight:800}
.kpi .badge{font-size:12px;font-weight:700;padding:3px 10px;border-radius:12px;margin-left:8px;vertical-align:middle}
.hit{background:#E4F6EC;color:#1B8A4B}.miss{background:#FDE7E5;color:#C42B1C}.warn{background:#FFF4DD;color:#9A6B00}
.card{background:#fff;border-radius:16px;padding:24px;box-shadow:0 2px 10px rgba(30,40,80,.06);margin-bottom:22px}
.card h2{font-size:17px;margin-bottom:16px}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;color:#7A8598;font-weight:600;padding:10px 12px;border-bottom:2px solid #EEF2F7}
td{padding:12px;border-bottom:1px solid #F2F5F9}
tr:last-child td{border-bottom:none}
.tag{font-size:12px;font-weight:700;padding:3px 10px;border-radius:11px}
.note{font-size:13px;color:#7A8598;line-height:1.7}
.ft{text-align:center;color:#9AA5B5;font-size:12px;margin-top:24px}
code{background:#1C1E24;color:#8BE28B;padding:2px 8px;border-radius:6px;font-size:12px}
"""

def esc(s): return html.escape(str(s))

def kpi_card(label, value, badge_txt, badge_cls):
    b = f'<span class="badge {badge_cls}">{badge_txt}</span>' if badge_txt else ""
    return f'<div class="kpi"><div class="lbl">{esc(label)}</div><div class="val">{esc(value)}{b}</div></div>'

def build(pid, n):
    prof = load_profile(pid)
    ns = prof.get("north_star", [])
    ns_names = [x["metric"] for x in ns]
    s = fb.get_session()
    user = fb.get_user_info(s)
    ids = fb.get_creator_item_ids(s)
    ids.sort(key=lambda v: fb.parse_ct(v.get("create_time")), reverse=True)
    top = ids[:n]
    mm = fb.get_metrics_batch(s, [d["item_id"] for d in top])

    # KPI:账号级 + 最新一条的北极星
    kpis = [kpi_card("粉丝", f'{user.get("follower_count",0):,}', "", ""),
            kpi_card("总获赞", f'{user.get("total_favorited",0):,}', "", "")]
    if top:
        m0 = mm.get(top[0]["item_id"], {})
        rows0, verdict0, _ = judge(m0, prof)
        for r in rows0:
            if r["指标"] in ns_names:
                st = r["状态"]
                cls = "hit" if "达标" in st else ("miss" if "未过" in st or st=="平庸" else "warn")
                kpis.append(kpi_card(f'最新·{r["指标"]}', r["值"], st, cls))

    # 逐视频表
    trows, hit = [], 0
    for d in top:
        m = mm.get(d["item_id"], {})
        _, verdict, _ = judge(m, prof)
        if verdict == "命中": hit += 1
        cls = "hit" if verdict=="命中" else ("warn" if "样本太小" in verdict else "miss")
        vals = "".join(f'<td>{fb_fmt(METRIC_REGISTRY[nm](m)) if nm in METRIC_REGISTRY else "?"}</td>' for nm in ns_names)
        ts = fb.parse_ct(d.get("create_time"))
        pub = datetime.fromtimestamp(ts).strftime("%m-%d") if ts else "?"
        title = (m.get("_description") or d.get("title") or "")[:18]
        trows.append(f'<tr><td>{pub}</td><td>{esc(title)}</td>{vals}<td><span class="tag {cls}">{esc(verdict)}</span></td></tr>')

    ths = "".join(f"<th>{esc(x)}</th>" for x in ns_names)
    anti = "、".join(prof.get("anti_metrics", [])) or "无"
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>抖音日报 · {esc(user.get('nick_name'))}</title><style>{CSS}</style></head><body><div class="wrap">
<div class="hd"><h1>📊 抖音日报 · {esc(user.get('nick_name'))}</h1>
<div class="sub">{datetime.now():%Y-%m-%d %H:%M} 自动生成</div>
<div class="ns">北极星:{esc('、'.join(ns_names))} ｜ 不看:{esc(anti)}</div></div>
<div class="kpis">{''.join(kpis)}</div>
<div class="card"><h2>近 {len(top)} 条 · 按你的北极星判定(命中 {hit}/{len(top)})</h2>
<table><thead><tr><th>发布</th><th>标题</th>{ths}<th>判定</th></tr></thead><tbody>{''.join(trows)}</tbody></table></div>
<div class="card"><h2>怎么看</h2><p class="note">
· <b>命中</b>=这条北极星全达标;<b>扑</b>=没过合格线;<b>样本太小</b>=播放&lt;500,比率不可信别判。<br>
· &lt;48h 的新视频数据未稳,别急着判(复盘铁律)。<br>
· 想要单条留存归因/限流排查 → <code>python3 engine/fetch/pull.py review {esc(pid)} --item-id X</code>
</p></div>
<div class="ft">内容生产 Agent · profile 驱动日报 · 判据来自 profiles/{esc(pid)}/profile.json</div>
</div></body></html>"""

def fb_fmt(v):
    return f"{v:.3g}" if isinstance(v, float) else str(v)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id"); ap.add_argument("--n", type=int, default=10)
    a = ap.parse_args()
    doc = build(a.id, a.n)
    outdir = os.path.join(ENGINE, "..", "reports"); os.makedirs(outdir, exist_ok=True)
    path = os.path.abspath(os.path.join(outdir, f"抖音日报_{datetime.now():%Y%m%d}.html"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    print(path)

if __name__ == "__main__":
    main()
