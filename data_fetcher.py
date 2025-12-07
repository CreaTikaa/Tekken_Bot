import re
import asyncio
from typing import Tuple, List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import aiohttp

async def _dummy_coro():
    await asyncio.sleep(0)
    return None

# ---------------------
# WAVU PARSER
# ---------------------
def parse_wavu_html(html: str, expected_player_name: str = "") -> Tuple[Optional[float], List[Dict]]:
    soup = BeautifulSoup(html, "html5lib")
    rating_mu = None
    mu_elem = soup.select_one(".mu")
    if mu_elem:
        try:
            text = re.sub(r"[^\d\.]", "", mu_elem.text.strip())
            if text: rating_mu = float(text)
        except: pass

    games = []
    rows = soup.select("table tr")
    for row in rows:
        tds = row.find_all("td")
        if len(tds) < 4: continue
        try:
            ts_match = re.search(r'printDateTime\((\d+)\)', str(tds[0]))
            timestamp_unix = int(ts_match.group(1)) if ts_match else 0
            
            left_char = tds[1].select_one(".char").text.strip() if tds[1].select_one(".char") else ""
            right_player = tds[3].select_one(".player a").text.strip() if tds[3].select_one(".player a") else ""
            result_text = tds[2].text.strip()
            
            my_char = left_char
            opponent = right_player
            
            score_parts = result_text.split('-')
            if len(score_parts) == 2:
                p_score, o_score = int(score_parts[0]), int(score_parts[1])
                result = "WIN" if p_score > o_score else "LOSS"
            else:
                result = "UNKNOWN"

            games.append({
                "timestamp_unix": timestamp_unix,
                "result": result,
                "score": result_text,
                "opponent": opponent,
                "opponent_rank": None,
                "my_char": my_char,
                "source": "wavu"
            })
        except Exception: continue
    return rating_mu, games

