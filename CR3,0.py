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

# WICHTIG: Füge hier den echten Link aus der Browser-Leiste ein (https://docs...)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1SZQhK7TeBRI6DspxVJWU31ul_PGTXNOoxcOwE6rn2u8/edit?gid=67403884#gid=67403884"

API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjhjMzk2MDM1LTgyMzMtNGFhMi04YzVjLTg3NjVmZDliYjE0MSIsImlhdCI6MTc3Nzk4NDU2Niwic3ViIjoiZGV2ZWxvcGVyL2MyYjczNjYyLWE2YjYtNzdkMC00N2I4LTM5YjE0MWYyNzcxOCIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyI5Mi4yMDguMjUuMTIiXSwidHlwZSI6ImNsaWVudCJ9XX0.LG_Q_jELSrMoeRPVVU5saPFnNWBrGbzaaaXtl_4HvKEMd-jDBBldJUpLZXQJ2101_tGsxgQ-3bU5tejtmY3wQg"

# --- GOOGLE SHEETS SETUP ---
@st.cache_resource
def init_google_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["google_credentials"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SHEET_URL)
    return sheet.worksheet("Karten_Data"), sheet.worksheet("Fun_Data"), sheet.worksheet("Profile_Data")

try:
    ws_comp, ws_fun, ws_prof = init_google_sheets()
except Exception as e:
    st.error(f"Datenbank-Verbindung fehlgeschlagen: {e}")
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
    if len(p_df) == 0: return pd.DataFrame(), pd.DataFrame()
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
    top_wr = res_df[res_df["Gespielt"] >= 3].sort_values("Winrate (%)", ascending=False).head(5) 
    return top_use, top_wr

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

def calc_nemesis_kryptonit(df):
    if df.empty: return []
    nemesis_data = []
    for p in TAGS.keys():
        p_df = df[(df['Spieler1'] == p) | (df['Spieler2'] == p)]
        if p_df.empty: continue
        opp_wr, krypt_cards = {}, {}
        for _, r in p_df.iterrows():
            is_p1 = (r['Spieler1'] == p)
            opp = r['Spieler2'] if is_p1 else r['Spieler1']
            p_won = (r['Score1'] > r['Score2']) if is_p1 else (r['Score2'] > r['Score1'])
            opp_cards = r['Karten2'] if is_p1 else r['Karten1']
            if opp not in opp_wr: opp_wr[opp] = [0, 0] 
            opp_wr[opp][0] += 1
            if not p_won: 
                opp_wr[opp][1] += 1
                for c in str(opp_cards).split(","):
                    c = c.strip()
                    if c: krypt_cards[c] = krypt_cards.get(c, 0) + 1
        nemesis = max(opp_wr.items(), key=lambda x: (x[1][1]/x[1][0] if x[1][0]>0 else 0, x[1][1]), default=(None, [0,0]))
        krypt = max(krypt_cards.items(), key=lambda x: x[1], default=("Keine", 0))
        if nemesis[0]:
            n_wr = (nemesis[1][1]/nemesis[1][0]*100) if nemesis[1][0]>0 else 0
            nemesis_data.append({"Spieler": p[:10], "Nemesis": f"{nemesis[0]} ({n_wr:.0f}%)", "Kryptonit-Karte": f"{krypt[0]} ({krypt[1]}x verloren)"})
    return pd.DataFrame(nemesis_data)

# --- ALGORITHMUS FÜR BUCHMACHER QUOTEN ---
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

def calc_matchup_odds(p1, p2, df, form_weight=1.0):
    match_df = df[((df['Spieler1'] == p1) & (df['Spieler2'] == p2)) | ((df['Spieler1'] == p2) & (df['Spieler2'] == p1))]
    total_h2h = len(match_df)
    p1_h2h_wins = sum(1 for _, r in match_df.iterrows() if (r['Spieler1']==p1 and r['Score1']>r['Score2']) or (r['Spieler2']==p1 and r['Score2']>r['Score1']))
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

# --- SESSION LOGIK ---
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

# --- ANALYSE HELPER (RADAR & POWER) ---
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

# --- DNA HELPER (SYNERGIEN & KONSISTENZ) ---
def get_top_synergies(player, df):
    p_df = df[(df['Spieler1'] == player) | (df['Spieler2'] == player)]
    synergy_stats = {}
    for _, r in p_df.iterrows():
        is_p1 = r['Spieler1'] == player
        win = (r['Score1'] > r['Score2']) if is_p1 else (r['Score2'] > r['Score1'])
        cards_str = r['Karten1'] if is_p1 else r['Karten2']
        cards = [c.strip().capitalize() for c in str(cards_str).split(",") if c.strip()]
        if len(cards) >= 2:
            pairs = itertools.combinations(sorted(cards), 2)
            for pair in pairs:
                if pair not in synergy_stats: synergy_stats[pair] = {'games': 0, 'wins': 0}
                synergy_stats[pair]['games'] += 1
                if win: synergy_stats[pair]['wins'] += 1
    data = []
    for pair, stats in synergy_stats.items():
        if stats['games'] >= 3:
            wr = (stats['wins'] / stats['games']) * 100
            data.append({'Karten-Duo': f"{pair[0]} & {pair[1]}", 'Spiele': stats['games'], 'Sieg-Quote (%)': wr})
    res_df = pd.DataFrame(data)
    if not res_df.empty:
        res_df = res_df.sort_values(by=['Sieg-Quote (%)', 'Spiele'], ascending=[False, False]).head(5)
        res_df['Sieg-Quote (%)'] = res_df['Sieg-Quote (%)'].apply(lambda x: f"{x:.1f}%")
    return res_df

