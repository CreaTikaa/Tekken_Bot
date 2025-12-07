# player_manager.py
import json
import os
import aiohttp
from datetime import datetime, timedelta
from config import PLAYERS, CACHE_FILE
from player import Player
from data_fetcher import fetch_both_profiles
from chart_generator import create_weekly_graph

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
                # On récupère 5 valeurs maintenant
                rank, rating, games, main_char, matchups, pentagon = await fetch_both_profiles(
                    self.session, urls['wavu'], urls['ewgf']
                )
            except Exception as e:
                print(f"Error fetching {name}: {e}")
                continue

            # On passe les 5 valeurs à update_stats
            p.update_stats(rank, rating, main_char, matchups, pentagon)
            
            # ... le reste ne change pas ...
            game_events = p.add_games(games) 
            for evt in game_events: all_events.append((name, evt))
            
            rank_events = p.detect_rank_events()
            for evt in rank_events: all_events.append((name, evt))

        self._save_cache()
        return all_events

    # --- DAILY REPORT ---
    def generate_daily_report(self, target_date: datetime = None):
        if target_date is None: target_date = datetime.now()
        date_str = target_date.strftime("%Y-%m-%d")
        
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        start_ts = start_of_day.timestamp()
        end_ts = end_of_day.timestamp()
        
        reports = []
        
        # NOUVEAUX TRACKERS (Winrate)
        max_wr = -1.0
        goat_info = None # (Nom, Winrate, Games)
        
        min_wr = 101.0
        fraud_info = None # (Nom, Winrate, Games)

        for name, p in self.players.items():
            todays_games = [g for g in p.games if start_ts <= g['timestamp_unix'] < end_ts]
            count = len(todays_games)
            wins = sum(1 for g in todays_games if g['result'] == 'WIN')
            losses = sum(1 for g in todays_games if g['result'] == 'LOSS')
            
            # On ne calcule que si le joueur a joué
            if count > 0:
                winrate = round((wins/count)*100, 1)
                
                # Logique GOAT (Max Winrate)
                # En cas d'égalité, on peut privilégier celui qui a le plus de games, 
                # mais ici on fait simple : premier trouvé ou strictement supérieur.
                if winrate > max_wr:
                    max_wr = winrate
                    goat_info = (name, winrate, count)
                
                # Logique FRAUDE (Min Winrate)
                if winrate < min_wr:
                    min_wr = winrate
                    fraud_info = (name, winrate, count)

                start_rank = p.daily_snapshot.get("rank", p.ewgf_rank) if p.daily_snapshot.get("date") == date_str else p.ewgf_rank
                
                reports.append({
                    "name": name,
                    "start_rank": start_rank,
                    "rank": p.ewgf_rank,
                    "wins": wins,
                    "losses": losses,
                    "winrate": winrate
                })
            
            if target_date.date() == datetime.now().date():
                p.last_daily_report_date = date_str

        self._save_cache()
        
        return {
            "stats": reports,
            "awards": {
                "goat": goat_info,   # Format: (Nom, Winrate, Games)
                "fraude": fraud_info # Format: (Nom, Winrate, Games)
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
        
        # NOUVEAUX TRACKERS (Winrate)
        max_wr = -1.0
        goat_info = None
        min_wr = 101.0
        fraud_info = None
        
        graph_data = {}

        for name, p in self.players.items():
            week_games = [g for g in p.games if g['timestamp_unix'] > week_ago_ts]
            
            if week_games:
                graph_data[name] = [(g['timestamp_unix'], g['result']) for g in week_games]

            count = len(week_games)
            if count == 0: continue
            
            wins = sum(1 for g in week_games if g['result'] == 'WIN')
            losses = count - wins
            winrate = round((wins/count)*100, 1)
            
            # CALCUL GOAT / FRAUDE (Winrate)
            if winrate > max_wr:
                max_wr = winrate
                goat_info = (name, winrate, count)
            
            if winrate < min_wr:
                min_wr = winrate
                fraud_info = (name, winrate, count)
            
            # ... (Le reste du code reste identique : calculs clutch, prime time, etc.) ...
            # COPIER LE RESTE DE LA FONCTION EXISTANTE ICI (awards, clutch, reports.append...)
            # Je remets le bloc complet pour éviter les erreurs de copier-coller :
            
            start_rank = p.weekly_snapshot.get("rank", "Unknown")
            end_rank = p.ewgf_rank
            close_losses = 0
            higher_rank_wins = 0
            my_current_idx = p.get_rank_index(p.ewgf_rank)
            clutch_wins = 0
            clutch_total = 0
            hour_buckets = {k: {'wins': 0, 'total': 0} for k in ["Matin", "Midi", "Soir", "Nuit"]}
            opp_stats = {} 

            for g in week_games:
                if g['result'] == 'LOSS' and g['score'] in ["2-3", "1-2"]: close_losses += 1
                if g['result'] == 'WIN':
                    opp_rank = g.get('opponent_rank')
                    if opp_rank:
                        opp_idx = p.get_rank_index(opp_rank)
                        if opp_idx > my_current_idx and opp_idx > -1: higher_rank_wins += 1
                try:
                    parts = g['score'].split('-')
                    if len(parts) == 2 and (int(parts[0]) + int(parts[1]) == 5):
                        clutch_total += 1
                        if g['result'] == 'WIN': clutch_wins += 1
                except: pass
                h = datetime.fromtimestamp(g['timestamp_unix']).hour 
                h = (h + 1) % 24 
                period = "Nuit"
                if 6 <= h < 12: period = "Matin"
                elif 12 <= h < 18: period = "Midi"
                elif 18 <= h < 24: period = "Soir"
                hour_buckets[period]['total'] += 1
                if g['result'] == 'WIN': hour_buckets[period]['wins'] += 1
                char = g.get('opponent_char')
                if char:
                    if char not in opp_stats: opp_stats[char] = {'wins': 0, 'total': 0}
                    opp_stats[char]['total'] += 1
                    if g['result'] == 'WIN': opp_stats[char]['wins'] += 1

            if close_losses > award_unlucky["count"]: award_unlucky = {"name": name, "count": close_losses}
            if higher_rank_wins > award_locked_in["count"]: award_locked_in = {"name": name, "count": higher_rank_wins}
            if count > award_chomeur["count"]: award_chomeur = {"name": name, "count": count}

            clutch_stat = None
            if clutch_total > 0:
                c_wr = round((clutch_wins/clutch_total)*100)
                clutch_stat = (c_wr, clutch_total)

            best_period = None
            best_wr = -1
            for period, d in hour_buckets.items():
                if d['total'] >= 3:
                    wr_p = (d['wins'] / d['total']) * 100
                    if wr_p > best_wr:
                        best_wr = wr_p
                        best_period = (period, int(wr_p))
            
            most_faced_stat = None
            if opp_stats:
                top_char = sorted(opp_stats.items(), key=lambda x: x[1]['total'], reverse=True)[0]
                char_name = top_char[0]
                stats = top_char[1]
                mf_wr = round((stats['wins'] / stats['total']) * 100)
                most_faced_stat = (char_name, stats['total'], mf_wr)

            nemesis_stat = None
            if p.matchups:
                valid_mus = [(char, d['winRate'], d['totalMatches']) for char, d in p.matchups.items() if d['totalMatches'] >= 5]
                if valid_mus:
                    worst = sorted(valid_mus, key=lambda x: x[1])[0]
                    nemesis_stat = worst

            pentagon_summary = None
            if p.pentagon_stats:
                flat_stats = {}
                for cat in ['attackComponents', 'defenseComponents', 'spiritComponents']:
                    if cat in p.pentagon_stats: flat_stats.update(p.pentagon_stats[cat])
                if flat_stats:
                    best_s = max(flat_stats.items(), key=lambda x: x[1])
                    worst_s = min(flat_stats.items(), key=lambda x: x[1])
                    pentagon_summary = (best_s, worst_s)

            reports.append({
                "name": name,
                "start_rank": start_rank,
                "end_rank": end_rank,
                "wins": wins,
                "losses": losses,
                "winrate": winrate,
                "total_games": count,
                "clutch": clutch_stat,
                "prime_time": best_period,
                "most_faced": most_faced_stat,
                "nemesis": nemesis_stat,
                "report_card": pentagon_summary
            })
            
            p.weekly_snapshot = {"date": today_str, "rank": p.ewgf_rank}
            p.last_weekly_report_date = today_str

        if not reports: return None
        
        chart_bytes = None
        if graph_data:
            try:
                chart_bytes = create_weekly_graph(graph_data)
            except Exception as e:
                print(f"Erreur graphique : {e}")

        self._save_cache()
        return {
            "stats": reports,
            "awards": {
                "unlucky": award_unlucky if award_unlucky["name"] else None,
                "locked_in": award_locked_in if award_locked_in["name"] else None,
                "chomeur": award_chomeur if award_chomeur["name"] else None,
                "goat": goat_info,   # (Nom, WR, Games)
                "fraude": fraud_info # (Nom, WR, Games)
            },
            "chart": chart_bytes
        }