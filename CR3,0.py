import streamlit as st
import pandas as pd
import requests
import itertools
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Clash Analyzer Pro", page_icon="🏆", layout="wide")

# --- KONFIGURATION ---
DB_FILE = "clash_karten_data.csv"      
DB_FUN_FILE = "clash_fun_data.csv"     
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjhjMzk2MDM1LTgyMzMtNGFhMi04YzVjLTg3NjVmZDliYjE0MSIsImlhdCI6MTc3Nzk4NDU2Niwic3ViIjoiZGV2ZWxvcGVyL2MyYjczNjYyLWE2YjYtNzdkMC00N2I4LTM5YjE0MWYyNzcxOCIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyI5Mi4yMDguMjUuMTIiXSwidHlwZSI6ImNsaWVudCJ9XX0.LG_Q_jELSrMoeRPVVU5saPFnNWBrGbzaaaXtl_4HvKEMd-jDBBldJUpLZXQJ2101_tGsxgQ-3bU5tejtmY3wQg"
OLD_TAGS = {"resan": "R902QGYCP", "gooterplayer": "VCGLJU02", "Jörg": "YY89R9L9G"}

# --- API LOGIK ---
@st.cache_data(ttl=60)
def get_api_data(endpoint, tag):
    url = f"https://api.clashroyale.com/v1/players/%23{tag}/{endpoint}" if endpoint else f"https://api.clashroyale.com/v1/players/%23{tag}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        return res.json() if res.status_code == 200 else None
    except: return None

# --- INITIALISIERUNG ---
@st.cache_resource
def init_tags():
    tags, mapping = {}, {}
    for old_initial, tag in OLD_TAGS.items():
        profile = get_api_data("", tag)
        if profile and 'name' in profile:
            real_name = profile['name']
            tags[real_name] = tag
            mapping[old_initial] = real_name
        else:
            tags[old_initial] = tag
            mapping[old_initial] = old_initial
    return tags, mapping

TAGS, NAME_MAPPING = init_tags()

def init_and_migrate_db(file_path):
    columns = ["ID", "Spieler1", "Spieler2", "Score1", "Score2", "Karten1", "Karten2"]
    if not os.path.exists(file_path): pd.DataFrame(columns=columns).to_csv(file_path, index=False)
    else:
        try:
            df = pd.read_csv(file_path)
            changed = False
            if "ID" not in df.columns:
                df.insert(0, "ID", "LEGACY_" + df.index.astype(str))
                changed = True
            if not df.empty:
                s1_orig = df['Spieler1'].copy()
                df['Spieler1'] = df['Spieler1'].replace(NAME_MAPPING)
                df['Spieler2'] = df['Spieler2'].replace(NAME_MAPPING)
                if not df['Spieler1'].equals(s1_orig): changed = True
            if changed: df.to_csv(file_path, index=False)
        except: pass

init_and_migrate_db(DB_FILE)
init_and_migrate_db(DB_FUN_FILE)

# --- AUTO-SCANNER ---
def scan_for_battles():
    try: df_comp = pd.read_csv(DB_FILE)
    except: df_comp = pd.DataFrame(columns=["ID", "Spieler1", "Spieler2", "Score1", "Score2", "Karten1", "Karten2"])
    try: df_fun = pd.read_csv(DB_FUN_FILE)
    except: df_fun = pd.DataFrame(columns=["ID", "Spieler1", "Spieler2", "Score1", "Score2", "Karten1", "Karten2"])

    new_comp, new_fun = 0, 0
    known_comp_ids, known_fun_ids = set(df_comp['ID'].astype(str)), set(df_fun['ID'].astype(str))

    for name, tag in TAGS.items():
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
                row_df = pd.DataFrame([{"ID": b_id, "Spieler1": name, "Spieler2": rival, "Score1": s1, "Score2": s2, "Karten1": k1, "Karten2": k2}])

                if b_id not in known_fun_ids:
                    df_fun = pd.concat([df_fun, row_df], ignore_index=True)
                    known_fun_ids.add(b_id); new_fun += 1

                is_solo = len(b.get('team', [])) == 1 and len(b.get('opponent', [])) == 1
                is_own_deck = b.get('deckSelection', 'collection') == 'collection'
                if is_solo and is_own_deck and b_id not in known_comp_ids:
                    df_comp = pd.concat([df_comp, row_df], ignore_index=True)
                    known_comp_ids.add(b_id); new_comp += 1

    df_comp.to_csv(DB_FILE, index=False)
    df_fun.to_csv(DB_FUN_FILE, index=False)
    return new_comp, new_fun

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
        
    # --- HIER IST DER SICHERHEITS-CHECK ---
    if not leaderboard:
        return pd.DataFrame()
        
    df_lb = pd.DataFrame(leaderboard).sort_values(by="Rating (KotH)", ascending=False).reset_index(drop=True)
    df_lb.index = df_lb.index + 1
    return df_lb

