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

# --- KONFIGURATION & HARDCODED TAGS ---
TAGS = {
    "resan": "R902QGYCP",
    "gooterplayer": "VCGLJU02",
    "Jörg": "YY89R9L9G"
}

# WICHTIG: Ersetze diesen Link durch deinen echten Google Sheet Link!
SHEET_URL = "https://docs.google.com/spreadsheets/d/1SZQhK7TeBRI6DspxVJWU31ul_PGTXNOoxcOwE6rn2u8/edit?gid=641247476#gid=641247476"

API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjhjMzk2MDM1LTgyMzMtNGFhMi04YzVjLTg3NjVmZDliYjE0MSIsImlhdCI6MTc3Nzk4NDU2Niwic3ViIjoiZGV2ZWxvcGVyL2MyYjczNjYyLWE2YjYtNzdkMC00N2I4LTM5YjE0MWYyNzcxOCIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyI5Mi4yMDguMjUuMTIiXSwidHlwZSI6ImNsaWVudCJ9XX0.LG_Q_jELSrMoeRPVVU5saPFnNWBrGbzaaaXtl_4HvKEMd-jDBBldJUpLZXQJ2101_tGsxgQ-3bU5tejtmY3wQg"

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

# --- HELFER FUNKTIONEN ---
def parse_time(id_str):
    if str(id_str).startswith("LEGACY") or str(id_str).startswith("MANUAL"): return pd.NaT
    try: return pd.to_datetime(id_str, format="%Y%m%dT%H%M%S.%fZ")
    except: return pd.NaT

def calculate_card_stats(spieler, df):
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
    return pd.DataFrame(data).sort_values("Gespielt", ascending=False).head(5)

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
        results.append({
            'Matchup': f"{p1[:10]} vs {p2[:10]}", 'Score': f"{wins_p1} : {wins_p2}", 'Spiele': total,
            'Dominanz': f"{p1 if wins_p1 >= wins_p2 else p2} ({max(wins_p1, wins_p2)/total*100:.0f}%)",
            'Streak': f"{streak_count}x {streak_winner}" if streak_count > 1 else "-"
        })
        if streak_count > global_current_streak["count"]: global_current_streak = {"player": streak_winner, "count": streak_count}
        if all_time_streak_count > global_all_time_streak["count"]: global_all_time_streak = {"player": all_time_streak_winner, "count": all_time_streak_count}
    return pd.DataFrame(results), global_current_streak, global_all_time_streak

def get_player_form_and_streak(player, df):
    p_df = df[(df['Spieler1'] == player) | (df['Spieler2'] == player)].sort_values('ID').tail(15)
    if p_df.empty: return 0, 0
    wins, streak, is_win_streak = 0, 0, None
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
    return wins - (len(p_df) - wins), (streak if is_win_streak else -streak)

def calc_matchup_odds(p1, p2, df, form_weight=1.0):
    match_df = df[((df['Spieler1'] == p1) & (df['Spieler2'] == p2)) | ((df['Spieler1'] == p2) & (df['Spieler2'] == p1))]
    total_h2h = len(match_df)
    p1_h2h_wins = sum(1 for _, r in match_df.iterrows() if (r['Spieler1']==p1 and r['Score1']>r['Score2']) or (r['Spieler2']==p1 and r['Score2']>r['Score1']))
    p1_h2h_wr = (p1_h2h_wins / total_h2h * 100) if total_h2h > 0 else 50
    f1, s1 = get_player_form_and_streak(p1, df)
    f2, s2 = get_player_form_and_streak(p2, df)
    score_p1 = max(10, 100 + (p1_h2h_wr-50)*1.5 + (f1*2)*form_weight + (s1*4)*form_weight)
    score_p2 = max(10, 100 + (50-p1_h2h_wr)*1.5 + (f2*2)*form_weight + (s2*4)*form_weight)
    prob1 = score_p1 / (score_p1 + score_p2)
    return prob1, 1-prob1, round(1/prob1, 2), round(1/(1-prob1), 2), "Matchup Analyse läuft..."

