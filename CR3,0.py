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
SHEET_URL = "https://docs.google.com/spreadsheets/d/1SZQhK7TeBRI6DspxVJWU31ul_PGTXNOoxcOwE6rn2u8/edit?gid=66925559#gid=66925559"

API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjhjMzk2MDM1LTgyMzMtNGFhMi04YzVjLTg3NjVmZDliYjE0MSIsImlhdCI6MTc3Nzk4NDU2Niwic3ViIjoiZGV2ZWxvcGVyL2MyYjczNjYyLWE2YjYtNzdkMC00N2I4LTM5YjE0MWYyNzcxOCIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyI5Mi4yMDguMjUuMTIiXSwidHlwZSI6ImNsaWVudCJ9XX0.LG_Q_jELSrMoeRPVVU5saPFnNWBrGbzaaaXtl_4HvKEMd-jDBBldJUpLZXQJ2101_tGsxgQ-3bU5tejtmY3wQg"

# --- GOOGLE SHEETS SETUP ---
@st.cache_resource
def init_google_sheets():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["google_credentials"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SHEET_URL)
    # Jetzt laden wir drei Blätter
    return sheet.worksheet("Karten_Data"), sheet.worksheet("Fun_Data"), sheet.worksheet("Profile_Data")

try:
    ws_comp, ws_fun, ws_prof = init_google_sheets()
except Exception as e:
    st.error(f"Bin kurz ein drehen bre... ({e})")
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

# --- AUTO-SCANNER (Google Sheets Sync) ---
def scan_for_battles():
    df_comp = get_df_from_sheet(ws_comp)
    df_fun = get_df_from_sheet(ws_fun)

    new_comp_rows, new_fun_rows, profile_rows = [], [], []
    known_comp_ids = set(df_comp['ID'].astype(str)) if not df_comp.empty else set()
    known_fun_ids = set(df_fun['ID'].astype(str)) if not df_fun.empty else set()

    for name, tag in TAGS.items():
        # 1. Spieler-Profil abrufen und für die DB speichern
        api_prof = get_api_data("", tag)
        if api_prof:
            profile_rows.append([
                name, 
                api_prof.get('trophies', 0),
                api_prof.get('bestTrophies', 0),
                api_prof.get('battleCount', 0),
                api_prof.get('wins', 0),
                api_prof.get('losses', 0),
                api_prof.get('threeCrownWins', 0)
            ])

        # 2. Kampflog abrufen
        log = get_api_data("battlelog", tag)
        if not log: continue
        for b in log:
            b_id = b.get('battleTime')
            opp_tag = b['opponent'][0].get('tag', '').replace('#', '')
            rival = next((n for n, t in TAGS.items() if t == opp_tag), None)
            
            if rival:
                s1, s2 = b['team'][0]['crowns'], b['opponent'][0]['crowns']
                k1 = ", ".join([c['name'] for c in b['team'][0]['cards']]) if 'cards' in b['team'][0] else ""
                k2 = ", ".join([c['name'] for c in b['opponent'][0]['cards']]) if 'cards' in b['opponent'][0] else ""
                row_data = [b_id, name, rival, s1, s2, k1, k2]

                if b_id not in known_fun_ids:
                    new_fun_rows.append(row_data)
                    known_fun_ids.add(b_id)

                is_solo = len(b.get('team', [])) == 1 and len(b.get('opponent', [])) == 1
                is_own_deck = b.get('deckSelection', 'collection') == 'collection'
                if is_solo and is_own_deck and b_id not in known_comp_ids:
                    new_comp_rows.append(row_data)
                    known_comp_ids.add(b_id)

    # In Tabellen schreiben
    if new_comp_rows: ws_comp.append_rows(new_comp_rows)
    if new_fun_rows: ws_fun.append_rows(new_fun_rows)
    if profile_rows:
        ws_prof.clear()
        ws_prof.append_row(["Spieler", "Trophies", "Max_Trophies", "Matches", "Wins", "Losses", "Three_Crowns"])
        ws_prof.append_rows(profile_rows)
    
    return len(new_comp_rows), len(new_fun_rows)

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
        
    if not leaderboard:
        return pd.DataFrame()
        
    df_lb = pd.DataFrame(leaderboard).sort_values(by="Rating (KotH)", ascending=False).reset_index(drop=True)
    df_lb.index = df_lb.index + 1
    return df_lb