def get_consistency_score(player, df):
    p_df = df[(df['Spieler1'] == player) | (df['Spieler2'] == player)].sort_values('ID')
    if len(p_df) < 5: return 50.0, "Zu wenige Spiele", "#888"
    streak_lengths, current_streak, last_res = [], 0, None
    for _, r in p_df.iterrows():
        is_p1 = r['Spieler1'] == player
        win = 1 if ((is_p1 and r['Score1'] > r['Score2']) or (not is_p1 and r['Score2'] > r['Score1'])) else 0
        if last_res is None or win == last_res: current_streak += 1
        else:
            streak_lengths.append(current_streak)
            current_streak = 1
        last_res = win
    if current_streak > 0: streak_lengths.append(current_streak)
    avg_streak = sum(streak_lengths) / len(streak_lengths) if streak_lengths else 1
    cons_score = max(0, min(100, 100 - ((avg_streak - 1) * 25)))
    if cons_score >= 80: return cons_score, "Maschine (Konstant)", "#4CAF50"
    elif cons_score >= 50: return cons_score, "Solide Form", "#2196F3"
    else: return cons_score, "Wundertüte (Streaky)", "#F44336"

# --- MONTE CARLO ENGINE ---
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
    progress_text = "Universen werden berechnet..."
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

# --- UI & LAYOUT ---
df_comp = get_df_from_sheet(ws_comp)
df_fun = get_df_from_sheet(ws_fun)
df_prof = get_df_from_sheet(ws_prof)

latest_match_str = "Keine Daten"
if not df_comp.empty:
    times = df_comp['ID'].apply(parse_time).dropna()
    if not times.empty: latest_match_str = times.max().strftime('%d.%m.%Y - %H:%M')

st.sidebar.title("Clash Analyzer Pro")
st.sidebar.markdown("---")
st.sidebar.write("**System-Status**")
st.sidebar.write(f"Datensätze: {len(df_comp)}")
st.sidebar.write(f"Letztes Match: {latest_match_str}")
st.sidebar.markdown("---")

tab_dbl, tab_spieler, tab_dbf, tab_nemesis, tab_trends, tab_zeit, tab_sessions, tab_prognose, tab_analyse, tab_mc, tab_dna = st.tabs([
    "1v1", "Spieler", "Fun", "Nemesis", "Trends", "Heatmap", "Sessions", "Prognose", "Analyse", "Monte Carlo", "Profil-DNA"
])

with tab_dbl:
    st.header("1v1 Leaderboard")
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
            df_lb.index = df_lb.index + 1
            st.dataframe(df_lb, use_container_width=True)
        st.markdown("---")
        h2h_df, curr_streak, at_streak = get_h2h_stats_data(df_comp)
        col1, col2 = st.columns(2)
        col1.metric("Aktuelle Winstreak", f"{curr_streak['count']}x", curr_streak['player'])
        col2.metric("All-Time Rekord", f"{at_streak['count']}x", at_streak['player'])
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

with tab_spieler:
    st.header("Spieler Profile")
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
            
            st.markdown("---")
            
            p_df = df_comp[(df_comp['Spieler1'] == name) | (df_comp['Spieler2'] == name)].sort_values('ID')
            if not p_df.empty:
                st.markdown("**Letzte 5 Spiele (Lokal)**")
                history_html = "<div style='font-family: monospace; font-size: 0.9rem;'>"
                for _, r in p_df.tail(5).iloc[::-1].iterrows():
                    is_p1 = r['Spieler1'] == name
                    opp = r['Spieler2'] if is_p1 else r['Spieler1']
                    s_me = r['Score1'] if is_p1 else r['Score2']
                    s_opp = r['Score2'] if is_p1 else r['Score1']
                    if s_me > s_opp:
                        res_col, res_text = "#4CAF50", "W"
                    elif s_me < s_opp:
                        res_col, res_text = "#F44336", "L"
                    else:
                        res_col, res_text = "#888888", "D"
                    history_html += f"<div style='margin-bottom: 4px;'><span style='color: {res_col}; font-weight: bold; width: 20px; display: inline-block;'>{res_text}</span> vs {opp} ({s_me}:{s_opp})</div>"
                history_html += "</div>"
                st.markdown(history_html, unsafe_allow_html=True)
                
            st.markdown("---")
            top_u, top_w = calculate_card_stats(name, df_comp)
            if not top_u.empty:
                st.markdown("**Meistgespielte Karten:**")
                st.dataframe(top_u, hide_index=True, use_container_width=True)

