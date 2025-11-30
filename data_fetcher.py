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
def parse_ewgf_html(html: str) -> Tuple[Optional[str], List[Dict], Optional[str]]:
    soup = BeautifulSoup(html, "html5lib")
    rank = None
    main_char = None
    games = []

    rank_img = soup.find("img", alt=re.compile(r" rank icon$", re.I))
    if rank_img:
        rank = rank_img["alt"].replace(" rank icon", "").strip()

    try:
        # Recherche pattern: \"mainChar\":{\"NomDuPerso\" vu que ça marchait pas autrement
        char_match = re.search(r'\\?"mainChar\\?":\s*\{\\?"([^"\\]+)', html)
        if char_match:
            main_char = char_match.group(1)
    except Exception as e:
        print(f"Error regex main_char: {e}")

    script = soup.find("script", string=re.compile("playerStats"))
    if script and script.string:
        import json
        m = re.search(r'playerStats\":({.+?})\}\]', script.string, re.DOTALL)
        if m:
            try:
                data_str = m.group(1) + "}"
                data = json.loads(data_str)

                if not main_char and data.get("mainChar"):
                    main_char = list(data["mainChar"].keys())[0]

                viewer_pid = data.get("playerMetadata", {}).get("polarisId")
                battles = data.get("battles", [])
                
                for b in battles:
                    if b.get("battleType") != "RANKED_BATTLE": continue

                    if b.get("p1PolarisId") == viewer_pid:
                        my_side, opp_side = "p1", "p2"
                        winner_side = 1
                    elif b.get("p2PolarisId") == viewer_pid:
                        my_side, opp_side = "p2", "p1"
                        winner_side = 2
                    else: continue

                    my_char = b.get(f"{my_side}Char")
                    opponent = b.get(f"{opp_side}Name")
                    opponent_rank = b.get(f"{opp_side}DanRank")

                    my_rounds = b.get(f"{my_side}RoundsWon")
                    opp_rounds = b.get(f"{opp_side}RoundsWon")
                    score = f"{my_rounds}-{opp_rounds}"
                    result = "WIN" if b.get("winner") == winner_side else "LOSS"

                    ts_str = b.get("battleAt")
                    ts_unix = 0
                    if ts_str:
                        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        ts_unix = int(dt.timestamp())

                    games.append({
                        "timestamp_unix": ts_unix,
                        "timestamp_iso": ts_str,
                        "result": result,
                        "score": score,
                        "opponent": opponent,
                        "opponent_rank": opponent_rank, 
                        "my_char": my_char,
                        "source": "ewgf"
                    })
            except Exception as e:
                print(f"EWGF JSON Error: {e}")

    return rank, games, main_char

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

    w_rating, w_games = parse_wavu_html(wavu_html) if wavu_html else (None, [])
    e_rank, e_games, main_char = parse_ewgf_html(ewgf_html) if ewgf_html else (None, [], None)

    merged = {}
    all_games = e_games + w_games 
    for g in all_games:
        key = f"{g['timestamp_unix']}_{g['opponent']}_{g['score']}"
        if key not in merged:
            merged[key] = g
        else:
            if not merged[key].get('opponent_rank') and g.get('opponent_rank'):
                 merged[key]['opponent_rank'] = g['opponent_rank']

    final_games = sorted(merged.values(), key=lambda x: x['timestamp_unix'], reverse=True)
    return e_rank, w_rating, final_games, main_char