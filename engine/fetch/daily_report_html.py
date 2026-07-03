#!/usr/bin/env python3
"""
网页版抖音日报(富版) —— 每早自动弹出的仪表盘。沿用作者自用版的结构和视觉,
数据全走 fetch_backend 真实底表、判定全读 profile.north_star,砍掉变美专属的
"选题建议""内容方向"两块(那归选题/复盘 skill)。

  python3 engine/fetch/daily_report_html.py {id} [--n 7]

区块:北极星判定条 · KPI行 · 近N条判定表 · 流量漏斗(最新) · 留存曲线 · 2s跳出曲线 · 流量来源 · 近N趋势图。
"""
import argparse, html, json, os, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ENGINE)

import fetch_backend as fb
from judge import load_profile, judge, METRIC_REGISTRY

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"PingFang SC","Helvetica Neue",sans-serif;background:#f0f2f5;color:#1a1a2e;font-size:14px}
.hdr{background:linear-gradient(135deg,#1F4E79,#2E75B6);color:#fff;padding:26px 40px 22px}
.hdr h1{font-size:21px;font-weight:700}.hdr .sub{font-size:12px;opacity:.75;margin-top:5px}
.hdr .ns{margin-top:10px;font-size:12px;background:rgba(255,255,255,.16);display:inline-block;padding:5px 12px;border-radius:20px}
.kpi-row{display:flex;gap:10px;padding:18px 40px 0;flex-wrap:wrap}
.kpi{background:#fff;border-radius:10px;padding:13px 16px;flex:1;min-width:110px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.kpi .lbl{font-size:10px;color:#888;letter-spacing:.5px}
.kpi .val{font-size:22px;font-weight:700;color:#1F4E79;margin:3px 0 1px}
.kpi .bdg{font-size:10px;font-weight:600;padding:2px 8px;border-radius:12px;margin-left:4px}
.hit{background:#d4edda;color:#1a7a43}.miss{background:#fde8e8;color:#c53030}.warn{background:#fff3cd;color:#856404}
.main{padding:18px 40px;display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:860px){.main{grid-template-columns:1fr}}
.card{background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.card.full{grid-column:1/-1}
.card h2{font-size:14px;font-weight:700;color:#1F4E79;border-left:4px solid #2E75B6;padding-left:9px;margin-bottom:14px}
table{width:100%;border-collapse:collapse;font-size:12px}
th{background:#f7f9fc;color:#555;font-weight:600;padding:7px 9px;text-align:left;border-bottom:2px solid #e8ecf0}
td{padding:7px 9px;border-bottom:1px solid #f0f2f5}tr:last-child td{border-bottom:none}
.tag{display:inline-block;padding:2px 8px;border-radius:11px;font-size:11px;font-weight:700}
.fs{display:flex;align-items:center;gap:7px;margin:5px 0}
.fl{width:82px;font-size:11px;color:#555;text-align:right;flex-shrink:0}
.fb{flex:1;background:#f0f2f5;border-radius:4px;height:24px;overflow:hidden}
.fv{height:100%;border-radius:4px;display:flex;align-items:center;padding-left:7px;font-size:11px;color:#fff;font-weight:600;min-width:2px}
.chart-wrap{position:relative;height:210px}
.sr{display:flex;align-items:center;gap:7px;margin:5px 0;font-size:12px}
.slbl{width:66px;color:#555;flex-shrink:0}.sbar-bg{flex:1;background:#f0f2f5;border-radius:3px;height:14px;overflow:hidden}
.sbar{height:100%;background:#2E75B6;border-radius:3px}.sval{width:46px;font-weight:600;text-align:right}
.note{font-size:12px;color:#888;line-height:1.7}
footer{text-align:center;padding:16px;font-size:11px;color:#bbb}
"""

def esc(s): return html.escape(str(s))
def rate(a, b): return (a / b) if b else 0.0

def curve_arrays(curves, sec_key="retention"):
    ret = (curves or {}).get(sec_key, {})
    cur, sim = ret.get("current_item", []), ret.get("similar_author", [])
    labels = [p.get("key", "") for p in cur]
    cv = [round(float(p.get("value") or 0) * 100, 2) for p in cur]
    sv = [round(float(p.get("value") or 0) * 100, 2) for p in sim] if sim else []
    return labels, cv, sv

def build(pid, n):
    prof = load_profile(pid)
    ns_names = [x["metric"] for x in prof.get("north_star", [])]
    s = fb.get_session()
    user = fb.get_user_info(s)
    ids = fb.get_creator_item_ids(s)
    ids.sort(key=lambda v: fb.parse_ct(v.get("create_time")), reverse=True)
    top = ids[:n]
    mm = fb.get_metrics_batch(s, [d["item_id"] for d in top])
    latest_id = top[0]["item_id"] if top else None
    m0 = mm.get(latest_id, {}) if latest_id else {}
    compare = fb.get_item_compare(s, latest_id) if latest_id else {}
    curves = fb.get_retention_curves(s, latest_id) if latest_id else {}
    psource = fb.get_play_source(s, latest_id) if latest_id else []

    # KPI 行(通用指标 + 北极星判定徽章)
    v0 = m0.get("view_count", 0)
    kpi = [("最新播放", f'{int(v0):,}', "", ""),
           ("完播率", f'{m0.get("completion_rate",0)*100:.2f}%', "", ""),
           ("2s跳出", f'{m0.get("bounce_rate_2s",0)*100:.1f}%', "", ""),
           ("涨粉", f'{int(m0.get("subscribe_count",0)):,}', "", ""),
           ("点赞率", f'{rate(m0.get("like_count",0),v0)*100:.2f}%', "", "")]
    rows0, verdict0, meta0 = judge(m0, prof)
    kpi_html = "".join(f'<div class="kpi"><div class="lbl">{esc(l)}</div><div class="val">{esc(val)}</div></div>' for l,val,_,_ in kpi)

    # 北极星判定条
    vcls = "hit" if verdict0=="命中" else ("warn" if "样本太小" in verdict0 else "miss")
    ns_line = " ｜ ".join(f'{r["指标"]} {r["值"]} <span class="tag {("hit" if "达标" in r["状态"] else "miss")}">{esc(r["状态"])}</span>'
                         for r in rows0 if r["指标"] in ns_names)

    # 近N判定表
    trows, hit = [], 0
    tr_labels, tr_play, tr_cr, tr_bnc = [], [], [], []
    for d in reversed(top):  # 时间正序给趋势图
        m = mm.get(d["item_id"], {})
        ts = fb.parse_ct(d.get("create_time"))
        tr_labels.append(datetime.fromtimestamp(ts).strftime("%m-%d") if ts else "?")
        tr_play.append(int(m.get("view_count", 0)))
        tr_cr.append(round(m.get("completion_rate", 0)*100, 2))
        tr_bnc.append(round(m.get("bounce_rate_2s", 0)*100, 2))
    for d in top:
        m = mm.get(d["item_id"], {})
        _, verdict, _ = judge(m, prof)
        if verdict == "命中": hit += 1
        cls = "hit" if verdict=="命中" else ("warn" if "样本太小" in verdict else "miss")
        vals = "".join(f'<td>{METRIC_REGISTRY[nm](m):.3g}</td>' if nm in METRIC_REGISTRY else "<td>?</td>" for nm in ns_names)
        ts = fb.parse_ct(d.get("create_time"))
        pub = datetime.fromtimestamp(ts).strftime("%m-%d") if ts else "?"
        title = esc((m.get("_description") or d.get("title") or "")[:16])
        trows.append(f'<tr><td>{pub}</td><td>{title}</td>{vals}<td><span class="tag {cls}">{esc(verdict)}</span></td></tr>')
    ths = "".join(f"<th>{esc(x)}</th>" for x in ns_names)

    # 漏斗(最新)
    funnel = [("5s留存", m0.get("completion_rate_5s",0)*100, m0.get("completion_rate_5s",0)*100, "#3A86FF"),
              ("完播率", m0.get("completion_rate",0)*100, m0.get("completion_rate",0)*500, "#FF9800"),
              ("点赞率", rate(m0.get("like_count",0),v0)*100, rate(m0.get("like_count",0),v0)*1000, "#E91E63"),
              ("收藏率", rate(m0.get("favorite_count",0),v0)*100, rate(m0.get("favorite_count",0),v0)*1000, "#9C27B0"),
              ("吸粉率", rate(m0.get("subscribe_count",0),v0)*100, rate(m0.get("subscribe_count",0),v0)*2000, "#22a06b")]
    funnel_html = "".join(f'<div class="fs"><div class="fl">{l}</div><div class="fb">'
                          f'<div class="fv" style="width:{max(min(w,100),2):.0f}%;background:{c}">{val:.2f}%</div></div></div>'
                          for l,val,w,c in funnel)

    # 流量来源
    src_map = {"homepage_hot":"推荐流","follow":"关注页","search":"搜索","profile":"主页","nearby":"附近","other":"其他"}
    src_html = "".join(f'<div class="sr"><div class="slbl">{src_map.get(p.get("key"),p.get("key"))}</div>'
                       f'<div class="sbar-bg"><div class="sbar" style="width:{float(p.get("value") or 0)*100:.0f}%"></div></div>'
                       f'<div class="sval">{float(p.get("value") or 0)*100:.1f}%</div></div>'
                       for p in (psource or [])) or '<p class="note">暂无流量来源数据</p>'

    ret_lbl, ret_cv, ret_sv = curve_arrays(curves)
    anti = "、".join(prof.get("anti_metrics", [])) or "无"

    # Chart.js 内联(vendor 本地文件,不依赖 CDN;缺了退回 CDN)
    vend = os.path.join(HERE, "vendor", "chart.umd.min.js")
    if os.path.exists(vend):
        with open(vend, encoding="utf-8") as vf:
            chart_tag = f"<script>{vf.read()}</script>"
    else:
        chart_tag = '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>'

    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>抖音日报 · {esc(user.get('nick_name'))}</title>
{chart_tag}
<style>{CSS}</style></head><body>
<div class="hdr"><h1>📊 抖音数据日报 · {esc(user.get('nick_name'))}</h1>
<div class="sub">{datetime.now():%Y-%m-%d %H:%M} · 粉丝 {user.get('follower_count',0):,} · 总获赞 {user.get('total_favorited',0):,} · 近 {len(top)} 条</div>
<div class="ns">北极星:{esc('、'.join(ns_names))} ｜ 不看:{esc(anti)}</div></div>
<div class="kpi-row">{kpi_html}</div>
<div class="main">
<div class="card full"><h2>🎯 最新一条 · 北极星判定 <span class="tag {vcls}">{esc(verdict0)}</span></h2>
<p class="note">{ns_line}</p></div>
<div class="card full"><h2>近 {len(top)} 条 · 按你的北极星判定(命中 {hit}/{len(top)})</h2>
<table><thead><tr><th>发布</th><th>标题</th>{ths}<th>判定</th></tr></thead><tbody>{''.join(trows)}</tbody></table>
<p class="note" style="margin-top:8px">&lt;48h 新视频、播放&lt;500 数据未稳,别急着判(复盘铁律)。</p></div>
<div class="card"><h2>① 流量漏斗(最新)</h2>{funnel_html}</div>
<div class="card"><h2>② 流量来源(最新)</h2>{src_html}</div>
<div class="card"><h2>③ 留存曲线 vs 同类大盘</h2><div class="chart-wrap"><canvas id="ret"></canvas></div></div>
<div class="card"><h2>④ 近 {len(top)} 条完播率 vs 2s跳出</h2><div class="chart-wrap"><canvas id="trend"></canvas></div></div>
<div class="card full"><h2>⑤ 近 {len(top)} 条播放量趋势</h2><div class="chart-wrap"><canvas id="play"></canvas></div></div>
</div>
<footer>数据来源 creator.douyin.com · profile 驱动日报 · 判据来自 profiles/{esc(pid)}/profile.json · 选题/归因建议交给「选题」「复盘」skill</footer>
<script>
const opt={{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{boxWidth:11,font:{{size:10}}}}}}}},scales:{{x:{{ticks:{{font:{{size:9}}}}}},y:{{ticks:{{font:{{size:9}}}}}}}}}};
new Chart(ret,{{type:"line",data:{{labels:{json.dumps(ret_lbl)},datasets:[
 {{label:"当前作品",data:{json.dumps(ret_cv)},borderColor:"#2E75B6",backgroundColor:"rgba(46,117,182,.12)",fill:true,tension:.3,pointRadius:0}},
 {{label:"同类大盘",data:{json.dumps(ret_sv)},borderColor:"#bbb",borderDash:[5,3],fill:false,tension:.3,pointRadius:0}}]}},options:opt}});
new Chart(trend,{{type:"line",data:{{labels:{json.dumps(tr_labels)},datasets:[
 {{label:"完播率%",data:{json.dumps(tr_cr)},borderColor:"#22a06b",tension:.3,pointRadius:4}},
 {{label:"2s跳出%",data:{json.dumps(tr_bnc)},borderColor:"#E53E3E",tension:.3,pointRadius:4}}]}},options:opt}});
new Chart(play,{{type:"line",data:{{labels:{json.dumps(tr_labels)},datasets:[
 {{label:"播放量",data:{json.dumps(tr_play)},borderColor:"#2E75B6",backgroundColor:"rgba(46,117,182,.1)",fill:true,tension:.3,pointRadius:4}}]}},options:opt}});
</script></body></html>"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id"); ap.add_argument("--n", type=int, default=7)
    a = ap.parse_args()
    doc = build(a.id, a.n)
    outdir = os.path.join(ENGINE, "..", "reports"); os.makedirs(outdir, exist_ok=True)
    path = os.path.abspath(os.path.join(outdir, f"抖音日报_{datetime.now():%Y%m%d}.html"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    print(path)

if __name__ == "__main__":
    main()
