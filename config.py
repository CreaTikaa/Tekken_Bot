# config.py
import os

# --- PARAMÈTRES GÉNÉRAUX ---
REFRESH_INTERVAL = 30 
CACHE_FILE = "data/cache.json"
BACKOFF_TIME = 1800  # 30 minutes en cas d'erreur critique

# --- DISCORD ---
DISCORD_TOKEN = "token"
# Canaux
ANNOUNCE_CHANNEL_ID = 1444506689771409448  # on se moque
RANK_UP_CHANNEL_ID = 1444461502122950886   # Canal rank up
ALERT_CHANNEL_ID = 1444720229082202132     # Logs admin
TEST_CHANNEL_ID = 1444745943248277605 # Tests
REPORT_CHANNEL_ID = 1444759347564511402# Reports
STATUS_COMMAND_GUILD_IDS = [1169786637740425266] 

# --- MEDIA / VIDÉOS (Rotation) ---
# LOSE STREAKS
VIDEOS_LOSE_3 = ["videos/loose/lost_3_row.mp4", "videos/loose/loose3.mp4", "videos/loose/loose3_2", "videos/loose/zero.mp4", "avoir_peur.mp4","videos/loose/explications.mp4", "videos/loose/epate.mp4", "videos/loose/aucune_emotion.mp4" ]
VIDEOS_LOSE_5 = ["videos/loose/caca_ville.mp4", "videos/loose/loose5.mp4", "videos/loose/loose5_2.mp4", "videos/loose/moi_mais_pas_moi.mp4", "videos/loose/feldup_grande_mission.mp4", "videos/loose/it_is_what_it_is.mp4" ]
VIDEOS_LOSE_8 = ["videos/loose/galere.mp4", "videos/loose/loose8.mp4", "videos/loose/tunnel.mp4"]  
VIDEOS_LOSE_10 = ["videos/loose/loose_10.mp4"] 

# WIN STREAKS
VIDEOS_WIN_3 = ["videos/wins/sourir.mp4", "videos/wins/moi_wesh.mp4", "videos/wins/bander.mp4", "videos/wins/baise.mp4", "videos/wins/emotions.mp4", "videos/wins/noirs_sapes.mp4", "videos/wins/freddy.mp4", "videos/wins/doigby.mp4" ]
VIDEOS_WIN_5 = ["videos/wins/connor.mp4", "videos/wins/célébration_mourhino.mp4", "videos/wins/lebron.mp4", "videos/wins/happy.mp4", "videos/wins/me_fallait.mp4", "videos/wins/we_back.mp4", "videos/win/dj_superidol.mp4"]
VIDEOS_WIN_8 = ["videos/wins/goat.mp4", "videos/wins/FUCKING_BACK.mp4"]   
VIDEOS_WIN_10 = ["videos/wins/smile.mp4"]  

# EVENTS
VIDEOS_KING_PICK = ["videos/events/king_alert.mp4", "videos/events/jonathan_furry.mp4"]

VIDEOS_DERANK = ["videos/events/derank_msg_faut_reviser_les_combos.mp4", "videos/events/derank.mp4", "videos/events/derank1.mp4", "videos/events/derank2.mp4", "videos/events/derank3.mp4", "videos/events/derank4.mp4", "videos/events/derank5.mp4", "videos/events/derank6.mp4", "videos/events/derank7.mp4", "videos/events/derank8.mp4", "videos/events/derank9.mp4"]
VIDEOS_RANK_UP = ["videos/events/cr7.mp4", "videos/events/rankup.mp4", "videos/events/rankup5.mp4", "videos/events/THANOS_DANCE.mp4", "videos/events/dance_freeze.mp4", "videos/events/jul_nepal.mp4", "videos/events/rankup2.mp4", "videos/events/rankup4.mp4", "videos/events/SIUUUU.mp4", "videos/events/shaku_shaku.mp4", "videos/events/rankup3.mp4", "videos/events/dr_raoul.mp4", "videos/events/doig-by-by-by.mp4"]

# --- JOUEURS ET IDs ---
PLAYERS = {
    "Gland Putréfié": {
        "wavu": "https://wank.wavu.wiki/player/2AhBmr775Tq8",
        "ewgf": "https://www.ewgf.gg/player/2AhBmr775Tq8"  
    },
    "GicleurCinglé": {
        "wavu": "https://wank.wavu.wiki/player/48Q56dfA8ydn",
        "ewgf": "https://www.ewgf.gg/player/48Q5-6dfA-8ydn"
    },
    "Haribo": {
        "wavu": "https://wank.wavu.wiki/player/4Rj6NNGd4Ryf",
        "ewgf": "https://www.ewgf.gg/player/4Rj6NNGd4Ryf"
    },
    "Barbatos": {
        "wavu": "https://wank.wavu.wiki/player/576jyLrQjmdf",
        "ewgf": "https://www.ewgf.gg/player/576jyLrQjmdf"
    },
    "PILOK": {
        "wavu": "https://wank.wavu.wiki/player/5dBfyLhtLJG4",
        "ewgf": "https://www.ewgf.gg/player/5dBfyLhtLJG4"
    }
}

DISCORD_IDS = {
    "Gland Putréfié": 394414936631279616,
    "GicleurCinglé": 439839878339887104,
    "Haribo": 726190319615475793,
    "Barbatos": 1180632930553446490,
    "PILOK" : 1368608579015151799
}

# Ordre des rangs pour la détection et les awards
RANK_TIERS_ORDER = [
    "Beginner", "1st Dan", "2nd Dan", "Fighter", "Strategist", "Combatant", "Brawler", "Ranger",
    "Cavalry", "Warrior", "Assailant", "Dominator", "Vanquisher", "Destroyer", "Eliminator",
    "Garyu", "Shinryu", "Tenryu", "Mighty Ruler", "Flame Ruler", "Battle Ruler",
    "Fujin", "Raijin", "Kishin", "Bushin", "Tekken King", "Tekken Emperor",
    "Tekken God", "Tekken God Supreme", "God of Destruction"
]