# --- UI & LAYOUT ---
df_comp = get_df_from_sheet(ws_comp)
df_fun = get_df_from_sheet(ws_fun)
df_prof = get_df_from_sheet(ws_prof)

st.sidebar.title("🎮 Clash Analyzer Pro")
st.sidebar.markdown("---")

if st.sidebar.button("🔄 Neue Spiele suchen", use_container_width=True, type="primary"):
    with st.spinner("Scanne API & synchronisiere mit Google Sheets..."):
        c, f = scan_for_battles()
        st.sidebar.success(f"{c} Kompetitiv / {f} Fun neu in der Tabelle!")
        st.rerun()

st.sidebar.markdown(f"*Letztes Update: {datetime.now().strftime('%H:%M:%S')}*")
st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ DB Status")
st.sidebar.write(f"Gespeicherte Duelle: {len(df_comp)}")

# Tabs 
tab_dbl, tab_spieler, tab_dbf, tab_nemesis, tab_trends, tab_zeit, tab_sessions, tab_orakel = st.tabs([
    "⚔️ DBL (1v1)", "👤 Spieler", "🎉 DBF (Fun)", "💀 Nemesis", "📈 Trends", "⏱️ Zeit & Ausdauer", "🏆 Sessions", "🔮 Orakel"
])

