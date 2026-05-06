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

# WICHTIG: Füge hier den echten Link aus der Browser-Leiste ein
SHEET_URL = "HIER_DEN_LINK_ZU_DEINER_GOOGLE_TABELLE_EINFÜGEN"

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
            nemesis_data.append({"Spieler": p[:10], "Angstgegner": f"{nemesis[0]} ({n_wr:.0f}%)", "Kryptonit-Karte": f"{krypt[0]} ({krypt[1]}x verloren)"})
    return pd.DataFrame(nemesis_data)

@st.cache_data(ttl=60)
def get_api_data(endpoint, tag):
    url = f"https://api.clashroyale.com/v1/players/%23{tag}/{endpoint}" if endpoint else f"https://api.clashroyale.com/v1/players/%23{tag}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        return res.json() if res.status_code == 200 else None
    except: return None

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
st.sidebar.title("Clash Analyzer Pro")
st.sidebar.markdown("---")
st.sidebar.write("**System-Status**")
st.sidebar.write(f"Datensätze (Lokal): {len(df_comp)}")
st.sidebar.write(f"Datensätze (Global): {len(df_global)}")
st.sidebar.write(f"Letztes Match: {latest_match_str}")
st.sidebar.markdown("---")

# --- KONSOLIDIERTE TABS ---
tab_dbl, tab_spieler_loc, tab_spieler_glob, tab_dbf, tab_trends, tab_sessions, tab_prognose, tab_analyse, tab_dna, tab_mc = st.tabs([
    "1v1 Liga", "Spieler (Lokal)", "Spieler (Global)", "Fun Matches", "Aktivität & Trends", "Sessions", "Prognose", "Match-Analyse", "Profil-DNA", "Monte Carlo"
])

# --- TAB 1: 1v1 LIGA ---
with tab_dbl:
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
            df_lb.index = df_lb.index + 1
            st.dataframe(df_lb, use_container_width=True)
            st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px;'>Net-Wins: Absolute Differenz zwischen Siegen und Niederlagen. Indikator für echten Fortschritt.</div>", unsafe_allow_html=True)

        st.markdown("---")
        h2h_df, curr_streak, at_streak = get_h2h_stats_data(df_comp)
        
        st.subheader("Head-to-Head Historie")
        st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:10px;'>Direkter Vergleich aller Begegnungen. Wer dominiert wen?</div>", unsafe_allow_html=True)
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

# --- TAB 2: SPIELER LOKAL ---
with tab_spieler_loc:
    st.header("Spieler Profile (Übersicht)")
    st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Globale Account-Daten (Trophäen) sowie lokale Crew-Performance.</div>", unsafe_allow_html=True)
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
                    if s_me > s_opp: res_col, res_text = "#4CAF50", "W"
                    elif s_me < s_opp: res_col, res_text = "#F44336", "L"
                    else: res_col, res_text = "#888888", "D"
                    history_html += f"<div style='margin-bottom: 4px;'><span style='color: {res_col}; font-weight: bold; width: 20px; display: inline-block;'>{res_text}</span> vs {opp} ({s_me}:{s_opp})</div>"
                history_html += "</div>"
                st.markdown(history_html, unsafe_allow_html=True)
                
            st.markdown("---")
            top_u, top_w = calculate_card_stats(name, df_comp)
            if not top_u.empty:
                st.markdown("**Meistgespielte Karten:**")
                st.dataframe(top_u, hide_index=True, use_container_width=True)

