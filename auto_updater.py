import time
import requests
import gspread
from datetime import datetime
import os
import pandas as pd
import json
from google.oauth2.service_account import Credentials

print("Starte Clash Analyzer Ghost-Bot (Big Data Edition)...")

# --- KONFIGURATION ---
TAGS = {
    "resan": "R902QGYCP",
    "gooterplayer": "VCGLJU02",
    "Jörg": "YY89R9L9G",
    "Flexus": "QUJC02U2L"  # <-- HIER IST DIE NULL KORRIGIERT!
}

SHEET_URL = "https://docs.google.com/spreadsheets/d/1SZQhK7TeBRI6DspxVJWU31ul_PGTXNOoxcOwE6rn2u8/edit?gid=641247476#gid=641247476"

# --- SPALTEN-SCHEMA (additiv erweitert) ---
GLOBAL_HEADER = ["ID_Unique", "Time_ID", "Spieler", "Opponent", "Score_Me", "Score_Opp", "Karten",
                 "Karten_Opp", "TrophyChange", "StartTrophies", "GameMode", "Type", "ElixirLeaked",
                 "PrincessHP", "KingHP"]
PROFILE_HEADER = ["Spieler", "Trophies", "Max_Trophies", "Matches", "Wins", "Losses", "Three_Crowns",
                  "ExpLevel", "WinStreak", "LeagueTrophies", "BestSeasonTrophies"]
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjM0MGI5OTVhLTg2MmEtNGUwOC1hNWM2LThhNzgyYmE5ZjI5NiIsImlhdCI6MTc4MDc0MjU0NSwic3ViIjoiZGV2ZWxvcGVyL2MyYjczNjYyLWE2YjYtNzdkMC00N2I4LTM5YjE0MWYyNzcxOCIsInNjb3BlcyI6WyJyb3lhbGUiXSwibGltaXRzIjpbeyJ0aWVyIjoiZGV2ZWxvcGVyL3NpbHZlciIsInR5cGUiOiJ0aHJvdHRsaW5nIn0seyJjaWRycyI6WyI5Mi4yMDguMjEuMjE4Il0sInR5cGUiOiJjbGllbnQifV19.W748jBxxPdxUGrrg95fH43GTX2oRGvDfYEVjTLJLPEPbepi_J7AjdwGOvlkq4BnAqcmK6RdJrNVKA4iK1VwePA"


aktueller_ordner = os.path.dirname(os.path.abspath(__file__))
schluessel_pfad = os.path.join(aktueller_ordner, 'credentials.json.json')

print("Verbinde mit Google Sheets...")
try:
    gc = gspread.service_account(filename=schluessel_pfad)
    sheet = gc.open_by_url(SHEET_URL)
    ws_comp = sheet.worksheet("Karten_Data")
    ws_fun = sheet.worksheet("Fun_Data")
    ws_prof = sheet.worksheet("Profile_Data")
    ws_global = sheet.worksheet("Global_Data")
    # Global_Data-Header additiv sicherstellen (überschreibt nur Zeile 1, keine Datenzeilen)
    try:
        head = ws_global.row_values(1)
        if head[:len(GLOBAL_HEADER)] != GLOBAL_HEADER:
            ws_global.update(values=[GLOBAL_HEADER], range_name="A1")
            print("ℹ️ Global_Data-Header um neue Spalten ergänzt.")
    except Exception as e:
        print(f"⚠️ Header-Check Global_Data fehlgeschlagen: {e}")
    print("✅ Verbindung erfolgreich!")
except Exception as e:
    print(f"❌ Fehler! Genaue Fehlermeldung: {e}")
    exit()

def get_api_data(endpoint, tag):
    url = f"https://api.clashroyale.com/v1/players/%23{tag}/{endpoint}" if endpoint else f"https://api.clashroyale.com/v1/players/%23{tag}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code != 200:
            print(f"   ❌ API Fehler {res.status_code}: {res.text[:150]}")
            return None
        return res.json()
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return None
    
