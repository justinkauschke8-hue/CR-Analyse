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
st.set_page_config(page_title="Clash Analyzer Pro", layout="wide")

# --- KONFIGURATION & HARDCODED TAGS ---
TAGS = {
    "resan": "R902QGYCP",
    "gooterplayer": "VCGLJU02",
    "Jörg": "YY89R9L9G"
}

# WICHTIG: Füge hier den echten Link aus der Browser-Leiste ein
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
    
    insight = "Ausgeglichenes Matchup"
    if total_h2h == 0: insight = "Keine H2H-Historie"
    elif p1_h2h_wr > 50 and s2 >= 3: insight = f"H2H {p1[:6]} | Momentum {p2[:6]} (+{s2})"
    elif p1_h2h_wr < 50 and s1 >= 3: insight = f"H2H {p2[:6]} | Momentum {p1[:6]} (+{s1})"
    elif f1 > f2 + 4: insight = f"Form {p1[:6]} (NW: +{f1})"
    elif f2 > f1 + 4: insight = f"Form {p2[:6]} (NW: +{f2})"
    
    return prob1, 1-prob1, round(1/prob1, 2), round(1/(1-prob1), 2), insight

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
        lb.append({"Spieler": p, "Matches": d["P"], "Wins": d["W"], "Losses": d["L"], "WR": f"{d['W']/d['P']*100:.0f}%", "Rating (KotH)": rating})
    return pd.DataFrame(lb).sort_values("Rating (KotH)", ascending=False).reset_index(drop=True)

def get_power_index(player, df):
    f, s = get_player_form_and_streak(player, df)
    pi = 50 + (f * 2.5) + (s * 5.0)
    return max(0, min(100, pi))

def get_player_stats_for_radar(player, opponent, df):
    f, s = get_player_form_and_streak(player, df)
    form_norm = max(0, min(100, (f + 15) / 30 * 100))
    momentum_norm = max(0, min(100, (s + 5) / 10 * 100))
    match_df = df[((df['Spieler1'] == player) & (df['Spieler2'] == opponent)) | ((df['Spieler1'] == opponent) & (df['Spieler2'] == player))]
    h2h_wins = sum(1 for _, r in match_df.iterrows() if (r['Spieler1']==player and r['Score1']>r['Score2']) or (r['Spieler2']==player and r['Score2']>r['Score1']))
    h2h_wr = (h2h_wins / len(match_df) * 100) if len(match_df) > 0 else 50
    crowns = 0
    for _, r in match_df.iterrows():
        crowns += r['Score1'] if r['Spieler1'] == player else r['Score2']
    avg_crowns = (crowns / len(match_df)) if len(match_df) > 0 else 1.5
    offense_norm = max(0, min(100, (avg_crowns / 3.0) * 100))
    p_df = df[(df['Spieler1'] == player) | (df['Spieler2'] == player)]
    g_wins = sum(1 for _, r in p_df.iterrows() if (r['Spieler1']==player and r['Score1']>r['Score2']) or (r['Spieler2']==player and r['Score2']>r['Score1']))
    global_wr = (g_wins / len(p_df) * 100) if len(p_df) > 0 else 50
    return [h2h_wr, form_norm, momentum_norm, offense_norm, global_wr]

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
    if len(p_df) < 5: return 50.0, "Zu wenig Daten", "#888"
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
    return score, ("Maschine" if score>=75 else ("Solide" if score>=50 else "Wundertüte")), color