# --- UI & LAYOUT ---
try: df_comp = pd.read_csv(DB_FILE)
except: df_comp = pd.DataFrame()
try: df_fun = pd.read_csv(DB_FUN_FILE)
except: df_fun = pd.DataFrame()

# Sidebar
st.sidebar.title("🎮 Clash Analyzer Pro")
st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ Debug Info (System-Röntgen)")
st.sidebar.write(f"Gefundene Spiele in DB: {len(df_comp)}")
st.sidebar.write(f"Eingestellte Such-Namen: {list(TAGS.keys())}")
if not df_comp.empty:
    st.sidebar.write("Echte Namen in der Datenbank:")
    st.sidebar.write(df_comp['Spieler1'].unique())
if st.sidebar.button("🔄 Livedaten Synchronisieren", use_container_width=True, type="primary"):
    with st.spinner("Frage Supercell-Server ab..."):
        c, f = scan_for_battles()
        st.sidebar.success(f"{c} Kompetitiv / {f} Fun Matches importiert.")
        st.rerun()

st.sidebar.markdown(f"*Letztes Update: {datetime.now().strftime('%H:%M:%S')}*")

# Tabs inkl. neuem Orakel Tab
tab_dbl, tab_spieler, tab_dbf, tab_nemesis, tab_trends, tab_sessions, tab_orakel = st.tabs([
    "⚔️ DBL (1v1)", "👤 Spieler", "🎉 DBF (Fun)", "💀 Nemesis", "📈 Trends", "🏆 Sessions", "🔮 Orakel"
])

with tab_dbl:
    st.header("Lokal 1v1 Dashboard")
    if not df_comp.empty:
        h2h_df, curr_streak, at_streak = get_h2h_stats_data(df_comp)
        col1, col2 = st.columns(2)
        col1.metric("Aktuelle Winstreak", f"{curr_streak['count']}x", curr_streak['player'])
        col2.metric("All-Time Rekord", f"{at_streak['count']}x", at_streak['player'])
        st.dataframe(h2h_df, use_container_width=True, hide_index=True)
        
        wr_data = []
        for p in TAGS.keys():
            p_df = df_comp[(df_comp['Spieler1'] == p) | (df_comp['Spieler2'] == p)]
            w = sum(1 for _, r in p_df.iterrows() if (r['Spieler1']==p and r['Score1']>r['Score2']) or (r['Spieler2']==p and r['Score2']>r['Score1']))
            if len(p_df) > 0: wr_data.append({"Spieler": p[:10], "Winrate (%)": round((w/len(p_df)*100), 1)})
        if wr_data:
            fig = px.bar(wr_data, x='Spieler', y='Winrate (%)', title="All-Time 1v1 Winrates", text_auto=True, color='Spieler')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine kompetitiven Duelle gefunden.")

with tab_spieler:
    st.header("Spieler Profile")
    cols = st.columns(3)
    for idx, (name, tag) in enumerate(TAGS.items()):
        with cols[idx % 3]:
            st.subheader(name[:10])
            api = get_api_data("", tag)
            if api:
                st.write(f"🏆 **Trophäen:** {api.get('trophies', 0)} (Rekord: {api.get('bestTrophies', 0)})")
                st.write(f"⚔️ **Siege:** {api.get('wins',0)} | **Ndl:** {api.get('losses',0)}")
            
            top_u, top_w = calculate_card_stats(name, df_comp)
            if not top_u.empty:
                st.markdown("**Meistgespielte Karten (Lokal):**")
                st.dataframe(top_u, hide_index=True, use_container_width=True)
                st.markdown("**Beste Winrate (Lokal):**")
                st.dataframe(top_w, hide_index=True, use_container_width=True)

