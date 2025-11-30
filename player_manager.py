# player_manager.py
import json
import os
import aiohttp
from datetime import datetime, timedelta
from config import PLAYERS, CACHE_FILE
from player import Player
from data_fetcher import fetch_both_profiles

class PlayerManager:
    def __init__(self):
        self.players = {name: Player(name) for name in PLAYERS}
        self.session = None
        self._load_cache()

    def _load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    data = json.load(f)
                    for name, p_data in data.items():
                        if name in self.players:
                            self.players[name] = Player.from_dict(p_data)
            except Exception as e:
                print(f"Cache load error: {e}")

    def _save_cache(self):
        try:
            data = {name: p.to_dict() for name, p in self.players.items()}
            with open(CACHE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Cache save error: {e}")

    async def update_all(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()

        all_events = []
        for name, urls in PLAYERS.items():
            p = self.players[name]
            try:
                rank, rating, games, main_char = await fetch_both_profiles(
                    self.session, urls['wavu'], urls['ewgf']
                )
            except Exception as e:
                print(f"Error fetching {name}: {e}")
                continue

            p.update_stats(rank, rating, main_char)
            
            # 1. Game Events (Streaks, King)
            # Cette fonction gère maintenant l'anti-doublon en interne
            game_events = p.add_games(games) 
            for evt in game_events: all_events.append((name, evt))
            
            # 2. State Events (Rank Up/Down)
            rank_events = p.detect_rank_events()
            for evt in rank_events: all_events.append((name, evt))

        self._save_cache()
        return all_events

    # --- DAILY REPORT ---
    def generate_daily_report(self, today_str: str):
        reports = []
        midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        midnight_ts = midnight.timestamp()
        
        max_wins = -1
        goat_name = None
        max_losses = -1
        fraud_name = None

        for name, p in self.players.items():
            todays_games = [g for g in p.games if g['timestamp_unix'] > midnight_ts]
            count = len(todays_games)
            wins = sum(1 for g in todays_games if g['result'] == 'WIN')
            losses = sum(1 for g in todays_games if g['result'] == 'LOSS')
            
            if wins > max_wins and count > 0:
                max_wins = wins
                goat_name = name
            if losses > max_losses and count > 0:
                max_losses = losses
                fraud_name = name

            if count > 0:
                winrate = round((wins/count)*100, 1)
                reports.append({
                    "name": name,
                    "rank": p.ewgf_rank,
                    "wins": wins,
                    "losses": losses,
                    "winrate": winrate
                })
            
            p.last_daily_report_date = today_str

        if not reports: return None
        self._save_cache()
        return {
            "stats": reports,
            "awards": {
                "goat": (goat_name, max_wins) if goat_name else None,
                "fraude": (fraud_name, max_losses) if fraud_name else None
            }
        }

    # --- WEEKLY REPORT ---
    def generate_weekly_report(self, today_str: str):
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        week_ago_ts = week_ago.timestamp()
        
        reports = []
        award_unlucky = {"name": None, "count": -1}
        award_locked_in = {"name": None, "count": -1}
        award_chomeur = {"name": None, "count": -1}

        for name, p in self.players.items():
            week_games = [g for g in p.games if g['timestamp_unix'] > week_ago_ts]
            count = len(week_games)
            if count == 0: continue
            
            wins = sum(1 for g in week_games if g['result'] == 'WIN')
            losses = count - wins
            winrate = round((wins/count)*100, 1)
            
            start_rank = p.weekly_snapshot.get("rank", "Unknown")
            end_rank = p.ewgf_rank
            
            close_losses = 0
            for g in week_games:
                if g['result'] == 'LOSS' and g['score'] in ["2-3", "1-2"]:
                    close_losses += 1
            if close_losses > award_unlucky["count"]:
                award_unlucky = {"name": name, "count": close_losses}
                
            higher_rank_wins = 0
            my_current_idx = p.get_rank_index(p.ewgf_rank)
            for g in week_games:
                if g['result'] == 'WIN':
                    opp_rank = g.get('opponent_rank')
                    if opp_rank:
                        opp_idx = p.get_rank_index(opp_rank)
                        if opp_idx > my_current_idx and opp_idx > -1:
                            higher_rank_wins += 1
            if higher_rank_wins > award_locked_in["count"]:
                award_locked_in = {"name": name, "count": higher_rank_wins}

            if count > award_chomeur["count"]:
                award_chomeur = {"name": name, "count": count}

            reports.append({
                "name": name,
                "start_rank": start_rank,
                "end_rank": end_rank,
                "wins": wins,
                "losses": losses,
                "winrate": winrate
            })
            
            p.weekly_snapshot = {"date": today_str, "rank": p.ewgf_rank}
            p.last_weekly_report_date = today_str

        if not reports: return None
        self._save_cache()
        return {
            "stats": reports,
            "awards": {
                "unlucky": award_unlucky if award_unlucky["name"] else None,
                "locked_in": award_locked_in if award_locked_in["name"] else None,
                "chomeur": award_chomeur if award_chomeur["name"] else None
            }
        }