def run_monte_carlo_tournament(df, target, sims, fw):
    players = list(TAGS.keys())
    results = {p: 0 for p in players}
    swp = 0
    probs = {p1: {p2: calc_matchup_odds(p1, p2, df, fw)[0] for p2 in players if p1!=p2} for p1 in players}
    my_bar = st.progress(0, text="Simuliere Universen...")
    for i in range(sims):
        if i % (sims // 10) == 0: my_bar.progress(i / sims)
        w = {p: 0 for p in players}
        winner = None
        while not winner:
            p1, p2 = random.sample(players, 2)
            if random.random() < probs[p1][p2]: w[p1]+=1
            else: w[p2]+=1
            if w[p1] == target: winner = p1; break
            if w[p2] == target: winner = p2; break
        results[winner] += 1
        if max([v for k,v in w.items() if k != winner]) <= target*0.2: swp+=1
    my_bar.empty()
    return results, swp

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

latest_match = "Keine Daten"
if not df_comp.empty:
    times = df_comp['ID'].apply(parse_time).dropna()
    if not times.empty: latest_match = times.max().strftime('%d.%m.%Y - %H:%M')

# --- SIDEBAR ---
st.sidebar.title("Clash Analyzer Pro")
st.sidebar.markdown("---")
st.sidebar.write("**System-Status**")
st.sidebar.write(f"Datensätze (Lokal): {len(df_comp)}")
st.sidebar.write(f"Datensätze (Global): {len(df_global)}")
st.sidebar.write(f"Letztes Match: {latest_match}")

# --- TABS ---
tabs = st.tabs([
    "1v1 Liga", "Spieler (Lokal)", "Spieler (Global)", "Formkurven", 
    "Sessions", "Prognose", "Match-Analyse", "Profil-DNA", "Monte Carlo"
])

# --- TAB 1: 1v1 LIGA ---
with tabs[0]:
    st.header("Offizielles 1v1 Leaderboard")
    st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Tabelle aller gewerteten internen Matches. Sortiert nach Winrate und Net-Wins.</div>", unsafe_allow_html=True)
    if not df_comp.empty:
        lb_data = []
        for p in TAGS.keys():
            p_df = df_comp[(df_comp['Spieler1'] == p) | (df_comp['Spieler2'] == p)]
            spiele = len(p_df)
            if spiele > 0:
                siege = sum(1 for _, r in p_df.iterrows() if (r['Spieler1']==p and r['Score1']>r['Score2']) or (r['Spieler2']==p and r['Score2']>r['Score1']))
                niederlagen = spiele - siege
                winrate = (siege / spiele) * 100
                net_wins = siege - niederlagen
                lb_data.append({"Spieler": p[:10], "Spiele": spiele, "Siege": siege, "Niederlagen": niederlagen, "Net-Wins": net_wins, "Winrate (%)": round(winrate, 1)})
        if lb_data:
            df_lb = pd.DataFrame(lb_data).sort_values(by=["Winrate (%)", "Net-Wins"], ascending=[False, False]).reset_index(drop=True)
            df_lb.index += 1
            st.dataframe(df_lb, use_container_width=True)

        st.markdown("---")
        h2h_df, curr_s, at_s = get_h2h_stats_data(df_comp)
        st.subheader("Head-to-Head Historie")
        col1, col2 = st.columns(2)
        col1.metric("Aktuelle Winstreak", f"{curr_s['count']}x", curr_s['player'])
        col2.metric("All-Time Rekord", f"{at_s['count']}x", at_s['player'])
        st.dataframe(h2h_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        if lb_data:
            c1, c2 = st.columns(2)
            with c1:
                fig_race = px.bar(df_lb, x='Spieler', y='Siege', text_auto=True, color='Spieler', title="Race to 200 (Absolute Siege)")
                fig_race.update_layout(yaxis=dict(range=[0, 200]), showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
                st.plotly_chart(fig_race, use_container_width=True)
            with c2:
                fig_wr = px.bar(df_lb, x='Spieler', y='Winrate (%)', text_auto='.1f', color='Spieler', title="Winrate Histogramm")
                fig_wr.update_layout(yaxis=dict(range=[0, 100]), showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
                st.plotly_chart(fig_wr, use_container_width=True)

# --- TAB 2: SPIELER LOKAL ---
with tabs[1]:
    st.header("Lokale Spieler Profile")
    st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Globale Account-Daten (Trophäen) sowie lokale Crew-Performance.</div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for idx, (name, tag) in enumerate(TAGS.items()):
        with cols[idx % 3]:
            st.subheader(name)
            if not df_prof.empty and name in df_prof['Spieler'].values:
                p_data = df_prof[df_prof['Spieler'] == name].iloc[0]
                wr_g = (p_data['Wins'] / p_data['Matches'] * 100) if p_data['Matches'] > 0 else 0
                st.write(f"**Trophäen:** {p_data['Trophies']} (Max: {p_data['Max_Trophies']})")
                st.write(f"**Matches:** {p_data['Matches']} | **Wins:** {p_data['Wins']} | **Losses:** {p_data['Losses']}")
                st.write(f"**Global WR:** {wr_g:.1f}%")
            
            st.markdown("---")
            p_df = df_comp[(df_comp['Spieler1'] == name) | (df_comp['Spieler2'] == name)].sort_values('ID')
            if not p_df.empty:
                st.markdown("**Letzte 5 Spiele (Lokal)**")
                hist_html = "<div style='font-family: monospace; font-size: 0.9rem;'>"
                for _, r in p_df.tail(5).iloc[::-1].iterrows():
                    is_p1 = r['Spieler1'] == name
                    opp = r['Spieler2'] if is_p1 else r['Spieler1']
                    s_me = r['Score1'] if is_p1 else r['Score2']
                    s_opp = r['Score2'] if is_p1 else r['Score1']
                    res_col, res_text = ("#4CAF50", "W") if s_me > s_opp else ("#F44336", "L") if s_me < s_opp else ("#888", "D")
                    hist_html += f"<div style='margin-bottom: 4px;'><span style='color: {res_col}; font-weight: bold; width: 20px; display: inline-block;'>{res_text}</span> vs {opp} ({s_me}:{s_opp})</div>"
                hist_html += "</div>"
                st.markdown(hist_html, unsafe_allow_html=True)
            st.markdown("---")
            top_u = calculate_card_stats(name, df_comp)
            if not top_u.empty:
                st.markdown("**Meistgespielte Karten:**")
                st.dataframe(top_u, hide_index=True, use_container_width=True)

# --- TAB 3: SPIELER GLOBAL ---
with tabs[2]:
    st.header("Globale Spieler-Analyse (Deep Dive)")
    st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Nutzt das Archiv (Global_Data) aller weltweit gespielten Matches des Accounts.</div>", unsafe_allow_html=True)
    sel_p = st.selectbox("Spieler auswählen:", list(TAGS.keys()), key="detail_player")
    
    if df_global.empty:
        st.warning("Keine Daten in Global_Data gefunden. Lass den Bot erst laufen!")
    else:
        p_global = df_global[df_global['Spieler'] == sel_p].sort_values('Time_ID')
        if p_global.empty:
            st.info(f"Keine globalen Spiele für {sel_p} im Archiv gefunden.")
        else:
            b_games, crowns_for, crowns_against = len(p_global), 0, 0
            clean_sheets, clutch_games, clutch_wins, three_crown_wins = 0, 0, 0, 0
            b_wins = sum(1 for _, r in p_global.iterrows() if r['Score_Me'] > r['Score_Opp'])
            unique_cards = set()
            last_5_html = "<div style='background-color: #121212; border-radius: 6px; border: 1px solid #333; padding: 0 15px; font-family: sans-serif;'>"
            count = 0
            
            for _, r in p_global.iloc[::-1].iterrows(): 
                my_cr, op_cr, opp_name = r['Score_Me'], r['Score_Opp'], r['Opponent']
                crowns_for += my_cr
                crowns_against += op_cr
                if op_cr == 0: clean_sheets += 1
                if abs(my_cr - op_cr) == 1:
                    clutch_games += 1
                    if my_cr > op_cr: clutch_wins += 1
                if my_cr == 3 and my_cr > op_cr: three_crown_wins += 1
                for c in str(r.get('Karten', '')).split(","):
                    if c.strip(): unique_cards.add(c.strip())
                
                if count < 5:
                    t = parse_time(r['Time_ID'])
                    t_str = t.strftime("%d.%m %H:%M") if pd.notnull(t) else "Unbekannt"
                    c_me = "#4CAF50" if my_cr > op_cr else ("#F44336" if my_cr < op_cr else "#888")
                    c_op = "#4CAF50" if op_cr > my_cr else ("#F44336" if op_cr < my_cr else "#888")
                    w_me, w_op = ("bold", "normal") if my_cr > op_cr else ("normal", "bold")
                    bb = "border-bottom: 1px solid #222;" if count != 4 else ""
                    last_5_html += f"<div style='display: flex; justify-content: space-between; align-items: center; {bb} padding: 12px 0;'><div style='width: 20%; color: #666; font-size: 0.85rem;'>{t_str}</div><div style='width: 30%; text-align: right; color: {c_me}; font-weight: {w_me}; font-size: 0.95rem;'>{sel_p[:10]}</div><div style='width: 20%; text-align: center; font-weight: bold; font-size: 1.1rem; letter-spacing: 2px;'><span style='color: {c_me};'>{my_cr}</span><span style='color: #444;'>:</span><span style='color: {c_op};'>{op_cr}</span></div><div style='width: 30%; text-align: left; color: {c_op}; font-weight: {w_op}; font-size: 0.95rem;'>{str(opp_name)[:10]}</div></div>"
                count += 1
            last_5_html += "</div>"
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**1. Historische Formkurve**")
                st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:5px;'>Gesamte Siegquote im Archiv.</div>", unsafe_allow_html=True)
                fig_wr = go.Figure(go.Indicator(mode="gauge+number", value=(b_wins/b_games*100) if b_games else 0, number={'suffix': "%"}, gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#2196F3"}, 'bgcolor': "#121212"}))
                fig_wr.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#0E1117", font={'color': "#FFF"})
                st.plotly_chart(fig_wr, use_container_width=True)
            with c2:
                st.markdown("**2 & 3. Offensiv vs Defensiv**")
                st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:5px;'>Durchschnittlich geholte/kassierte Kronen.</div>", unsafe_allow_html=True)
                df_cr = pd.DataFrame({'Typ': ['Offensiv', 'Defensiv'], 'Kronen': [crowns_for/b_games if b_games else 0, crowns_against/b_games if b_games else 0]})
                fig_cr = px.bar(df_cr, x='Typ', y='Kronen', text_auto='.2f', color='Typ', color_discrete_map={'Offensiv': '#4CAF50', 'Defensiv': '#F44336'})
                fig_cr.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#0E1117", plot_bgcolor="#121212", showlegend=False, font={'color': "#FFF"})
                st.plotly_chart(fig_cr, use_container_width=True)
            with c3:
                st.markdown("**7. Deck-Flexibilität**")
                st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:30px;'>Anzahl genutzter einzigartiger Karten.</div>", unsafe_allow_html=True)
                st.metric(label="Gespielte einzigartige Karten", value=len(unique_cards), delta=f"Aus {b_games} Matches", delta_color="off")
                
            c4, c5, c6 = st.columns(3)
            with c4:
                st.markdown("**4. Zu-Null-Quote**")
                cs_pct = clean_sheets/b_games*100 if b_games else 0
                fig_cs = px.pie(names=['Clean Sheets', 'Gegentor'], values=[cs_pct, 100-cs_pct], hole=0.6, color_discrete_sequence=['#2196F3', '#333'])
                fig_cs.update_traces(textinfo='none')
                fig_cs.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#0E1117", showlegend=False, annotations=[dict(text=f"{cs_pct:.0f}%", x=0.5, y=0.5, font_size=20, showarrow=False, font_color="#FFF")])
                st.plotly_chart(fig_cs, use_container_width=True)
            with c5:
                st.markdown("**5. Clutch-Rating**")
                cl_pct = clutch_wins/clutch_games*100 if clutch_games else 0
                fig_cl = px.pie(names=['Sieg', 'Ndl'], values=[cl_pct, 100-cl_pct], hole=0.6, color_discrete_sequence=['#4CAF50', '#333'])
                fig_cl.update_traces(textinfo='none')
                fig_cl.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#0E1117", showlegend=False, annotations=[dict(text=f"{cl_pct:.0f}%", x=0.5, y=0.5, font_size=20, showarrow=False, font_color="#FFF")])
                st.plotly_chart(fig_cl, use_container_width=True)
            with c6:
                st.markdown("**6. Zerstörungs-Quote**")
                tc_pct = three_crown_wins/b_wins*100 if b_wins else 0
                fig_3c = px.pie(names=['3 Kronen', 'Normal'], values=[tc_pct, 100-tc_pct], hole=0.6, color_discrete_sequence=['#FFC107', '#333'])
                fig_3c.update_traces(textinfo='none')
                fig_3c.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#0E1117", showlegend=False, annotations=[dict(text=f"{tc_pct:.0f}%", x=0.5, y=0.5, font_size=20, showarrow=False, font_color="#FFF")])
                st.plotly_chart(fig_3c, use_container_width=True)

            with st.expander("Erklärungen und Formeln zu den Kennzahlen"):
                st.markdown(r"""
                Diese Daten basieren auf den im Archiv hinterlegten globalen Spielen.
                *   **Historische Formkurve:** $\frac{Siege}{Matches} \times 100$
                *   **Offensiv/Defensiv:** $\frac{\sum Kronen}{Matches}$
                *   **Zu-Null-Quote:** $\frac{Spiele\ mit\ 0\ Gegentoren}{Matches} \times 100$
                *   **Clutch-Rating:** $\frac{Siege\ mit\ 1\ Krone\ Diff}{Alle\ Matches\ mit\ 1\ Krone\ Diff} \times 100$
                *   **Zerstörungs-Quote:** $\frac{3\text{-Kronen Siege}}{Alle\ Siege} \times 100$
                """)

            st.markdown("---")
            st.subheader("Letzte 5 Globale Matches")
            st.markdown(last_5_html, unsafe_allow_html=True)

# --- TAB 4: TRENDS ---
with tabs[3]:
    st.header("Formkurven")
    st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Die Linie steigt bei Sieg und fällt bei Niederlage. Zeigt Momentum.</div>", unsafe_allow_html=True)
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
            fig.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#121212", font={'color': "#FFF"})
            st.plotly_chart(fig, use_container_width=True)

# --- TAB 5: SESSIONS ---
with tabs[4]:
    st.header("Session Leaderboards")
    st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Zusammenhängende Spiel-Sessions (Unterbrechungen von max. 30 Minuten).</div>", unsafe_allow_html=True)
    sessions = build_sessions(df_comp)
    if sessions:
        selected_s = st.selectbox("Wähle eine Session:", list(sessions.keys()))
        s_df = sessions[selected_s].copy()
        s_df['Time'] = s_df['ID'].apply(parse_time)
        s_df_valid = s_df.dropna(subset=['Time']).sort_values('Time')
        if not s_df_valid.empty:
            dur = (s_df_valid['Time'].iloc[-1] + timedelta(minutes=3)) - s_df_valid['Time'].iloc[0]
            st.info(f"**Dauer:** {dur} | **Spiele:** {len(s_df)}")
        lb = get_session_leaderboard(s_df)
        if not lb.empty: 
            st.dataframe(lb, use_container_width=True)
            with st.expander("Wie wird das King of the Hill (KotH) Rating berechnet?"):
                st.markdown(r"""
                Das **KotH-Rating (0-10)** bewertet den MVP der Session.
                *   **Winrate (Max 4.0 Pkt):** $Winrate \times 4.0$
                *   **Dominanz (Max 3.5 Pkt):** $\frac{Eigene Siege}{Max Siege aller Spieler} \times 3.5$
                *   **Wichtigkeit (Max 2.5 Pkt):** $\frac{Eigene Matches}{Gesamt Matches} \times 2.5$
                """)
    else:
        st.info("Noch keine Sessions registriert.")

# --- TAB 6: PROGNOSE ---
with tabs[5]:
    st.header("Live Buchmacher-Quoten")
    st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Automatische Buchmacher-Quoten basierend auf Head-to-Head Historie und aktueller Tagesform.</div>", unsafe_allow_html=True)
    if not df_comp.empty:
        pairs = list(itertools.combinations(TAGS.keys(), 2))
        cols = st.columns(3)
        for idx, (p1, p2) in enumerate(pairs):
            with cols[idx % 3]:
                pr1, pr2, o1, o2, ins = calc_matchup_odds(p1, p2, df_comp)
                st.markdown(f"""
<div style='background-color: #121212; color: #FFF; padding: 15px; border-radius: 6px; border: 1px solid #333; margin-bottom: 20px; font-family: sans-serif;'>
<div style='text-align: center; font-weight: 600; font-size: 1rem; margin-bottom: 15px; border-bottom: 1px solid #222; padding-bottom: 8px;'>
{p1[:10]} <span style='color: #666; font-size: 0.8rem; margin: 0 8px;'>VS</span> {p2[:10]}
</div>
<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
<div style='text-align: left; width: 45%;'>
<div style='font-size: 1.3rem; font-weight: 700; color: #4CAF50;'>{o1:.2f}</div>
<div style='font-size: 0.75rem; color: #777;'>{pr1*100:.0f}%</div>
</div>
<div style='text-align: right; width: 45%;'>
<div style='font-size: 1.3rem; font-weight: 700; color: #2196F3;'>{o2:.2f}</div>
<div style='font-size: 0.75rem; color: #777;'>{pr2*100:.0f}%</div>
</div>
</div>
<div style='width: 100%; background-color: #222; border-radius: 3px; height: 4px; margin-bottom: 12px; display: flex; overflow: hidden;'>
<div style='width: {pr1*100}%; background-color: #4CAF50; height: 100%;'></div>
<div style='width: {pr2*100}%; background-color: #2196F3; height: 100%;'></div>
</div>
<div style='font-size: 0.75rem; color: #888; text-align: center; text-transform: uppercase;'>{ins}</div>
</div>
""", unsafe_allow_html=True)
        with st.expander("Wie werden diese Buchmacher-Quoten berechnet?"):
            st.markdown(r"""
            Der Score $S$ basiert auf 100 Punkten Startkapital.
            *   **H2H-Bonus:** $1.5 \times (H2H_{WR} - 50)$
            *   **Formkurve:** $+2 \times NetWins$
            *   **Momentum:** $+4 \times Streak$
            Wahrscheinlichkeit $P_A = \frac{S_A}{S_A + S_B}$. Quote $= \frac{1}{P_A}$
            """)

# --- TAB 7: MATCH-ANALYSE ---
with tabs[6]:
    st.header("Match-Analyse")
    if not df_comp.empty:
        c1, c2 = st.columns([1.5, 1])
        with c1:
            st.subheader("Aktueller Power-Index")
            st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:10px;'>Kurzzeit-Leistungsmesser (letzte 15 Spiele). Über 60 ist 'On Fire'.</div>", unsafe_allow_html=True)
            cols_pi = st.columns(3)
            for idx, p in enumerate(TAGS.keys()):
                pi = get_power_index(p, df_comp)
                fig_pi = go.Figure(go.Indicator(mode="gauge+number", value=pi, title={'text': p, 'font': {'color': '#FFF'}}, gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#4CAF50" if pi >= 50 else "#F44336"}, 'bgcolor': "#121212"}))
                fig_pi.update_layout(height=200, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="#0E1117", font={'color': "#FFF"})
                cols_pi[idx].plotly_chart(fig_pi, use_container_width=True)

        with c2:
            st.subheader("Matchup Radar")
            st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:10px;'>Werte auf 0-100 normiert. Größere Fläche = Stärker.</div>", unsafe_allow_html=True)
            players = list(TAGS.keys())
            sel1 = st.selectbox("Spieler A", players, index=0)
            sel2 = st.selectbox("Spieler B", players, index=1)
            if sel1 != sel2:
                fig_rad = go.Figure()
                fig_rad.add_trace(go.Scatterpolar(r=get_player_stats_for_radar(sel1, sel2, df_comp), theta=['H2H', 'Form', 'Momentum', 'Offense', 'Global'], fill='toself', name=sel1, line_color='#4CAF50'))
                fig_rad.add_trace(go.Scatterpolar(r=get_player_stats_for_radar(sel2, sel1, df_comp), theta=['H2H', 'Form', 'Momentum', 'Offense', 'Global'], fill='toself', name=sel2, line_color='#2196F3'))
                fig_rad.update_layout(height=250, polar=dict(radialaxis=dict(visible=True, range=[0, 100]), bgcolor="#121212"), paper_bgcolor="#0E1117", font={'color': "#FFF"}, margin=dict(t=30, b=30, l=30, r=30))
                st.plotly_chart(fig_rad, use_container_width=True)

        st.markdown("---")
        st.subheader("H2H Dominanz-Matrix")
        st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:10px;'>Lies von der Y-Achse (Links) zur X-Achse (Unten). Grün = Du dominierst den Gegner.</div>", unsafe_allow_html=True)
        matrix_data = []
        for p1 in players:
            row = []
            for p2 in players:
                if p1 == p2: row.append(None)
                else:
                    match_df = df_comp[((df_comp['Spieler1'] == p1) & (df_comp['Spieler2'] == p2)) | ((df_comp['Spieler1'] == p2) & (df_comp['Spieler2'] == p1))]
                    if match_df.empty: row.append(50.0)
                    else:
                        p1_wins = sum(1 for _, r in match_df.iterrows() if (r['Spieler1']==p1 and r['Score1']>r['Score2']) or (r['Spieler2']==p1 and r['Score2']>r['Score1']))
                        row.append((p1_wins / len(match_df)) * 100)
            matrix_data.append(row)
        fig_heat = px.imshow(matrix_data, x=players, y=players, text_auto=".0f", color_continuous_scale=[[0, "#F44336"], [0.5, "#222"], [1, "#4CAF50"]], zmin=0, zmax=100)
        fig_heat.update_layout(height=350, paper_bgcolor="#0E1117", plot_bgcolor="#0E1117", font={'color': "#FFF"})
        st.plotly_chart(fig_heat, use_container_width=True)

# --- TAB 8: DNA ---
with tabs[7]:
    st.header("Profil-DNA")
    if not df_comp.empty:
        st.subheader("Glicko Konsistenz-Index")
        st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:15px;'>Misst Nervenstärke und Verlässlichkeit (0-100).</div>", unsafe_allow_html=True)
        for p in TAGS.keys():
            sc, lbl, col = get_consistency_score(p, df_comp)
            st.markdown(f"<div style='margin-bottom:15px; font-family: sans-serif;'><div style='display: flex; justify-content: space-between; margin-bottom: 5px;'><span style='color: #FFF; font-weight: bold;'>{p[:10]}</span><span style='color: {col}; font-weight: bold;'>Score: {sc:.0f} / 100</span></div><div style='width: 100%; background-color: #222; border-radius: 4px; height: 12px;'><div style='width: {sc}%; background-color: {col}; height: 100%; border-radius: 4px;'></div></div><div style='text-align: right; font-size: 0.75rem; color: #888; margin-top: 3px;'>Urteil: <span style='color: {col};'>{lbl}</span></div></div>", unsafe_allow_html=True)
        with st.expander("Wie wird die Konsistenz berechnet?"):
            st.markdown(r"Wir berechnen den Durchschnitt der Längen aller Serien ($\overline{Streak}$). $Konsistenz = 100 - ((\overline{Streak} - 1) \times 25)$")
        st.markdown("---")
        st.subheader("Deck-Synergien (Deadly Duos)")
        sel_dna = st.selectbox("Synergien für:", list(TAGS.keys()))
        syn_df = get_top_synergies(sel_dna, df_comp)
        if not syn_df.empty:
            col_s1, col_s2 = st.columns(2)
            with col_s1: st.dataframe(syn_df.reset_index(drop=True), use_container_width=True)
            with col_s2:
                syn_df['WR_Float'] = syn_df['Sieg-Quote (%)'].str.replace('%', '').astype(float)
                fig_syn = px.bar(syn_df, x='WR_Float', y='Karten-Duo', orientation='h', color='Spiele')
                fig_syn.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), yaxis={'categoryorder':'total ascending'}, paper_bgcolor="#0E1117", plot_bgcolor="#121212", font={'color': "#FFF"})
                st.plotly_chart(fig_syn, use_container_width=True)

# --- TAB 9: MONTE CARLO ---
with tabs[8]:
    st.header("Turnier Simulator (Monte Carlo)")
    st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Der Algorithmus simuliert virtuelle Turniere basierend auf den echten Formkurven und H2H-Stats.</div>", unsafe_allow_html=True)
    if not df_comp.empty:
        c1, c2, c3 = st.columns(3)
        sim_count = c1.select_slider("Anzahl Durchläufe", options=[100, 1000, 5000, 10000], value=10000)
        target_w = c2.slider("Ziel-Siege", 5, 100, 20)
        fw = c3.slider("Form-Gewichtung", 0.0, 2.0, 1.0)
        if st.button("Simulation starten", type="primary", use_container_width=True):
            res_dict, total_swp = run_monte_carlo_tournament(df_comp, target_w, sim_count, fw)
            st.session_state['mc_results'] = res_dict
            st.session_state['mc_sweeps'] = total_swp
            st.session_state['mc_sims'] = sim_count
        st.markdown("---")
        if st.session_state['mc_results']:
            res_df = pd.DataFrame(list(st.session_state['mc_results'].items()), columns=['Spieler', 'Wins'])
            res_df['Wahrscheinlichkeit'] = res_df['Wins'] / st.session_state['mc_sims'] * 100
            res_df = res_df.sort_values(by='Wins', ascending=False)
            vis = st.selectbox("Visualisierung", ["1. Balkendiagramm", "2. Kreisdiagramm", "3. Zahlen"])
            col_chart, col_stats = st.columns([2, 1])
            with col_chart:
                if "Balkendiagramm" in vis:
                    fig_mc = px.bar(res_df, x='Spieler', y='Wahrscheinlichkeit', text_auto='.1f', color='Spieler')
                    fig_mc.update_traces(textposition='outside')
                    fig_mc.update_layout(yaxis=dict(range=[0, 100]), showlegend=False, paper_bgcolor="#0E1117", plot_bgcolor="#121212", font={'color': "#FFF"})
                    st.plotly_chart(fig_mc, use_container_width=True)
                elif "Kreisdiagramm" in vis:
                    fig_pie = px.pie(res_df, names='Spieler', values='Wahrscheinlichkeit', hole=0.4, color='Spieler')
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    fig_pie.update_layout(paper_bgcolor="#0E1117", font={'color': "#FFF"}, showlegend=False)
                    st.plotly_chart(fig_pie, use_container_width=True)
                elif "Zahlen" in vis:
                    st.dataframe(res_df.reset_index(drop=True), use_container_width=True)
            with col_stats:
                st.markdown("<br><br>", unsafe_allow_html=True)
                st.info(f"**Top-Favorit:**<br>Zu {res_df.iloc[0]['Wahrscheinlichkeit']:.1f}% gewinnt **{res_df.iloc[0]['Spieler']}**.")
                st.warning(f"**Vernichtungs-Quote (Sweeps):**<br>{(st.session_state['mc_sweeps']/st.session_state['mc_sims'])*100:.1f}%")