with tab_dbf:
    st.header("Fun Dashboard")
    if not df_fun.empty:
        h2h_df, _, _ = get_h2h_stats_data(df_fun)
        st.dataframe(h2h_df, use_container_width=True, hide_index=True)

with tab_nemesis:
    st.header("Kryptonit")
    if not df_comp.empty:
        nem_df = calc_nemesis_kryptonit(df_comp)
        if not nem_df.empty: st.table(nem_df)

with tab_trends:
    st.header("Formkurve (Net-Wins)")
    if not df_comp.empty:
        tf = st.selectbox("Zeitraum:", ["Letzte 15 Spiele", "Letzte 30 Spiele", "All-Time"])
        trend_data = []
        for p in TAGS.keys():
            p_df = df_comp[(df_comp['Spieler1'] == p) | (df_comp['Spieler2'] == p)].sort_values('ID')
            if tf == "Letzte 15 Spiele": p_df = p_df.tail(15)
            elif tf == "Letzte 30 Spiele": p_df = p_df.tail(30)
            net_wins = 0
            for i, r in p_df.iterrows():
                is_p1 = (r['Spieler1'] == p)
                p_won = (r['Score1'] > r['Score2']) if is_p1 else (r['Score2'] > r['Score1'])
                net_wins += (1 if p_won else -1)
                trend_data.append({"Spieler": p[:10], "Match-Nr": len([d for d in trend_data if d['Spieler']==p[:10]])+1, "Net-Wins": net_wins})
        tdf = pd.DataFrame(trend_data)
        if not tdf.empty:
            fig = px.line(tdf, x="Match-Nr", y="Net-Wins", color="Spieler", markers=True, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

with tab_zeit:
    st.header("Aktivitäts-Heatmap")
    if not df_comp.empty:
        df_time = df_comp.copy()
        df_time['Time'] = df_time['ID'].apply(parse_time)
        df_time = df_time.dropna(subset=['Time'])
        if not df_time.empty:
            df_time['Wochentag'] = df_time['Time'].dt.day_name()
            df_time['Stunde'] = df_time['Time'].dt.hour
            day_map = {"Monday": "Montag", "Tuesday": "Dienstag", "Wednesday": "Mittwoch", "Thursday": "Donnerstag", "Friday": "Freitag", "Saturday": "Samstag", "Sunday": "Sonntag"}
            df_time['Wochentag'] = df_time['Wochentag'].map(day_map)
            heatmap_data = df_time.groupby(['Wochentag', 'Stunde']).size().reset_index(name='Spiele')
            pivot_data = heatmap_data.pivot(index='Wochentag', columns='Stunde', values='Spiele').fillna(0)
            days_order = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
            for d in days_order:
                if d not in pivot_data.index: pivot_data.loc[d] = 0
            pivot_data = pivot_data.reindex(days_order)
            for h in range(24):
                if h not in pivot_data.columns: pivot_data[h] = 0
            pivot_data = pivot_data[list(range(24))]
            fig_heat = px.imshow(pivot_data, labels=dict(x="Uhrzeit", y="Wochentag", color="Spiele"), x=list(range(24)), y=days_order, color_continuous_scale="Inferno", aspect="auto")
            fig_heat.update_xaxes(dtick=1)
            st.plotly_chart(fig_heat, use_container_width=True)

with tab_sessions:
    st.header("Session Leaderboards")
    st.markdown("Zusammenhängende Spiel-Sessions (Unterbrechungen von max. 30 Minuten).")
    
    if df_comp.empty:
        st.warning("Keine Datenbasis für Sessions vorhanden.")
    else:
        sessions = build_sessions(df_comp)
        if sessions:
            selected_s = st.selectbox("Wähle eine Session:", list(sessions.keys()))
            s_df = sessions[selected_s].copy()
            s_df['Time'] = s_df['ID'].apply(parse_time)
            s_df_valid = s_df.dropna(subset=['Time']).sort_values('Time')
            
            if not s_df_valid.empty:
                dur = (s_df_valid['Time'].iloc[-1] + timedelta(minutes=3)) - s_df_valid['Time'].iloc[0]
                h, r = divmod(dur.total_seconds(), 3600)
                m, s = divmod(r, 60)
                dur_str = f"{int(h)}h {int(m)}m {int(s)}s" if h>0 else (f"{int(m)}m {int(s)}s" if m>0 else f"{int(s)}s")
                st.info(f"**Dauer:** {dur_str} | **Spiele gespielt:** {len(s_df)}")
            
            lb = get_session_leaderboard(s_df)
            if not lb.empty: 
                st.dataframe(lb, use_container_width=True)
                
                with st.expander("Wie wird das King of the Hill (KotH) Rating berechnet?"):
                    st.markdown("""
                    Das **KotH-Rating (0-10)** bewertet, wer die Session dominiert hat. Es ist nicht nur eine einfache Winrate, sondern belohnt auch, wenn jemand *viele* Spiele gemacht hat und *lange* Siegesserien halten konnte.
                    
                    **Die Formel (Maximal 10 Punkte):**
                    *   **Winrate (Max 4.0 Pkt):** Basis-Skillfaktor. Formel: $Winrate \times 4.0$
                    *   **Dominanz (Max 3.5 Pkt):** Anteil an den maximalen Siegen des besten Spielers. Formel: $\frac{Eigene Siege}{Max Siege aller Spieler} \times 3.5$
                    *   **Wichtigkeit (Max 2.5 Pkt):** Wie viele Spiele der Session hast du bestritten? Formel: $\frac{Eigene Matches}{Gesamt Matches} \times 2.5$
                    *   **Streak-Modifikator:** Bonus für Winstreaks, Abzug für Lösestreaks. Formel: $+ (\max Winstreak - 1) \times 0.3 - (\max Lösestreak - 1) \times 0.3$
                    """)
        else:
            st.info("Noch keine vollständigen Sessions registriert.")

with tab_prognose:
    st.header("Live-Quoten & Historie")
    st.markdown(f"<div style='color: #888; font-size: 0.9rem; margin-bottom: 20px;'>Letzte Aktualisierung: {latest_match_str}</div>", unsafe_allow_html=True)
    
    if not df_comp.empty:
        pairs = list(itertools.combinations(TAGS.keys(), 2))
        cols = st.columns(3)
        for idx, (p1, p2) in enumerate(pairs):
            with cols[idx % 3]:
                prob1, prob2, odds1, odds2, insight = calc_matchup_odds(p1, p2, df_comp)
                prob1_pct = prob1 * 100
                prob2_pct = prob2 * 100
                st.markdown(f"""
<div style='background-color: #121212; color: #FFF; padding: 15px; border-radius: 6px; border: 1px solid #333; margin-bottom: 20px; font-family: sans-serif;'>
<div style='text-align: center; font-weight: 600; font-size: 1rem; margin-bottom: 15px; border-bottom: 1px solid #222; padding-bottom: 8px;'>
{p1[:10]} <span style='color: #666; font-size: 0.8rem; margin: 0 8px;'>VS</span> {p2[:10]}
</div>
<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
<div style='text-align: left; width: 45%;'>
<div style='font-size: 1.3rem; font-weight: 700; color: #4CAF50;'>{odds1:.2f}</div>
<div style='font-size: 0.75rem; color: #777;'>{prob1_pct:.0f}%</div>
</div>
<div style='text-align: right; width: 45%;'>
<div style='font-size: 1.3rem; font-weight: 700; color: #2196F3;'>{odds2:.2f}</div>
<div style='font-size: 0.75rem; color: #777;'>{prob2_pct:.0f}%</div>
</div>
</div>
<div style='width: 100%; background-color: #222; border-radius: 3px; height: 4px; margin-bottom: 12px; display: flex; overflow: hidden;'>
<div style='width: {prob1_pct}%; background-color: #4CAF50; height: 100%;'></div>
<div style='width: {prob2_pct}%; background-color: #2196F3; height: 100%;'></div>
</div>
<div style='font-size: 0.75rem; color: #888; text-align: center; text-transform: uppercase;'>{insight}</div>
</div>
""", unsafe_allow_html=True)
        
        with st.expander("Wie werden diese Buchmacher-Quoten berechnet?"):
            st.markdown("""
            Die App berechnet für jedes Matchup einen **Power-Score** für beide Spieler, der sich aus drei historischen Faktoren zusammensetzt. Je mehr "Punkte" (Score) ein Spieler sammelt, desto höher seine Siegwahrscheinlichkeit.
            
            **1. Der Score:**
            Jeder Spieler startet mit 100 Basis-Punkten. Darauf werden addiert:
            *   **H2H-Bonus:** Historische Winrate gegen diesen spezifischen Gegner. (z.B. 60% WR bringt +15 Punkte). Formel: $1.5 \times (H2H_{WR} - 50)$
            *   **Formkurve:** Die Net-Wins (Siege minus Niederlagen) aus den letzten 15 Spielen insgesamt. Jeder Net-Win gibt +2 Punkte.
            *   **Momentum:** Eine aktive Siegesserie (Streak) bringt fette Punkte. Formel: $+4 \times Streak$. (Verliert man gerade in Serie, gibt es Minus-Punkte).
            
            **2. Die Wahrscheinlichkeit:**
            Die Wahrscheinlichkeit berechnet sich aus dem Anteil am Gesamt-Score beider Spieler:
            $Prob_{A} = \frac{Score_A}{Score_A + Score_B}$
            
            **3. Die Quote:**
            Buchmacher-Quote = $1 / Wahrscheinlichkeit$. (Eine 50% Chance entspricht einer Quote von 2.00).
            """)
        
        st.subheader("Letzte 5 globale Matches")
        last_5_df = df_comp.sort_values(by='ID', ascending=False).head(5)
        history_html = "<div style='background-color: #121212; border-radius: 6px; border: 1px solid #333; padding: 0 15px; font-family: sans-serif;'>"
        for idx, r in last_5_df.iterrows():
            t = parse_time(r['ID'])
            t_str = t.strftime("%H:%M") if pd.notnull(t) else "Unbekannt"
            p1, p2 = r['Spieler1'], r['Spieler2']
            s1, s2 = r['Score1'], r['Score2']
            c_p1 = "#FFF" if s1 > s2 else "#666"
            c_p2 = "#FFF" if s2 > s1 else "#666"
            w_p1 = "bold" if s1 > s2 else "normal"
            w_p2 = "bold" if s2 > s1 else "normal"
            border_bottom = "border-bottom: 1px solid #222;" if idx != last_5_df.index[-1] else ""
            history_html += f"""
<div style='display: flex; justify-content: space-between; align-items: center; {border_bottom} padding: 12px 0;'>
<div style='width: 15%; color: #666; font-size: 0.85rem;'>{t_str}</div>
<div style='width: 35%; text-align: right; color: {c_p1}; font-weight: {w_p1}; font-size: 0.95rem;'>{p1}</div>
<div style='width: 15%; text-align: center; font-weight: bold; font-size: 1.1rem; letter-spacing: 2px;'>
<span style='color: {c_p1};'>{s1}</span><span style='color: #444;'>:</span><span style='color: {c_p2};'>{s2}</span>
</div>
<div style='width: 35%; text-align: left; color: {c_p2}; font-weight: {w_p2}; font-size: 0.95rem;'>{p2}</div>
</div>
"""
        history_html += "</div>"
        st.markdown(history_html, unsafe_allow_html=True)

with tab_analyse:
    st.header("Deep Data Analytics")
    if not df_comp.empty:
        st.markdown(f"<div style='color: #888; font-size: 0.9rem; margin-bottom: 10px;'>Live Snapshot: {latest_match_str}</div>", unsafe_allow_html=True)
        
        st.subheader("Aktueller Power-Index")
        st.markdown("<span style='color:#888; font-size:0.85rem;'>Dynamischer Wert (0-100) basierend auf Form und Siegesserien.</span>", unsafe_allow_html=True)
        cols_pi = st.columns(3)
        for idx, p in enumerate(TAGS.keys()):
            pi = get_power_index(p, df_comp)
            fig_pi = go.Figure(go.Indicator(
                mode="gauge+number", value=pi, title={'text': p, 'font': {'size': 18, 'color': '#FFF'}},
                gauge={'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#444"}, 'bar': {'color': "#4CAF50" if pi >= 50 else "#F44336"}, 'bgcolor': "#121212", 'borderwidth': 0, 'steps': [{'range': [0, 40], 'color': "#2A1212"}, {'range': [40, 60], 'color': "#222"}, {'range': [60, 100], 'color': "#122A12"}]}
            ))
            fig_pi.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="#0E1117", font={'color': "#FFF"})
            cols_pi[idx].plotly_chart(fig_pi, use_container_width=True)

        with st.expander("Was bedeutet der Power-Index?"):
            st.markdown("""
            Der Power-Index (PI) ist ein Tacho für die **aktuelle Hitze** eines Spielers. Er ignoriert die All-Time Stats und schaut nur auf die allerjüngste Vergangenheit.
            
            Jeder Spieler ruht bei einem neutralen Wert von 50.
            *   **Form (letzte 15 Spiele):** Hast du mehr Siege als Niederlagen (Net-Wins), steigt der Index. $NetWins \times 2.5$
            *   **Momentum:** Eine aktive Winstreak drückt den Tacho massiv nach oben. $Streak \times 5.0$
            
            **Die Formel:**
            $PI = \max(0, \min(100, 50 + 2.5 \times NetWins + 5.0 \times Streak))$
            *(Werte über 60 sind extrem gut, Werte unter 40 zeigen einen Tilt).*
            """)

        st.markdown("---")
        st.subheader("H2H Dominanz-Matrix")
        matrix_data = []
        players = list(TAGS.keys())
        for p1 in players:
            row = []
            for p2 in players:
                if p1 == p2: row.append(None)
                else:
                    match_df = df_comp[((df_comp['Spieler1'] == p1) & (df_comp['Spieler2'] == p2)) | ((df_comp['Spieler1'] == p2) & (df_comp['Spieler2'] == p1))]
                    if len(match_df) == 0: row.append(50.0)
                    else:
                        p1_wins = sum(1 for _, r in match_df.iterrows() if (r['Spieler1']==p1 and r['Score1']>r['Score2']) or (r['Spieler2']==p1 and r['Score2']>r['Score1']))
                        row.append((p1_wins / len(match_df)) * 100)
            matrix_data.append(row)
            
        fig_heat = px.imshow(matrix_data, x=players, y=players, text_auto=".0f", color_continuous_scale=[[0, "#F44336"], [0.5, "#222"], [1, "#4CAF50"]], zmin=0, zmax=100)
        fig_heat.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#0E1117", font={'color': "#FFF"})
        st.plotly_chart(fig_heat, use_container_width=True)
        
        with st.expander("Wie lese ich die Dominanz-Matrix?"):
            st.markdown("""
            Die Matrix ist ein Schere-Stein-Papier Check. Sie zeigt die **pure historische Winrate** von Spieler A gegen Spieler B in Prozent.
            *   **Lese-Richtung:** Lies von der Y-Achse (Links) zur X-Achse (Unten). 
            *   *Beispiel:* Wenn links "resan" steht und du gehst rüber zur Spalte "Jörg", dann zeigt die Zahl, zu wie viel Prozent resan historisch gegen Jörg gewinnt.
            *   **Grün:** Du dominierst den Gegner (>50%).
            *   **Rot:** Er ist dein Angstgegner (<50%).
            """)

        st.markdown("---")
        st.subheader("Matchup Deep-Dive")
        c1, c2 = st.columns(2)
        sel_p1 = c1.selectbox("Spieler A", players, index=0)
        sel_p2 = c2.selectbox("Spieler B", players, index=1)
        
        if sel_p1 != sel_p2:
            st.markdown("<br>**Letzte 10 direkte Duelle (Tauziehen)**", unsafe_allow_html=True)
            direct_df = df_comp[((df_comp['Spieler1'] == sel_p1) & (df_comp['Spieler2'] == sel_p2)) | ((df_comp['Spieler1'] == sel_p2) & (df_comp['Spieler2'] == sel_p1))].sort_values('ID').tail(10)
            if not direct_df.empty:
                tug_html = f"<div style='display: flex; width: 100%; height: 30px; border-radius: 4px; overflow: hidden; border: 1px solid #333; margin-top: 10px;'>"
                for _, r in direct_df.iterrows():
                    p1_won = (r['Spieler1'] == sel_p1 and r['Score1'] > r['Score2']) or (r['Spieler2'] == sel_p1 and r['Score2'] > r['Score1'])
                    color = "#4CAF50" if p1_won else "#2196F3"
                    tug_html += f"<div style='flex: 1; background-color: {color}; border-right: 1px solid #111;'></div>"
                tug_html += "</div>"
                st.markdown(f"<div style='display: flex; justify-content: space-between; font-size: 0.8rem; color: #AAA; margin-top: 5px;'><span style='color: #4CAF50;'>{sel_p1} (Grün)</span><span style='color: #2196F3;'>{sel_p2} (Blau)</span></div>", unsafe_allow_html=True)
                st.markdown(tug_html, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_radar, col_line = st.columns(2)
            with col_radar:
                st.markdown("**Metrik-Vergleich (Radar)**")
                cat = ['H2H Winrate', 'Aktuelle Form', 'Momentum', 'Offensiv-Power', 'Globale Winrate']
                fig_rad = go.Figure()
                fig_rad.add_trace(go.Scatterpolar(r=get_player_stats_for_radar(sel_p1, sel_p2, df_comp), theta=cat, fill='toself', name=sel_p1, line_color='#4CAF50'))
                fig_rad.add_trace(go.Scatterpolar(r=get_player_stats_for_radar(sel_p2, sel_p1, df_comp), theta=cat, fill='toself', name=sel_p2, line_color='#2196F3'))
                fig_rad.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], color="#555"), bgcolor="#121212"), paper_bgcolor="#0E1117", font={'color': "#FFF"}, margin=dict(t=30, b=30, l=30, r=30))
                st.plotly_chart(fig_rad, use_container_width=True)
                
                with st.expander("Wie normalisiert das Radar diese Werte auf 0-100?"):
                    st.markdown("""
                    Um Äpfel mit Birnen vergleichen zu können (z.B. Winrate vs. Kronen), werden alle Werte auf eine Skala von 0 bis 100 umgerechnet:
                    *   **H2H Winrate & Globale Winrate:** Werden direkt als 0-100% übernommen.
                    *   **Aktuelle Form:** Net-Wins der letzten 15 Spiele (Maximum ist +15, Minimum -15). Formel: $\frac{NetWins + 15}{30} \times 100$
                    *   **Momentum:** Winstreak (Max gedeckelt bei 5). Formel: $\frac{Streak + 5}{10} \times 100$
                    *   **Offensiv-Power:** Durchschnittlich geholte Kronen pro Spiel gegen diesen Gegner (Max. 3.0). Formel: $\frac{AvgCrowns}{3.0} \times 100$
                    """)
                    
            with col_line:
                st.markdown("**Quoten-Verlauf**")
                if len(direct_df) >= 3:
                    o1_h, o2_h, lbl = [], [], []
                    for idx, row in direct_df.iterrows():
                        _, _, o1, o2, _ = calc_matchup_odds(sel_p1, sel_p2, df_comp.loc[:idx])
                        o1_h.append(o1); o2_h.append(o2)
                    fig_trend = px.line(pd.DataFrame({'Match': range(1, len(o1_h)+1), sel_p1: o1_h, sel_p2: o2_h}), x='Match', y=[sel_p1, sel_p2], color_discrete_map={sel_p1: '#4CAF50', sel_p2: '#2196F3'})
                    fig_trend.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#121212", font={'color': "#FFF"}, yaxis_title="Quote (Tiefer=Besser)", xaxis_title="", legend_title="")
                    fig_trend.update_yaxes(autorange="reversed")
                    st.plotly_chart(fig_trend, use_container_width=True)