def scan_for_battles():
    print("\n--- Starte neuen Scan-Durchlauf ---")
    df_comp = pd.DataFrame(ws_comp.get_all_records() or [])
    df_fun = pd.DataFrame(ws_fun.get_all_records() or [])
    df_global = pd.DataFrame(ws_global.get_all_records() or [])

    new_comp_rows, new_fun_rows, new_global_rows, profile_rows = [], [], [], []
    known_comp_ids = set(df_comp['ID'].astype(str)) if not df_comp.empty else set()
    known_fun_ids = set(df_fun['ID'].astype(str)) if not df_fun.empty else set()
    known_global_ids = set(df_global['ID_Unique'].astype(str)) if not df_global.empty else set()

    # HIER IST DIE ECHTE SCHLEIFE DES BOTS
    for name, tag in TAGS.items():
        print(f"🤖 Lade Profil von {name} (Tag: {tag})...")
        
        api_prof = get_api_data("", tag)
        if api_prof:
            print(f"   ✅ Profil geladen!")
            ls = api_prof.get('leagueStatistics') or {}
            league_cur = (ls.get('currentSeason') or {}).get('trophies', '')
            league_best = (ls.get('bestSeason') or {}).get('trophies', '')
            profile_rows.append([
                name, api_prof.get('trophies', 0), api_prof.get('bestTrophies', 0),
                api_prof.get('battleCount', 0), api_prof.get('wins', 0),
                api_prof.get('losses', 0), api_prof.get('threeCrownWins', 0),
                api_prof.get('expLevel', 0), api_prof.get('currentWinLoseStreak', 0),
                league_cur, league_best
            ])

        log = get_api_data("battlelog", tag)
        if not log: continue
        
        for b in log:
            if 'team' not in b or 'opponent' not in b: continue
            
            b_id = b.get('battleTime')
            unique_global_id = f"{b_id}_{name}"

            team = b['team'][0]
            opp = b['opponent'][0]
            opp_tag = opp.get('tag', '').replace('#', '')
            opp_name = opp.get('name', 'Unbekannt')
            my_cr = team.get('crowns', 0)
            op_cr = opp.get('crowns', 0)

            my_cards_str = ", ".join([c['name'] for c in team.get('cards', [])])
            op_cards_str = ", ".join([c['name'] for c in opp.get('cards', [])])

            game_mode = (b.get('gameMode') or {}).get('name', '')
            princess_hp = "/".join(str(x) for x in (team.get('princessTowersHitPoints') or []))

            # 1. Speichern in Global Data (Für alle Spiele) – volles Schema
            if unique_global_id not in known_global_ids:
                new_global_rows.append([
                    unique_global_id, b_id, name, opp_name, my_cr, op_cr, my_cards_str,
                    op_cards_str, team.get('trophyChange', ''), team.get('startingTrophies', ''),
                    game_mode, b.get('type', ''), team.get('elixirLeaked', ''),
                    princess_hp, team.get('kingTowerHitPoints', '')
                ])
                known_global_ids.add(unique_global_id)

            # 2. Prüfen auf Crew-Matches (1v1 DBL oder Fun)
            rival = next((n for n, t in TAGS.items() if t == opp_tag), None)
            if rival:
                print(f"   🎯 CREW-MATCH gefunden: {name} vs {rival} ({b_id})")
            if rival:
                row_data = [b_id, name, rival, my_cr, op_cr, my_cards_str, op_cards_str]

                if b_id not in known_fun_ids:
                    new_fun_rows.append(row_data)
                    known_fun_ids.add(b_id)

                is_solo = len(b.get('team', [])) == 1 and len(b.get('opponent', [])) == 1
                is_own_deck = b.get('deckSelection', '') in ('collection', 'own', '')
                if is_solo and is_own_deck and b_id not in known_comp_ids:
                    new_comp_rows.append(row_data)
                    known_comp_ids.add(b_id)

    if new_comp_rows: ws_comp.append_rows(new_comp_rows)
    if new_fun_rows: ws_fun.append_rows(new_fun_rows)
    if new_global_rows: ws_global.append_rows(new_global_rows)
    
    if profile_rows:
        ws_prof.clear()
        ws_prof.append_row(PROFILE_HEADER)
        ws_prof.append_rows(profile_rows)
    
    return len(new_comp_rows), len(new_global_rows)

print("Starte Endlos-Schleife (alle 60 Sekunden)...\n")

while True:
    now = datetime.now().strftime('%H:%M:%S')
    try:
        c, g = scan_for_battles()
        print(f"[{now}] Update erfolgreich! {c} 1v1 / {g} Globale Spiele neu erfasst.")
    except Exception as e:
        print(f"[{now}] Fehler beim Scan: {e}")
        
    time.sleep(10)