def get_session_leaderboard(session_df):
    total_games = len(session_df)
    stats = {p: {"P": 0, "W": 0, "L": 0, "curr_s": 0, "is_win": None, "max_w": 0, "max_l": 0} for p in TAGS.keys()}
    for _, row in session_df.iterrows():
        p1, p2 = row['Spieler1'], row['Spieler2']
        if p1 in stats and p2 in stats:
            p1_won = row['Score1'] > row['Score2']
            stats[p1]["P"] += 1; stats[p2]["P"] += 1
            if p1_won:
                stats[p1]["W"] += 1; stats[p2]["L"] += 1
                if stats[p1]["is_win"]: stats[p1]["curr_s"] += 1
                else: stats[p1]["is_win"]=True; stats[p1]["curr_s"]=1
                stats[p1]["max_w"] = max(stats[p1]["max_w"], stats[p1]["curr_s"])
            else:
                stats[p2]["W"] += 1; stats[p1]["L"] += 1
                if stats[p2]["is_win"]: stats[p2]["curr_s"] += 1
                else: stats[p2]["is_win"]=True; stats[p2]["curr_s"]=1
                stats[p2]["max_w"] = max(stats[p2]["max_w"], stats[p2]["curr_s"])
    max_wins = max([d["W"] for d in stats.values()]) or 1
    lb = []
    for p, d in stats.items():
        if d["P"]==0: continue
        rating = round((d["W"]/d["P"]*4.0) + (d["W"]/max_wins*3.5) + (d["P"]/total_games*2.5), 1)
        lb.append({"Spieler": p, "Matches": d["P"], "Wins": d["W"], "WR": f"{d['W']/d['P']*100:.0f}%", "Rating": rating})
    return pd.DataFrame(lb).sort_values("Rating", ascending=False)

def get_top_synergies(player, df):
    p_df = df[(df['Spieler1'] == player) | (df['Spieler2'] == player)]
    syn = {}
    for _, r in p_df.iterrows():
        is_p1 = r['Spieler1'] == player
        win = (r['Score1'] > r['Score2']) if is_p1 else (r['Score2'] > r['Score1'])
        cards = sorted([c.strip().capitalize() for c in str(r['Karten1'] if is_p1 else r['Karten2']).split(",") if c.strip()])
        if len(cards) >= 2:
            for pair in itertools.combinations(cards, 2):
                if pair not in syn: syn[pair] = {'g': 0, 'w': 0}
                syn[pair]['g'] += 1
                if win: syn[pair]['w'] += 1
    res = [{'Duo': f"{p[0]} & {p[1]}", 'Spiele': s['g'], 'WR': s['w']/s['g']*100} for p, s in syn.items() if s['g'] >= 3]
    return pd.DataFrame(res).sort_values("WR", ascending=False).head(5) if res else pd.DataFrame()

def get_consistency_score(player, df):
    p_df = df[(df['Spieler1'] == player) | (df['Spieler2'] == player)].sort_values('ID')
    if len(p_df) < 5: return 50.0, "Neutral", "#888"
    streak_lens, curr, last = [], 0, None
    for _, r in p_df.iterrows():
        win = 1 if ((r['Spieler1']==player and r['Score1']>r['Score2']) or (r['Spieler2']==player and r['Score2']>r['Score1'])) else 0
        if last is None or win == last: curr += 1
        else: streak_lens.append(curr); curr = 1
        last = win
    streak_lens.append(curr)
    avg = sum(streak_lens)/len(streak_lens)
    score = max(0, min(100, 100 - ((avg-1)*25)))
    color = "#4CAF50" if score >= 75 else ("#2196F3" if score >= 50 else "#F44336")
    return score, ("Maschine" if score>=75 else "Variabel"), color

def run_monte_carlo_tournament(df, target, sims, fw):
    players = list(TAGS.keys())
    results = {p: 0 for p in players}
    swp = 0
    probs = {p1: {p2: calc_matchup_odds(p1, p2, df, fw)[0] for p2 in players if p1!=p2} for p1 in players}
    for _ in range(sims):
        w = {p: 0 for p in players}
        while True:
            p1, p2 = random.sample(players, 2)
            if random.random() < probs[p1][p2]: w[p1]+=1
            else: w[p2]+=1
            if w[p1] == target: results[p1]+=1; break
            if w[p2] == target: results[p2]+=1; break
        if max([v for k,v in w.items() if v < target]) <= target*0.2: swp+=1
    return results, swp