with tab_mc:
    st.header("Der Turnier-Simulator (Monte Carlo)")
    with st.expander("Wie funktioniert das und was sehe ich hier?"):
        st.markdown("""
        **Stell dir vor, Doctor Strange schaut sich 10.000 mögliche Zukünfte an.**
        Der Computer würfelt jedes einzelne Match im Hintergrund aus. Aber er würfelt nicht fair (50/50), sondern er nutzt eure echten Winrates, eure Form und das Momentum. 
        """)

    if df_comp.empty:
        st.warning("Keine Datenbasis für Simulationen.")
    else:
        st.markdown("### Die Spielregeln (Parameter)")
        col_c1, col_c2, col_c3 = st.columns(3)
        sim_count = col_c1.select_slider("Wie oft soll in die Zukunft geblickt werden?", options=[100, 1000, 5000, 10000, 50000], value=10000)
        target_w = col_c2.slider("Wie viele Siege braucht man für den Turniersieg?", min_value=3, max_value=200, value=50, step=1)
        fw = col_c3.slider("Wie stark zählt die heutige Tagesform?", min_value=0.0, max_value=2.0, value=1.0, step=0.1)
        
        if st.button("Turnier-Simulation jetzt starten", type="primary", use_container_width=True):
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
            
            st.subheader(f"Die Ergebnisse aus {sims_done:,} simulierten Turnieren".replace(',', '.'))
            vis_choice = st.selectbox("Wie möchtest du das Ergebnis sehen?", ["1. Klassisches Podest (Balkendiagramm)", "2. Kuchen-Verteilung (Kreisdiagramm)", "3. Wahrscheinlichkeits-Tacho", "4. Harte Fakten (Zahlen)"])
            col_chart, col_stats = st.columns([2, 1])
            with col_chart:
                if "Podest" in vis_choice:
                    fig_mc = px.bar(res_df, x='Spieler', y='Wahrscheinlichkeit', text_auto='.1f', color='Spieler', title=f"Chance auf den Turniersieg")
                    fig_mc.update_traces(textposition='outside')
                    fig_mc.update_layout(yaxis=dict(title='Wahrscheinlichkeit (%)', range=[0, 100]), showlegend=False, paper_bgcolor="#0E1117", plot_bgcolor="#121212", font={'color': "#FFF"})
                    st.plotly_chart(fig_mc, use_container_width=True)
                elif "Kuchen" in vis_choice:
                    fig_pie = px.pie(res_df, names='Spieler', values='Wahrscheinlichkeit', hole=0.4, title="Anteile an den Turniersiegen", color='Spieler')
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    fig_pie.update_layout(paper_bgcolor="#0E1117", font={'color': "#FFF"}, showlegend=False)
                    st.plotly_chart(fig_pie, use_container_width=True)
                elif "Tacho" in vis_choice:
                    st.markdown("**Sieg-Wahrscheinlichkeit pro Spieler**")
                    tacho_cols = st.columns(3)
                    for i, (index, row) in enumerate(res_df.iterrows()):
                        fig_gauge = go.Figure(go.Indicator(mode="gauge+number", value=row['Wahrscheinlichkeit'], number={'suffix': "%"}, title={'text': row['Spieler'], 'font': {'size': 16, 'color': '#FFF'}}, gauge={'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#444"}, 'bar': {'color': "#2196F3"}, 'bgcolor': "#121212", 'borderwidth': 0}))
                        fig_gauge.update_layout(height=200, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="#0E1117", font={'color': "#FFF"})
                        tacho_cols[i % 3].plotly_chart(fig_gauge, use_container_width=True)
                elif "Fakten" in vis_choice:
                    st.markdown("**Exakte Turniersiege (Absolute Zahlen)**")
                    f_cols = st.columns(3)
                    for i, (index, row) in enumerate(res_df.iterrows()):
                        f_cols[i % 3].metric(label=row['Spieler'], value=f"{row['Turniersiege']:,}".replace(',', '.'), delta=f"{row['Wahrscheinlichkeit']:.1f}% Winrate", delta_color="normal")
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.dataframe(res_df.reset_index(drop=True), use_container_width=True)

            with col_stats:
                st.markdown("<br><br>", unsafe_allow_html=True)
                st.info(f"**Der Favorit:**<br>Zu {res_df.iloc[0]['Wahrscheinlichkeit']:.1f}% gewinnt **{res_df.iloc[0]['Spieler']}**.")
                st.warning(f"**Vernichtungs-Quote:**<br>{(st.session_state['mc_sweeps']/sims_done)*100:.1f}%")

with tab_dna:
    st.header("Profil-DNA & Spiel-Psychologie")
    if df_comp.empty:
        st.warning("Keine Datenbasis vorhanden.")
    else:
        st.markdown(f"<div style='color: #888; font-size: 0.9rem; margin-bottom: 20px;'>Live Snapshot: {latest_match_str}</div>", unsafe_allow_html=True)
        
        # --- TEIL 1: KONSISTENZ-INDEX ---
        st.subheader("Glicko Konsistenz-Index (Volatilität)")
        st.markdown("<span style='color:#888; font-size:0.85rem;'>Misst die Verlässlichkeit und Nervenstärke eines Spielers.</span>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        for p in TAGS.keys():
            score, label, color = get_consistency_score(p, df_comp)
            st.markdown(f"""
<div style='margin-bottom: 15px; font-family: sans-serif;'>
<div style='display: flex; justify-content: space-between; margin-bottom: 5px;'>
    <span style='color: #FFF; font-weight: bold;'>{p[:10]}</span>
    <span style='color: {color}; font-weight: bold;'>Score: {score:.0f} / 100</span>
</div>
<div style='width: 100%; background-color: #222; border-radius: 4px; height: 12px; overflow: hidden; border: 1px solid #333;'>
    <div style='width: {score}%; background-color: {color}; height: 100%; border-radius: 4px;'></div>
</div>
<div style='text-align: right; font-size: 0.75rem; color: #888; margin-top: 3px;'>
    Urteil: <span style='color: {color};'>{label}</span>
</div>
</div>
""", unsafe_allow_html=True)

        with st.expander("Wie wird die Konsistenz (Wundertüte vs. Maschine) berechnet?"):
            st.markdown("""
            Der Score misst die **Volatilität** – also wie extrem die Leistung schwankt.
            
            Ein Spieler, der exakt 50% Winrate hat, kann diese auf zwei Arten erreichen:
            1.  **Die Maschine:** Sieg, Niederlage, Sieg, Niederlage. (Er ist konstant, man weiß was man bekommt).
            2.  **Die Wundertüte:** 10 Siege in Folge, danach 10 Niederlagen am Stück in einem Tilt. (Er ist extrem unberechenbar).
            
            **Die Formel:**
            Wir zählen die Länge jeder einzelnen "Serie" (egal ob Sieg- oder Niederlagenserie) und berechnen den Durchschnitt ($\overline{Streak}$).
            $Konsistenz = 100 - ((\overline{Streak} - 1) \times 25)$
            
            *Wenn deine durchschnittliche Serie sehr kurz ist, bleibt der Score hoch (nah an 100). Hast du oft extrem lange Serien (z.B. Durchschnitt 4.0), bricht der Score zusammen.*
            """)

        st.markdown("---")
        
        # --- TEIL 2: DECK SYNERGIEN ---
        st.subheader("Deck-Synergien (Deadly Duos)")
        st.markdown("<span style='color:#888; font-size:0.85rem;'>Welche 2-Karten-Kombinationen im selben Deck sind für diesen Spieler am tödlichsten?</span>", unsafe_allow_html=True)
        
        sel_player = st.selectbox("Wähle einen Spieler:", list(TAGS.keys()), key="dna_player")
        synergy_df = get_top_synergies(sel_player, df_comp)
        
        if synergy_df.empty:
            st.info("Zu wenige Daten für Kombinationen (Gleiche Karten müssen öfter gespielt werden).")
        else:
            col_s1, col_s2 = st.columns([1, 1])
            with col_s1:
                st.dataframe(synergy_df.reset_index(drop=True), use_container_width=True)
            with col_s2:
                plot_df = synergy_df.copy()
                plot_df['WR_Float'] = plot_df['Sieg-Quote (%)'].str.replace('%', '').astype(float)
                fig_syn = px.bar(plot_df, x='WR_Float', y='Karten-Duo', orientation='h', text='Sieg-Quote (%)', color='Spiele', color_continuous_scale="Viridis", title=f"Tödlichste Duos von {sel_player}")
                fig_syn.update_layout(yaxis={'categoryorder':'total ascending'}, paper_bgcolor="#0E1117", plot_bgcolor="#121212", font={'color': "#FFF"}, xaxis_title="Sieg-Wahrscheinlichkeit (%)")
                st.plotly_chart(fig_syn, use_container_width=True)

        with st.expander("Wie findet der Algorithmus diese 'Synergien'?"):
            st.markdown("""
            Normale Analysen schauen nur darauf, ob du z.B. mit dem "Ritter" oft gewinnst. Aber Profis gewinnen durch das Zusammenspiel von Karten.
            
            **Die Logik dahinter:**
            1.  Der Bot nimmt jedes Spiel, das du gespielt hast.
            2.  Er spaltet dein 8-Karten Deck auf in **alle möglichen 2er-Kombinationen** (insgesamt 28 Kombinationen pro Deck).
            3.  Er vergleicht über hunderte Spiele hinweg, welches Karten-Pärchen (z.B. "Ritter + Koboldfass") am häufigsten in Decks auftaucht, die letztendlich auch **gewonnen** haben.
            4.  Um Zufälle auszuschließen, zeigt das System nur Duos, die du mindestens 3 Mal zusammen gespielt hast.
            """)