with tab_dbf:
    st.header("Lokal Fun Dashboard")
    if not df_fun.empty:
        h2h_df, _, _ = get_h2h_stats_data(df_fun)
        st.dataframe(h2h_df, use_container_width=True, hide_index=True)
    else:
        st.info("Keine Fun-Matches gefunden.")

with tab_nemesis:
    st.header("Kryptonit & Angstgegner")
    if not df_comp.empty:
        nem_df = calc_nemesis_kryptonit(df_comp)
        st.table(nem_df)

with tab_trends:
    st.header("Interaktive Formkurve (Net-Wins)")
    if not df_comp.empty:
        c1, c2 = st.columns(2)
        tf = c1.selectbox("Zeitraum:", ["All-Time", "Letzte 15 Spiele", "Letzte 30 Spiele"])
        show_ma = c2.checkbox("Gleitenden Durchschnitt anzeigen (Glättung)")

        trend_data = []
        for p in TAGS.keys():
            p_df = df_comp[(df_comp['Spieler1'] == p) | (df_comp['Spieler2'] == p)].sort_values('ID')
            if tf == "Letzte 15 Spiele": p_df = p_df.tail(15)
            elif tf == "Letzte 30 Spiele": p_df = p_df.tail(30)
            
            net_wins = 0
            for i, r in p_df.iterrows():
                is_p1 = (r['Spieler1'] == p)
                p_won = (r['Score1'] > r['Score2']) if is_p1 else (r['Score2'] > r['Score1'])
                opp = r['Spieler2'] if is_p1 else r['Spieler1']
                net_wins += (1 if p_won else -1)
                trend_data.append({"Spieler": p[:10], "Match-Nr": len([d for d in trend_data if d['Spieler']==p[:10]])+1, 
                                   "Net-Wins": net_wins, "Gegner": opp[:10], "Resultat": "Sieg" if p_won else "Niederlage"})
        
        tdf = pd.DataFrame(trend_data)
        if not tdf.empty:
            fig = px.line(tdf, x="Match-Nr", y="Net-Wins", color="Spieler", markers=True, 
                          hover_data=["Resultat", "Gegner"], template="plotly_white")
            if show_ma:
                for p in tdf['Spieler'].unique():
                    ma = tdf[tdf['Spieler'] == p]['Net-Wins'].rolling(window=3, min_periods=1).mean()
                    fig.add_trace(go.Scatter(x=tdf[tdf['Spieler']==p]['Match-Nr'], y=ma, mode='lines', 
                                             line=dict(dash='dash'), name=f"{p} (Trend)", opacity=0.5))
            st.plotly_chart(fig, use_container_width=True)

with tab_sessions:
    st.header("Session Leaderboards")
    if not df_comp.empty:
        sessions = build_sessions(df_comp)
        if sessions:
            selected_s = st.selectbox("Wähle eine Session:", list(sessions.keys()))
            s_df = sessions[selected_s]
            
            s_df['Time'] = s_df['ID'].apply(parse_time)
            s_df_valid = s_df.dropna(subset=['Time']).sort_values('Time')
            if not s_df_valid.empty:
                dur = (s_df_valid['Time'].iloc[-1] + timedelta(minutes=3)) - s_df_valid['Time'].iloc[0]
                h, r = divmod(dur.total_seconds(), 3600)
                m, s = divmod(r, 60)
                dur_str = f"{int(h)}h {int(m)}m {int(s)}s" if h>0 else (f"{int(m)}m {int(s)}s" if m>0 else f"{int(s)}s")
                st.info(f"⏱️ **Dauer:** {dur_str}  |  🎮 **Spiele:** {len(s_df)}")
            
            lb = get_session_leaderboard(s_df)
            st.dataframe(lb, use_container_width=True)
        else:
            st.warning("Noch keine Sessions (mit mind. 2 Spielen) gefunden.")