# --- UI LAYOUT ---
df_comp = get_df_from_sheet(ws_comp)
df_fun = get_df_from_sheet(ws_fun)
df_prof = get_df_from_sheet(ws_prof)
df_global = get_df_from_sheet(ws_global)

tabs = st.tabs(["🏆 Liga", "👤 Spieler (Loc)", "🌍 Spieler (Glob)", "📈 Trends", "⏱️ Sessions", "🔮 Prognose", "🔬 Analyse", "🧬 DNA", "🎲 Monte Carlo"])

# TAB: LIGA
with tabs[0]:
    st.header("1v1 Leaderboard")
    if not df_comp.empty:
        lb = []
        for p in TAGS.keys():
            p_df = df_comp[(df_comp['Spieler1']==p)|(df_comp['Spieler2']==p)]
            if not p_df.empty:
                w = sum(1 for _,r in p_df.iterrows() if (r['Spieler1']==p and r['Score1']>r['Score2']) or (r['Spieler2']==p and r['Score2']>r['Score1']))
                lb.append({"Spieler": p, "Matches": len(p_df), "Wins": w, "Net-Wins": w-(len(p_df)-w), "WR": round(w/len(p_df)*100,1)})
        st.dataframe(pd.DataFrame(lb).sort_values("WR", ascending=False), use_container_width=True)
        st.markdown("---")
        h2h, _, _ = get_h2h_stats_data(df_comp)
        st.subheader("Direktvergleich")
        st.dataframe(h2h, use_container_width=True, hide_index=True)

# TAB: SPIELER LOKAL
with tabs[1]:
    st.header("Crew Profile")
    c = st.columns(3)
    for i, name in enumerate(TAGS.keys()):
        with c[i]:
            st.subheader(name)
            p_df = df_comp[(df_comp['Spieler1']==name)|(df_comp['Spieler2']==name)].sort_values('ID', ascending=False).head(5)
            for _, r in p_df.iterrows():
                win = (r['Spieler1']==name and r['Score1']>r['Score2']) or (r['Spieler2']==name and r['Score2']>r['Score1'])
                st.write(f"<span style='color:{'#4CAF50' if win else '#F44336'}; font-weight:bold;'>{'W' if win else 'L'}</span> vs {r['Spieler2'] if r['Spieler1']==name else r['Spieler1']} ({r['Score1']}:{r['Score2']})", unsafe_allow_html=True)
            st.markdown("---")
            st.write("**Top Karten:**")
            st.dataframe(calculate_card_stats(name, df_comp), hide_index=True)

# TAB: SPIELER GLOBAL
with tabs[2]:
    st.header("Globales Archiv")
    sel = st.selectbox("Spieler:", list(TAGS.keys()))
    p_g = df_global[df_global['Spieler']==sel]
    if p_g.empty: st.info("Keine Daten vorhanden.")
    else:
        c1, c2, c3 = st.columns(3)
        w = sum(1 for _,r in p_g.iterrows() if r['Score_Me'] > r['Score_Opp'])
        c1.metric("Winrate", f"{w/len(p_g)*100:.1f}%")
        c2.metric("Avg Crowns", round(p_g['Score_Me'].mean(), 2))
        c3.metric("Clean Sheets", f"{sum(1 for _,r in p_g.iterrows() if r['Score_Opp']==0)}")
        st.markdown("---")
        st.subheader("Historie (Top 5)")
        for _, r in p_g.tail(5).iloc[::-1].iterrows():
            st.write(f"{r['Time_ID'][:10]} | {sel} {r['Score_Me']}:{r['Score_Opp']} {r['Opponent']}")

