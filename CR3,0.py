import streamlit as st
import pandas as pd
import requests
import itertools
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import gspread
import random
from google.oauth2.service_account import Credentials

# --- PAGE CONFIG ---
st.set_page_config(page_title="Clash Analyzer Pro", layout="wide", page_icon="📊")

# --- GLOBALES DESIGN-SYSTEM (Theme & CSS) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root{
  --bg:#0B0E14; --surface:#141A23; --surface-2:#1B2230; --border:#262E3D;
  --text:#E6EAF1; --muted:#8A93A6; --primary:#5B8DEF; --win:#22C55E; --loss:#F43F5E; --gold:#F5B544;
}

html, body, [class*="css"], .stApp{ font-family:'Inter',sans-serif; }
.stApp{ background:
  radial-gradient(1200px 600px at 82% -12%, rgba(91,141,239,0.10), transparent 60%),
  radial-gradient(900px 500px at 0% 0%, rgba(124,92,255,0.06), transparent 55%),
  var(--bg); }

.block-container{ padding-top:1.3rem; padding-bottom:3rem; max-width:1300px; }

h1,h2,h3{ color:var(--text); font-weight:700; letter-spacing:-0.02em; }
h2{ font-size:1.45rem; } h3{ font-size:1.12rem; }

/* Hero */
.hero{ display:flex; align-items:center; justify-content:space-between;
  background:linear-gradient(135deg, rgba(91,141,239,0.16), rgba(20,26,35,0.55));
  border:1px solid var(--border); border-radius:18px; padding:20px 26px; margin-bottom:20px;
  box-shadow:0 10px 34px rgba(0,0,0,0.38); }