# ---------------------
# EWGF PARSER
# ---------------------
def parse_ewgf_html(html: str) -> Tuple[Optional[str], List[Dict], Optional[str], Optional[Dict], Optional[Dict]]:
    soup = BeautifulSoup(html, "html5lib")
    rank = None
    main_char = None
    games = []
    matchups = {}
    pentagon = {}

    # 1. Rang et Main Character
    rank_img = soup.find("img", alt=re.compile(r" rank icon$", re.I))
    if rank_img:
        rank = rank_img["alt"].replace(" rank icon", "").strip()

    try:
        char_match = re.search(r'\\?"mainChar\\?":\s*\{\\?"([^"\\]+)', html)
        if char_match:
            main_char = char_match.group(1)
    except Exception as e:
        print(f"Error regex main_char: {e}")

    # 2. EXTRACTION JSON ROBUSTE
    scripts = soup.find_all("script")
    
    for s in scripts:
        if s.string and 'playerStats' in s.string:
            txt = s.string
            idx = txt.find("playerStats")
            if idx == -1: continue
            
            start = txt.find('{', idx)
            if start == -1: continue
            
            balance = 0
            end = -1
            for i in range(start, len(txt)):
                if txt[i] == '{': balance += 1
                elif txt[i] == '}': balance -= 1
                
                if balance == 0:
                    end = i + 1
                    break
            
            if end != -1:
                raw_json = txt[start:end]
                clean_json = raw_json.replace('\\"', '"')
                
                try:
                    import json
                    data = json.loads(clean_json)
                    
                    # --- PARSING ---
                    if not main_char and data.get("mainChar"):
                        main_char = list(data["mainChar"].keys())[0]

                    if main_char and "playedCharacters" in data:
                        char_data = data["playedCharacters"].get(main_char, {})
                        ranked_data = char_data.get("RANKED_BATTLE", {})
                        if "allTimeMatchups" in ranked_data:
                            matchups = ranked_data["allTimeMatchups"]

                    # On essaie de récupérer le pentagone
                    if "statPentagonData" in data:
                        pentagon = data["statPentagonData"]

                    # Extraction des Games
                    # (On extrait toujours les games au cas où ce bloc soit le bon)
                    temp_games = [] 
                    viewer_pid = data.get("playerMetadata", {}).get("polarisId")
                    battles = data.get("battles", [])
                    
                    for b in battles:
                        if b.get("battleType") != "RANKED_BATTLE": continue
                        
                        if b.get("p1PolarisId") == viewer_pid:
                            ws, my, op = 1, "p1", "p2"
                        elif b.get("p2PolarisId") == viewer_pid:
                            ws, my, op = 2, "p2", "p1"
                        else: continue

                        my_c = b.get(f"{my}Char")
                        op_c = b.get(f"{op}Char")
                        opp_n = b.get(f"{op}Name")
                        opp_r = b.get(f"{op}DanRank")
                        r_won = b.get(f"{my}RoundsWon")
                        r_lost = b.get(f"{op}RoundsWon")
                        score = f"{r_won}-{r_lost}"
                        result = "WIN" if b.get("winner") == ws else "LOSS"

                        ts_str = b.get("battleAt")
                        ts_unix = 0
                        if ts_str:
                            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            ts_unix = int(dt.timestamp())

                        temp_games.append({
                            "timestamp_unix": ts_unix,
                            "timestamp_iso": ts_str,
                            "result": result,
                            "score": score,
                            "opponent": opp_n,
                            "opponent_char": op_c,
                            "opponent_rank": opp_r, 
                            "my_char": my_c,
                            "source": "ewgf"
                        })
                    
                    # Si on a trouvé des games dans ce bloc, on les garde
                    if temp_games:
                        games = temp_games

                    # --- CONDITION D'ARRÊT MODIFIÉE ---
                    # On ne s'arrête QUE si on a trouvé le pentagone.
                    # Sinon, on continue de chercher dans les autres scripts !
                    if pentagon:
                        break

                except Exception as e:
                    print(f"JSON Parse Error: {e}")
                    continue

    return rank, games, main_char, matchups, pentagon
# ---------------------
# FETCH BOTH
# ---------------------
async def fetch_html(session, url):
    headers = {"User-Agent": "Mozilla/5.0"}
    async with session.get(url, headers=headers, timeout=20) as resp:
        if resp.status != 200: return None
        return await resp.text()

async def fetch_both_profiles(session, wavu_url=None, ewgf_url=None):
    tasks = []
    tasks.append(fetch_html(session, wavu_url) if wavu_url else _dummy_coro())
    tasks.append(fetch_html(session, ewgf_url) if ewgf_url else _dummy_coro())
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    wavu_html = results[0] if isinstance(results[0], str) else None
    ewgf_html = results[1] if isinstance(results[1], str) else None

    if wavu_html:
        w_rating, w_games = await asyncio.to_thread(parse_wavu_html, wavu_html)
    else:
        w_rating, w_games = (None, [])

    # Modification ici pour récupérer matchups et pentagon
    if ewgf_html:
        e_rank, e_games, main_char, matchups, pentagon = await asyncio.to_thread(parse_ewgf_html, ewgf_html)
    else:
        e_rank, e_games, main_char, matchups, pentagon = (None, [], None, {}, {})

    merged = {}
    all_games = e_games + w_games 
    
    for g in all_games:
        opp_clean = re.sub(r'\W+', '', g['opponent']).lower()
        key = f"{g['timestamp_unix']}_{opp_clean}_{g['score']}"
        if key not in merged:
            merged[key] = g
        else:
            if not merged[key].get('opponent_rank') and g.get('opponent_rank'):
                 merged[key]['opponent_rank'] = g['opponent_rank']

    final_games = sorted(merged.values(), key=lambda x: x['timestamp_unix'], reverse=True)
    # On retourne tout
    return e_rank, w_rating, final_games, main_char, matchups, pentagon