# --- TAB 3: SPIELER GLOBAL (DEEP DIVE) ---
with tab_spieler_glob:
    st.header("Globale Spieler-Analyse (Deep Dive)")
    st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Nutzt das Archiv (Global_Data) aller weltweit gespielten Matches des Accounts.</div>", unsafe_allow_html=True)
    
    selected_p = st.selectbox("Spieler auswählen:", list(TAGS.keys()), key="detail_player")
    
    if df_global.empty:
        st.warning("Keine Daten in Global_Data gefunden. Lass den Bot erst laufen!")
    else:
        p_global = df_global[df_global['Spieler'] == selected_p].sort_values('Time_ID')
        
        if p_global.empty:
            st.info(f"Keine globalen Spiele für {selected_p} im Archiv gefunden.")
        else:
            total_global_games = len(p_global)
            st.markdown(f"<div style='color:#4CAF50; font-weight:bold; margin-bottom:10px;'>Berechnungen basieren auf {total_global_games} archivierten globalen Spielen.</div>", unsafe_allow_html=True)
            
            b_games, b_wins, b_losses = 0, 0, 0
            crowns_for, crowns_against = 0, 0
            clean_sheets, clutch_games, clutch_wins, three_crown_wins = 0, 0, 0, 0
            unique_cards = set()
            
            last_5_html = "<div style='background-color: #121212; border-radius: 6px; border: 1px solid #333; padding: 0 15px; font-family: sans-serif;'>"
            
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
                    c_me = "#4CAF50" if my_cr > op_cr else ("#F44336" if my_cr < op_cr else "#888")
                    c_op = "#4CAF50" if op_cr > my_cr else ("#F44336" if op_cr < my_cr else "#888")
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
                st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:5px;'>Gesamte Siegquote im Archiv. Über 50% = Positiv.</div>", unsafe_allow_html=True)
                fig_wr = go.Figure(go.Indicator(mode="gauge+number", value=wr_recent, number={'suffix': "%"}, gauge={'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#444"}, 'bar': {'color': "#2196F3"}, 'bgcolor': "#121212", 'borderwidth': 0}))
                fig_wr.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#0E1117", font={'color': "#FFF"})
                st.plotly_chart(fig_wr, use_container_width=True)
            with c2:
                st.markdown("**2 & 3. Offensiv vs Defensiv**")
                st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:5px;'>Durchschnittlich geholte/kassierte Kronen. Höher = Aggressiver.</div>", unsafe_allow_html=True)
                df_cr = pd.DataFrame({'Typ': ['Offensiv', 'Defensiv'], 'Kronen': [avg_cr_for, avg_cr_ag]})
                fig_cr = px.bar(df_cr, x='Typ', y='Kronen', text_auto='.2f', color='Typ', color_discrete_map={'Offensiv': '#4CAF50', 'Defensiv': '#F44336'})
                fig_cr.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#0E1117", plot_bgcolor="#121212", showlegend=False, font={'color': "#FFF"}, yaxis_title="", xaxis_title="")
                st.plotly_chart(fig_cr, use_container_width=True)
            with c3:
                st.markdown("**7. Deck-Flexibilität**")
                st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:30px;'>Anzahl genutzter einzigartiger Karten. Je höher, desto unberechenbarer.</div>", unsafe_allow_html=True)
                st.metric(label="Gespielte einzigartige Karten", value=flex_index, delta=f"Aus {b_games} Matches", delta_color="off")
                
            c4, c5, c6 = st.columns(3)
            with c4:
                st.markdown("**4. Zu-Null-Quote (Clean Sheets)**")
                st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:5px;'>Prozentsatz der Spiele ohne Gegentor (Perfekte Defensive).</div>", unsafe_allow_html=True)
                fig_cs = px.pie(names=['Clean Sheets', 'Gegentor'], values=[clean_sheet_pct, 100-clean_sheet_pct], hole=0.6, color_discrete_sequence=['#2196F3', '#333'])
                fig_cs.update_traces(textinfo='none')
                fig_cs.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#0E1117", font={'color': "#FFF"}, showlegend=False, annotations=[dict(text=f"{clean_sheet_pct:.0f}%", x=0.5, y=0.5, font_size=20, showarrow=False)])
                st.plotly_chart(fig_cs, use_container_width=True)
            with c5:
                st.markdown("**5. Clutch-Rating (Nervenstärke)**")
                st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:5px;'>Siegquote bei knappen Spielen (Exakt 1 Krone Unterschied).</div>", unsafe_allow_html=True)
                if clutch_games == 0:
                    st.info("Keine knappen Spiele verzeichnet.")
                else:
                    fig_cl = px.pie(names=['Knapper Sieg', 'Knappe Ndl'], values=[clutch_pct, 100-clutch_pct], hole=0.6, color_discrete_sequence=['#4CAF50', '#333'])
                    fig_cl.update_traces(textinfo='none')
                    fig_cl.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#0E1117", font={'color': "#FFF"}, showlegend=False, annotations=[dict(text=f"{clutch_pct:.0f}%", x=0.5, y=0.5, font_size=20, showarrow=False)])
                    st.plotly_chart(fig_cl, use_container_width=True)
            with c6:
                st.markdown("**6. Zerstörungs-Quote (3-Crowns)**")
                st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:5px;'>Anteil der Siege, die durch absolute Vernichtung erzielt wurden.</div>", unsafe_allow_html=True)
                if b_wins == 0:
                    st.info("Keine Siege verzeichnet.")
                else:
                    fig_3c = px.pie(names=['3 Kronen', 'Normaler Sieg'], values=[three_cr_pct, 100-three_cr_pct], hole=0.6, color_discrete_sequence=['#FFC107', '#333'])
                    fig_3c.update_traces(textinfo='none')
                    fig_3c.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#0E1117", font={'color': "#FFF"}, showlegend=False, annotations=[dict(text=f"{three_cr_pct:.0f}%", x=0.5, y=0.5, font_size=20, showarrow=False)])
                    st.plotly_chart(fig_3c, use_container_width=True)

            with st.expander("Erklärungen und Formeln zu den Kennzahlen (Ausklappen)"):
                st.markdown("""
                Diese Daten basieren auf den im Archiv hinterlegten globalen Spielen.
                
                **1. Historische Formkurve:** Die exakte Siegquote aller erfassten globalen Spiele. Formel: $\frac{Siege}{Matches} \times 100$
                **2 & 3. Offensiv/Defensiv:** Durchschnitt der geholten/zugelassenen Kronen pro Spiel. Formel: $\frac{\sum Kronen}{Matches}$
                **4. Zu-Null-Quote:** Spiele ohne eine einzige zugelassene Krone des Gegners. Formel: $\frac{Spiele\ mit\ 0\ Gegentoren}{Matches} \times 100$
                **5. Clutch-Rating:** Siegesquote bei extrem engen Matches (exakt 1 Krone Differenz). Formel: $\frac{Siege\ mit\ 1\ Krone\ Diff}{Alle\ Matches\ mit\ 1\ Krone\ Diff} \times 100$
                **6. Zerstörungs-Quote:** Anteil der Siege, die mit 3 Kronen gewonnen wurden. Formel: $\frac{3\text{-Kronen Siege}}{Alle\ Siege} \times 100$
                **7. Flexibilität:** Absolute Anzahl unterschiedlicher gespielter Karten in der gesamten erfassten Historie.
                """)

            st.markdown("---")
            st.subheader("Letzte 5 Globale Matches")
            st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:10px;'>Auszug aus dem Global-Archiv für diesen Spieler.</div>", unsafe_allow_html=True)
            st.markdown(last_5_html, unsafe_allow_html=True)

# --- TAB 4: FUN MATCHES ---
with tab_dbf:
    st.header("Fun Dashboard")
    st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Interne Spiele, die außerhalb des kompetitiven 1v1-Standards stattfanden.</div>", unsafe_allow_html=True)
    if not df_fun.empty:
        h2h_df, _, _ = get_h2h_stats_data(df_fun)
        st.dataframe(h2h_df, use_container_width=True, hide_index=True)

# --- TAB 5: AKTIVITÄT & TRENDS ---
with tab_trends:
    st.header("Aktivität & Formkurven")
    st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Wann wird gespielt und wer hat den besten Lauf?</div>", unsafe_allow_html=True)
    
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.subheader("Formkurve (Net-Wins)")
        st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:10px;'>Die Linie steigt bei Sieg und fällt bei Niederlage. Zeigt Momentum.</div>", unsafe_allow_html=True)
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
                fig = px.line(tdf, x="Match-Nr", y="Net-Wins", color="Spieler", markers=True)
                fig.update_layout(paper_bgcolor="#0E1117", plot_bgcolor="#121212", font={'color': "#FFF"}, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig, use_container_width=True)

    with col_t2:
        st.subheader("Aktivitäts-Heatmap")
        st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:10px;'>Helle Flächen markieren die Uhrzeiten mit den meisten Spielen.</div>", unsafe_allow_html=True)
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
                fig_heat.update_layout(paper_bgcolor="#0E1117", font={'color': "#FFF"})
                st.plotly_chart(fig_heat, use_container_width=True)

# --- TAB 6: SESSIONS ---
with tab_sessions:
    st.header("Session Leaderboards")
    st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Zusammenhängende Spiel-Sessions (Unterbrechungen von max. 30 Minuten). Das King-of-the-Hill (KotH) Rating ermittelt den MVP der Session.</div>", unsafe_allow_html=True)
    
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
                st.dataframe(lb, use_container_width=True)
                
                with st.expander("Erklärung: Wie wird das King of the Hill (KotH) Rating berechnet?"):
                    st.markdown("""
                    Das **KotH-Rating (0-10)** bewertet den Most Valuable Player (MVP) der Session.
                    Es bestraft Spieler, die nur 1x spielen, gewinnen und dann aufhören ("Leaver"), und belohnt diejenigen, die das Schlachtfeld dominieren.
                    
                    **Die Formel (Maximal 10 Punkte):**
                    *   **Winrate (Max 4.0 Pkt):** Basis-Skillfaktor. Formel: $Winrate \times 4.0$
                    *   **Dominanz (Max 3.5 Pkt):** Anteil an den maximalen Siegen des besten Spielers. Formel: $\frac{Eigene Siege}{Max Siege aller Spieler} \times 3.5$
                    *   **Wichtigkeit (Max 2.5 Pkt):** Wie viele Spiele der Session hast du bestritten? Formel: $\frac{Eigene Matches}{Gesamt Matches} \times 2.5$
                    *   **Streak-Modifikator:** Bonus für Winstreaks, Abzug für Lösestreaks. Formel: $+ (\max Winstreak - 1) \times 0.3 - (\max Lösestreak - 1) \times 0.3$
                    """)
        else:
            st.info("Noch keine vollständigen Sessions registriert.")

# --- TAB 7: PROGNOSE ---
with tab_prognose:
    st.header("Live-Quoten & Prognose")
    st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Automatische Buchmacher-Quoten basierend auf Head-to-Head Historie und aktueller Tagesform.</div>", unsafe_allow_html=True)
    
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
        
        with st.expander("Erklärung: Wie werden diese Buchmacher-Quoten berechnet?"):
            st.markdown("""
            Die App berechnet für jedes Matchup einen **Power-Score** für beide Spieler, der sich aus drei historischen Faktoren zusammensetzt.
            
            **1. Der Score:**
            Jeder Spieler startet mit 100 Basis-Punkten. Darauf werden addiert:
            *   **H2H-Bonus:** Historische Winrate gegen diesen spezifischen Gegner. Formel: $1.5 \times (H2H_{WR} - 50)$
            *   **Formkurve:** Jeder Net-Win aus der jüngsten Vergangenheit gibt +2 Punkte.
            *   **Momentum:** Eine aktive Siegesserie bringt zusätzliche Punkte. Formel: $+4 \times Streak$.
            
            **2. Die Wahrscheinlichkeit:**
            Berechnet sich aus dem Anteil am Gesamt-Score beider Spieler:
            $Prob_{A} = \frac{Score_A}{Score_A + Score_B}$
            
            **3. Die Quote:**
            Typische Sportwetten-Logik: $Quote = 1 / Wahrscheinlichkeit$. (Eine 50% Chance = Quote 2.00).
            """)

# --- TAB 8: MATCH-ANALYSE ---
with tab_analyse:
    st.header("Match-Analyse & Nemesis")
    st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Zusammenfassung von Momentum, historischen Angstgegnern und direkten Kräfteverhältnissen.</div>", unsafe_allow_html=True)
    if not df_comp.empty:
        c1, c2 = st.columns([1.5, 1])
        with c1:
            st.subheader("Aktueller Power-Index")
            st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:10px;'>Dynamischer Wert (0-100). Werte über 60 zeigen eine heiße Phase (On-Fire). Unter 40 deutet auf einen Tilt hin.</div>", unsafe_allow_html=True)
            cols_pi = st.columns(3)
            for idx, p in enumerate(TAGS.keys()):
                pi = get_power_index(p, df_comp)
                fig_pi = go.Figure(go.Indicator(
                    mode="gauge+number", value=pi, title={'text': p, 'font': {'size': 18, 'color': '#FFF'}},
                    gauge={'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#444"}, 'bar': {'color': "#4CAF50" if pi >= 50 else "#F44336"}, 'bgcolor': "#121212", 'borderwidth': 0, 'steps': [{'range': [0, 40], 'color': "#2A1212"}, {'range': [40, 60], 'color': "#222"}, {'range': [60, 100], 'color': "#122A12"}]}
                ))
                fig_pi.update_layout(height=200, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="#0E1117", font={'color': "#FFF"})
                cols_pi[idx].plotly_chart(fig_pi, use_container_width=True)

        with c2:
            st.subheader("Kryptonit & Angstgegner")
            st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:10px;'>Gegen wen und gegen welche Karte verliert man statistisch am häufigsten?</div>", unsafe_allow_html=True)
            nem_df = calc_nemesis_kryptonit(df_comp)
            if not nem_df.empty: st.dataframe(nem_df, hide_index=True, use_container_width=True)

        with st.expander("Erklärung: Was bedeutet der Power-Index?"):
            st.markdown("""
            Der Power-Index (PI) ist ein Tacho für die **aktuelle Hitze** eines Spielers. Er ignoriert die All-Time Stats komplett.
            Jeder Spieler ruht bei einem neutralen Wert von 50.
            *   **Form (letzte 15 Spiele):** $NetWins \times 2.5$
            *   **Momentum:** $Streak \times 5.0$
            **Die Formel:**
            $PI = \max(0, \min(100, 50 + 2.5 \times NetWins + 5.0 \times Streak))$
            """)

        st.markdown("---")
        c3, c4 = st.columns(2)
        with c3:
            st.subheader("H2H Dominanz-Matrix")
            st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:10px;'>Lies von der Y-Achse (Links) zur X-Achse (Unten). Grün = Du dominierst den Gegner. Rot = Du wirst dominiert.</div>", unsafe_allow_html=True)
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
            fig_heat.update_layout(height=350, margin=dict(t=20, b=20, l=20, r=20), paper_bgcolor="#0E1117", plot_bgcolor="#0E1117", font={'color': "#FFF"})
            st.plotly_chart(fig_heat, use_container_width=True)

        with c4:
            st.subheader("Matchup Radar-Vergleich")
            st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:10px;'>Direkter Skill-Vergleich zwischen zwei Spielern (Werte auf 0-100 normiert). Je größer die Fläche, desto stärker.</div>", unsafe_allow_html=True)
            sel_p1 = st.selectbox("Spieler A (Grün)", players, index=0)
            sel_p2 = st.selectbox("Spieler B (Blau)", players, index=1)
            if sel_p1 != sel_p2:
                cat = ['H2H Winrate', 'Aktuelle Form', 'Momentum', 'Offensiv-Power', 'Globale Winrate']
                fig_rad = go.Figure()
                fig_rad.add_trace(go.Scatterpolar(r=get_player_stats_for_radar(sel_p1, sel_p2, df_comp), theta=cat, fill='toself', name=sel_p1, line_color='#4CAF50'))
                fig_rad.add_trace(go.Scatterpolar(r=get_player_stats_for_radar(sel_p2, sel_p1, df_comp), theta=cat, fill='toself', name=sel_p2, line_color='#2196F3'))
                fig_rad.update_layout(height=280, polar=dict(radialaxis=dict(visible=True, range=[0, 100], color="#555"), bgcolor="#121212"), paper_bgcolor="#0E1117", font={'color': "#FFF"}, margin=dict(t=30, b=30, l=30, r=30))
                st.plotly_chart(fig_rad, use_container_width=True)

# --- TAB 9: PROFIL DNA ---
with tab_dna:
    st.header("Profil-DNA & Spiel-Psychologie")
    st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Tiefenanalyse von Verlässlichkeit und Deckbau.</div>", unsafe_allow_html=True)
    if df_comp.empty:
        st.warning("Keine Datenbasis vorhanden.")
    else:
        st.subheader("Glicko Konsistenz-Index (Volatilität)")
        st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:15px;'>Misst Nervenstärke und Verlässlichkeit (0-100). Wer extremen Schwankungen (Tilts/Winstreaks) unterliegt, bekommt einen niedrigen Wert.</div>", unsafe_allow_html=True)
        
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

        with st.expander("Erklärung: Wie wird die Konsistenz berechnet?"):
            st.markdown("""
            Der Score misst die **Volatilität** – also wie extrem die Leistung schwankt.
            
            Ein Spieler, der exakt 50% Winrate hat, kann diese auf zwei Arten erreichen:
            1.  **Die Maschine:** Sieg, Niederlage, Sieg, Niederlage. (Er ist konstant, man weiß was man bekommt).
            2.  **Die Wundertüte:** 10 Siege in Folge, danach 10 Niederlagen am Stück in einem Tilt. (Er ist extrem unberechenbar).
            
            **Die Formel:**
            Wir berechnen den Durchschnitt der Längen aller Serien ($\overline{Streak}$).
            $Konsistenz = 100 - ((\overline{Streak} - 1) \times 25)$
            """)

        st.markdown("---")
        st.subheader("Deck-Synergien (Deadly Duos)")
        st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:15px;'>Welche 2-Karten-Kombinationen im selben Deck erzielen für diesen Spieler die absolut höchste Siegwahrscheinlichkeit? (Min. 3 Einsätze)</div>", unsafe_allow_html=True)
        
        sel_player = st.selectbox("Wähle einen Spieler für die Analyse:", list(TAGS.keys()), key="dna_player")
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
                fig_syn = px.bar(plot_df, x='WR_Float', y='Karten-Duo', orientation='h', text='Sieg-Quote (%)', color='Spiele', color_continuous_scale="Viridis")
                fig_syn.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), yaxis={'categoryorder':'total ascending'}, paper_bgcolor="#0E1117", plot_bgcolor="#121212", font={'color': "#FFF"}, xaxis_title="Sieg-Wahrscheinlichkeit (%)")
                st.plotly_chart(fig_syn, use_container_width=True)

# --- TAB 10: MONTE CARLO ---
with tab_mc:
    st.header("Turnier-Simulator (Monte Carlo)")
    st.markdown("<div style='color:#888; font-size:13px; margin-top:-10px; margin-bottom:20px;'>Ein statistischer Blick in die Zukunft. Der Algorithmus simuliert virtuelle Turniere basierend auf den echten Formkurven und H2H-Stats.</div>", unsafe_allow_html=True)

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
                    fig_mc.update_layout(yaxis=dict(title='Turniersieg Chance (%)', range=[0, 100]), showlegend=False, paper_bgcolor="#0E1117", plot_bgcolor="#121212", font={'color': "#FFF"})
                    st.plotly_chart(fig_mc, use_container_width=True)
                elif "Kuchen" in vis_choice:
                    fig_pie = px.pie(res_df, names='Spieler', values='Wahrscheinlichkeit', hole=0.4, color='Spieler')
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    fig_pie.update_layout(paper_bgcolor="#0E1117", font={'color': "#FFF"}, showlegend=False)
                    st.plotly_chart(fig_pie, use_container_width=True)
                elif "Tacho" in vis_choice:
                    st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:10px;'>Exakte prozentuale Siegchance pro Spieler.</div>", unsafe_allow_html=True)
                    tacho_cols = st.columns(3)
                    for i, (index, row) in enumerate(res_df.iterrows()):
                        fig_gauge = go.Figure(go.Indicator(mode="gauge+number", value=row['Wahrscheinlichkeit'], number={'suffix': "%"}, title={'text': row['Spieler'], 'font': {'size': 16, 'color': '#FFF'}}, gauge={'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#444"}, 'bar': {'color': "#2196F3"}, 'bgcolor': "#121212", 'borderwidth': 0}))
                        fig_gauge.update_layout(height=200, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="#0E1117", font={'color': "#FFF"})
                        tacho_cols[i % 3].plotly_chart(fig_gauge, use_container_width=True)
                elif "Fakten" in vis_choice:
                    st.markdown("<div style='color:#888; font-size:12px; margin-top:-10px; margin-bottom:10px;'>Absolute Zahlen: Wie oft hat der Spieler das Turnier virtuell gewonnen?</div>", unsafe_allow_html=True)
                    f_cols = st.columns(3)
                    for i, (index, row) in enumerate(res_df.iterrows()):
                        f_cols[i % 3].metric(label=row['Spieler'], value=f"{row['Turniersiege']:,}".replace(',', '.'), delta=f"{row['Wahrscheinlichkeit']:.1f}% Winrate", delta_color="normal")
                    st.dataframe(res_df.reset_index(drop=True), use_container_width=True)

            with col_stats:
                st.markdown("<br><br>", unsafe_allow_html=True)
                st.info(f"**Top-Favorit:**<br>Zu {res_df.iloc[0]['Wahrscheinlichkeit']:.1f}% gewinnt **{res_df.iloc[0]['Spieler']}**.")
                st.warning(f"**Vernichtungs-Quote (Sweeps):**<br>{(st.session_state['mc_sweeps']/sims_done)*100:.1f}%<br><span style='font-size:0.75rem; color:#444;'>Anteil der Turniere, in denen der Sieger alle anderen völlig deklassiert hat.</span>")
