#!/usr/bin/env python3
"""
update.py — Regenera o index.html do Dashboard Prospera com dados frescos do Attio.

Uso:
  python3 update.py dados.json
  python3 update.py dados.json --date 25/05/2026
"""

import sys
import json
import re
import os
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(SCRIPT_DIR, "prospera_companies.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "index.html")


def parse_args():
    args = sys.argv[1:]
    input_file = None
    gen_date = date.today().strftime("%d/%m/%Y")
    i = 0
    while i < len(args):
        if args[i] == "--date" and i + 1 < len(args):
            gen_date = args[i + 1]
            i += 2
        else:
            input_file = args[i]
            i += 1
    if not input_file:
        print("Uso: python3 update.py <arquivo.json> [--date DD/MM/YYYY]")
        sys.exit(1)
    return input_file, gen_date


def load_cache():
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_entries(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        return json.load(f)


def merge(entries, cache):
    for e in entries:
        rid = e.get("record_id", "")
        e["company"] = cache.get(rid, rid[:8] if rid else "Desconhecido")
    return entries


def compute_stats(entries):
    total = len(entries)
    active_count = sum(1 for e in entries if e.get("active") == "ATIVO")
    on_hold_count = sum(1 for e in entries if e.get("active") == "ON HOLD")
    declined_inv = sum(1 for e in entries if e.get("active") == "DECLINADO INVESTIDOR")
    declined_nord = sum(1 for e in entries if e.get("active") == "DECLINADO NORDER")
    updates_count = sum(1 for e in entries if e.get("active") == "UPDATES")

    adv_analysis = sum(1 for e in entries if e.get("status") == "7. ANÁLISE AVANÇADA")
    with_meeting = sum(1 for e in entries if e.get("status", "") >= "4." and e.get("status", "") <= "9.")
    stage5 = sum(1 for e in entries if e.get("status") == "5. AGENDAMENTO COM O CLIENTE")

    stage_counts = {}
    for i in range(8):
        prefix = f"{i}."
        stage_counts[i] = sum(1 for e in entries if e.get("status", "").startswith(prefix))

    return {
        "total": total,
        "active": active_count,
        "on_hold": on_hold_count,
        "declined_inv": declined_inv,
        "declined_nord": declined_nord,
        "updates": updates_count,
        "adv_analysis": adv_analysis,
        "with_meeting": with_meeting,
        "stage5": stage5,
        "stages": stage_counts,
    }


def build_investors_js(entries):
    rows = []
    for e in entries:
        row = {
            "company": e.get("company", ""),
            "status": e.get("status", ""),
            "active": e.get("active", ""),
            "status_notes": e.get("status_notes", "") or "",
            "lost_reason": e.get("lost_reason", "") or "",
        }
        rows.append(row)
    return json.dumps(rows, ensure_ascii=False, indent=2)


def build_html(entries, stats, gen_date):
    investors_js = build_investors_js(entries)

    s = stats
    total = s["total"]

    # Donut percentages (cumulative)
    pct_active = round(s["active"] / total * 100, 1) if total else 0
    pct_updates = round(s["updates"] / total * 100, 1) if total else 0
    pct_hold = round(s["on_hold"] / total * 100, 1) if total else 0
    pct_dec_inv = round(s["declined_inv"] / total * 100, 1) if total else 0
    pct_dec_nord = round(s["declined_nord"] / total * 100, 1) if total else 0

    # Conic gradient segments
    c1 = pct_active
    c2 = c1 + pct_updates
    c3 = c2 + pct_hold
    c4 = c3 + pct_dec_inv
    # c5 = 100 (remainder)

    # Funnel bars — max stage is stage 1 count for proportional bars
    max_stage = max(s["stages"].values()) if s["stages"] else 1

    def bar_w(n):
        return round(n / max_stage * 100, 1) if max_stage else 0

    def pct_str(n):
        return f"{round(n/total*100,1)}%" if total else "0%"

    # Conversion rates
    in_process = sum(s["stages"][i] for i in range(1, 8))
    conv_proc = round(in_process / total * 100, 1) if total else 0
    conv_meeting = round(s["with_meeting"] / in_process * 100, 1) if in_process else 0
    conv_adv = round(s["adv_analysis"] / s["with_meeting"] * 100, 1) if s["with_meeting"] else 0

    stage_names = [
        ("Não Contactado", False),
        ("Abordagem Realizada", True),
        ("Análise Inicial", True),
        ("Agendamento Norder", False),
        ("Reunião c/ Norder", True),
        ("Agendamento c/ Prospera", True),
        ("Reunião c/ Prospera", True),
        ("Análise Avançada", True),
    ]
    stage_colors = {
        0: "#c8d0db",
        1: "#1a3a5c",
        2: "#1a3a5c",
        3: "#c8d0db",
        4: "#1db87e",
        5: "#1db87e",
        6: "#1db87e",
        7: "#1db87e",
    }

    funnel_html = ""
    for i in range(8):
        cnt = s["stages"][i]
        name, is_active = stage_names[i]
        color = stage_colors[i]
        w = bar_w(cnt)
        num_cls = "" if is_active else " dim"
        name_cls = "" if is_active else " dim"
        cnt_cls = "" if cnt > 0 else " zero"
        cnt_style = 'style="color:var(--green2);font-weight:700"' if i == 7 and cnt > 0 else ""
        num_style = 'style="background:var(--green)"' if i == 7 and cnt > 0 else ""
        fill_label = f"{cnt}" if cnt > 0 and w > 15 else ""
        funnel_html += f"""
        <div class="stage">
          <div class="s-num{num_cls}"{num_style}>{i}</div>
          <div class="s-name{name_cls}"{' style="color:var(--green2);font-weight:700"' if i == 7 and cnt > 0 else ""}>{name}</div>
          <div class="s-track"><div class="s-fill" style="width:{w}%;background:{color}">{fill_label}</div></div>
          <div class="s-pct">{pct_str(cnt) if cnt > 0 else "—"}</div>
          <div class="s-count{cnt_cls}"{cnt_style}>{cnt if cnt > 0 else "0"}</div>
        </div>"""

    # Extra rows (on hold, declined)
    hold_w = bar_w(s["on_hold"])
    dec_inv_w = bar_w(s["declined_inv"])
    dec_nord_w = bar_w(s["declined_nord"])
    funnel_html += f"""
        <div style="margin: 14px 0 10px; border-top:1px dashed var(--line); padding-top:12px;">
          <div class="stage">
            <div class="s-num" style="background:#8496ae">—</div>
            <div class="s-name dim">On Hold</div>
            <div class="s-track"><div class="s-fill" style="width:{hold_w}%;background:#8496ae">{s["on_hold"] if hold_w > 15 else ""}</div></div>
            <div class="s-pct">{pct_str(s["on_hold"])}</div>
            <div class="s-count" style="color:#8496ae">{s["on_hold"]}</div>
          </div>
          <div class="stage">
            <div class="s-num" style="background:#d94f4f">✕</div>
            <div class="s-name dim">Declinados (investidor)</div>
            <div class="s-track"><div class="s-fill" style="width:{dec_inv_w}%;background:#d94f4f">{s["declined_inv"] if dec_inv_w > 20 else ""}</div></div>
            <div class="s-pct">{pct_str(s["declined_inv"])}</div>
            <div class="s-count" style="color:#d94f4f">{s["declined_inv"]}</div>
          </div>
          <div class="stage">
            <div class="s-num" style="background:#e0998c">✕</div>
            <div class="s-name dim">Declinados (Norder)</div>
            <div class="s-track"><div class="s-fill" style="width:{dec_nord_w}%;background:#e0998c"></div></div>
            <div class="s-pct">{pct_str(s["declined_nord"]) if s["declined_nord"] else "—"}</div>
            <div class="s-count" style="color:#d94f4f">{s["declined_nord"]}</div>
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Prospera — Roadshow de Investidores</title>

<!-- DATA_START -->
<script>
const GENERATED_DATE = "{gen_date}";
const INVESTORS = {investors_js};
</script>
<!-- DATA_END -->

<style>
  :root {{
    --navy:   #0f2540;
    --navy2:  #1a3a5c;
    --green:  #1db87e;
    --green2: #17a06d;
    --amber:  #e8a020;
    --red:    #d94f4f;
    --slate:  #8496ae;
    --line:   #e4e9f0;
    --bg:     #f0f3f7;
    --card:   #ffffff;
    --ink:    #1a2535;
  }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg); color: var(--ink); -webkit-font-smoothing: antialiased; }}

  /* ── HEADER ── */
  header {{
    background: var(--navy);
    padding: 22px 0 0;
    position: relative;
    overflow: hidden;
  }}
  header::before {{
    content: "";
    position: absolute; inset: 0;
    background: radial-gradient(ellipse at 80% 50%, rgba(29,184,126,.15) 0%, transparent 60%);
    pointer-events: none;
  }}
  .hdr-inner {{
    max-width: 1160px; margin: 0 auto; padding: 0 28px;
    display: flex; justify-content: space-between; align-items: center; gap: 24px; flex-wrap: wrap;
  }}
  .hdr-left {{ display: flex; align-items: center; gap: 16px; }}
  .hdr-brand {{ font-size: 22px; font-weight: 900; color: #fff; letter-spacing: -.3px; }}
  .hdr-brand span {{ color: var(--green); }}
  .hdr-tagline {{ font-size: 13px; color: #7fa8cc; }}
  .hdr-right {{ display: flex; align-items: center; gap: 10px; }}
  .view-btn {{
    cursor: pointer; border: none; font-size: 13px; font-weight: 600;
    padding: 7px 16px; border-radius: 20px; transition: background .15s, color .15s;
    display: flex; align-items: center; gap: 6px;
  }}
  .view-btn.active {{ background: #fff; color: var(--navy); }}
  .view-btn.inactive {{ background: transparent; color: rgba(255,255,255,.85);
    border: 1.5px solid rgba(255,255,255,.35); }}
  .view-btn.inactive:hover {{ background: rgba(255,255,255,.1); }}

  .progress-strip {{
    max-width: 1160px; margin: 18px auto 0; padding: 0 28px 0;
    display: flex; align-items: center; gap: 0; overflow: hidden; border-radius: 6px 6px 0 0;
  }}
  .ps-seg {{ flex: 1; height: 5px; }}

  /* ── VIEWS ── */
  .view {{ transition: opacity .2s; }}
  .view.hidden {{ display: none; }}

  /* ── WRAP ── */
  .wrap {{ max-width: 1160px; margin: 0 auto; padding: 0 28px 56px; }}

  /* ── KPIs ── */
  .kpis {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin-top: 18px; }}
  .kpi {{
    background: var(--card); border-radius: 12px; padding: 18px 16px 15px;
    border: 1px solid var(--line); box-shadow: 0 3px 14px rgba(15,37,64,.07);
    position: relative; overflow: hidden;
  }}
  .kpi::after {{
    content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    border-radius: 12px 12px 0 0;
  }}
  .kpi.c-green::after  {{ background: var(--green); }}
  .kpi.c-navy::after   {{ background: var(--navy2); }}
  .kpi.c-amber::after  {{ background: var(--amber); }}
  .kpi.c-red::after    {{ background: var(--red); }}
  .kpi.c-slate::after  {{ background: var(--slate); }}
  .kpi .lbl {{ font-size: 10.5px; text-transform: uppercase; letter-spacing: .7px;
    font-weight: 700; color: var(--slate); }}
  .kpi .val {{ font-size: 34px; font-weight: 800; color: var(--navy); margin-top: 8px; line-height: 1; }}
  .kpi .val small {{ font-size: 15px; font-weight: 600; color: var(--slate); }}
  .kpi .sub {{ font-size: 11.5px; color: var(--slate); margin-top: 5px; }}

  /* ── Section titles ── */
  .sec {{ margin-top: 22px; }}
  .sec-title {{ font-size: 12px; text-transform: uppercase; letter-spacing: 1px;
    font-weight: 700; color: var(--slate); margin-bottom: 12px; display: flex;
    align-items: center; gap: 8px; }}
  .sec-title::after {{ content: ""; flex: 1; height: 1px; background: var(--line); }}

  /* ── Cards ── */
  .card {{
    background: var(--card); border-radius: 12px;
    border: 1px solid var(--line); box-shadow: 0 2px 10px rgba(15,37,64,.05);
    padding: 20px 22px;
  }}
  .card h3 {{ font-size: 14px; font-weight: 700; color: var(--navy); margin-bottom: 3px; }}
  .card .desc {{ font-size: 12px; color: var(--slate); margin-bottom: 16px; }}

  .grid-2 {{ display: grid; grid-template-columns: 1.5fr 1fr; gap: 16px; }}

  /* ── Funnel bars ── */
  .stage {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }}
  .s-num  {{ width: 22px; height: 22px; border-radius: 50%; background: var(--navy);
    color: #fff; font-size: 10px; font-weight: 700; display: flex; align-items: center;
    justify-content: center; flex-shrink: 0; }}
  .s-num.dim {{ background: #d0d8e4; color: #8496ae; }}
  .s-name {{ width: 210px; font-size: 12.5px; font-weight: 600; flex-shrink: 0; }}
  .s-name.dim {{ color: var(--slate); font-weight: 500; }}
  .s-track {{ flex: 1; background: #edf0f5; border-radius: 6px; height: 22px; overflow: hidden; }}
  .s-fill  {{ height: 100%; border-radius: 6px; display: flex; align-items: center;
    padding-left: 10px; color: #fff; font-size: 11px; font-weight: 700; }}
  .s-pct {{ font-size: 11px; color: var(--slate); width: 40px; text-align: right; flex-shrink: 0; }}
  .s-count {{ width: 28px; text-align: right; font-size: 13px; font-weight: 700;
    color: var(--navy); flex-shrink: 0; }}
  .s-count.zero {{ color: #c8d0db; }}

  /* ── Conversion ── */
  .conv {{ display: flex; align-items: stretch; gap: 0; }}
  .conv-step {{
    flex: 1; text-align: center; padding: 14px 10px;
    border-right: 1px dashed var(--line); position: relative;
  }}
  .conv-step:last-child {{ border-right: none; }}
  .conv-n {{ font-size: 28px; font-weight: 800; color: var(--navy); }}
  .conv-lbl {{ font-size: 10.5px; text-transform: uppercase; letter-spacing: .5px;
    color: var(--slate); font-weight: 600; margin-top: 3px; }}
  .conv-rate {{ font-size: 12px; font-weight: 700; color: var(--green); margin-top: 6px; }}
  .conv-rate.na {{ color: var(--slate); }}

  /* ── Donut ── */
  .donut-row {{ display: flex; align-items: center; gap: 22px; }}
  .donut {{ width: 140px; height: 140px; border-radius: 50%; flex-shrink: 0; position: relative; }}
  .donut::after {{ content: ""; position: absolute; inset: 28px;
    background: var(--card); border-radius: 50%; }}
  .donut-center {{ position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; z-index: 2; }}
  .donut-center .dn {{ font-size: 26px; font-weight: 800; color: var(--navy); }}
  .donut-center .dt {{ font-size: 10px; color: var(--slate); text-transform: uppercase; }}
  .legend {{ flex: 1; }}
  .leg-item {{ display: flex; align-items: center; gap: 9px; font-size: 13px; margin-bottom: 10px; }}
  .leg-dot {{ width: 12px; height: 12px; border-radius: 3px; flex-shrink: 0; }}
  .leg-n {{ margin-left: auto; font-weight: 700; color: var(--navy); font-size: 14px; }}
  .leg-pct {{ font-size: 11px; color: var(--slate); margin-left: 4px; }}

  /* ── Milestones ── */
  .milestones {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 16px; }}
  .ms {{ border-radius: 10px; padding: 14px 16px; border: 1px solid var(--line); }}
  .ms.active  {{ background: rgba(29,184,126,.06); border-color: rgba(29,184,126,.3); }}
  .ms.pending {{ background: rgba(232,160,32,.05);  border-color: rgba(232,160,32,.3); }}
  .ms.done    {{ background: rgba(29,184,126,.06); border-color: rgba(29,184,126,.3); }}
  .ms-icon {{ font-size: 18px; }}
  .ms-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: .5px;
    font-weight: 700; color: var(--slate); margin-top: 8px; }}
  .ms-val {{ font-size: 22px; font-weight: 800; color: var(--navy); margin-top: 2px; }}
  .ms-note {{ font-size: 11.5px; color: var(--slate); margin-top: 3px; }}

  /* ── Insights ── */
  .insights li {{ list-style: none; padding: 12px 0 12px 30px; position: relative;
    border-bottom: 1px dashed var(--line); font-size: 13.5px; line-height: 1.55; }}
  .insights li:last-child {{ border-bottom: none; }}
  .insights li::before {{ position: absolute; left: 0; top: 10px; font-size: 15px; }}
  .insights li.ok::before   {{ content: "✅"; }}
  .insights li.warn::before {{ content: "⚠️"; }}
  .insights li.info::before {{ content: "📊"; }}
  .insights li.next::before {{ content: "🎯"; }}
  .insights b {{ color: var(--navy); }}

  /* ── TABLE VIEW ── */
  .tbl-wrap {{ max-width: 1160px; margin: 0 auto; padding: 0 28px 56px; }}
  .tbl-controls {{
    position: sticky; top: 0; z-index: 20;
    background: var(--bg); padding: 14px 0 12px;
    border-bottom: 1px solid var(--line);
    display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  }}
  .tbl-search {{
    flex: 1; min-width: 220px; max-width: 340px;
    padding: 8px 12px; border-radius: 8px;
    border: 1.5px solid var(--line); font-size: 13px;
    background: var(--card); color: var(--ink); outline: none;
  }}
  .tbl-search:focus {{ border-color: var(--green); }}
  .filter-chips {{ display: flex; gap: 6px; flex-wrap: wrap; }}
  .chip {{
    cursor: pointer; padding: 5px 12px; border-radius: 20px; font-size: 11.5px;
    font-weight: 600; border: 1.5px solid var(--line); background: var(--card);
    color: var(--slate); transition: all .12s;
    white-space: nowrap;
  }}
  .chip.on {{ border-color: var(--navy); background: var(--navy); color: #fff; }}
  .chip:hover:not(.on) {{ border-color: var(--navy2); color: var(--navy2); }}
  .tbl-counter {{ font-size: 12px; color: var(--slate); margin-left: auto; white-space: nowrap; }}
  .tbl-sort-wrap {{ display: flex; align-items: center; gap: 6px; }}
  .tbl-sort-wrap label {{ font-size: 12px; color: var(--slate); }}
  .tbl-sort {{
    padding: 6px 10px; border-radius: 8px; border: 1.5px solid var(--line);
    font-size: 12px; background: var(--card); color: var(--ink); cursor: pointer; outline: none;
  }}

  .tbl-container {{ margin-top: 12px; border-radius: 12px; overflow: hidden;
    border: 1px solid var(--line); box-shadow: 0 2px 10px rgba(15,37,64,.05); }}
  table {{ width: 100%; border-collapse: collapse; background: var(--card); }}
  thead {{ position: sticky; top: 64px; z-index: 10; }}
  thead th {{
    background: var(--navy); color: rgba(255,255,255,.85);
    font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .6px;
    padding: 11px 14px; text-align: left; cursor: pointer; user-select: none;
    white-space: nowrap;
  }}
  thead th:hover {{ background: var(--navy2); }}
  thead th .sort-arrow {{ margin-left: 4px; opacity: .5; }}
  thead th.sorted .sort-arrow {{ opacity: 1; color: var(--green); }}
  tbody tr {{ border-bottom: 1px solid var(--line); transition: background .1s; }}
  tbody tr:last-child {{ border-bottom: none; }}
  tbody tr:nth-child(even) {{ background: #f7f9fc; }}
  tbody tr:hover {{ background: rgba(29,184,126,.04); border-left: 3px solid var(--green); }}
  tbody td {{ padding: 10px 14px; font-size: 13px; vertical-align: middle; }}
  td.td-num {{ color: var(--slate); font-size: 11px; width: 42px; text-align: right; padding-right: 8px; }}
  td.td-company {{ font-weight: 600; color: var(--navy); }}
  td.td-status {{ }}
  td.td-active {{ }}
  td.td-notes {{ color: var(--slate); font-size: 12px; max-width: 220px; }}
  td.td-notes .notes-text {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    max-width: 200px; display: block; cursor: default; }}

  /* Badges */
  .badge {{
    display: inline-block; padding: 3px 10px; border-radius: 12px;
    font-size: 11px; font-weight: 700; white-space: nowrap;
  }}
  .badge-ativo {{ background: #2E7D32; color: #fff; }}
  .badge-updates {{ background: #1565C0; color: #fff; }}
  .badge-onhold {{ background: #F57F17; color: #fff; }}
  .badge-dec-inv {{ background: #455A64; color: #fff; }}
  .badge-dec-nord {{ background: #C62828; color: #fff; }}

  /* Status pills */
  .pill {{
    display: inline-block; padding: 3px 9px; border-radius: 10px;
    font-size: 11px; font-weight: 600; white-space: nowrap;
  }}
  .pill-0 {{ background:#f0f2f5; color:#8496ae; }}
  .pill-1 {{ background:#e8eef6; color:#1a3a5c; }}
  .pill-2 {{ background:#e3ecf9; color:#1a3a5c; }}
  .pill-3 {{ background:#fff3e0; color:#e65100; }}
  .pill-4 {{ background:#e8f5e9; color:#2E7D32; }}
  .pill-5 {{ background:#e8f5e9; color:#2E7D32; }}
  .pill-6 {{ background:#e8f5e9; color:#2E7D32; }}
  .pill-7 {{ background:#c8f0de; color:#155724; font-weight:700; }}

  .tbl-footer {{ padding: 14px 0; font-size: 11.5px; color: var(--slate); text-align: center; }}

  footer {{ margin-top: 28px; padding-top: 16px; border-top: 1px solid var(--line);
    font-size: 11.5px; color: var(--slate); display: flex;
    justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }}
  .footer-logo {{ font-weight: 700; color: var(--navy); letter-spacing: .5px; }}

  @media (max-width: 900px) {{
    .kpis {{ grid-template-columns: repeat(2, 1fr); }}
    .grid-2 {{ grid-template-columns: 1fr; }}
    .milestones {{ grid-template-columns: 1fr 1fr; }}
    .hdr-right {{ flex-wrap: wrap; gap: 6px; }}
  }}
</style>
</head>
<body>

<!-- Header -->
<header>
  <div class="hdr-inner">
    <div class="hdr-left">
      <div>
        <div class="hdr-brand">PROSPERA</div>
        <div class="hdr-tagline">Roadshow de Investidores — Norder Capital</div>
      </div>
    </div>
    <div class="hdr-right">
      <button class="view-btn active" id="btn-dashboard" onclick="showView('dashboard')">📊 Dashboard</button>
      <button class="view-btn inactive" id="btn-table" onclick="showView('table')">📋 Lista</button>
    </div>
  </div>
  <div class="progress-strip">
    <div class="ps-seg" style="background:#253e5c"></div>
    <div class="ps-seg" style="background:#2e5070"></div>
    <div class="ps-seg" style="background:#1db87e;flex:2"></div>
    <div class="ps-seg" style="background:#17a06d;flex:.5"></div>
    <div class="ps-seg" style="background:#e8a020;flex:.3"></div>
    <div class="ps-seg" style="background:#d94f4f;flex:4"></div>
    <div class="ps-seg" style="background:#8496ae;flex:1"></div>
  </div>
</header>

<!-- VIEW 1: Dashboard -->
<div id="view-dashboard" class="view">
<div class="wrap">

  <!-- KPIs -->
  <div class="kpis" id="kpi-row"></div>

  <!-- Funil + Donut + Conversão -->
  <div class="sec">
    <div class="sec-title">Pipeline por estágio</div>
    <div class="grid-2">

      <div class="card">
        <h3>Funil do roadshow</h3>
        <div class="desc" id="funnel-desc"></div>
        {funnel_html}
      </div>

      <div style="display:flex;flex-direction:column;gap:16px">
        <div class="card">
          <h3>Visão geral do universo</h3>
          <div class="desc" id="donut-desc"></div>
          <div class="donut-row">
            <div class="donut" id="donut-chart">
              <div class="donut-center">
                <div class="dn" id="donut-n"></div>
                <div class="dt">total</div>
              </div>
            </div>
            <div class="legend" id="donut-legend"></div>
          </div>
        </div>

        <div class="card">
          <h3>Conversão do funil</h3>
          <div class="desc">Taxa de avanço pelos estágios-chave.</div>
          <div class="conv" id="conv-row"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- Milestones -->
  <div class="sec">
    <div class="sec-title">Marcos do processo</div>
    <div class="milestones" id="milestones-row"></div>
  </div>

  <!-- Insights -->
  <div class="sec">
    <div class="sec-title">Análise e próximos passos</div>
    <div class="card">
      <ul class="insights" id="insights-list"></ul>
    </div>
  </div>

  <footer>
    <div>Fonte: Attio · Lista Prospera · Gerado em <span id="footer-date-dash"></span></div>
    <div class="footer-logo">NORDER CAPITAL</div>
  </footer>
</div>
</div>

<!-- VIEW 2: Lista de Investidores -->
<div id="view-table" class="view hidden">
<div class="tbl-wrap">
  <div class="tbl-controls">
    <input class="tbl-search" id="tbl-search" type="text" placeholder="🔍 Buscar empresa..." oninput="renderTable()">
    <div class="filter-chips" id="filter-chips"></div>
    <div class="tbl-sort-wrap">
      <label>Ordenar:</label>
      <select class="tbl-sort" id="tbl-sort" onchange="renderTable()">
        <option value="stage">Por estágio</option>
        <option value="az">A–Z</option>
        <option value="za">Z–A</option>
      </select>
    </div>
    <div class="tbl-counter" id="tbl-counter"></div>
  </div>

  <div class="tbl-container">
    <table>
      <thead>
        <tr>
          <th class="td-num">#</th>
          <th onclick="toggleSort('company')">Empresa <span class="sort-arrow" id="arr-company"></span></th>
          <th onclick="toggleSort('status')">Pipeline Status <span class="sort-arrow" id="arr-status"></span></th>
          <th onclick="toggleSort('active')">Situação <span class="sort-arrow" id="arr-active"></span></th>
          <th>Observações</th>
        </tr>
      </thead>
      <tbody id="tbl-body"></tbody>
    </table>
  </div>
  <div class="tbl-footer">
    Fonte: Attio · Lista Prospera · Gerado em <span id="footer-date-tbl"></span>
  </div>
</div>
</div>

<script>
// ── Stats from data ──
function computeStats() {{
  const total = INVESTORS.length;
  const activeCount  = INVESTORS.filter(i => i.active === "ATIVO").length;
  const onHold       = INVESTORS.filter(i => i.active === "ON HOLD").length;
  const decInv       = INVESTORS.filter(i => i.active === "DECLINADO INVESTIDOR").length;
  const decNord      = INVESTORS.filter(i => i.active === "DECLINADO NORDER").length;
  const updates      = INVESTORS.filter(i => i.active === "UPDATES").length;
  const advAnalysis  = INVESTORS.filter(i => i.status === "7. ANÁLISE AVANÇADA").length;
  const withMeeting  = INVESTORS.filter(i => i.status >= "4.").length;
  const inProcess    = INVESTORS.filter(i => i.status > "0.").length;
  const stage5       = INVESTORS.filter(i => i.status === "5. AGENDAMENTO COM O CLIENTE").length;
  return {{ total, activeCount, onHold, decInv, decNord, updates, advAnalysis, withMeeting, inProcess, stage5 }};
}}

// ── Render KPIs ──
function renderKPIs(s) {{
  const pctActive = s.total ? ((s.activeCount / s.total)*100).toFixed(1) : 0;
  const convMeeting = s.activeCount ? ((s.withMeeting / (s.activeCount + s.onHold + s.updates))*100).toFixed(1) : 0;
  document.getElementById("kpi-row").innerHTML = `
    <div class="kpi c-green">
      <div class="lbl">Universo mapeado</div>
      <div class="val">${{s.total}}</div>
      <div class="sub">investidores identificados</div>
    </div>
    <div class="kpi c-navy">
      <div class="lbl">Pipeline ativo</div>
      <div class="val">${{s.activeCount}}</div>
      <div class="sub">em processo (${{pctActive}}%)</div>
    </div>
    <div class="kpi c-green">
      <div class="lbl">Análise avançada</div>
      <div class="val">${{s.advAnalysis}}</div>
      <div class="sub">investidores em due diligence</div>
    </div>
    <div class="kpi c-amber">
      <div class="lbl">Reuniões realizadas</div>
      <div class="val">${{s.withMeeting}}</div>
      <div class="sub">${{s.total ? ((s.withMeeting/s.total)*100).toFixed(1) : 0}}% taxa de conversão</div>
    </div>
    <div class="kpi c-slate">
      <div class="lbl">On Hold</div>
      <div class="val">${{s.onHold}}</div>
      <div class="sub">aguardando retomada</div>
    </div>
  `;
}}

// ── Render Donut ──
function renderDonut(s) {{
  const t = s.total;
  const pA  = t ? (s.activeCount/t*100).toFixed(1) : 0;
  const pU  = t ? (s.updates/t*100).toFixed(1) : 0;
  const pH  = t ? (s.onHold/t*100).toFixed(1) : 0;
  const pDI = t ? (s.decInv/t*100).toFixed(1) : 0;
  const pDN = t ? (s.decNord/t*100).toFixed(1) : 0;
  const c1 = +pA;
  const c2 = c1 + +pU;
  const c3 = c2 + +pH;
  const c4 = c3 + +pDI;
  document.getElementById("donut-chart").style.background =
    `conic-gradient(#1db87e 0 ${{c1}}%, #1565C0 ${{c1}}% ${{c2}}%, #F57F17 ${{c2}}% ${{c3}}%, #455A64 ${{c3}}% ${{c4}}%, #C62828 ${{c4}}% 100%)`;
  document.getElementById("donut-n").textContent = t;
  document.getElementById("donut-desc").textContent = `Distribuição de todos os ${{t}} investidores.`;
  document.getElementById("funnel-desc").textContent = `Distribuição dos ${{t}} investidores por etapa do processo.`;
  document.getElementById("donut-legend").innerHTML = `
    <div class="leg-item"><span class="leg-dot" style="background:#1db87e"></span>Ativo
      <span class="leg-n">${{s.activeCount}}</span><span class="leg-pct">${{pA}}%</span></div>
    ${{s.updates ? `<div class="leg-item"><span class="leg-dot" style="background:#1565C0"></span>Updates
      <span class="leg-n">${{s.updates}}</span><span class="leg-pct">${{pU}}%</span></div>` : ''}}
    <div class="leg-item"><span class="leg-dot" style="background:#F57F17"></span>On Hold
      <span class="leg-n">${{s.onHold}}</span><span class="leg-pct">${{pH}}%</span></div>
    <div class="leg-item"><span class="leg-dot" style="background:#455A64"></span>Declinado Inv.
      <span class="leg-n">${{s.decInv}}</span><span class="leg-pct">${{pDI}}%</span></div>
    ${{s.decNord ? `<div class="leg-item"><span class="leg-dot" style="background:#C62828"></span>Declinado Norder
      <span class="leg-n">${{s.decNord}}</span><span class="leg-pct">${{pDN}}%</span></div>` : ''}}
  `;
}}

// ── Render Conversion ──
function renderConversion(s) {{
  const t = s.total;
  const pProc = t ? ((s.inProcess/t)*100).toFixed(1) : 0;
  const pMeet = s.inProcess ? ((s.withMeeting/s.inProcess)*100).toFixed(1) : 0;
  const pAdv  = s.withMeeting ? ((s.advAnalysis/s.withMeeting)*100).toFixed(1) : 0;
  document.getElementById("conv-row").innerHTML = `
    <div class="conv-step"><div class="conv-n">${{t}}</div><div class="conv-lbl">Universo</div><div class="conv-rate na">—</div></div>
    <div class="conv-step"><div class="conv-n">${{s.inProcess}}</div><div class="conv-lbl">Em processo</div><div class="conv-rate">${{pProc}}%</div></div>
    <div class="conv-step"><div class="conv-n">${{s.withMeeting}}</div><div class="conv-lbl">Com reunião</div><div class="conv-rate">${{pMeet}}%</div></div>
    <div class="conv-step"><div class="conv-n">${{s.advAnalysis}}</div><div class="conv-lbl">Análise Av.</div><div class="conv-rate">${{pAdv}}%</div></div>
  `;
}}

// ── Render Milestones ──
function renderMilestones(s) {{
  const reached = INVESTORS.filter(i => i.status > "0.").length;
  document.getElementById("milestones-row").innerHTML = `
    <div class="ms done"><div class="ms-icon">📨</div>
      <div class="ms-label">Abordagens enviadas</div>
      <div class="ms-val">${{reached}}</div>
      <div class="ms-note">${{s.total ? ((reached/s.total)*100).toFixed(1) : 0}}% do universo contactado</div></div>
    <div class="ms done"><div class="ms-icon">🤝</div>
      <div class="ms-label">Reuniões com Norder</div>
      <div class="ms-val">${{s.withMeeting}}</div>
      <div class="ms-note">investidores apresentados ao deal</div></div>
    <div class="ms ${{s.advAnalysis > 0 ? 'active' : 'pending'}}"><div class="ms-icon">🔬</div>
      <div class="ms-label">Em análise avançada</div>
      <div class="ms-val">${{s.advAnalysis}}</div>
      <div class="ms-note">due diligence em andamento</div></div>
    <div class="ms ${{s.stage5 > 0 ? 'active' : 'pending'}}"><div class="ms-icon">📅</div>
      <div class="ms-label">Agendado c/ Prospera</div>
      <div class="ms-val">${{s.stage5}}</div>
      <div class="ms-note">1ª reunião com o cliente marcada</div></div>
    <div class="ms pending"><div class="ms-icon">🏁</div>
      <div class="ms-label">Aprovados</div>
      <div class="ms-val">0</div>
      <div class="ms-note">processo em curso</div></div>
    <div class="ms pending"><div class="ms-icon">⏸️</div>
      <div class="ms-label">On Hold</div>
      <div class="ms-val">${{s.onHold}}</div>
      <div class="ms-note">aguardando retomada</div></div>
  `;
}}

// ── Render Insights ──
function renderInsights(s) {{
  const pDeclined = s.total ? ((s.decInv + s.decNord)/s.total*100).toFixed(1) : 0;
  document.getElementById("insights-list").innerHTML = `
    ${{s.advAnalysis > 0 ? `<li class="ok"><b>${{s.advAnalysis}} investidor${{s.advAnalysis>1?'es':''}} em análise avançada</b> — estágio mais crítico e promissor do processo. Esses fundos avançaram além das reuniões iniciais e estão conduzindo due diligence ativo.</li>` : ''}}
    ${{s.stage5 > 0 ? `<li class="ok"><b>${{s.stage5}} investidor${{s.stage5>1?'es':''}} já agendou reunião direta com a Prospera</b> (estágio 5) — marco relevante do roadshow, indicando interesse concreto.</li>` : ''}}
    <li class="info"><b>${{pDeclined}}% do universo declinaram</b> (${{s.decInv + s.decNord}} de ${{s.total}}). Taxa esperada para um roadshow de captação. O foco agora é concentrar energia nos ${{s.advAnalysis}} em análise avançada e nos ${{s.onHold}} em on hold que podem ser reativados.</li>
    ${{s.onHold > 0 ? `<li class="warn"><b>${{s.onHold}} investidores em on hold</b> — oportunidade de reativação. Vale mapear os motivos de pausa e identificar quais têm potencial de retomada no curto prazo.</li>` : ''}}
    ${{s.advAnalysis > 0 ? `<li class="next"><b>Próximo passo crítico:</b> converter os ${{s.advAnalysis}} de análise avançada para o estágio de reunião com a Prospera e, eventualmente, para aprovação.</li>` : '<li class="next"><b>Próximo passo:</b> avançar investidores para as fases de análise e reunião com a Prospera.</li>'}}
  `;
}}

// ── TABLE VIEW LOGIC ──
let activeFilter = "all";
let sortCol = null;
let sortDir = 1;

const BADGE = {{
  "ATIVO":                 ["badge-ativo",    "Ativo"],
  "UPDATES":               ["badge-updates",  "Updates"],
  "ON HOLD":               ["badge-onhold",   "On Hold"],
  "DECLINADO INVESTIDOR":  ["badge-dec-inv",  "Decl. Inv."],
  "DECLINADO NORDER":      ["badge-dec-nord", "Decl. Norder"],
}};

const PILL_CLASS = {{
  "0": "pill-0", "1": "pill-1", "2": "pill-2", "3": "pill-3",
  "4": "pill-4", "5": "pill-5", "6": "pill-6", "7": "pill-7",
}};

function stageNum(status) {{
  const m = status.match(/^(\\d)/);
  return m ? m[1] : "0";
}}

function renderTable() {{
  const q = document.getElementById("tbl-search").value.toLowerCase();
  const sortSelect = document.getElementById("tbl-sort").value;

  let data = INVESTORS.filter(inv => {{
    const matchSearch = !q || inv.company.toLowerCase().includes(q);
    let matchFilter = true;
    if (activeFilter === "ativo")      matchFilter = inv.active === "ATIVO";
    else if (activeFilter === "onhold") matchFilter = inv.active === "ON HOLD";
    else if (activeFilter === "updates") matchFilter = inv.active === "UPDATES";
    else if (activeFilter === "dec-inv") matchFilter = inv.active === "DECLINADO INVESTIDOR";
    else if (activeFilter === "dec-nord") matchFilter = inv.active === "DECLINADO NORDER";
    return matchSearch && matchFilter;
  }});

  // Sort
  if (sortCol) {{
    data.sort((a, b) => {{
      let va = a[sortCol] || "", vb = b[sortCol] || "";
      return va < vb ? -sortDir : va > vb ? sortDir : 0;
    }});
  }} else {{
    if (sortSelect === "az") data.sort((a,b) => a.company.localeCompare(b.company));
    else if (sortSelect === "za") data.sort((a,b) => b.company.localeCompare(a.company));
    else data.sort((a,b) => b.status.localeCompare(a.status)); // stage desc
  }}

  document.getElementById("tbl-counter").textContent =
    `Exibindo ${{data.length}} de ${{INVESTORS.length}} investidores`;

  const rows = data.map((inv, idx) => {{
    const [bClass, bLabel] = BADGE[inv.active] || ["badge-dec-inv", inv.active];
    const sn = stageNum(inv.status);
    const pClass = PILL_CLASS[sn] || "pill-0";
    const notes = inv.status_notes || inv.lost_reason || "";
    const notesTrunc = notes.length > 50 ? notes.substring(0, 50) + "…" : notes;
    return `<tr>
      <td class="td-num">${{idx+1}}</td>
      <td class="td-company">${{inv.company}}</td>
      <td class="td-status"><span class="pill ${{pClass}}">${{inv.status}}</span></td>
      <td class="td-active"><span class="badge ${{bClass}}">${{bLabel}}</span></td>
      <td class="td-notes"><span class="notes-text" title="${{notes.replace(/"/g,"&quot;")}}">${{notesTrunc || "—"}}</span></td>
    </tr>`;
  }}).join("");

  document.getElementById("tbl-body").innerHTML = rows;
}}

function setFilter(f) {{
  activeFilter = f;
  document.querySelectorAll(".chip").forEach(c => c.classList.remove("on"));
  document.getElementById("chip-" + f).classList.add("on");
  renderTable();
}}

function toggleSort(col) {{
  if (sortCol === col) sortDir *= -1;
  else {{ sortCol = col; sortDir = 1; }}
  document.querySelectorAll(".sort-arrow").forEach(a => a.textContent = "");
  document.getElementById("arr-" + col).textContent = sortDir === 1 ? " ↑" : " ↓";
  document.querySelectorAll("thead th").forEach(th => th.classList.remove("sorted"));
  event.currentTarget.classList.add("sorted");
  renderTable();
}}

function buildFilterChips() {{
  const chips = [
    ["all", "Todos"],
    ["ativo", "ATIVO"],
    ["onhold", "ON HOLD"],
    ["updates", "UPDATES"],
    ["dec-inv", "DECLINADO INV."],
    ["dec-nord", "DECLINADO NORDER"],
  ];
  document.getElementById("filter-chips").innerHTML = chips.map(([f, label]) =>
    `<div class="chip${{f === "all" ? " on" : ""}}" id="chip-${{f}}" onclick="setFilter('${{f}}')">${{label}}</div>`
  ).join("");
}}

// ── View toggle ──
function showView(view) {{
  document.getElementById("view-dashboard").classList.toggle("hidden", view !== "dashboard");
  document.getElementById("view-table").classList.toggle("hidden", view !== "table");
  document.getElementById("btn-dashboard").className = "view-btn " + (view === "dashboard" ? "active" : "inactive");
  document.getElementById("btn-table").className = "view-btn " + (view === "table" ? "active" : "inactive");
  if (view === "table") renderTable();
}}

// ── INIT ──
(function init() {{
  const s = computeStats();
  renderKPIs(s);
  renderDonut(s);
  renderConversion(s);
  renderMilestones(s);
  renderInsights(s);
  buildFilterChips();

  // Set dates
  document.getElementById("footer-date-dash").textContent = GENERATED_DATE;
  document.getElementById("footer-date-tbl").textContent = GENERATED_DATE;
}})();
</script>
</body>
</html>"""

    return html


def main():
    input_file, gen_date = parse_args()
    cache = load_cache()
    entries = load_entries(input_file)
    entries = merge(entries, cache)
    stats = compute_stats(entries)
    html = build_html(entries, stats, gen_date)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✓ index.html gerado com {len(entries)} investidores")


if __name__ == "__main__":
    main()