# TAB: TRENDS
with tabs[3]:
    st.header("Performance Kurven")
    if not df_comp.empty:
        trend = []
        for p in TAGS.keys():
            p_df = df_comp[(df_comp['Spieler1']==p)|(df_comp['Spieler2']==p)].sort_values('ID').tail(20)
            nw = 0
            for i, r in p_df.iterrows():
                nw += 1 if ((r['Spieler1']==p and r['Score1']>r['Score2']) or (r['Spieler2']==p and r['Score2']>r['Score1'])) else -1
                trend.append({"Spieler": p, "Match": len([x for x in trend if x['Spieler']==p])+1, "Net-Wins": nw})
        st.plotly_chart(px.line(pd.DataFrame(trend), x="Match", y="Net-Wins", color="Spieler", markers=True), use_container_width=True)

# TAB: SESSIONS
with tabs[4]:
    st.header("Session Auswertung")
    sess = build_sessions(df_comp)
    if sess:
        s_sel = st.selectbox("Session:", list(sess.keys()))
        st.dataframe(get_session_leaderboard(sess[s_sel]), use_container_width=True)
        with st.expander("Rating Formel"):
            st.write(r"Rating = $Winrate \times 4.0 + \frac{Siege}{MaxSiege} \times 3.5 + \frac{Matches}{GesamtMatches} \times 2.5$")

# TAB: PROGNOSE
with tabs[5]:
    st.header("Live-Quoten")
    pairs = list(itertools.combinations(TAGS.keys(), 2))
    cols = st.columns(3)
    for i, (p1, p2) in enumerate(pairs):
        with cols[i%3]:
            pr1, pr2, o1, o2, _ = calc_matchup_odds(p1, p2, df_comp)
            st.markdown(f"""
            <div style='background:#121212; padding:15px; border-radius:6px; border:1px solid #333; text-align:center;'>
                <b>{p1} vs {p2}</b><br><br>
                <div style='display:flex; justify-content:space-between;'>
                    <div><span style='color:#4CAF50; font-size:1.2rem;'>{o1}</span><br><small>{pr1*100:.0f}%</small></div>
                    <div><span style='color:#2196F3; font-size:1.2rem;'>{o2}</span><br><small>{pr2*100:.0f}%</small></div>
                </div>
            </div>""", unsafe_allow_html=True)

# TAB: ANALYSE
with tabs[6]:
    st.header("Match-Analyse")
    c1, c2 = st.columns(3) # Dummy für Power Index
    for i, p in enumerate(TAGS.keys()):
        pi = get_power_index(p, df_comp)
        with st.columns(3)[i]:
            st.metric(f"Power-Index {p}", f"{pi:.0f}")
    st.markdown("---")
    players = list(TAGS.keys())
    sel1 = st.selectbox("Spieler A", players, index=0)
    sel2 = st.selectbox("Spieler B", players, index=1)
    if sel1 != sel2:
        st.plotly_chart(go.Figure(data=[go.Scatterpolar(r=get_player_stats_for_radar(sel1, sel2, df_comp), theta=['H2H', 'Form', 'Momentum', 'Offense', 'Global'], fill='toself')]), use_container_width=True)

# TAB: DNA
with tabs[7]:
    st.header("Profil-DNA")
    for p in TAGS.keys():
        sc, lbl, col = get_consistency_score(p, df_comp)
        st.write(f"**{p}**: {sc:.0f}/100 ({lbl})")
        st.progress(sc/100)
    st.markdown("---")
    syn_p = st.selectbox("Synergien für:", list(TAGS.keys()))
    st.dataframe(get_top_synergies(syn_p, df_comp), use_container_width=True)

# TAB: MONTE CARLO
with tabs[8]:
    st.header("Turnier Simulator")
    c1, c2, c3 = st.columns(3)
    sims = c1.select_slider("Anzahl Durchläufe", options=[100, 1000, 10000], value=1000)
    target = c2.slider("Ziel-Siege", 5, 100, 20)
    res, _ = run_monte_carlo_tournament(df_comp, target, sims, 1.0)
    st.plotly_chart(px.pie(names=list(res.keys()), values=list(res.values()), hole=0.4, title="Gewinnwahrscheinlichkeit"), use_container_width=True)
