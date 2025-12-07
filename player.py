# player.py
from typing import List, Dict, Optional
from datetime import datetime
import copy

class Player:
    RANK_TIERS_ORDER = [
        "Beginner", "1st Dan", "2nd Dan", "Fighter", "Strategist", "Combatant", "Brawler", "Ranger",
        "Cavalry", "Warrior", "Assailant", "Dominator", "Vanquisher", "Destroyer", "Eliminator",
        "Garyu", "Shinryu", "Tenryu", "Mighty Ruler", "Flame Ruler", "Battle Ruler",
        "Fujin", "Raijin", "Kishin", "Bushin", "Tekken King", "Tekken Emperor",
        "Tekken God", "Tekken God Supreme", "God of Destruction"
    ]

    def __init__(self, display_name: str):
        self.name = display_name
        
        self.ewgf_rank: Optional[str] = None
        self.last_ewgf_rank: Optional[str] = None
        self.rating_mu: Optional[float] = None
        self.main_char: Optional[str] = None

        self.games: List[Dict] = []
        self.seen_game_ids: set = set()
        
        self.matchups: Dict = {}
        self.pentagon_stats: Dict = {}

        self.current_lose_streak: int = 0
        self.current_win_streak: int = 0
        
        self.last_daily_report_date: Optional[str] = None
        
        # --- AJOUT ICI ---
        self.daily_snapshot: Dict = {}   # Snapshot du matin
        self.weekly_snapshot: Dict = {}
        self.last_weekly_report_date: Optional[str] = None

    def update_stats(self, rank: str, rating: float, main_char: str, matchups: Dict, pentagon: Dict):
        # 1. Gestion du Daily Snapshot (Le rang du matin)
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Si on n'a pas de snapshot OU que le snapshot date d'hier (ou avant)
        # On enregistre le rang ACTUEL comme étant le rang de départ de ce nouveau jour
        if rank and (not self.daily_snapshot or self.daily_snapshot.get('date') != today):
            self.daily_snapshot = {
                "date": today,
                "rank": rank # On fige le rang du matin
            }

        # 2. Update Rank actuel
        if rank and rank in self.RANK_TIERS_ORDER:
            if self.ewgf_rank != rank:
                self.last_ewgf_rank = self.ewgf_rank
                self.ewgf_rank = rank
        
        if rating: self.rating_mu = rating
        if main_char: self.main_char = main_char
        
        # Update New Stats
        if matchups: self.matchups = matchups
        if pentagon: self.pentagon_stats = pentagon
            
        # Weekly Snapshot
        if not self.weekly_snapshot and self.ewgf_rank:
            self.weekly_snapshot = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "rank": self.ewgf_rank
            }

    def add_games(self, new_games: List[dict]) -> List[tuple]:
        events = []
        truly_new_games = []
        
        # Le nom de l'adversaire est déjà nettoyé dans data_fetcher pour la clé, 
        # mais on recrée l'ID ici de la même façon pour le set seen_game_ids
        import re
        for g in new_games:
            opp_clean = re.sub(r'\W+', '', g['opponent']).lower()
            uid = f"{g['timestamp_unix']}_{opp_clean}_{g['score']}"
            
            if uid not in self.seen_game_ids:
                self.seen_game_ids.add(uid)
                truly_new_games.append(g)

        if not truly_new_games: return []

        truly_new_games.sort(key=lambda x: x['timestamp_unix'])
        
        now_ts = datetime.now().timestamp()
        NOTIFICATION_THRESHOLD = 1800 # 30 minutes

        for g in truly_new_games:
            self.games.insert(0, g)
            
            # --- FILTRE DE FRAICHEUR ---
            # Si le match date de plus de 30 min, on ne notifie PAS (on update juste stats/streak interne)
            is_fresh = (now_ts - g['timestamp_unix']) < NOTIFICATION_THRESHOLD
            
            # Logic King
            char_played = g.get('my_char', '').lower() if g.get('my_char') else ""
            if is_fresh and 'king' in char_played:
                events.append(("king_picked", g))

            # Logic Streaks
            if g['result'] == 'WIN':
                self.current_lose_streak = 0
                self.current_win_streak += 1
                
                if is_fresh:
                    if self.current_win_streak == 3: events.append(("win_streak_3", 3))
                    elif self.current_win_streak == 5: events.append(("win_streak_5", 5))
                    elif self.current_win_streak == 8: events.append(("win_streak_8", 8))
                    elif self.current_win_streak == 10: events.append(("win_streak_10", 10))

            elif g['result'] == 'LOSS':
                self.current_win_streak = 0
                self.current_lose_streak += 1
                
                if is_fresh:
                    if self.current_lose_streak == 3: events.append(("lose_streak_3", 3))
                    elif self.current_lose_streak == 5: events.append(("lose_streak_5", 5))
                    elif self.current_lose_streak == 8: events.append(("lose_streak_8", 8))
                    elif self.current_lose_streak == 10: events.append(("lose_streak_10", 10))

        self.games.sort(key=lambda x: x['timestamp_unix'], reverse=True)
        self.games = self.games[:1500]
        
        return events

    def detect_rank_events(self) -> List[tuple]:
        events = []
        
        # Sécurité : Si l'un des rangs est manquant, on ne fait rien
        if not self.last_ewgf_rank or not self.ewgf_rank:
            return events

        # Si le rang est identique à la dernière fois, on arrête tout de suite
        if self.last_ewgf_rank == self.ewgf_rank:
            return events

        try:
            old_i = self.RANK_TIERS_ORDER.index(self.last_ewgf_rank)
            new_i = self.RANK_TIERS_ORDER.index(self.ewgf_rank)
            
            # Détection
            if new_i > old_i:
                events.append(("rank_up", self.last_ewgf_rank, self.ewgf_rank))
            elif new_i < old_i:
                events.append(("derank", self.last_ewgf_rank, self.ewgf_rank))
            
            # CRUCIAL : On met à jour last_ewgf_rank ICI pour dire "C'est bon, j'ai vu le changement"
            # Cela empêche de redéclencher l'event à la prochaine boucle
            self.last_ewgf_rank = self.ewgf_rank
            
        except ValueError:
            # Si un rang n'est pas dans la liste (ex: un nouveau rang ajouté par le jeu), on ignore
            pass
            
        return events
    
    def get_rank_index(self, rank_name):
        if not rank_name or rank_name not in self.RANK_TIERS_ORDER: return -1
        return self.RANK_TIERS_ORDER.index(rank_name)

    def to_dict(self):
        d = copy.deepcopy(self.__dict__)
        d['seen_game_ids'] = list(self.seen_game_ids)
        return d

    @classmethod
    def from_dict(cls, d):
        p = cls(d["name"])
        p.__dict__.update(d)
        p.seen_game_ids = set(d.get("seen_game_ids", []))
        # Récupération du snapshot s'il existe dans le cache
        p.daily_snapshot = d.get("daily_snapshot", {}) 
        return p