with tab_dbl:
    st.header("Lokal 1v1 Dashboard")
    if not df_comp.empty:
        # 1. DATEN FÜR LEADERBOARD BERECHNEN
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
        
        # 2. LEADERBOARD TABELLE ANZEIGEN
        if lb_data:
            st.subheader("🏆 All-Time Leaderboard")
            df_lb = pd.DataFrame(lb_data)
            df_lb = df_lb.sort_values(by=["Winrate (%)", "Net-Wins"], ascending=[False, False]).reset_index(drop=True)
            df_lb.index = df_lb.index + 1
            df_lb.index.name = "Rang"
            st.dataframe(df_lb, use_container_width=True)

        st.markdown("---")
        
        # 3. HEAD-TO-HEAD & STREAKS
        h2h_df, curr_streak, at_streak = get_h2h_stats_data(df_comp)
        col1, col2 = st.columns(2)
        col1.metric("🔥 Aktuelle Winstreak", f"{curr_streak['count']}x", curr_streak['player'])
        col2.metric("👑 All-Time Rekord", f"{at_streak['count']}x", at_streak['player'])
        st.dataframe(h2h_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")

        # 4. RACE TO 200 (ABSOLUTE SIEGE)
        if lb_data:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🏁 Race to 200 (Erster bei 200 Siegen)")
                fig_race = px.bar(
                    df_lb, 
                    x='Spieler', 
                    y='Siege', 
                    text_auto=True, 
                    color='Spieler',
                    title="Absolute Siege (Ziel: 200)"
                )
                fig_race.update_layout(yaxis=dict(range=[0, 200]), showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
                st.plotly_chart(fig_race, use_container_width=True)
                
            # 5. HISTOGRAMM (WINS x / 100)
            with c2:
                st.subheader("📊 Performance-Vergleich (0 - 100%)")
                fig_wr = px.bar(
                    df_lb, 
                    x='Spieler', 
                    y='Winrate (%)', 
                    text_auto='.1f', 
                    color='Spieler',
                    title="Winrate Histogramm"
                )
                fig_wr.update_layout(yaxis=dict(range=[0, 100]), showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
                st.plotly_chart(fig_wr, use_container_width=True)
    else:
        st.info("Noch keine Daten in der Google Tabelle gefunden.")

with tab_spieler:
    st.header("👤 All-Time Spieler Profile")
    cols = st.columns(3)
    for idx, (name, tag) in enumerate(TAGS.items()):
        with cols[idx % 3]:
            st.subheader(f"🛡️ {name}")
            
            # 1. GLOBALE API STATISTIKEN (Jetzt aus Google Sheets!)
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
                st.warning("*(Profil noch nicht in der Datenbank. Bitte einmal am PC auf 'Neue Spiele suchen' klicken!)*")
            
            st.markdown("---")
            
            # 2. LETZTE 5 SPIELE KAMPFLOG (LOKAL)
            p_df = df_comp[(df_comp['Spieler1'] == name) | (df_comp['Spieler2'] == name)].sort_values('ID')
            if not p_df.empty:
                st.markdown(f"**📜 Letzte 5 Spiele (vs. Crew):**")
                # Wir nehmen die letzten 5 Einträge und drehen sie um (neueste zuerst)
                for _, r in p_df.tail(5).iloc[::-1].iterrows():
                    is_p1 = r['Spieler1'] == name
                    opp = r['Spieler2'] if is_p1 else r['Spieler1']
                    s_me = r['Score1'] if is_p1 else r['Score2']
                    s_opp = r['Score2'] if is_p1 else r['Score1']
                    
                    if s_me > s_opp:
                        res_icon = "🟢 Sieg"
                    elif s_me < s_opp:
                        res_icon = "🔴 Ndl"
                    else:
                        res_icon = "⚪ Remis"
                        
                    st.write(f"{res_icon} vs **{opp}** ({s_me}:{s_opp})")
            
            st.markdown("---")
            
            # 3. KARTEN STATISTIKEN
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
            
            day_map = {
                "Monday": "Montag", "Tuesday": "Dienstag", "Wednesday": "Mittwoch", 
                "Thursday": "Donnerstag", "Friday": "Freitag", "Saturday": "Samstag", "Sunday": "Sonntag"
            }
            df_time['Wochentag'] = df_time['Wochentag'].map(day_map)
            
            heatmap_data = df_time.groupby(['Wochentag', 'Stunde']).size().reset_index(name='Spiele')
            pivot_data = heatmap_data.pivot(index='Wochentag', columns='Stunde', values='Spiele').fillna(0)
            
            # Raster auffüllen (alle Tage und 24 Stunden erzwingen)
            days_order = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
            for d in days_order:
                if d not in pivot_data.index: pivot_data.loc[d] = 0
            pivot_data = pivot_data.reindex(days_order)
            
            for h in range(24):
                if h not in pivot_data.columns: pivot_data[h] = 0
            pivot_data = pivot_data[list(range(24))]
            
            fig_heat = px.imshow(
                pivot_data, 
                labels=dict(x="Uhrzeit", y="Wochentag", color="Spiele"), 
                x=list(range(24)),
                y=days_order,
                color_continuous_scale="Inferno", 
                aspect="auto",
                title="🔥 Aktivitäts-Heatmap (Wann zockt ihr am meisten?)"
            )
            fig_heat.update_xaxes(dtick=1)
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("Spiele haben noch keine korrekten Zeitstempel (Die alten manuellen CSV-Daten haben keine Uhrzeit).")
    else:
        st.info("Keine Daten vorhanden.")

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

with tab_orakel:
    st.header("🔮 Das Match-Orakel")
    cols = st.columns(2)
    p1 = cols[0].selectbox("Herausforderer 1", list(TAGS.keys()), index=0)
    p2 = cols[1].selectbox("Herausforderer 2", list(TAGS.keys()), index=1 if len(TAGS)>1 else 0)
    if st.button("Prognose Berechnen", type="primary") and p1 != p2:
        st.success("Berechnung läuft auf Basis der neuen DB!")