# --- DAS NEUE ORAKEL ---
with tab_orakel:
    st.header("🔮 Das Match-Orakel")
    st.markdown("Berechne die statistische Wahrscheinlichkeit für das nächste Aufeinandertreffen basierend auf **historischer Dominanz (60%)** und **aktuellem Momentum der letzten 10 Spiele (40%)**.")

    cols = st.columns(2)
    p1 = cols[0].selectbox("Herausforderer 1", list(TAGS.keys()), index=0)
    p2 = cols[1].selectbox("Herausforderer 2", list(TAGS.keys()), index=1)

    if p1 == p2:
        st.warning("Bitte wähle zwei unterschiedliche Spieler aus.")
    elif not df_comp.empty:
        if st.button("⚡ Prognose Berechnen", use_container_width=True, type="primary"):
            
            # 1. Historie abrufen
            h2h = df_comp[((df_comp['Spieler1'] == p1) & (df_comp['Spieler2'] == p2)) | ((df_comp['Spieler1'] == p2) & (df_comp['Spieler2'] == p1))]
            if len(h2h) == 0:
                hist_w1 = 0.5 
            else:
                w1 = sum(1 for _, r in h2h.iterrows() if (r['Spieler1']==p1 and r['Score1']>r['Score2']) or (r['Spieler2']==p1 and r['Score2']>r['Score1']))
                hist_w1 = w1 / len(h2h)

            # 2. Momentum berechnen (Die letzten 10 Spiele beider Spieler)
            def get_recent_wr(p, n=10):
                pdf = df_comp[(df_comp['Spieler1'] == p) | (df_comp['Spieler2'] == p)].sort_values('ID').tail(n)
                if len(pdf) == 0: return 0.5
                wins = sum(1 for _, r in pdf.iterrows() if (r['Spieler1']==p and r['Score1']>r['Score2']) or (r['Spieler2']==p and r['Score2']>r['Score1']))
                return wins / len(pdf)

            mom_p1 = get_recent_wr(p1)
            mom_p2 = get_recent_wr(p2)

            if mom_p1 + mom_p2 == 0: rel_mom = 0.5
            else: rel_mom = mom_p1 / (mom_p1 + mom_p2)

            # 3. Der Master-Algorithmus (60/40)
            prob_p1 = (0.6 * hist_w1) + (0.4 * rel_mom)
            prob_p2 = 1.0 - prob_p1

            st.markdown("---")
            res_col1, res_col2 = st.columns(2)
            res_col1.metric(f"Siegwahrscheinlichkeit: {p1[:10]}", f"{prob_p1*100:.1f}%", f"Historie: {hist_w1*100:.0f}% | Letzte 10 Spiele: {mom_p1*100:.0f}% WR")
            res_col2.metric(f"Siegwahrscheinlichkeit: {p2[:10]}", f"{prob_p2*100:.1f}%", f"Historie: {(1-hist_w1)*100:.0f}% | Letzte 10 Spiele: {mom_p2*100:.0f}% WR", delta_color="inverse")

            # 4. Tachometer Visualisierung (Gauge Chart)
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = prob_p1 * 100,
                number = {'suffix': "%", 'font': {'size': 40}},
                title = {'text': f"Vorteil für {p1[:10]}", 'font': {'size': 24}},
                gauge = {
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': "rgba(0,0,0,0)"}, 
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "gray",
                    'steps': [
                        {'range': [0, 50], 'color': "#e74c3c"},     # Rot für P2
                        {'range': [50, 100], 'color': "#2ecc71"}],  # Grün für P1
                    'threshold': {
                        'line': {'color': "black", 'width': 5},
                        'thickness': 0.75,
                        'value': prob_p1 * 100}
                }
            ))
            fig_gauge.update_layout(height=350, margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig_gauge, use_container_width=True)

            # 5. Orakel-Spruch
            if prob_p1 > 0.65: st.success(f"🔮 **Fazit:** {p1} ist der klare Favorit. {p2} braucht ein Wunder (oder ein perfektes Konter-Deck).")
            elif prob_p1 < 0.35: st.error(f"🔮 **Fazit:** {p2} ist aktuell kaum zu stoppen. Schweres Matchup für {p1}.")
            else: st.warning("🔮 **Fazit:** Ein absoluter Thriller! Die Quoten stehen 50:50. Hier entscheidet die Tagesform.")