.hero .brand{ display:flex; align-items:center; gap:16px; }
.hero .logo{ width:48px; height:48px; border-radius:13px; display:grid; place-items:center;
  background:linear-gradient(135deg,var(--primary),#7C5CFF); font-size:25px;
  box-shadow:0 8px 20px rgba(91,141,239,0.45); }
.hero h1{ margin:0; font-size:1.5rem; font-weight:800; }
.hero p{ margin:3px 0 0; color:var(--muted); font-size:0.85rem; }
.hero .pill{ background:rgba(34,197,94,0.12); color:var(--win); border:1px solid rgba(34,197,94,0.32);
  padding:7px 14px; border-radius:999px; font-size:0.78rem; font-weight:600; white-space:nowrap; }

/* Tabs */
.stTabs [data-baseweb="tab-list"]{ gap:4px; border-bottom:1px solid var(--border); background:transparent; }
.stTabs [data-baseweb="tab"]{ height:44px; padding:0 18px; background:transparent;
  border-radius:11px 11px 0 0; color:var(--muted); font-weight:600; font-size:0.9rem; }
.stTabs [aria-selected="true"]{ color:var(--text); background:var(--surface);
  border-bottom:2px solid var(--primary); }

/* Metric-Karten */
[data-testid="stMetric"]{ background:var(--surface); border:1px solid var(--border);
  border-radius:14px; padding:16px 18px; box-shadow:0 4px 16px rgba(0,0,0,0.25); }
[data-testid="stMetricLabel"] p{ color:var(--muted); font-weight:600; font-size:0.75rem;
  text-transform:uppercase; letter-spacing:0.05em; }
[data-testid="stMetricValue"]{ color:var(--text); font-weight:700; }

/* Buttons */
.stButton>button{ border-radius:10px; font-weight:600; border:1px solid var(--border);
  background:var(--surface); color:var(--text); transition:all .15s ease; }
.stButton>button:hover{ border-color:var(--primary); color:#fff; transform:translateY(-1px); }
.stButton>button[kind="primary"]{ background:linear-gradient(135deg,var(--primary),#7C5CFF);
  border:none; box-shadow:0 8px 18px rgba(91,141,239,0.40); }

/* Tabellen / Expander */
[data-testid="stDataFrame"]{ border:1px solid var(--border); border-radius:14px; overflow:hidden; }
[data-testid="stExpander"]{ border:1px solid var(--border); border-radius:12px; background:var(--surface); }

/* Sidebar */
[data-testid="stSidebar"]{ background:#0D121B; border-right:1px solid var(--border); }
.side-brand{ display:flex; align-items:center; gap:12px; padding:4px 2px 12px; }
.side-brand .logo{ width:38px; height:38px; border-radius:11px; display:grid; place-items:center;
  background:linear-gradient(135deg,var(--primary),#7C5CFF); font-size:19px; }
.side-brand .t{ font-weight:800; font-size:1.02rem; color:var(--text); line-height:1.1; }
.side-brand .s{ font-size:0.72rem; color:var(--muted); }

/* KPI-Kacheln */
.kpi-grid{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin:6px 0 18px; }
.kpi{ background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:16px 18px; box-shadow:0 4px 16px rgba(0,0,0,0.25); }
.kpi .label{ color:var(--muted); font-size:0.74rem; text-transform:uppercase; letter-spacing:0.05em; font-weight:600; }
.kpi .value{ font-size:1.7rem; font-weight:700; margin-top:6px; color:var(--text); }
.kpi .sub{ font-size:0.82rem; margin-top:2px; color:var(--muted); }
.kpi .sub.up{ color:var(--win); } .kpi .sub.down{ color:var(--loss); }

/* Custom-Tabellen */
.tbl-wrap{ background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:6px 10px; box-shadow:0 4px 16px rgba(0,0,0,0.25); }
.ctable{ width:100%; border-collapse:collapse; font-size:0.9rem; }
.ctable thead th{ text-align:left; color:var(--muted); font-weight:600; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.05em; padding:10px 12px; border-bottom:1px solid var(--border); }
.ctable tbody td{ padding:11px 12px; border-bottom:1px solid rgba(38,46,61,0.5); color:var(--text); }
.ctable tbody tr:last-child td{ border-bottom:none; }
.ctable tbody tr:hover{ background:rgba(91,141,239,0.06); }
.ctable .name{ font-weight:600; }
.ctable .wr{ font-weight:700; }
.rank{ width:26px; height:26px; border-radius:8px; display:inline-grid; place-items:center; font-weight:700; font-size:0.78rem; background:var(--surface-2); color:var(--text); }
.rank.g{ background:linear-gradient(135deg,#F5B544,#E89A2B); color:#1a1205; }
.chip{ padding:3px 9px; border-radius:999px; font-size:0.76rem; font-weight:600; }
.chip.pos{ background:rgba(34,197,94,0.14); color:var(--win); }
.chip.neg{ background:rgba(244,63,94,0.14); color:var(--loss); }
.chip.neu{ background:var(--surface-2); color:var(--muted); }

/* H2H – sachlich, monochrom, Fortschritt zu 100 Siegen pro Begegnung */
.h2h-row{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:15px 20px; margin-bottom:10px; }
.h2h-head{ display:flex; justify-content:space-between; align-items:baseline; margin-bottom:13px; padding-bottom:11px; border-bottom:1px solid var(--border); }
.h2h-title{ font-weight:600; font-size:0.95rem; color:var(--text); }
.h2h-meta{ font-size:0.74rem; color:var(--muted); }
.h2h-line{ display:flex; align-items:center; gap:14px; margin:9px 0; }
.h2h-pname{ width:104px; font-size:0.87rem; color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.h2h-track{ flex:1; height:7px; background:var(--surface-2); border-radius:6px; overflow:hidden; }
.h2h-fill{ height:100%; background:#5A6678; border-radius:6px; }
.h2h-count{ width:62px; text-align:right; font-size:0.85rem; font-weight:600; color:var(--muted); font-variant-numeric:tabular-nums; }
.h2h-line.lead .h2h-pname{ color:var(--text); font-weight:600; }
.h2h-line.lead .h2h-fill{ background:#E6EAF1; }
.h2h-line.lead .h2h-count{ color:var(--text); }

/* Horizontale Wertebalken (Race / Winrate) – Spielerfarbe als Kennung, ruhiger Look */
.hbar-row{ display:flex; align-items:center; gap:14px; margin:12px 0; }
.hbar-name{ width:104px; font-size:0.87rem; color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.hbar-track{ flex:1; height:12px; background:var(--surface-2); border-radius:7px; overflow:hidden; }
.hbar-fill{ height:100%; border-radius:7px; opacity:0.9; }
.hbar-val{ width:64px; text-align:right; font-size:0.85rem; font-weight:600; color:var(--text); font-variant-numeric:tabular-nums; }

/* dezente Notiz */
.subtle-note{ color:var(--muted); font-size:0.82rem; margin:-6px 0 16px; }

/* Scrollbar */
::-webkit-scrollbar{ width:10px; height:10px; }
::-webkit-scrollbar-thumb{ background:#2A3343; border-radius:8px; }
::-webkit-scrollbar-track{ background:transparent; }
</style>
""", unsafe_allow_html=True)

# --- KONFIGURATION ---
TAGS = {
    "resan": "R902QGYCP",
    "gooterplayer": "VCGLJU02",
    "Jörg": "YY89R9L9G"
}

SOLO_TAGS = {
    "Flexus": "QUJC02U2L"
}

SHEET_URL = "https://docs.google.com/spreadsheets/d/1SZQhK7TeBRI6DspxVJWU31ul_PGTXNOoxcOwE6rn2u8/edit?gid=641247476#gid=641247476"

API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjM0MGI5OTVhLTg2MmEtNGUwOC1hNWM2LThhNzgyYmE5ZjI5NiIsImlhdCI6MTc4MDc0MjU0NSwic3ViIjoiZGV2ZWxvcGVyL2MyYjczNjYyLWE2YjYtNzdkMC00N2I4LTM5YjE0MWYyNzcxOCIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyI5Mi4yMDguMjEuMjE4Il0sInR5cGUiOiJjbGllbnQifV19.W748jBxxPdxUGrrg95fH43GTX2oRGvDfYEVjTLJLPEPbepi_J7AjdwGOvlkq4BnAqcmK6RdJrNVKA4iK1VwePA"

# --- GOOGLE SHEETS SETUP ---
@st.cache_resource
def init_google_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["google_credentials"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SHEET_URL)
    return (
        sheet.worksheet("Karten_Data"),
        sheet.worksheet("Fun_Data"),
        sheet.worksheet("Profile_Data"),
        sheet.worksheet("Global_Data")
    )

try:
    ws_comp, ws_fun, ws_prof, ws_global = init_google_sheets()
except Exception as e:
    st.error(f"Datenbank-Verbindung fehlgeschlagen. Bitte SHEET_URL prüfen! Fehler: {e}")
    st.stop()

def get_df_from_sheet(worksheet):
    data = worksheet.get_all_records()
    if data: return pd.DataFrame(data)
    return pd.DataFrame()

# --- API LOGIK ---
@st.cache_data(ttl=60)
def get_api_data(endpoint, tag):
    url = f"https://api.clashroyale.com/v1/players/%23{tag}/{endpoint}" if endpoint else f"https://api.clashroyale.com/v1/players/%23{tag}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
        else:
            return {"_error": True, "_status": res.status_code, "_msg": res.text[:300]}
    except Exception as e:
        return {"_error": True, "_status": 0, "_msg": str(e)}

# --- AUTO-SCANNER (Google Sheets Sync) ---
def scan_for_battles():
    df_comp = get_df_from_sheet(ws_comp)
    df_fun = get_df_from_sheet(ws_fun)

    new_comp_rows, new_fun_rows = [], []
    known_comp_ids = set(df_comp['ID'].astype(str)) if not df_comp.empty else set()
    known_fun_ids = set(df_fun['ID'].astype(str)) if not df_fun.empty else set()

    api_errors = []

    for name, tag in TAGS.items():
        log = get_api_data("battlelog", tag)

        if log is None or (isinstance(log, dict) and log.get("_error")):
            status = log.get("_status", "?") if isinstance(log, dict) else "?"
            msg = log.get("_msg", "") if isinstance(log, dict) else ""
            api_errors.append(f"**{name}** → Status `{status}`: {msg}")
            continue

        if not isinstance(log, list):
            api_errors.append(f"**{name}** → Unerwartetes Format: {str(log)[:200]}")
            continue

        for b in log:
            b_id = b.get('battleTime')
            if not b.get('opponent') or not b.get('team'):
                continue
            opp_tag = b['opponent'][0].get('tag', '').replace('#', '')
            rival = next((n for n, t in TAGS.items() if t == opp_tag), None)

            if rival:
                s1, s2 = b['team'][0].get('crowns', 0), b['opponent'][0].get('crowns', 0)
                k1 = ", ".join([c['name'] for c in b['team'][0].get('cards', [])])
                k2 = ", ".join([c['name'] for c in b['opponent'][0].get('cards', [])])
                row_data = [b_id, name, rival, s1, s2, k1, k2]

                if b_id not in known_fun_ids:
                    new_fun_rows.append(row_data)
                    known_fun_ids.add(b_id)

                is_solo = len(b.get('team', [])) == 1 and len(b.get('opponent', [])) == 1
                # FIX: deckSelection kann 'collection', 'own' oder leer sein
                deck_val = b.get('deckSelection', '')
                is_own_deck = deck_val in ('collection', 'own', '')
                if is_solo and is_own_deck and b_id not in known_comp_ids:
                    new_comp_rows.append(row_data)
                    known_comp_ids.add(b_id)

    if new_comp_rows:
        ws_comp.append_rows(new_comp_rows)
    if new_fun_rows:
        ws_fun.append_rows(new_fun_rows)

    return len(new_comp_rows), len(new_fun_rows), api_errors

# --- EINHEITLICHES DIAGRAMM-DESIGN ---
CHART_COLORWAY = ["#5B8DEF", "#22C55E", "#F5B544", "#F43F5E", "#7C5CFF"]
PLAYER_COLORS = {p[:10]: CHART_COLORWAY[i % len(CHART_COLORWAY)] for i, p in enumerate(TAGS.keys())}

def style_fig(fig, height=300, legend=True, smooth=True):
    """Einheitliches, elegantes Dark-Theme fuer ALLE Plotly-Diagramme:
    transparenter Hintergrund, Inter-Font, dezente Achsen, weiche Spline-Linien,
    randlose Balken mit abgerundeten Ecken, saubere Donut-Trenner und gestylter Hover."""
    fig.update_layout(
        height=height,
        font=dict(family="Inter, sans-serif", color="#E6EAF1", size=12),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=34, b=10, l=10, r=14),
        showlegend=legend,
        colorway=CHART_COLORWAY,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        hoverlabel=dict(bgcolor="#141A23", bordercolor="#262E3D",
                        font=dict(family="Inter, sans-serif", color="#E6EAF1", size=12)),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#262E3D", ticks="")
    fig.update_yaxes(showgrid=True, gridcolor="#1A2230", zeroline=True,
                     zerolinecolor="#2A3343", zerolinewidth=1, linecolor="rgba(0,0,0,0)", ticks="")
    for tr in fig.data:
        t = getattr(tr, "type", None)
        if t == "scatter":
            if smooth and "lines" in (tr.mode or ""):
                tr.line.shape = "spline"
                tr.line.smoothing = 0.6
                if not tr.line.width or tr.line.width < 2.5:
                    tr.line.width = 2.5
        elif t == "bar":
            if tr.marker.line is not None:
                tr.marker.line.width = 0
        elif t == "pie":
            tr.marker.line = dict(color="#0B0E14", width=2)
    try:
        fig.update_layout(barcornerradius=6)
    except Exception:
        pass
    return fig

# --- HELFER FUNKTIONEN ---
def parse_time(id_str):
    if str(id_str).startswith("LEGACY") or str(id_str).startswith("MANUAL"): return pd.NaT
    try: return pd.to_datetime(id_str, format="%Y%m%dT%H%M%S.%fZ")
    except: return pd.NaT

def count_wins(player, df):
    """Anzahl der Siege eines Spielers in einem 1v1-DataFrame (Spieler1/Spieler2-Schema)."""
    return sum(1 for _, r in df.iterrows()
               if (r['Spieler1'] == player and r['Score1'] > r['Score2'])
               or (r['Spieler2'] == player and r['Score2'] > r['Score1']))

def calculate_card_stats(spieler, df):
    if df.empty or 'Spieler1' not in df.columns: return pd.DataFrame()
    p_df = df[(df['Spieler1'] == spieler) | (df['Spieler2'] == spieler)]
    if len(p_df) == 0: return pd.DataFrame()
    counts = {}
    for _, row in p_df.iterrows():
        is_p1 = row['Spieler1'] == spieler
        win = (row['Score1'] > row['Score2']) if is_p1 else (row['Score2'] > row['Score1'])
        for k in str(row['Karten1'] if is_p1 else row['Karten2']).split(","):
            k = k.strip().capitalize()
            if k:
                if k not in counts: counts[k] = [0, 0]
                counts[k][0] += 1
                if win: counts[k][1] += 1
    data = [{"Karte": k, "Gespielt": v[0], "Winrate (%)": round((v[1]/v[0]*100),1)} for k, v in counts.items()]
    res_df = pd.DataFrame(data)
    top_use = res_df.sort_values("Gespielt", ascending=False).head(5)
    return top_use

def get_h2h_stats_data(df):
    pairs = list(itertools.combinations(TAGS.keys(), 2))
    results, global_current_streak, global_all_time_streak = [], {"player": "-", "count": 0}, {"player": "-", "count": 0}
    for p1, p2 in pairs:
        match_df = df[((df['Spieler1'] == p1) & (df['Spieler2'] == p2)) | ((df['Spieler1'] == p2) & (df['Spieler2'] == p1))].sort_values(by='ID')
        if len(match_df) == 0: continue
        wins_p1, wins_p2, streak_winner, streak_count, all_time_streak_winner, all_time_streak_count = 0, 0, None, 0, None, 0
        for _, row in match_df.iterrows():
            is_p1_win = (row['Spieler1'] == p1 and row['Score1'] > row['Score2']) or (row['Spieler2'] == p1 and row['Score2'] > row['Score1'])
            if is_p1_win:
                wins_p1 += 1
                if streak_winner == p1: streak_count += 1
                else: streak_winner, streak_count = p1, 1
            else:
                wins_p2 += 1
                if streak_winner == p2: streak_count += 1
                else: streak_winner, streak_count = p2, 1
            if streak_count > all_time_streak_count: all_time_streak_count, all_time_streak_winner = streak_count, streak_winner
        total = wins_p1 + wins_p2
        wr_p1, wr_p2 = (wins_p1 / total) * 100, (wins_p2 / total) * 100
        results.append({
            'Matchup': f"{p1[:10]} vs {p2[:10]}", 'Score': f"{wins_p1} : {wins_p2}", 'Spiele': total,
            'Dominanz': f"{p1 if wr_p1 >= wr_p2 else p2} ({max(wr_p1, wr_p2):.0f}%)",
            'Streak': f"{streak_count}x {streak_winner}" if streak_count > 1 else "-"
        })
        if streak_count > global_current_streak["count"]: global_current_streak = {"player": streak_winner, "count": streak_count}
        if all_time_streak_count > global_all_time_streak["count"]: global_all_time_streak = {"player": all_time_streak_winner, "count": all_time_streak_count}
    return pd.DataFrame(results), global_current_streak, global_all_time_streak

def get_player_form_and_streak(player, df):
    p_df = df[(df['Spieler1'] == player) | (df['Spieler2'] == player)].sort_values('ID').tail(15)
    if p_df.empty: return 0, 0
    wins, streak = 0, 0
    is_win_streak = None
    for _, r in p_df.iterrows():
        is_p1 = r['Spieler1'] == player
        p_won = (r['Score1'] > r['Score2']) if is_p1 else (r['Score2'] > r['Score1'])
        if p_won:
            wins += 1
            if is_win_streak in (None, True): streak += 1; is_win_streak = True
            else: streak = 1; is_win_streak = True
        else:
            if is_win_streak in (None, False): streak += 1; is_win_streak = False
            else: streak = 1; is_win_streak = False
    net_wins = wins - (len(p_df) - wins)
    actual_streak = streak if is_win_streak else -streak
    return net_wins, actual_streak

def get_global_streaks(player, df_global):
    """Persönliche Streak-Analyse über ALLE globalen Spiele eines Spielers (nicht nur die internen 1v1).
    Gibt zurück: (aktuelle_streak_signiert, längste_winstreak, längste_lostreak, anzahl_spiele).
    Positiv = aktive Siegesserie, Negativ = aktive Niederlagenserie, 0 = Unentschieden/keine Serie."""
    if df_global is None or df_global.empty or 'Spieler' not in df_global.columns:
        return 0, 0, 0, 0
    p_df = df_global[df_global['Spieler'] == player].sort_values('Time_ID')
    if p_df.empty:
        return 0, 0, 0, 0
    outcomes = []
    for _, r in p_df.iterrows():
        if r['Score_Me'] > r['Score_Opp']: outcomes.append('W')
        elif r['Score_Me'] < r['Score_Opp']: outcomes.append('L')
        else: outcomes.append('D')
    longest_win, longest_lose, run, run_type = 0, 0, 0, None
    for o in outcomes:
        if o == run_type: run += 1
        else: run, run_type = 1, o
        if o == 'W': longest_win = max(longest_win, run)
        elif o == 'L': longest_lose = max(longest_lose, run)
    last = outcomes[-1]
    cur = 0
    for o in reversed(outcomes):
        if o == last: cur += 1
        else: break
    current_signed = cur if last == 'W' else (-cur if last == 'L' else 0)
    return current_signed, longest_win, longest_lose, len(outcomes)

def calc_matchup_odds(p1, p2, df, form_weight=1.0):
    match_df = df[((df['Spieler1'] == p1) & (df['Spieler2'] == p2)) | ((df['Spieler1'] == p2) & (df['Spieler2'] == p1))]
    total_h2h = len(match_df)
    p1_h2h_wins = count_wins(p1, match_df)
    p1_h2h_wr = (p1_h2h_wins / total_h2h * 100) if total_h2h > 0 else 50
    p2_h2h_wr = 100 - p1_h2h_wr if total_h2h > 0 else 50
    h2h_bonus_p1 = (p1_h2h_wr - 50) * 1.5
    h2h_bonus_p2 = (p2_h2h_wr - 50) * 1.5
    f1, s1 = get_player_form_and_streak(p1, df)
    f2, s2 = get_player_form_and_streak(p2, df)
    score_p1 = max(10, 100 + h2h_bonus_p1 + ((f1 * 2) * form_weight) + ((s1 * 4) * form_weight))
    score_p2 = max(10, 100 + h2h_bonus_p2 + ((f2 * 2) * form_weight) + ((s2 * 4) * form_weight))
    prob_1 = score_p1 / (score_p1 + score_p2)
    prob_2 = score_p2 / (score_p1 + score_p2)
    odds_1 = max(1.01, round(1 / prob_1, 2))
    odds_2 = max(1.01, round(1 / prob_2, 2))
    insight = "Ausgeglichenes Matchup"
    if total_h2h == 0: insight = "Keine H2H-Historie"
    elif p1_h2h_wr > 50 and s2 >= 3: insight = f"H2H {p1[:6]} | Momentum {p2[:6]} (+{s2})"
    elif p2_h2h_wr > 50 and s1 >= 3: insight = f"H2H {p2[:6]} | Momentum {p1[:6]} (+{s1})"
    elif f1 > f2 + 4: insight = f"Form {p1[:6]} (NW: +{f1})"
    elif f2 > f1 + 4: insight = f"Form {p2[:6]} (NW: +{f2})"
    elif p1_h2h_wr >= 70: insight = f"H2H-Dominanz {p1[:6]} ({p1_h2h_wr:.0f}%)"
    elif p2_h2h_wr >= 70: insight = f"H2H-Dominanz {p2[:6]} ({p2_h2h_wr:.0f}%)"
    return prob_1, prob_2, odds_1, odds_2, insight

def build_sessions(df):
    if df.empty: return {}
    df = df.copy()
    df['Time'] = df['ID'].apply(parse_time)
    df_valid = df.dropna(subset=['Time']).sort_values('Time').copy()
    if df_valid.empty: return {}
    df_valid['Time_Diff'] = df_valid['Time'].diff()
    df_valid['Session_Num'] = (df_valid['Time_Diff'] > pd.Timedelta(minutes=30)).cumsum()
    sessions = {}
    for s_num, group in df_valid.groupby('Session_Num'):
        if len(group) < 2: continue
        start_time = group['Time'].iloc[0].strftime("%d.%m.%Y - %H:%M")
        s_name = f"{start_time} ({len(group)} Spiele)"
        sessions[s_name] = group
    return dict(reversed(list(sessions.items())))

def get_session_leaderboard(session_df):
    total_games = len(session_df)
    stats = {p: {"P": 0, "W": 0, "L": 0, "curr_streak": 0, "is_win": None, "max_w_streak": 0, "max_l_streak": 0} for p in TAGS.keys()}
    for _, row in session_df.iterrows():
        p1, p2 = row['Spieler1'], row['Spieler2']
        if p1 in stats and p2 in stats:
            p1_won = row['Score1'] > row['Score2']
            stats[p1]["P"] += 1; stats[p2]["P"] += 1
            if p1_won:
                stats[p1]["W"] += 1; stats[p2]["L"] += 1
                if stats[p1]["is_win"] == True: stats[p1]["curr_streak"] += 1
                else: stats[p1]["is_win"] = True; stats[p1]["curr_streak"] = 1
                stats[p1]["max_w_streak"] = max(stats[p1]["max_w_streak"], stats[p1]["curr_streak"])
                if stats[p2]["is_win"] == False: stats[p2]["curr_streak"] += 1
                else: stats[p2]["is_win"] = False; stats[p2]["curr_streak"] = 1
                stats[p2]["max_l_streak"] = max(stats[p2]["max_l_streak"], stats[p2]["curr_streak"])
            else:
                stats[p2]["W"] += 1; stats[p1]["L"] += 1
                if stats[p2]["is_win"] == True: stats[p2]["curr_streak"] += 1
                else: stats[p2]["is_win"] = True; stats[p2]["curr_streak"] = 1
                stats[p2]["max_w_streak"] = max(stats[p2]["max_w_streak"], stats[p2]["curr_streak"])
                if stats[p1]["is_win"] == False: stats[p1]["curr_streak"] += 1
                else: stats[p1]["is_win"] = False; stats[p1]["curr_streak"] = 1
                stats[p1]["max_l_streak"] = max(stats[p1]["max_l_streak"], stats[p1]["curr_streak"])
    max_wins = max([data["W"] for data in stats.values()]) if stats else 0
    leaderboard = []
    for p, data in stats.items():
        if data["P"] == 0: continue
        wr = data["W"] / data["P"]
        score_wr = wr * 4.0
        score_dom = (data["W"] / max_wins * 3.5) if max_wins > 0 else 0
        score_imp = (data["P"] / total_games * 2.5) if total_games > 0 else 0
        max_w_s = max(1, data["max_w_streak"]) if data["W"] > 0 else 1
        max_l_s = max(1, data["max_l_streak"]) if data["L"] > 0 else 1
        streak_mod = ((max_w_s - 1) * 0.3) - ((max_l_s - 1) * 0.3)
        final_rating = max(0.0, min(10.0, score_wr + score_dom + score_imp + streak_mod))
        leaderboard.append({
            "Spieler": p[:10], "Matches": data["P"], "Wins": data["W"], "Losses": data["L"],
            "WR": f"{wr*100:.0f}%", "Streaks": f"+{data['max_w_streak']} / -{data['max_l_streak']}", "Rating (KotH)": round(final_rating, 1)
        })
    if not leaderboard: return pd.DataFrame()
    df_lb = pd.DataFrame(leaderboard).sort_values(by="Rating (KotH)", ascending=False).reset_index(drop=True)
    df_lb.index = df_lb.index + 1
    return df_lb

def get_session_analysis(session_df):
    """Detaillierte Per-Spieler-Statistiken + chronologischer Momentum-Verlauf einer Session.
    Returns: (stats_dict, players_list, timeline_df).
    timeline_df enthält die kumulierten Netto-Siege jedes Spielers nach jedem Spiel (für Verlaufs-Grafik)."""
    sdf = session_df.copy()
    sdf['Time'] = sdf['ID'].apply(parse_time)
    sdf = sdf.dropna(subset=['Time']).sort_values('Time')
    if sdf.empty:
        sdf = session_df.copy().sort_values('ID')
    present = set(sdf['Spieler1']).union(set(sdf['Spieler2']))
    players = [p for p in TAGS.keys() if p in present]
    stats = {p: {"P": 0, "W": 0, "L": 0, "CF": 0, "CA": 0, "cur": 0, "is_win": None, "max_w": 0, "max_l": 0} for p in players}
    cum = {p: 0 for p in players}
    timeline = [{"Spiel": 0, "Spieler": p[:10], "Netto-Siege": 0} for p in players]
    game_idx = 0
    for _, row in sdf.iterrows():
        p1, p2 = row['Spieler1'], row['Spieler2']
        if p1 not in stats or p2 not in stats: continue
        game_idx += 1
        s1, s2 = int(row['Score1']), int(row['Score2'])
        stats[p1]["P"] += 1; stats[p2]["P"] += 1
        stats[p1]["CF"] += s1; stats[p1]["CA"] += s2
        stats[p2]["CF"] += s2; stats[p2]["CA"] += s1
        if s1 > s2:
            stats[p1]["W"] += 1; stats[p2]["L"] += 1; cum[p1] += 1; cum[p2] -= 1
            if stats[p1]["is_win"] == True: stats[p1]["cur"] += 1
            else: stats[p1]["is_win"], stats[p1]["cur"] = True, 1
            stats[p1]["max_w"] = max(stats[p1]["max_w"], stats[p1]["cur"])
            if stats[p2]["is_win"] == False: stats[p2]["cur"] += 1
            else: stats[p2]["is_win"], stats[p2]["cur"] = False, 1
            stats[p2]["max_l"] = max(stats[p2]["max_l"], stats[p2]["cur"])
        elif s2 > s1:
            stats[p2]["W"] += 1; stats[p1]["L"] += 1; cum[p2] += 1; cum[p1] -= 1
            if stats[p2]["is_win"] == True: stats[p2]["cur"] += 1
            else: stats[p2]["is_win"], stats[p2]["cur"] = True, 1
            stats[p2]["max_w"] = max(stats[p2]["max_w"], stats[p2]["cur"])
            if stats[p1]["is_win"] == False: stats[p1]["cur"] += 1
            else: stats[p1]["is_win"], stats[p1]["cur"] = False, 1
            stats[p1]["max_l"] = max(stats[p1]["max_l"], stats[p1]["cur"])
        for p in players:
            timeline.append({"Spiel": game_idx, "Spieler": p[:10], "Netto-Siege": cum[p]})
    return stats, players, pd.DataFrame(timeline)

def run_monte_carlo_tournament(df, target_wins, sims, form_weight):
    players = list(TAGS.keys())
    if len(players) < 2: return {}
    prob_matrix = {}
    for p1 in players:
        prob_matrix[p1] = {}
        for p2 in players:
            if p1 != p2:
                prob1, _, _, _, _ = calc_matchup_odds(p1, p2, df, form_weight)
                prob_matrix[p1][p2] = prob1
    results = {p: 0 for p in players}
    sweeps = 0
    progress_text = "Simuliere Universen..."
    my_bar = st.progress(0, text=progress_text)
    for i in range(sims):
        if i % (sims // 10) == 0: my_bar.progress(i / sims, text=progress_text)
        wins = {p: 0 for p in players}
        tournament_winner = None
        while not tournament_winner:
            p1, p2 = random.sample(players, 2)
            prob_p1_wins = prob_matrix[p1][p2]
            if random.random() < prob_p1_wins:
                wins[p1] += 1
                if wins[p1] == target_wins: tournament_winner = p1
            else:
                wins[p2] += 1
                if wins[p2] == target_wins: tournament_winner = p2
        results[tournament_winner] += 1
        sweep_threshold = target_wins * 0.2
        others_scores = [wins[p] for p in players if p != tournament_winner]
        if max(others_scores) <= sweep_threshold: sweeps += 1
    my_bar.empty()
    return results, sweeps

if 'mc_results' not in st.session_state:
    st.session_state['mc_results'] = None
    st.session_state['mc_sweeps'] = 0
    st.session_state['mc_sims'] = 0
    st.session_state['mc_target'] = 0

# --- LADE DATEN ---
df_comp = get_df_from_sheet(ws_comp)
df_fun = get_df_from_sheet(ws_fun)
df_prof = get_df_from_sheet(ws_prof)
df_global = get_df_from_sheet(ws_global)

latest_match_str = "Keine Daten"
if not df_comp.empty:
    times = df_comp['ID'].apply(parse_time).dropna()
    if not times.empty: latest_match_str = times.max().strftime('%d.%m.%Y - %H:%M')

# --- SIDEBAR ---
st.sidebar.markdown("""
<div class='side-brand'>
  <div class='logo'>📊</div>
  <div><div class='t'>Clash Analyzer</div><div class='s'>Pro Edition</div></div>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

# SCAN BUTTON
if st.sidebar.button("🔄 Neue Spiele suchen", use_container_width=True, type="primary"):
    with st.spinner("Scanne API & synchronisiere mit Google Sheets..."):
        get_api_data.clear()
        c, f, errors = scan_for_battles()
        if errors:
            for err in errors:
                st.sidebar.error(f"⚠️ API Fehler: {err}")
        else:
            st.sidebar.success(f"✅ {c} Kompetitiv / {f} Fun neu!")
        st.rerun()

# DEBUG EXPANDER
with st.sidebar.expander("🔧 API Debug"):
    if st.button("Vollständige Diagnose", use_container_width=True):
        known_tags = set(TAGS.values())
        for name, tag in TAGS.items():
            url = f"https://api.clashroyale.com/v1/players/%23{tag}/battlelog"
            headers = {"Authorization": f"Bearer {API_KEY}"}
            try:
                res = requests.get(url, headers=headers, timeout=10)
                if res.status_code != 200:
                    st.error(f"❌ **{name}**: Status {res.status_code}")
                    continue

                data = res.json()
                st.success(f"✅ **{name}**: {len(data)} Kämpfe im Log")

                # Zeige die letzten 5 Gegner-Tags RAW
                st.markdown(f"**Letzte 5 Gegner-Tags von {name}:**")
                matches_found = 0
                for b in data[:5]:
                    if not b.get('opponent'): continue
                    raw_tag = b['opponent'][0].get('tag', 'KEIN TAG')
                    clean_tag = raw_tag.replace('#', '')
                    is_crew = clean_tag in known_tags
                    marker = "🟢 CREW-MATCH!" if is_crew else "⚪"
                    deck_val = b.get('deckSelection', 'FEHLT')
                    st.caption(f"{marker} Raw: `{raw_tag}` | Clean: `{clean_tag}` | deck: `{deck_val}`")
                    if is_crew:
                        matches_found += 1

                # Prüfe ob ein Crew-Match irgendwo in den letzten 25 Kämpfen ist
                crew_matches_total = 0
                for b in data:
                    if not b.get('opponent'): continue
                    opp_tag = b['opponent'][0].get('tag', '').replace('#', '')
                    if opp_tag in known_tags:
                        crew_matches_total += 1

                if crew_matches_total == 0:
                    st.warning(f"⚠️ Kein einziges Crew-Match in den letzten {len(data)} Kämpfen von {name} gefunden. Die Spieler haben möglicherweise noch nicht gegeneinander gespielt — oder die Tags in TAGS stimmen nicht mit den echten API-Tags überein.")
                else:
                    st.info(f"🎯 {crew_matches_total} Crew-Matches gefunden in {len(data)} Kämpfen")

            except Exception as e:
                st.error(f"❌ **{name}**: {e}")

        # TAG Vergleich: Was ist in TAGS vs was kommt aus der API
        st.markdown("---")
        st.markdown("**TAGS-Konfiguration (zum Vergleich):**")
        for n, t in TAGS.items():
            st.caption(f"`{n}` → `{t}`")

st.sidebar.markdown("---")
st.sidebar.write("**System-Status**")
st.sidebar.write(f"Datensätze (Lokal): {len(df_comp)}")
st.sidebar.write(f"Datensätze (Global): {len(df_global)}")
st.sidebar.write(f"Letztes Match: {latest_match_str}")
st.sidebar.markdown("---")

# --- HERO HEADER ---
st.markdown(f"""
<div class='hero'>
  <div class='brand'>
    <div class='logo'>👑</div>
    <div>
      <h1>Clash Analyzer Pro</h1>
      <p>Crew-Liga · Spieler-Analysen · Live-Prognosen</p>
    </div>
  </div>
  <div class='pill'>● Live · {len(df_comp)} Duelle erfasst</div>
</div>
""", unsafe_allow_html=True)

# --- NAVIGATION ---
tab_dbl, tab_spieler_loc, tab_spieler_glob, tab_trends, tab_sessions, tab_prognose, tab_mc, tab_flexus = st.tabs([
    "1v1 Liga", "Spieler (Lokal)", "Spieler-Analyse", "Aktivität & Trends", "Sessions", "Prognose", "Monte Carlo", "Flexus (Solo)"
])

# --- TAB 1: 1v1 LIGA ---
with tab_dbl:
    st.header("Offizielles 1v1 Leaderboard")
    st.markdown("<div class='subtle-note'>Race to 100 · Winner stays · alle gewerteten internen Matches, sortiert nach Winrate und Net-Wins.</div>", unsafe_allow_html=True)
    if not df_comp.empty:
        lb_data = []
        for p in TAGS.keys():
            p_df = df_comp[(df_comp['Spieler1'] == p) | (df_comp['Spieler2'] == p)]
            spiele = len(p_df)
            if spiele > 0:
                siege = count_wins(p, p_df)
                niederlagen = spiele - siege
                winrate = (siege / spiele) * 100
                net_wins = siege - niederlagen
                lb_data.append({"Spieler": p[:10], "Spiele": spiele, "Siege": siege, "Niederlagen": niederlagen, "Net-Wins": net_wins, "Winrate (%)": round(winrate, 1)})
        h2h_df, curr_streak, at_streak = get_h2h_stats_data(df_comp)

        if lb_data:
            df_lb = pd.DataFrame(lb_data).sort_values(by=["Winrate (%)", "Net-Wins"], ascending=[False, False]).reset_index(drop=True)
            df_lb.index = df_lb.index + 1
            race_leader = df_lb.sort_values('Siege', ascending=False).iloc[0]

            # --- KPI-Kacheln ---
            st.markdown(f"""
<div class='kpi-grid'>
  <div class='kpi'><div class='label'>Aktuelle Winstreak</div><div class='value'>{curr_streak['count']}&times;</div><div class='sub up'>&#9650; {curr_streak['player']}</div></div>
  <div class='kpi'><div class='label'>All-Time Rekord</div><div class='value'>{at_streak['count']}&times;</div><div class='sub'>{at_streak['player']}</div></div>
  <div class='kpi'><div class='label'>F&uuml;hrend &middot; Race to 100</div><div class='value'>{int(race_leader['Siege'])} <span style='font-size:0.9rem;color:var(--muted)'>/ 100</span></div><div class='sub up'>&#9650; {race_leader['Spieler']}</div></div>
</div>
""", unsafe_allow_html=True)

            # --- Leaderboard als Custom-Tabelle ---
            rows = ""
            for rank, (_, r) in enumerate(df_lb.iterrows(), start=1):
                rcls = "rank g" if rank == 1 else "rank"
                nw = int(r['Net-Wins'])
                chip = (f"<span class='chip pos'>+{nw}</span>" if nw > 0 else
                        (f"<span class='chip neg'>{nw}</span>" if nw < 0 else "<span class='chip neu'>0</span>"))
                rows += (f"<tr><td><span class='{rcls}'>{rank}</span></td><td class='name'>{r['Spieler']}</td>"
                         f"<td>{int(r['Spiele'])}</td><td>{int(r['Siege'])}</td><td>{int(r['Niederlagen'])}</td>"
                         f"<td>{chip}</td><td class='wr'>{r['Winrate (%)']:.1f}%</td></tr>")
            st.markdown(
                "<div class='tbl-wrap'><table class='ctable'><thead><tr><th>#</th><th>Spieler</th>"
                "<th>Spiele</th><th>Siege</th><th>Niederl.</th><th>Net-Wins</th><th>Winrate</th></tr></thead>"
                f"<tbody>{rows}</tbody></table></div>", unsafe_allow_html=True)
            st.markdown("<div class='subtle-note' style='margin-top:10px;'>Net-Wins: Differenz aus Siegen und Niederlagen &ndash; Indikator f&uuml;r echten Fortschritt.</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Head-to-Head Historie")
        st.markdown("<div class='subtle-note' style='margin-bottom:14px;'>Direkter Vergleich aller Begegnungen. Wer dominiert wen?</div>", unsafe_allow_html=True)
        if not h2h_df.empty:
            html = ""
            for _, r in h2h_df.iterrows():
                parts = str(r['Matchup']).split(" vs ")
                p1 = parts[0]; p2 = parts[1] if len(parts) > 1 else ""
                sc = str(r['Score']).split(":")
                try:
                    w1 = int(sc[0].strip()); w2 = int(sc[1].strip())
                except Exception:
                    w1 = w2 = 0
                lead1 = " lead" if w1 >= w2 else ""
                lead2 = " lead" if w2 > w1 else ""
                html += (
                    "<div class='h2h-row'>"
                    f"<div class='h2h-head'><span class='h2h-title'>{p1} &nbsp;vs&nbsp; {p2}</span>"
                    f"<span class='h2h-meta'>{int(r['Spiele'])} Spiele &middot; Dominanz {r['Dominanz']}</span></div>"
                    f"<div class='h2h-line{lead1}'><span class='h2h-pname'>{p1}</span>"
                    f"<div class='h2h-track'><div class='h2h-fill' style='width:{min(100, w1)}%'></div></div>"
                    f"<span class='h2h-count'>{w1} / 100</span></div>"
                    f"<div class='h2h-line{lead2}'><span class='h2h-pname'>{p2}</span>"
                    f"<div class='h2h-track'><div class='h2h-fill' style='width:{min(100, w2)}%'></div></div>"
                    f"<span class='h2h-count'>{w2} / 100</span></div>"
                    "</div>"
                )
            st.markdown(html, unsafe_allow_html=True)

        st.markdown("---")
        if lb_data:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("<h3 style='font-size:1.05rem; margin:0 0 12px;'>Race to 100 &middot; Gesamtsiege</h3>", unsafe_allow_html=True)
                bars = ""
                for _, r in df_lb.sort_values('Siege', ascending=False).iterrows():
                    col = PLAYER_COLORS.get(r['Spieler'], "#5B8DEF")
                    bars += (f"<div class='hbar-row'><span class='hbar-name'>{r['Spieler']}</span>"
                             f"<div class='hbar-track'><div class='hbar-fill' style='width:{min(100, int(r['Siege']))}%; background:{col}'></div></div>"
                             f"<span class='hbar-val'>{int(r['Siege'])} / 100</span></div>")
                st.markdown(f"<div class='tbl-wrap' style='padding:16px 20px;'>{bars}</div>", unsafe_allow_html=True)
            with c2:
                st.markdown("<h3 style='font-size:1.05rem; margin:0 0 12px;'>Winrate</h3>", unsafe_allow_html=True)
                bars = ""
                for _, r in df_lb.sort_values('Winrate (%)', ascending=False).iterrows():
                    col = PLAYER_COLORS.get(r['Spieler'], "#5B8DEF")
                    bars += (f"<div class='hbar-row'><span class='hbar-name'>{r['Spieler']}</span>"
                             f"<div class='hbar-track'><div class='hbar-fill' style='width:{r['Winrate (%)']:.0f}%; background:{col}'></div></div>"
                             f"<span class='hbar-val'>{r['Winrate (%)']:.1f}%</span></div>")
                st.markdown(f"<div class='tbl-wrap' style='padding:16px 20px;'>{bars}</div>", unsafe_allow_html=True)

# --- TAB 2: SPIELER LOKAL ---
with tab_spieler_loc:
    st.header("Spieler Profile (Übersicht)")
    st.markdown("<div style='color:#8A93A6; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Globale Account-Daten (Trophäen) sowie lokale Crew-Performance.</div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for idx, (name, tag) in enumerate(TAGS.items()):
        with cols[idx % 3]:
            st.subheader(f"{name}")
            if not df_prof.empty and name in df_prof['Spieler'].values:
                p_data = df_prof[df_prof['Spieler'] == name].iloc[0]
                matches, wins, losses = p_data['Matches'], p_data['Wins'], p_data['Losses']
                wr_global = (wins / matches * 100) if matches > 0 else 0
                st.write(f"**Trophäen:** {p_data['Trophies']} (Max: {p_data['Max_Trophies']})")
                st.write(f"**Matches:** {matches} | **Wins:** {wins} | **Losses:** {losses}")
                st.write(f"**Global WR:** {wr_global:.1f}%")

            # --- Persönliche Winstreak über ALLE Spiele (Global-Archiv), nicht nur die internen 1v1 ---
            cur_s, max_w_s, max_l_s, g_games = get_global_streaks(name, df_global)
            if g_games == 0:
                st.markdown("""
<div style='background-color:#141A23; border:1px solid #262E3D; border-left:4px solid #555; border-radius:6px; padding:10px 14px; margin-top:4px; margin-bottom:4px; font-family:sans-serif;'>
  <div style='font-size:0.72rem; color:#8A93A6; text-transform:uppercase; letter-spacing:1px;'>Persönliche Winstreak · Alle Spiele</div>
  <div style='font-size:0.9rem; color:#777; margin-top:4px;'>Noch keine globalen Daten im Archiv.</div>
</div>
""", unsafe_allow_html=True)
            else:
                if cur_s > 0:
                    s_color, s_icon, s_label = "#22C55E", "🔥", f"{cur_s} Siege in Folge"
                elif cur_s < 0:
                    s_color, s_icon, s_label = "#F43F5E", "🥶", f"{abs(cur_s)} Niederlagen in Folge"
                else:
                    s_color, s_icon, s_label = "#8A93A6", "➖", "Keine aktive Serie"
                st.markdown(f"""
<div style='background-color:#141A23; border:1px solid #262E3D; border-left:4px solid {s_color}; border-radius:6px; padding:10px 14px; margin-top:4px; margin-bottom:4px; font-family:sans-serif;'>
  <div style='font-size:0.72rem; color:#8A93A6; text-transform:uppercase; letter-spacing:1px;'>Persönliche Winstreak · Alle Spiele</div>
  <div style='font-size:1.25rem; font-weight:700; color:{s_color}; margin-top:2px;'>{s_icon} {s_label}</div>
  <div style='font-size:0.72rem; color:#777; margin-top:4px;'>Längste Serie: <span style='color:#22C55E;'>+{max_w_s}</span> / <span style='color:#F43F5E;'>-{max_l_s}</span> · Basis: {g_games} Spiele</div>
</div>
""", unsafe_allow_html=True)

            st.markdown("---")
            p_df = df_comp[(df_comp['Spieler1'] == name) | (df_comp['Spieler2'] == name)].sort_values('ID') if (not df_comp.empty and 'Spieler1' in df_comp.columns) else pd.DataFrame()
            if not p_df.empty:
                st.markdown("**Letzte 5 Spiele (Lokal)**")
                history_html = "<div style='font-family: monospace; font-size: 0.9rem;'>"
                for _, r in p_df.tail(5).iloc[::-1].iterrows():
                    is_p1 = r['Spieler1'] == name
                    opp = r['Spieler2'] if is_p1 else r['Spieler1']
                    s_me = r['Score1'] if is_p1 else r['Score2']
                    s_opp = r['Score2'] if is_p1 else r['Score1']
                    if s_me > s_opp: res_col, res_text = "#22C55E", "W"
                    elif s_me < s_opp: res_col, res_text = "#F43F5E", "L"
                    else: res_col, res_text = "#8A93A6888", "D"
                    history_html += f"<div style='margin-bottom: 4px;'><span style='color: {res_col}; font-weight: bold; width: 20px; display: inline-block;'>{res_text}</span> vs {opp} ({s_me}:{s_opp})</div>"
                history_html += "</div>"
                st.markdown(history_html, unsafe_allow_html=True)

            st.markdown("---")
            top_u = calculate_card_stats(name, df_comp)
            if not top_u.empty:
                st.markdown("**Meistgespielte Karten:**")
                st.dataframe(top_u, hide_index=True, use_container_width=True)

# --- TAB 3: SPIELER-ANALYSE (DETAIL, GLOBAL) ---
with tab_spieler_glob:
    st.header("Globale Spieler-Analyse (Deep Dive)")
    st.markdown("<div style='color:#8A93A6; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Nutzt das Archiv (Global_Data) aller weltweit gespielten Matches des Accounts.</div>", unsafe_allow_html=True)

    selected_p = st.selectbox("Spieler auswählen:", list(TAGS.keys()), key="detail_player")

    if df_global.empty:
        st.warning("Keine Daten in Global_Data gefunden. Lass den Bot erst laufen!")
    else:
        p_global = df_global[df_global['Spieler'] == selected_p].sort_values('Time_ID')

        if p_global.empty:
            st.info(f"Keine globalen Spiele für {selected_p} im Archiv gefunden.")
        else:
            total_global_games = len(p_global)
            st.markdown(f"<div style='color:#22C55E; font-weight:bold; margin-bottom:10px;'>Berechnungen basieren auf {total_global_games} archivierten globalen Spielen.</div>", unsafe_allow_html=True)

            # --- Formkurve im Trophäenpfad (Ladder-Verlauf) ---
            st.subheader("Formkurve im Trophäenpfad")
            st.markdown("<div style='color:#8A93A6; font-size:12px; margin-top:-10px; margin-bottom:10px;'>Kumulierte Netto-Siege über alle erfassten Ladder-Spiele. Die Linie steigt bei Sieg und fällt bei Niederlage – sie zeigt, wie sich der Spieler im Trophäenpfad schlägt.</div>", unsafe_allow_html=True)
            tf_glob = st.radio("Zeitraum:", ["Letzte 30 Spiele", "Letzte 100 Spiele", "All-Time"], horizontal=True, key="glob_form_range")
            form_src = p_global.tail(30) if "30" in tf_glob else (p_global.tail(100) if "100" in tf_glob else p_global)
            nw_glob, form_rows = 0, []
            for gi, (_, gr) in enumerate(form_src.iterrows(), start=1):
                nw_glob += 1 if gr['Score_Me'] > gr['Score_Opp'] else (-1 if gr['Score_Me'] < gr['Score_Opp'] else 0)
                form_rows.append({"Spiel-Nr": gi, "Netto-Siege": nw_glob})
            if form_rows:
                xs = [r["Spiel-Nr"] for r in form_rows]
                ys = [r["Netto-Siege"] for r in form_rows]
                end_val = ys[-1]
                if end_val > 0:   accent, fillc = "#22C55E", "rgba(34,197,94,0.16)"
                elif end_val < 0: accent, fillc = "#F43F5E", "rgba(244,63,94,0.16)"
                else:             accent, fillc = "#5B8DEF", "rgba(91,141,239,0.16)"
                fig_form = go.Figure()
                fig_form.add_trace(go.Scatter(
                    x=xs, y=ys, mode="lines",
                    line=dict(color=accent, width=3, shape="spline", smoothing=0.6),
                    fill="tozeroy", fillcolor=fillc,
                    hovertemplate="Spiel %{x} · %{y} Netto-Siege<extra></extra>"))
                fig_form.add_trace(go.Scatter(
                    x=[xs[-1]], y=[ys[-1]], mode="markers+text",
                    marker=dict(size=12, color=accent, line=dict(color="#0B0E14", width=3)),
                    text=[f"  {end_val:+d}"], textposition="middle right",
                    textfont=dict(color=accent, size=14, family="Inter"), hoverinfo="skip"))
                fig_form = style_fig(fig_form, height=300, legend=False)
                fig_form.add_hline(y=0, line_dash="dot", line_color="#2A3343", line_width=1)
                fig_form.update_xaxes(visible=False, showgrid=False)
                fig_form.update_yaxes(title_text="", showgrid=True, gridcolor="#1A2230", zeroline=False)
                fig_form.update_layout(margin=dict(t=14, b=10, l=10, r=46), hovermode="x unified")
                st.plotly_chart(fig_form, use_container_width=True)
            st.markdown("---")

            b_games, b_wins, b_losses = 0, 0, 0
            crowns_for, crowns_against = 0, 0
            clean_sheets, clutch_games, clutch_wins, three_crown_wins = 0, 0, 0, 0
            unique_cards = set()

            last_5_html = "<div style='background-color: #141A23; border-radius: 6px; border: 1px solid #262E3D; padding: 0 15px; font-family: sans-serif;'>"

            count = 0
            for i, r in p_global.iloc[::-1].iterrows():
                my_cr = r['Score_Me']
                op_cr = r['Score_Opp']
                opp_name = r['Opponent']

                b_games += 1
                crowns_for += my_cr
                crowns_against += op_cr

                if op_cr == 0: clean_sheets += 1
                if abs(my_cr - op_cr) == 1:
                    clutch_games += 1
                    if my_cr > op_cr: clutch_wins += 1
                if my_cr == 3 and my_cr > op_cr: three_crown_wins += 1

                if my_cr > op_cr: b_wins += 1
                elif my_cr < op_cr: b_losses += 1

                cards_str = str(r.get('Karten', ''))
                for c in cards_str.split(","):
                    if c.strip(): unique_cards.add(c.strip())

                if count < 5:
                    t = parse_time(r['Time_ID'])
                    t_str = t.strftime("%d.%m %H:%M") if pd.notnull(t) else "Unbekannt"
                    c_me = "#22C55E" if my_cr > op_cr else ("#F43F5E" if my_cr < op_cr else "#8A93A6")
                    c_op = "#22C55E" if op_cr > my_cr else ("#F43F5E" if op_cr < my_cr else "#8A93A6")
                    w_me = "bold" if my_cr > op_cr else "normal"
                    w_op = "bold" if op_cr > my_cr else "normal"
                    border_bottom = "border-bottom: 1px solid #222;" if count != 4 else ""

                    last_5_html += f"""
<div style='display: flex; justify-content: space-between; align-items: center; {border_bottom} padding: 12px 0;'>
<div style='width: 20%; color: #666; font-size: 0.85rem;'>{t_str}</div>
<div style='width: 30%; text-align: right; color: {c_me}; font-weight: {w_me}; font-size: 0.95rem;'>{selected_p[:10]}</div>
<div style='width: 20%; text-align: center; font-weight: bold; font-size: 1.1rem; letter-spacing: 2px;'>
<span style='color: {c_me};'>{my_cr}</span><span style='color: #444;'>:</span><span style='color: {c_op};'>{op_cr}</span>
</div>
<div style='width: 30%; text-align: left; color: {c_op}; font-weight: {w_op}; font-size: 0.95rem;'>{str(opp_name)[:10]}</div>
</div>
"""
                count += 1
            last_5_html += "</div>"

            wr_recent = (b_wins / b_games * 100) if b_games > 0 else 0
            avg_cr_for = crowns_for / b_games if b_games > 0 else 0
            avg_cr_ag = crowns_against / b_games if b_games > 0 else 0
            clean_sheet_pct = (clean_sheets / b_games * 100) if b_games > 0 else 0
            clutch_pct = (clutch_wins / clutch_games * 100) if clutch_games > 0 else 0
            three_cr_pct = (three_crown_wins / b_wins * 100) if b_wins > 0 else 0
            flex_index = len(unique_cards)

            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**1. Historische Formkurve**")
                st.markdown("<div style='color:#8A93A6; font-size:12px; margin-top:-10px; margin-bottom:5px;'>Gesamte Siegquote im Archiv. Über 50% = Positiv.</div>", unsafe_allow_html=True)
                fig_wr = go.Figure(go.Indicator(mode="gauge+number", value=wr_recent, number={'suffix': "%"}, gauge={'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#444"}, 'bar': {'color': "#5B8DEF"}, 'bgcolor': "#141A23", 'borderwidth': 0}))
                fig_wr = style_fig(fig_wr, height=200, legend=False)
                st.plotly_chart(fig_wr, use_container_width=True)
            with c2:
                st.markdown("**2 & 3. Offensiv vs Defensiv**")
                st.markdown("<div style='color:#8A93A6; font-size:12px; margin-top:-10px; margin-bottom:5px;'>Durchschnittlich geholte/kassierte Kronen. Höher = Aggressiver.</div>", unsafe_allow_html=True)
                df_cr = pd.DataFrame({'Typ': ['Offensiv', 'Defensiv'], 'Kronen': [avg_cr_for, avg_cr_ag]})
                fig_cr = px.bar(df_cr, x='Typ', y='Kronen', text_auto='.2f', color='Typ', color_discrete_map={'Offensiv': '#22C55E', 'Defensiv': '#F43F5E'})
                fig_cr = style_fig(fig_cr, height=200, legend=False); fig_cr.update_layout(yaxis_title="", xaxis_title="")
                st.plotly_chart(fig_cr, use_container_width=True)
            with c3:
                st.markdown("**7. Deck-Flexibilität**")
                st.markdown("<div style='color:#8A93A6; font-size:12px; margin-top:-10px; margin-bottom:30px;'>Anzahl genutzter einzigartiger Karten. Je höher, desto unberechenbarer.</div>", unsafe_allow_html=True)
                st.metric(label="Gespielte einzigartige Karten", value=flex_index, delta=f"Aus {b_games} Matches", delta_color="off")

            c4, c5, c6 = st.columns(3)
            with c4:
                st.markdown("**4. Zu-Null-Quote (Clean Sheets)**")
                st.markdown("<div style='color:#8A93A6; font-size:12px; margin-top:-10px; margin-bottom:5px;'>Prozentsatz der Spiele ohne Gegentor (Perfekte Defensive).</div>", unsafe_allow_html=True)
                fig_cs = px.pie(names=['Clean Sheets', 'Gegentor'], values=[clean_sheet_pct, 100-clean_sheet_pct], hole=0.6, color_discrete_sequence=['#5B8DEF', '#262E3D'])
                fig_cs.update_traces(textinfo='none')
                fig_cs = style_fig(fig_cs, height=200, legend=False); fig_cs.update_layout(annotations=[dict(text=f"{clean_sheet_pct:.0f}%", x=0.5, y=0.5, font_size=22, showarrow=False)])
                st.plotly_chart(fig_cs, use_container_width=True)
            with c5:
                st.markdown("**5. Clutch-Rating (Nervenstärke)**")
                st.markdown("<div style='color:#8A93A6; font-size:12px; margin-top:-10px; margin-bottom:5px;'>Siegquote bei knappen Spielen (Exakt 1 Krone Unterschied).</div>", unsafe_allow_html=True)
                if clutch_games == 0:
                    st.info("Keine knappen Spiele verzeichnet.")
                else:
                    fig_cl = px.pie(names=['Knapper Sieg', 'Knappe Ndl'], values=[clutch_pct, 100-clutch_pct], hole=0.6, color_discrete_sequence=['#22C55E', '#262E3D'])
                    fig_cl.update_traces(textinfo='none')
                    fig_cl = style_fig(fig_cl, height=200, legend=False); fig_cl.update_layout(annotations=[dict(text=f"{clutch_pct:.0f}%", x=0.5, y=0.5, font_size=22, showarrow=False)])
                    st.plotly_chart(fig_cl, use_container_width=True)
            with c6:
                st.markdown("**6. Zerstörungs-Quote (3-Crowns)**")
                st.markdown("<div style='color:#8A93A6; font-size:12px; margin-top:-10px; margin-bottom:5px;'>Anteil der Siege, die durch absolute Vernichtung erzielt wurden.</div>", unsafe_allow_html=True)
                if b_wins == 0:
                    st.info("Keine Siege verzeichnet.")
                else:
                    fig_3c = px.pie(names=['3 Kronen', 'Normaler Sieg'], values=[three_cr_pct, 100-three_cr_pct], hole=0.6, color_discrete_sequence=['#F5B544', '#262E3D'])
                    fig_3c.update_traces(textinfo='none')
                    fig_3c = style_fig(fig_3c, height=200, legend=False); fig_3c.update_layout(annotations=[dict(text=f"{three_cr_pct:.0f}%", x=0.5, y=0.5, font_size=22, showarrow=False)])
                    st.plotly_chart(fig_3c, use_container_width=True)

            with st.expander("Erklärungen und Formeln zu den Kennzahlen (Ausklappen)"):
                st.markdown("""
                Diese Daten basieren auf den im Archiv hinterlegten globalen Spielen.

                **1. Historische Formkurve:** Die exakte Siegquote aller erfassten globalen Spiele. Formel: $\\frac{Siege}{Matches} \\times 100$
                **2 & 3. Offensiv/Defensiv:** Durchschnitt der geholten/zugelassenen Kronen pro Spiel. Formel: $\\frac{\\sum Kronen}{Matches}$
                **4. Zu-Null-Quote:** Spiele ohne eine einzige zugelassene Krone des Gegners. Formel: $\\frac{Spiele\\ mit\\ 0\\ Gegentoren}{Matches} \\times 100$
                **5. Clutch-Rating:** Siegesquote bei extrem engen Matches (exakt 1 Krone Differenz). Formel: $\\frac{Siege\\ mit\\ 1\\ Krone\\ Diff}{Alle\\ Matches\\ mit\\ 1\\ Krone\\ Diff} \\times 100$
                **6. Zerstörungs-Quote:** Anteil der Siege, die mit 3 Kronen gewonnen wurden. Formel: $\\frac{3\\text{-Kronen Siege}}{Alle\\ Siege} \\times 100$
                **7. Flexibilität:** Absolute Anzahl unterschiedlicher gespielter Karten in der gesamten erfassten Historie.
                """)

            st.markdown("---")
            st.subheader("Letzte 5 Globale Matches")
            st.markdown("<div style='color:#8A93A6; font-size:13px; margin-top:-10px; margin-bottom:10px;'>Auszug aus dem Global-Archiv für diesen Spieler.</div>", unsafe_allow_html=True)
            st.markdown(last_5_html, unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("Karten, gegen die am meisten verloren wurde")
            st.markdown("<div style='color:#8A93A6; font-size:13px; margin-top:-10px; margin-bottom:10px;'>Welche gegnerischen Karten tauchen in den Niederlagen dieses Spielers am häufigsten auf?</div>", unsafe_allow_html=True)
            st.info("⏳ Daten werden noch gesammelt. Für diese Auswertung muss der Bot (auto_updater.py) zusätzlich die gegnerischen Decks im Global-Archiv speichern – diese Erweiterung kommt separat. Sobald Daten vorliegen, erscheint hier automatisch die Tabelle.")

# --- TAB 4: AKTIVITÄT & TRENDS ---
with tab_trends:
    st.header("Formkurven")
    st.markdown("<div style='color:#8A93A6; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Die Linie steigt bei Sieg und fällt bei Niederlage. Zeigt Momentum über die volle Breite.</div>", unsafe_allow_html=True)
    if not df_comp.empty:
        tf = st.selectbox("Zeitraum:", ["Letzte 15 Spiele", "Letzte 30 Spiele", "All-Time"])
        trend_data = []
        for p in TAGS.keys():
            p_df = df_comp[(df_comp['Spieler1'] == p) | (df_comp['Spieler2'] == p)].sort_values('ID')
            if "15" in tf: p_df = p_df.tail(15)
            elif "30" in tf: p_df = p_df.tail(30)
            nw = 0
            for i, r in p_df.iterrows():
                win = (r['Spieler1']==p and r['Score1']>r['Score2']) or (r['Spieler2']==p and r['Score2']>r['Score1'])
                nw += 1 if win else -1
                trend_data.append({"Spieler": p, "Match-Nr": len([d for d in trend_data if d['Spieler']==p])+1, "Net-Wins": nw})
        if trend_data:
            fig = px.line(pd.DataFrame(trend_data), x="Match-Nr", y="Net-Wins", color="Spieler", markers=True)
            fig = style_fig(fig, height=380)
            st.plotly_chart(fig, use_container_width=True)

# --- TAB 5: SESSIONS ---
with tab_sessions:
    st.header("Session Leaderboards")
    st.markdown("<div style='color:#8A93A6; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Zusammenhängende Spiel-Sessions (Unterbrechungen von max. 30 Minuten). Das King-of-the-Hill (KotH) Rating ermittelt den MVP der Session.</div>", unsafe_allow_html=True)

    if df_comp.empty:
        st.warning("Keine Datenbasis für Sessions vorhanden.")
    else:
        sessions = build_sessions(df_comp)
        if sessions:
            selected_s = st.selectbox("Wähle eine Session aus der Historie:", list(sessions.keys()))
            s_df = sessions[selected_s].copy()
            s_df['Time'] = s_df['ID'].apply(parse_time)
            s_df_valid = s_df.dropna(subset=['Time']).sort_values('Time')

            if not s_df_valid.empty:
                dur = (s_df_valid['Time'].iloc[-1] + timedelta(minutes=3)) - s_df_valid['Time'].iloc[0]
                h, r = divmod(dur.total_seconds(), 3600)
                m, s = divmod(r, 60)
                dur_str = f"{int(h)}h {int(m)}m {int(s)}s" if h>0 else (f"{int(m)}m {int(s)}s" if m>0 else f"{int(s)}s")
                st.info(f"**Gesamtdauer:** {dur_str} | **Spiele gespielt:** {len(s_df)}")

            lb = get_session_leaderboard(s_df)
            if not lb.empty:
                stats, players, timeline_df = get_session_analysis(s_df)
                pstats_df = pd.DataFrame([
                    {"Spieler": p[:10], "Matches": d["P"], "Siege": d["W"], "Niederlagen": d["L"],
                     "Winrate": round((d["W"] / d["P"] * 100), 0) if d["P"] > 0 else 0,
                     "Kronen (für)": d["CF"], "Kronen (gegen)": d["CA"],
                     "Kronen-Diff": d["CF"] - d["CA"], "Beste Serie": d["max_w"]}
                    for p, d in stats.items() if d["P"] > 0
                ])

                # --- KPI-HIGHLIGHTS: Wer hat die Session geprägt? ---
                if not pstats_df.empty:
                    st.subheader("Session-Highlights")
                    mvp = lb.iloc[0]
                    most_active = pstats_df.sort_values("Matches", ascending=False).iloc[0]
                    best_streak = pstats_df.sort_values("Beste Serie", ascending=False).iloc[0]
                    most_crowns = pstats_df.sort_values("Kronen (für)", ascending=False).iloc[0]
                    best_diff = pstats_df.sort_values("Kronen-Diff", ascending=False).iloc[0]
                    k1, k2, k3, k4, k5 = st.columns(5)
                    k1.metric("🏆 MVP (KotH)", mvp['Spieler'], delta=f"Rating {mvp['Rating (KotH)']}", delta_color="off")
                    k2.metric("🎮 Aktivster", most_active['Spieler'], delta=f"{int(most_active['Matches'])} Spiele", delta_color="off")
                    k3.metric("🔥 Beste Serie", best_streak['Spieler'], delta=f"+{int(best_streak['Beste Serie'])} Siege", delta_color="off")
                    k4.metric("👑 Meiste Kronen", most_crowns['Spieler'], delta=f"{int(most_crowns['Kronen (für)'])} geholt", delta_color="off")
                    k5.metric("⚖️ Beste Kronen-Diff", best_diff['Spieler'], delta=f"{int(best_diff['Kronen-Diff']):+d}", delta_color="off")
                    st.markdown("---")

                st.subheader("Leaderboard (King of the Hill)")
                st.dataframe(lb, use_container_width=True)

                with st.expander("Erklärung: Wie wird das King of the Hill (KotH) Rating berechnet?"):
                    st.markdown("""
                    Das **KotH-Rating (0-10)** bewertet den Most Valuable Player (MVP) der Session.

                    **Die Formel (Maximal 10 Punkte):**
                    *   **Winrate (Max 4.0 Pkt):** Basis-Skillfaktor. Formel: $Winrate \\times 4.0$
                    *   **Dominanz (Max 3.5 Pkt):** Anteil an den maximalen Siegen des besten Spielers. Formel: $\\frac{Eigene Siege}{Max Siege aller Spieler} \\times 3.5$
                    *   **Wichtigkeit (Max 2.5 Pkt):** Wie viele Spiele der Session hast du bestritten? Formel: $\\frac{Eigene Matches}{Gesamt Matches} \\times 2.5$
                    *   **Streak-Modifikator:** Bonus für Winstreaks. Formel: $+ (\\max Winstreak - 1) \\times 0.3 - (\\max Lösestreak - 1) \\times 0.3$
                    """)

                # --- VISUELLE UMFASSENDE ANALYSE: Wer hat wie gespielt? ---
                if not pstats_df.empty:
                    st.markdown("---")
                    st.subheader("Visuelle Session-Analyse")
                    st.markdown("<div style='color:#8A93A6; font-size:13px; margin-top:-10px; margin-bottom:15px;'>Wer hat in dieser Session wie gespielt? Der Momentum-Verlauf zeigt, wer sich im Laufe der Session absetzt – die übrigen Grafiken vergleichen Siege, Kronen und Effizienz.</div>", unsafe_allow_html=True)

                    fig_mom = px.line(timeline_df, x="Spiel", y="Netto-Siege", color="Spieler", markers=True, title="Session-Momentum: Netto-Siege im Verlauf")
                    fig_mom.add_hline(y=0, line_dash="dash", line_color="#555")
                    fig_mom = style_fig(fig_mom, height=350); fig_mom.update_layout(xaxis_title="Spiel-Nr. (chronologisch)", yaxis_title="Kumulierte Netto-Siege")
                    st.plotly_chart(fig_mom, use_container_width=True)

                    c_a, c_b = st.columns(2)
                    with c_a:
                        wl_long = pstats_df.melt(id_vars="Spieler", value_vars=["Siege", "Niederlagen"], var_name="Ergebnis", value_name="Anzahl")
                        fig_wl = px.bar(wl_long, x="Spieler", y="Anzahl", color="Ergebnis", barmode="stack", text_auto=True, color_discrete_map={"Siege": "#22C55E", "Niederlagen": "#F43F5E"}, title="Siege & Niederlagen")
                        fig_wl = style_fig(fig_wl, height=300); fig_wl.update_layout(xaxis_title="", yaxis_title="")
                        st.plotly_chart(fig_wl, use_container_width=True)
                    with c_b:
                        cr_long = pstats_df.melt(id_vars="Spieler", value_vars=["Kronen (für)", "Kronen (gegen)"], var_name="Typ", value_name="Kronen")
                        fig_cr = px.bar(cr_long, x="Spieler", y="Kronen", color="Typ", barmode="group", text_auto=True, color_discrete_map={"Kronen (für)": "#22C55E", "Kronen (gegen)": "#F43F5E"}, title="Kronen-Bilanz (geholt vs. kassiert)")
                        fig_cr = style_fig(fig_cr, height=300); fig_cr.update_layout(xaxis_title="", yaxis_title="")
                        st.plotly_chart(fig_cr, use_container_width=True)

                    c_c, c_d = st.columns(2)
                    with c_c:
                        fig_wr = px.bar(pstats_df.sort_values("Winrate", ascending=False), x="Spieler", y="Winrate", text_auto=".0f", color="Spieler", title="Win-Rate pro Spieler (%)")
                        fig_wr = style_fig(fig_wr, height=300, legend=False); fig_wr.update_yaxes(range=[0, 100]); fig_wr.update_layout(xaxis_title="")
                        st.plotly_chart(fig_wr, use_container_width=True)
                    with c_d:
                        if pstats_df["Siege"].sum() > 0:
                            fig_share = px.pie(pstats_df[pstats_df["Siege"] > 0], names="Spieler", values="Siege", hole=0.45, title="Sieg-Verteilung der Session")
                            fig_share.update_traces(textposition='inside', textinfo='percent+label')
                            fig_share = style_fig(fig_share, height=300, legend=False)
                            st.plotly_chart(fig_share, use_container_width=True)
                        else:
                            st.info("Keine entschiedenen Spiele für die Sieg-Verteilung.")
        else:
            st.info("Noch keine vollständigen Sessions registriert.")

# --- TAB 6: PROGNOSE ---
with tab_prognose:
    st.header("Live-Quoten & Prognose")
    st.markdown("<div style='color:#8A93A6; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Automatische Buchmacher-Quoten basierend auf Head-to-Head Historie und aktueller Tagesform.</div>", unsafe_allow_html=True)

    if not df_comp.empty:
        pairs = list(itertools.combinations(TAGS.keys(), 2))
        cols = st.columns(3)
        for idx, (p1, p2) in enumerate(pairs):
            with cols[idx % 3]:
                prob1, prob2, odds1, odds2, insight = calc_matchup_odds(p1, p2, df_comp)
                prob1_pct = prob1 * 100
                prob2_pct = prob2 * 100
                st.markdown(f"""
<div style='background-color: #141A23; color: #FFF; padding: 15px; border-radius: 6px; border: 1px solid #262E3D; margin-bottom: 20px; font-family: sans-serif;'>
<div style='text-align: center; font-weight: 600; font-size: 1rem; margin-bottom: 15px; border-bottom: 1px solid #222; padding-bottom: 8px;'>
{p1[:10]} <span style='color: #666; font-size: 0.8rem; margin: 0 8px;'>VS</span> {p2[:10]}
</div>
<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
<div style='text-align: left; width: 45%;'>
<div style='font-size: 1.3rem; font-weight: 700; color: #22C55E;'>{odds1:.2f}</div>
<div style='font-size: 0.75rem; color: #777;'>{prob1_pct:.0f}%</div>
</div>
<div style='text-align: right; width: 45%;'>
<div style='font-size: 1.3rem; font-weight: 700; color: #5B8DEF;'>{odds2:.2f}</div>
<div style='font-size: 0.75rem; color: #777;'>{prob2_pct:.0f}%</div>
</div>
</div>
<div style='width: 100%; background-color: #222; border-radius: 3px; height: 4px; margin-bottom: 12px; display: flex; overflow: hidden;'>
<div style='width: {prob1_pct}%; background-color: #22C55E; height: 100%;'></div>
<div style='width: {prob2_pct}%; background-color: #5B8DEF; height: 100%;'></div>
</div>
<div style='font-size: 0.75rem; color: #8A93A6; text-align: center; text-transform: uppercase;'>{insight}</div>
</div>
""", unsafe_allow_html=True)

        with st.expander("Erklärung: Wie werden diese Buchmacher-Quoten berechnet?"):
            st.markdown("""
            Die App berechnet für jedes Matchup einen **Power-Score** für beide Spieler, der sich aus drei historischen Faktoren zusammensetzt.

            **1. Der Score:**
            Jeder Spieler startet mit 100 Basis-Punkten. Darauf werden addiert:
            *   **H2H-Bonus:** Historische Winrate gegen diesen spezifischen Gegner. Formel: $1.5 \\times (H2H_{WR} - 50)$
            *   **Formkurve:** Jeder Net-Win aus der jüngsten Vergangenheit gibt +2 Punkte.
            *   **Momentum:** Eine aktive Siegesserie bringt zusätzliche Punkte. Formel: $+4 \\times Streak$.

            **2. Die Wahrscheinlichkeit:**
            Berechnet sich aus dem Anteil am Gesamt-Score beider Spieler:
            $Prob_{A} = \\frac{Score_A}{Score_A + Score_B}$

            **3. Die Quote:**
            Typische Sportwetten-Logik: $Quote = 1 / Wahrscheinlichkeit$. (Eine 50% Chance = Quote 2.00).
            """)

# --- TAB 7: MONTE CARLO ---
with tab_mc:
    st.header("Turnier-Simulator (Monte Carlo)")
    st.markdown("<div style='color:#8A93A6; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Ein statistischer Blick in die Zukunft. Der Algorithmus simuliert virtuelle Turniere basierend auf den echten Formkurven und H2H-Stats.</div>", unsafe_allow_html=True)

    if df_comp.empty:
        st.warning("Keine Datenbasis für Simulationen.")
    else:
        st.markdown("### Die Spielregeln (Parameter)")
        col_c1, col_c2, col_c3 = st.columns(3)
        sim_count = col_c1.select_slider("Anzahl der Universen (Simulationen):", options=[100, 1000, 5000, 10000, 50000], value=10000)
        target_w = col_c2.slider("Turnier-Ziel (Race to X Wins):", min_value=3, max_value=200, value=50, step=1)
        fw = col_c3.slider("Gewichtung der Tagesform:", min_value=0.0, max_value=2.0, value=1.0, step=0.1)

        if st.button("Turnier-Simulation starten", type="primary", use_container_width=True):
            res_dict, total_sweeps = run_monte_carlo_tournament(df_comp, target_w, sim_count, fw)
            st.session_state['mc_results'] = res_dict
            st.session_state['mc_sweeps'] = total_sweeps
            st.session_state['mc_sims'] = sim_count
            st.session_state['mc_target'] = target_w

        st.markdown("---")

        if st.session_state['mc_results']:
            res_dict = st.session_state['mc_results']
            sims_done = st.session_state['mc_sims']
            res_df = pd.DataFrame(list(res_dict.items()), columns=['Spieler', 'Turniersiege'])
            res_df['Wahrscheinlichkeit'] = (res_df['Turniersiege'] / sims_done) * 100
            res_df = res_df.sort_values(by='Turniersiege', ascending=False)

            st.subheader(f"Ergebnisse aus {sims_done:,} Turnieren".replace(',', '.'))
            vis_choice = st.selectbox("Visualisierung auswählen:", ["1. Klassisches Podest (Balkendiagramm)", "2. Kuchen-Verteilung (Kreisdiagramm)", "3. Wahrscheinlichkeits-Tacho", "4. Harte Fakten (Zahlen)"])

            col_chart, col_stats = st.columns([2, 1])
            with col_chart:
                if "Podest" in vis_choice:
                    fig_mc = px.bar(res_df, x='Spieler', y='Wahrscheinlichkeit', text_auto='.1f', color='Spieler')
                    fig_mc.update_traces(textposition='outside')
                    fig_mc = style_fig(fig_mc, height=360, legend=False); fig_mc.update_yaxes(title='Turniersieg Chance (%)', range=[0, 100])
                    st.plotly_chart(fig_mc, use_container_width=True)
                elif "Kuchen" in vis_choice:
                    fig_pie = px.pie(res_df, names='Spieler', values='Wahrscheinlichkeit', hole=0.4, color='Spieler')
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    fig_pie = style_fig(fig_pie, height=320, legend=False)
                    st.plotly_chart(fig_pie, use_container_width=True)
                elif "Tacho" in vis_choice:
                    st.markdown("<div style='color:#8A93A6; font-size:12px; margin-top:-10px; margin-bottom:10px;'>Exakte prozentuale Siegchance pro Spieler.</div>", unsafe_allow_html=True)
                    tacho_cols = st.columns(3)
                    for i, (index, row) in enumerate(res_df.iterrows()):
                        fig_gauge = go.Figure(go.Indicator(mode="gauge+number", value=row['Wahrscheinlichkeit'], number={'suffix': "%"}, title={'text': row['Spieler'], 'font': {'size': 16, 'color': '#FFF'}}, gauge={'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#444"}, 'bar': {'color': "#5B8DEF"}, 'bgcolor': "#141A23", 'borderwidth': 0}))
                        fig_gauge = style_fig(fig_gauge, height=200, legend=False)
                        tacho_cols[i % 3].plotly_chart(fig_gauge, use_container_width=True)
                elif "Fakten" in vis_choice:
                    st.markdown("<div style='color:#8A93A6; font-size:12px; margin-top:-10px; margin-bottom:10px;'>Absolute Zahlen: Wie oft hat der Spieler das Turnier virtuell gewonnen?</div>", unsafe_allow_html=True)
                    f_cols = st.columns(3)
                    for i, (index, row) in enumerate(res_df.iterrows()):
                        f_cols[i % 3].metric(label=row['Spieler'], value=f"{row['Turniersiege']:,}".replace(',', '.'), delta=f"{row['Wahrscheinlichkeit']:.1f}% Winrate", delta_color="normal")
                    st.dataframe(res_df.reset_index(drop=True), use_container_width=True)

            with col_stats:
                st.markdown("<br><br>", unsafe_allow_html=True)
                st.info(f"**Top-Favorit:**<br>Zu {res_df.iloc[0]['Wahrscheinlichkeit']:.1f}% gewinnt **{res_df.iloc[0]['Spieler']}**.")
                st.warning(f"**Vernichtungs-Quote (Sweeps):**<br>{(st.session_state['mc_sweeps']/sims_done)*100:.1f}%<br><span style='font-size:0.75rem; color:#8A93A6;'>Anteil der Turniere, in denen der Sieger alle anderen völlig deklassiert hat.</span>")

# --- TAB 8: FLEXUS ---
with tab_flexus:
    st.markdown("""
        <div style='background: linear-gradient(90deg, #1e1e2f 0%, #141A23 100%); padding: 25px; border-radius: 15px; border-left: 5px solid #22C55E; margin-bottom: 25px;'>
            <h1 style='margin:0; color: #FFF; font-family: sans-serif; font-weight: 800; letter-spacing: -1px;'>🤴 flexus abi statistik</h1>
            <p style='margin:0; color: #8A93A6; font-size: 0.9rem;'>Zentrale Dateneinsicht & Live-Prognosen | Global Account</p>
        </div>
    """, unsafe_allow_html=True)

    f_name = "Flexus"

    # Robust gegen leere/spaltenlose Sheets: get_df_from_sheet liefert bei 0 Datensätzen
    # einen leeren DataFrame OHNE Spalten -> df['Spieler'] würde sonst KeyError werfen.
    f_prof_all = df_prof[df_prof['Spieler'] == f_name] if (not df_prof.empty and 'Spieler' in df_prof.columns) else pd.DataFrame()
    f_glob = df_global[df_global['Spieler'] == f_name].sort_values('Time_ID') if (not df_global.empty and 'Spieler' in df_global.columns) else pd.DataFrame()

    if f_prof_all.empty:
        st.warning("⚠️ Keine Profildaten für Flexus gefunden. Bitte Bot-Verbindung prüfen.")
    else:
        f_prof = f_prof_all.iloc[-1]

        st.subheader("📊 Harte Fakten")
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Trophäen", f"{f_prof['Trophies']}")
        c2.metric("Rekord", f"{f_prof['Max_Trophies']}")
        c3.metric("Matches", f"{f_prof['Matches']:,}".replace(',', '.'))
        c4.metric("Wins", f"{f_prof['Wins']:,}".replace(',', '.'))
        c5.metric("Losses", f"{f_prof['Losses']:,}".replace(',', '.'))
        wr_f = (f_prof['Wins'] / f_prof['Matches'] * 100) if f_prof['Matches'] > 0 else 0
        c6.metric("Winrate", f"{wr_f:.1f}%")

        st.markdown("---")

        st.subheader("🎲 Live-Quote: Nächstes Spiel")
        st.markdown("<div style='color:#8A93A6; font-size:12px; margin-top:-10px; margin-bottom:15px;'>Buchmacher-Quote gegen einen durchschnittlichen Ladder-Gegner. Basiert auf globaler Winrate, Tagesform (letzte 15) und aktuellem Momentum.</div>", unsafe_allow_html=True)

        if not f_glob.empty:
            f_total_games = len(f_glob)
            f_total_wins = sum(1 for _, r in f_glob.iterrows() if r['Score_Me'] > r['Score_Opp'])
            f_global_wr = (f_total_wins / f_total_games * 100) if f_total_games > 0 else 50

            f_last_15 = f_glob.tail(15)
            f_net_wins, f_streak = 0, 0
            f_is_win_streak = None

            for _, r in f_last_15.iterrows():
                p_won = r['Score_Me'] > r['Score_Opp']
                if p_won:
                    f_net_wins += 1
                    if f_is_win_streak in (None, True): f_streak += 1; f_is_win_streak = True
                    else: f_streak = 1; f_is_win_streak = True
                else:
                    f_net_wins -= 1
                    if f_is_win_streak in (None, False): f_streak += 1; f_is_win_streak = False
                    else: f_streak = 1; f_is_win_streak = False

            actual_streak = f_streak if f_is_win_streak else -f_streak

            score_flexus = max(10, 100 + (f_global_wr - 50)*1.5 + (f_net_wins * 2) + (actual_streak * 4))
            score_field = 100

            prob_flexus = score_flexus / (score_flexus + score_field)
            prob_field = score_field / (score_flexus + score_field)
            odds_flexus = max(1.01, round(1 / prob_flexus, 2))
            odds_field = max(1.01, round(1 / prob_field, 2))

            pf_pct = prob_flexus * 100
            po_pct = prob_field * 100

            insight = "Ausgeglichenes Matchmaking"
            if f_global_wr > 55: insight = f"Starke globale Winrate ({f_global_wr:.1f}%)"
            if actual_streak >= 3: insight = f"Momentum Flexus (+{actual_streak} Win-Streak)"
            elif actual_streak <= -3: insight = f"Tilt-Gefahr ({actual_streak} Lose-Streak)"
            elif f_net_wins >= 4: insight = "Gute Tagesform (+ Net-Wins)"

            st.markdown(f"""
            <div style='background-color: #141A23; color: #FFF; padding: 15px; border-radius: 6px; border: 1px solid #262E3D; margin-bottom: 20px; font-family: sans-serif; max-width: 800px;'>
            <div style='text-align: center; font-weight: 600; font-size: 1rem; margin-bottom: 15px; border-bottom: 1px solid #222; padding-bottom: 8px;'>
            Flexus <span style='color: #666; font-size: 0.8rem; margin: 0 8px;'>VS</span> Unbekannter Gegner (Ladder)
            </div>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
            <div style='text-align: left; width: 45%;'>
            <div style='font-size: 1.3rem; font-weight: 700; color: #22C55E;'>{odds_flexus:.2f}</div>
            <div style='font-size: 0.75rem; color: #777;'>Sieg Flexus ({pf_pct:.0f}%)</div>
            </div>
            <div style='text-align: right; width: 45%;'>
            <div style='font-size: 1.3rem; font-weight: 700; color: #F43F5E;'>{odds_field:.2f}</div>
            <div style='font-size: 0.75rem; color: #777;'>Niederlage ({po_pct:.0f}%)</div>
            </div>
            </div>
            <div style='width: 100%; background-color: #222; border-radius: 3px; height: 4px; margin-bottom: 12px; display: flex; overflow: hidden;'>
            <div style='width: {pf_pct}%; background-color: #22C55E; height: 100%;'></div>
            <div style='width: {po_pct}%; background-color: #F43F5E; height: 100%;'></div>
            </div>
            <div style='font-size: 0.75rem; color: #8A93A6; text-align: center; text-transform: uppercase;'>Einflussfaktor: {insight}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Benötige Kampfdaten für die Prognose.")

        st.markdown("---")

        col_left, col_right = st.columns([1, 1.2])

        with col_left:
            st.subheader("🕹️ Letzte 5 Spiele")
            if not f_glob.empty:
                f_last_5 = f_glob.tail(5).iloc[::-1]
                rows_html = ""
                for _, r in f_last_5.iterrows():
                    my, op = r['Score_Me'], r['Score_Opp']
                    if my > op: chip = "<span style='color:#22C55E; font-weight:bold; letter-spacing:1px;'>WIN</span>"
                    elif my < op: chip = "<span style='color:#F43F5E; font-weight:bold; letter-spacing:1px;'>LOSS</span>"
                    else: chip = "<span style='color:#8A93A6; font-weight:bold; letter-spacing:1px;'>DRAW</span>"
                    t_str = str(r['Time_ID'])
                    if len(t_str) >= 13: t_format = f"{t_str[6:8]}.{t_str[4:6]} {t_str[9:11]}:{t_str[11:13]}"
                    else: t_format = "Unbekannt"
                    rows_html += f"""
                        <div style='background: #141A23; padding: 12px; border-radius: 8px; border: 1px solid #222; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; font-family: sans-serif;'>
                            <div style='width: 25%; font-size: 0.8rem; color: #8A93A6;'>{t_format}</div>
                            <div style='width: 20%; font-size: 0.9rem;'>{chip}</div>
                            <div style='width: 20%; font-size: 1.1rem; font-weight: bold; color: #FFF;'>{my} : {op}</div>
                            <div style='width: 35%; font-size: 0.8rem; color: #aaa; text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>vs {str(r['Opponent'])}</div>
                        </div>
                    """
                st.markdown(rows_html, unsafe_allow_html=True)
            else:
                st.info("Noch keine Kämpfe im Global-Archiv.")

        with col_right:
            st.subheader("📈 Trophäen-Entwicklung")
            if len(f_prof_all) > 1:
                trend_filter = st.radio("Zeitraum auswählen:", ["All-Time", "Letzte 15 Messungen"], horizontal=True, label_visibility="collapsed")
                plot_data = f_prof_all.tail(15) if "15" in trend_filter else f_prof_all
                fig_trend = px.line(plot_data, x=plot_data.index, y='Trophies', markers=True)
                fig_trend = style_fig(fig_trend, height=350, legend=False)
                fig_trend.update_xaxes(showgrid=False, visible=False)
                fig_trend.update_yaxes(title='Trophäen')
                fig_trend.update_traces(line_color='#22C55E', line_width=3, marker=dict(size=8, color="#FFF", line=dict(width=2, color="#22C55E")))
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("Sammle mehr Datenpunkte (Lass den Bot ein paarmal laufen), um die Kurve zu zeichnen.")