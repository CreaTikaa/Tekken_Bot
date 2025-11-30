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

        # On stocke les streaks actuels
        self.current_lose_streak: int = 0
        self.current_win_streak: int = 0
        
        # Reports
        self.last_daily_report_date: Optional[str] = None
        self.weekly_snapshot: Dict = {}
        self.last_weekly_report_date: Optional[str] = None

    def update_stats(self, rank: str, rating: float, main_char: str):
        if rank and rank in self.RANK_TIERS_ORDER:
            self.last_ewgf_rank = self.ewgf_rank
            self.ewgf_rank = rank
        
        self.rating_mu = rating
        if main_char:
            self.main_char = main_char
            
        if not self.weekly_snapshot and self.ewgf_rank:
            self.weekly_snapshot = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "rank": self.ewgf_rank
            }

    def add_games(self, new_games: List[dict]) -> List[tuple]:
        """
        Ajoute les nouveaux jeux et retourne les événements déclenchés.
        new_games arrive souvent du plus récent au plus ancien.
        On doit les traiter du plus ancien au plus récent pour calculer les streaks correctement.
        """
        events = []
        
        # On filtre ceux qu'on a déjà vus
        truly_new_games = []
        for g in new_games:
            uid = f"{g['timestamp_unix']}_{g['opponent']}_{g['score']}"
            if uid not in self.seen_game_ids:
                self.seen_game_ids.add(uid)
                truly_new_games.append(g)

        # S'il n'y a rien de neuf, on arrête tout de suite (pas de doublons possibles)
        if not truly_new_games:
            return []

        # On trie les nouveaux jeux par ordre chronologique (du plus vieux au plus récent)
        # pour simuler l'évolution des streaks
        truly_new_games.sort(key=lambda x: x['timestamp_unix'])

        for g in truly_new_games:
            # 1. Mise à jour de l'historique global (insert en tête car self.games est décroissant)
            self.games.insert(0, g)
            
            # 2. Détection King (seulement si récent < 30min)
            is_fresh = (datetime.now().timestamp() - g['timestamp_unix']) < 1800 
            char_played = g.get('my_char', '').lower() if g.get('my_char') else ""
            if is_fresh and 'king' in char_played:
                events.append(("king_picked", g))

            # 3. Calcul dynamique des Streaks
            # C'est ICI qu'on empêche les doublons : on regarde l'évolution pas à pas.
            if g['result'] == 'WIN':
                self.current_lose_streak = 0
                self.current_win_streak += 1
                
                # Check triggers Win
                if self.current_win_streak == 3: events.append(("win_streak_3", 3))
                elif self.current_win_streak == 5: events.append(("win_streak_5", 5))
                elif self.current_win_streak == 8: events.append(("win_streak_8", 8))   # NOUVEAU
                elif self.current_win_streak == 10: events.append(("win_streak_10", 10)) # NOUVEAU

            elif g['result'] == 'LOSS':
                self.current_win_streak = 0
                self.current_lose_streak += 1
                
                # Check triggers Lose
                if self.current_lose_streak == 3: events.append(("lose_streak_3", 3))
                elif self.current_lose_streak == 5: events.append(("lose_streak_5", 5))
                elif self.current_lose_streak == 8: events.append(("lose_streak_8", 8))   # NOUVEAU
                elif self.current_lose_streak == 10: events.append(("lose_streak_10", 10)) # NOUVEAU

        # On garde l'historique propre (trié décroissant pour l'affichage status)
        self.games.sort(key=lambda x: x['timestamp_unix'], reverse=True)
        self.games = self.games[:500]
        
        return events

    def detect_rank_events(self) -> List[tuple]:
        # Séparé des streaks car le rank n'est pas lié à un match précis dans l'API wavu/ewgf
        events = []
        if (self.last_ewgf_rank and self.ewgf_rank and self.last_ewgf_rank != self.ewgf_rank):
            try:
                old_i = self.RANK_TIERS_ORDER.index(self.last_ewgf_rank)
                new_i = self.RANK_TIERS_ORDER.index(self.ewgf_rank)
                if new_i > old_i:
                    events.append(("rank_up", self.last_ewgf_rank, self.ewgf_rank))
                elif new_i < old_i:
                    events.append(("derank", self.last_ewgf_rank, self.ewgf_rank))
            except ValueError: pass
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
        return p