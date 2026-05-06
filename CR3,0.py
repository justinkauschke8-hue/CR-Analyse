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
from google.oauth2.service_account import Credentials

# --- PAGE CONFIG ---
st.set_page_config(page_title="Clash Analyzer Pro", page_icon="🏆", layout="wide")

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
    st.error(f"Fehler bei Google Sheets! ({e})")
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
        res = requests.get(url, headers=headers, timeout=5)
        return res.json() if res.status_code == 200 else None
    except: return None

# --- HELFER FUNKTIONEN ---
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
    results, global_current_streak, global_all_time_streak = [], {"player": None, "count": 0}, {"player": None, "count": 0}
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
            nemesis_data.append({"Spieler": p[:10], "💀 Nemesis": f"{nemesis[0]} ({n_wr:.0f}%)", "☢️ Kryptonit-Karte": f"{krypt[0]} ({krypt[1]}x verloren)"})
    return pd.DataFrame(nemesis_data)

# --- ALGORITHMUS FÜR BUCHMACHER QUOTEN ---
def get_player_form_and_streak(player, df):
    p_df = df[(df['Spieler1'] == player) | (df['Spieler2'] == player)].sort_values('ID').tail(15)
    if p_df.empty: return 0, 0
    wins = 0
    streak = 0
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

def calc_matchup_odds(p1, p2, df):
    match_df = df[((df['Spieler1'] == p1) & (df['Spieler2'] == p2)) | ((df['Spieler1'] == p2) & (df['Spieler2'] == p1))]
    total_h2h = len(match_df)
    
    p1_h2h_wins = sum(1 for _, r in match_df.iterrows() if (r['Spieler1']==p1 and r['Score1']>r['Score2']) or (r['Spieler2']==p1 and r['Score2']>r['Score1']))
    p1_h2h_wr = (p1_h2h_wins / total_h2h * 100) if total_h2h > 0 else 50
    p2_h2h_wr = 100 - p1_h2h_wr if total_h2h > 0 else 50
    
    h2h_bonus_p1 = (p1_h2h_wr - 50) * 1.5 
    h2h_bonus_p2 = (p2_h2h_wr - 50) * 1.5
    
    f1, s1 = get_player_form_and_streak(p1, df)
    f2, s2 = get_player_form_and_streak(p2, df)
    
    score_p1 = max(10, 100 + h2h_bonus_p1 + (f1 * 2) + (s1 * 4))
    score_p2 = max(10, 100 + h2h_bonus_p2 + (f2 * 2) + (s2 * 4))
    
    prob_1 = score_p1 / (score_p1 + score_p2)
    prob_2 = score_p2 / (score_p1 + score_p2)
    
    odds_1 = max(1.01, round(1 / prob_1, 2))
    odds_2 = max(1.01, round(1 / prob_2, 2))
    
    insight = "Ausgeglichenes Matchup."
    if total_h2h == 0: insight = "Keine H2H-Historie."
    elif p1_h2h_wr > 50 and s2 >= 3: insight = f"H2H-Vorteil {p1[:6]} | Momentum {p2[:6]} (+{s2})"
    elif p2_h2h_wr > 50 and s1 >= 3: insight = f"H2H-Vorteil {p2[:6]} | Momentum {p1[:6]} (+{s1})"
    elif f1 > f2 + 4: insight = f"Form-Vorteil {p1[:6]} (NW: +{f1})"
    elif f2 > f1 + 4: insight = f"Form-Vorteil {p2[:6]} (NW: +{f2})"
    elif p1_h2h_wr >= 70: insight = f"H2H-Dominanz {p1[:6]} ({p1_h2h_wr:.0f}%)"
    elif p2_h2h_wr >= 70: insight = f"H2H-Dominanz {p2[:6]} ({p2_h2h_wr:.0f}%)"
    
    return prob_1*100, prob_2*100, odds_1, odds_2, insight

# --- SESSION LOGIK ---
def parse_time(id_str):
    if str(id_str).startswith("LEGACY") or str(id_str).startswith("MANUAL"): return pd.NaT
    try: return pd.to_datetime(id_str, format="%Y%m%dT%H%M%S.%fZ")
    except: return pd.NaT

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
            "WR": f"{wr*100:.0f}%", "Max Streaks": f"+{data['max_w_streak']} / -{data['max_l_streak']}", "Rating (KotH)": round(final_rating, 1)
        })
        
    if not leaderboard: return pd.DataFrame()
    df_lb = pd.DataFrame(leaderboard).sort_values(by="Rating (KotH)", ascending=False).reset_index(drop=True)
    df_lb.index = df_lb.index + 1
    return df_lb

# --- UI & LAYOUT ---
df_comp = get_df_from_sheet(ws_comp)
df_fun = get_df_from_sheet(ws_fun)
df_prof = get_df_from_sheet(ws_prof)

st.sidebar.title("🎮 Clash Analyzer Pro")
st.sidebar.markdown("---")

if st.sidebar.button("🔄 Manueller Sync", use_container_width=True):
    st.sidebar.warning("Nutze deinen lokalen Bot für Live-Daten!")
    
st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ DB Status")
st.sidebar.write(f"Gespeicherte Duelle: {len(df_comp)}")

# Tabs 
tab_dbl, tab_spieler, tab_dbf, tab_nemesis, tab_trends, tab_zeit, tab_sessions, tab_prognose = st.tabs([
    "⚔️ DBL (1v1)", "👤 Spieler", "🎉 DBF (Fun)", "💀 Nemesis", "📈 Trends", "⏱️ Zeit & Ausdauer", "🏆 Sessions", "📊 Prognose"
])

with tab_dbl:
    st.header("Lokal 1v1 Dashboard")
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
                lb_data.append({
                    "Spieler": p[:10],
                    "Spiele": spiele,
                    "Siege": siege,
                    "Niederlagen": niederlagen,
                    "Net-Wins": net_wins,
                    "Winrate (%)": round(winrate, 1)
                })
        
        if lb_data:
            st.subheader("🏆 All-Time Leaderboard")
            df_lb = pd.DataFrame(lb_data).sort_values(by=["Winrate (%)", "Net-Wins"], ascending=[False, False]).reset_index(drop=True)
            df_lb.index = df_lb.index + 1
            df_lb.index.name = "Rang"
            st.dataframe(df_lb, use_container_width=True)

        st.markdown("---")
        
        h2h_df, curr_streak, at_streak = get_h2h_stats_data(df_comp)
        col1, col2 = st.columns(2)
        col1.metric("🔥 Aktuelle Winstreak", f"{curr_streak['count']}x", curr_streak['player'])
        col2.metric("👑 All-Time Rekord", f"{at_streak['count']}x", at_streak['player'])
        st.dataframe(h2h_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")

        if lb_data:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🏁 Race to 200 (Erster bei 200 Siegen)")
                fig_race = px.bar(df_lb, x='Spieler', y='Siege', text_auto=True, color='Spieler', title="Absolute Siege")
                fig_race.update_layout(yaxis=dict(range=[0, 200]), showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
                st.plotly_chart(fig_race, use_container_width=True)
                
            with c2:
                st.subheader("📊 Performance-Vergleich (0 - 100%)")
                fig_wr = px.bar(df_lb, x='Spieler', y='Winrate (%)', text_auto='.1f', color='Spieler', title="Winrate Histogramm")
                fig_wr.update_layout(yaxis=dict(range=[0, 100]), showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
                st.plotly_chart(fig_wr, use_container_width=True)

with tab_spieler:
    st.header("👤 All-Time Spieler Profile")
    cols = st.columns(3)
    for idx, (name, tag) in enumerate(TAGS.items()):
        with cols[idx % 3]:
            st.subheader(f"🛡️ {name}")
            if not df_prof.empty and name in df_prof['Spieler'].values:
                p_data = df_prof[df_prof['Spieler'] == name].iloc[0]
                matches = p_data['Matches']
                wins = p_data['Wins']
                losses = p_data['Losses']
                three_crowns = p_data['Three_Crowns']
                wr_global = (wins / matches * 100) if matches > 0 else 0
                three_crown_rate = (three_crowns / wins * 100) if wins > 0 else 0
                
                st.markdown("**🌍 Globale Account-Stats:**")
                st.write(f"🏆 **Trophäen:** {p_data['Trophies']} (Max: {p_data['Max_Trophies']})")
                st.write(f"⚔️ **Matches:** {matches} | ✅ **Wins:** {wins} | ❌ **Losses:** {losses}")
                st.write(f"📊 **Global WR:** {wr_global:.1f}%")
                st.write(f"👑 **3-Kronen:** {three_crowns} *(Das sind {three_crown_rate:.1f}% aller Siege!)*")
            else:
                st.warning("*(Profil-Daten fehlen. Bot muss laufen!)*")
            
            st.markdown("---")
            
            p_df = df_comp[(df_comp['Spieler1'] == name) | (df_comp['Spieler2'] == name)].sort_values('ID')
            if not p_df.empty:
                st.markdown(f"**📜 Letzte 5 Spiele (vs. Crew):**")
                for _, r in p_df.tail(5).iloc[::-1].iterrows():
                    is_p1 = r['Spieler1'] == name
                    opp = r['Spieler2'] if is_p1 else r['Spieler1']
                    s_me = r['Score1'] if is_p1 else r['Score2']
                    s_opp = r['Score2'] if is_p1 else r['Score1']
                    res_icon = "🟢 Sieg" if s_me > s_opp else ("🔴 Ndl" if s_me < s_opp else "⚪ Remis")
                    st.write(f"{res_icon} vs **{opp}** ({s_me}:{s_opp})")
            
            st.markdown("---")
            
            top_u, top_w = calculate_card_stats(name, df_comp)
            if not top_u.empty:
                st.markdown("**🃏 Meistgespielte Karten:**")
                st.dataframe(top_u, hide_index=True, use_container_width=True)

with tab_dbf:
    st.header("Lokal Fun Dashboard")
    if not df_fun.empty:
        h2h_df, _, _ = get_h2h_stats_data(df_fun)
        st.dataframe(h2h_df, use_container_width=True, hide_index=True)

with tab_nemesis:
    st.header("Kryptonit & Angstgegner")
    if not df_comp.empty:
        nem_df = calc_nemesis_kryptonit(df_comp)
        if not nem_df.empty: st.table(nem_df)

with tab_trends:
    st.header("Interaktive Formkurve (Net-Wins)")
    if not df_comp.empty:
        tf = st.selectbox("Zeitraum:", ["All-Time", "Letzte 15 Spiele", "Letzte 30 Spiele"])
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
    st.header("⏱️ Zeit & Ausdauer (Heatmap)")
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
            
            fig_heat = px.imshow(pivot_data, labels=dict(x="Uhrzeit", y="Wochentag", color="Spiele"), x=list(range(24)), y=days_order, color_continuous_scale="Inferno", aspect="auto", title="🔥 Aktivitäts-Heatmap")
            fig_heat.update_xaxes(dtick=1)
            st.plotly_chart(fig_heat, use_container_width=True)

with tab_sessions:
    st.header("Session Leaderboards")
    if not df_comp.empty:
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
                st.info(f"⏱️ **Dauer der Session:** {dur_str}  |  🎮 **Spiele:** {len(s_df)}")
            
            lb = get_session_leaderboard(s_df)
            if not lb.empty: st.dataframe(lb, use_container_width=True)

with tab_prognose:
    st.header("Live-Quoten & Match-Prognosen")
    
    if df_comp.empty:
        st.warning("Datenbasis nicht ausreichend für Prognosen.")
    else:
        pairs = list(itertools.combinations(TAGS.keys(), 2))
        cols = st.columns(3)
        
        for idx, (p1, p2) in enumerate(pairs):
            with cols[idx % 3]:
                prob1, prob2, odds1, odds2, insight = calc_matchup_odds(p1, p2, df_comp)
                
                # Das HTML muss für Streamlit komplett links anliegen, sonst wird es als Code gewertet!
                st.markdown(f"""
<div style='background-color: #1E1E1E; color: #FFF; padding: 16px; border-radius: 8px; border: 1px solid #333; margin-bottom: 15px; font-family: sans-serif;'>
    <div style='text-align: center; font-weight: 600; font-size: 1.05rem; margin-bottom: 16px; border-bottom: 1px solid #333; padding-bottom: 8px;'>
        {p1[:10]} <span style='color: #777; font-weight: 400; font-size: 0.85rem; margin: 0 5px;'>vs</span> {p2[:10]}
    </div>
    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
        <div style='text-align: left; width: 45%;'>
            <div style='font-size: 1.4rem; font-weight: 700; color: #4CAF50;'>{odds1:.2f}</div>
            <div style='font-size: 0.75rem; color: #888; margin-top: 2px;'>{prob1:.0f}%</div>
        </div>
        <div style='width: 10%; text-align: center; color: #555; font-size: 0.7rem; text-transform: uppercase;'>Quote</div>
        <div style='text-align: right; width: 45%;'>
            <div style='font-size: 1.4rem; font-weight: 700; color: #2196F3;'>{odds2:.2f}</div>
            <div style='font-size: 0.75rem; color: #888; margin-top: 2px;'>{prob2:.0f}%</div>
        </div>
    </div>
    <div style='width: 100%; background-color: #2b2b2b; border-radius: 4px; height: 6px; margin-bottom: 16px; display: flex; overflow: hidden;'>
        <div style='width: {prob1}%; background-color: #4CAF50; height: 100%;'></div>
        <div style='width: {prob2}%; background-color: #2196F3; height: 100%;'></div>
    </div>
    <div style='font-size: 0.75rem; color: #AAA; text-align: center; background-color: #252525; padding: 6px; border-radius: 4px; min-height: 26px; display: flex; align-items: center; justify-content: center;'>
        {insight}
    </div>
</div>
""", unsafe_allow_html=True)
