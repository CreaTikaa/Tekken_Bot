# discord_bot.py
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime, timezone
import pytz
import os
import random
import time # Ajout nécessaire pour le test du graph
#from datetime import datetime, timezone, timedelta

from config import (
    DISCORD_TOKEN, ANNOUNCE_CHANNEL_ID, RANK_UP_CHANNEL_ID, 
    REPORT_CHANNEL_ID, TEST_CHANNEL_ID, STATUS_COMMAND_GUILD_IDS, 
    INTERVAL_ACTIVE, INTERVAL_IDLE, INTERVAL_SLEEP, ACTIVITY_THRESHOLD,
    VIDEOS_LOSE_3, VIDEOS_LOSE_5, VIDEOS_LOSE_8, VIDEOS_LOSE_10,
    VIDEOS_WIN_3, VIDEOS_WIN_5, VIDEOS_WIN_8, VIDEOS_WIN_10, 
    VIDEOS_RANK_UP, VIDEOS_KING_PICK, VIDEOS_DERANK, 
    PLAYERS, DISCORD_IDS,
    MESSAGES_LOSE_3, MESSAGES_LOSE_5, MESSAGES_LOSE_8, MESSAGES_LOSE_10,
    MESSAGES_WIN_3, MESSAGES_WIN_5, MESSAGES_WIN_8, MESSAGES_WIN_10,
    MESSAGES_RANK_UP, MESSAGES_DERANK, MESSAGES_KING
)
from player_manager import PlayerManager
from chart_generator import create_weekly_graph

TZ_PARIS = pytz.timezone("Europe/Paris")
intents = discord.Intents.default()
intents.message_content = True

WIDE_SPACER_IMAGE = "images/spacer.png"
TEKKEN8_LOGO = "images/Tekken-8-Logo.png"

# -----------------------
# SLASH COMMANDS
# -----------------------

"""
@app_commands.command(name="force_daily", description="ADMIN: Générer un Daily Report (Aujourd'hui ou Passé)")
@app_commands.choices(jour=[
    app_commands.Choice(name="Aujourd'hui", value=0),
    app_commands.Choice(name="Hier", value=1),
    app_commands.Choice(name="Avant-hier", value=2)
])
async def force_daily(interaction: discord.Interaction, jour: int = 0):
    # Vérification (Optionnel : limiter aux admins)
    # if interaction.user.id != TON_ID: return ...

    bot = interaction.client
    channel = bot.get_channel(REPORT_CHANNEL_ID)
    if not channel: 
        return await interaction.response.send_message("❌ Channel Report introuvable.", ephemeral=True)
    
    await interaction.response.send_message(f"🔄 Génération du rapport (J-{jour})...", ephemeral=True)
    
    # Calcul de la date cible (Maintenant - X jours)
    target_date = datetime.now(TZ_PARIS) - timedelta(days=jour)
    date_title = target_date.strftime("%d/%m/%Y")
    
    # Génération
    data = bot.pm.generate_daily_report(target_date)
    
    # Envoi
    if data and data['stats']:
        # On hack un peu l'envoi pour changer le titre
        # On appelle send_daily_report normalement, mais on précise la date dans un footer ou message avant
        await channel.send(f"**📂 Rattrapage Rapport du {date_title}**")
        await bot.send_daily_report(channel, data)
    else:
        await channel.send(f"💤 **Rapport du {date_title}** : Aucun match trouvé cette journée-là.")
"""
@app_commands.command(name="tekken_stats", description="Affiche la carte d'identité complète (Stats All-Time, Matchups, Bulletin Technique)")
@app_commands.choices(player=[app_commands.Choice(name=n, value=n) for n in PLAYERS])
async def full_stats(interaction: discord.Interaction, player: str):
    bot = interaction.client
    p = bot.pm.players.get(player)
    
    if not p: 
        return await interaction.response.send_message("Joueur inconnu.", ephemeral=True)
    
    wins = sum(1 for g in p.games if g['result'] == 'WIN')
    total = len(p.games)
    losses = total - wins
    wr = round(wins/total*100, 1) if total > 0 else 0.0
    
    # CLUTCH
    clutch_wins = 0
    clutch_total = 0
    for g in p.games:
        if 'score' in g:
            try:
                parts = g['score'].split('-')
                if len(parts) == 2 and (int(parts[0]) + int(parts[1]) == 5):
                    clutch_total += 1
                    if g['result'] == 'WIN': clutch_wins += 1
            except: continue

    clutch_wr = round((clutch_wins / clutch_total) * 100, 1) if clutch_total > 0 else 0
    if clutch_total < 5: clutch_title = "Pas assez de données"
    elif clutch_wr >= 60: clutch_title = "❄️ **ICE COLD** (Sang froid)"
    elif clutch_wr >= 45: clutch_title = "👍 **Solide** (Normal)"
    else: clutch_title = "🥀 **Mental de chips** (Choke)"

    # PRIME TIME
    slots = {k: {'wins': 0, 'total': 0} for k in ["🌅 Matin (06-12h)", "😎 Midi (12-18h)", "🔥 Soir (18-00h)", "🦉 Nuit (00-06h)"]}
    for g in p.games:
        dt = datetime.fromtimestamp(g['timestamp_unix'], tz=TZ_PARIS)
        h = dt.hour
        key = "🦉 Nuit (00-06h)"
        if 6 <= h < 12: key = "🌅 Matin (06-12h)"
        elif 12 <= h < 18: key = "😎 Midi (12-18h)"
        elif 18 <= h < 24: key = "🔥 Soir (18-00h)"
        
        slots[key]['total'] += 1
        if g['result'] == 'WIN': slots[key]['wins'] += 1

    best_slot_name = "Indéterminé"
    best_slot_wr = -1
    prime_time_txt = ""
    for name, s in slots.items():
        if s['total'] > 0:
            swr = round((s['wins'] / s['total']) * 100, 0)
            prime_time_txt += f"{name} : `{swr}%` ({s['wins']}/{s['total']})\n"
            if s['total'] >= 5 and swr > best_slot_wr:
                best_slot_wr = swr
                best_slot_name = name

    # EMBED
    embed = discord.Embed(title=f"🥋 Rapport Complet : {p.name}", color=0x2ECC71)
    if p.ewgf_rank:
        rank_clean = p.ewgf_rank.replace(" ", "")
        embed.set_thumbnail(url=f"https://www.ewgf.gg/static/rank-icons/{rank_clean}T8.webp")

    embed.add_field(name="🔹 Général", value=f"🏆 **Rank :** {p.ewgf_rank or 'N/A'}\n📈 **Rating :** {p.rating_mu or 'N/A'}\n📊 **Winrate :** `{wr}%` ({wins}W - {losses}L | {total} Games)", inline=False)
    
    embed.add_field(name="🧠 Mental & Clutch Factor", value=f"**Indice Clutch :** `{clutch_wr}%` sur {clutch_total} matchs décisifs.\nVerdict : {clutch_title}\n\n**⚡ Prime Time :** {best_slot_name} \n{prime_time_txt}", inline=False)

    # BULLETIN (VERBEUX)
    if p.pentagon_stats:
        s = p.pentagon_stats
        flat_stats = {}
        for cat in ['attackComponents', 'defenseComponents', 'spiritComponents']:
            if cat in s: flat_stats.update(s[cat])
        
        bulletin_txt = ""
        if flat_stats:
            best_s = max(flat_stats.items(), key=lambda x: x[1])
            worst_s = min(flat_stats.items(), key=lambda x: x[1])
            trans = {'aggressiveness': 'Agressivité', 'heavyDamage': 'Dégâts', 'block': 'Garde', 'throwEscape': 'Déchoppe', 'evasion': 'Evasion', 'comeback': 'Comeback', 'closeBattles': 'Clutch', 'respect': 'Respect', 'ambition': 'Ambition'}
            bulletin_txt = f"📝 **Bulletin :** Brille par son **{trans.get(best_s[0], best_s[0])}** ({best_s[1]}/25) mais pue un peu sur son **{trans.get(worst_s[0], worst_s[0])}** ({worst_s[1]}/25).\n\n"

        atk = s.get('attackComponents', {})
        defs = s.get('defenseComponents', {})
        tech_txt = bulletin_txt + f"⚔️ **Attaque :** Aggro {atk.get('aggressiveness', 0)}/25 • Dégâts {atk.get('heavyDamage', 0)}/25\n🛡️ **Défense :** Garde {defs.get('block', 0)}/25 • Déchoppe {defs.get('throwEscape', 0)}/25"
        embed.add_field(name="🔸 Profil Technique", value=tech_txt, inline=False)

    # --- AJOUT ICI : LES PLUS AFFRONTÉS ---
    if p.matchups:
        # On trie par 'totalMatches' décroissant
        most_played = sorted(p.matchups.items(), key=lambda x: x[1]['totalMatches'], reverse=True)[:3]
        encounter_txt = ""
        for char_name, data in most_played:
            encounter_txt += f"**{char_name}** : {data['totalMatches']} games ({int(data['winRate'])}% WR)\n"
        
        if encounter_txt:
            embed.add_field(name="👊 Persos les plus affrontés (All time)", value=encounter_txt, inline=False)

    # NEMESIS & MATCHUPS
    if p.matchups:
        nemesis_txt = ""
        valid_mus = [(char, d['winRate'], d['totalMatches']) for char, d in p.matchups.items() if d['totalMatches'] >= 5]
        if valid_mus:
            worst_mu = sorted(valid_mus, key=lambda x: x[1])[0]
            nemesis_txt = f"☠️ **Nemesis :** Se fait malaxer par **{worst_mu[0]}** ({int(worst_mu[1])}% WR sur {worst_mu[2]} games).\n\n"

        mu_list = []
        for char_name, data in p.matchups.items():
            if data['totalMatches'] >= 3:
                mu_list.append((char_name, data['winRate'], data['totalMatches'], data['wins'], data['losses']))
        
        mu_list.sort(key=lambda x: x[1], reverse=True)
        best = mu_list[:3]
        worst = sorted(mu_list, key=lambda x: x[1])[:3]

        best_txt = "\n".join([f"**{m[0]}** : `{int(m[1])}%` ({m[3]}-{m[4]})" for m in best]) or "N/A"
        worst_txt = "\n".join([f"**{m[0]}** : `{int(m[1])}%` ({m[3]}-{m[4]})" for m in worst]) or "N/A"
        
        embed.add_field(name="⚔️ Matchups", value=f"{nemesis_txt}✅ **Victimes :**\n{best_txt}\n\n❌ **Cauchemars :**\n{worst_txt}", inline=False)

    embed.set_footer(text=f"Données: EWGF & Wavu • {datetime.now().strftime('%H:%M')}")
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="tekken_status", description="Afficher les stats simples d'un joueur")
@app_commands.choices(player=[app_commands.Choice(name=n, value=n) for n in PLAYERS])
async def status(interaction: discord.Interaction, player: str):
    bot = interaction.client
    p = bot.pm.players.get(player)
    if not p: return await interaction.response.send_message("Joueur inconnu.", ephemeral=True)

    embed = discord.Embed(title=f"🥊 {p.name}", color=0x5865F2, timestamp=datetime.now(timezone.utc))
    embed.description = f"**Main Character :** {p.main_char or 'Inconnu'}\n━━━━━━━━━━━━━━━━━━"
    
    wins = sum(1 for g in p.games if g['result'] == 'WIN')
    total = len(p.games)
    wr = round(wins/total*100, 1) if total > 0 else 0.0

    embed.add_field(name="🏆 Rank Actuel", value=f"**{p.ewgf_rank or 'Unranked'}**", inline=True)
    embed.add_field(name="📈 Rating", value=f"**{p.rating_mu or 'N/A'}**", inline=True)
    embed.add_field(name="📊 Winrate", value=f"**{wr}%** ({total} games)", inline=False)

    last_5 = []
    for g in p.games[:5]:
        emoji = "✅" if g['result'] == 'WIN' else "❌"
        ts = datetime.fromtimestamp(g['timestamp_unix']).strftime("%d/%m %H:%M")
        last_5.append(f"`{ts}` • {emoji} **{g['score']}** vs {g['opponent']}")
    
    embed.add_field(name="📋 5 Derniers Matchs", value="\n".join(last_5) or "Aucun match.", inline=False)
    embed.set_footer(text=f"Données : EWGF & Wavu • {p.name}")
    
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="test_events", description="ADMIN: Tester events + reports")
async def test_events(interaction: discord.Interaction):
    bot = interaction.client
    channel = bot.get_channel(TEST_CHANNEL_ID)
    if not channel: return await interaction.response.send_message("Channel introuvable", ephemeral=True)
    
    await interaction.response.send_message("🧪 Tests lancés...", ephemeral=True)
    dummy = list(PLAYERS.keys())[0]
    
    # 1. EVENTS
    scenarios = [("king_picked", {}), ("lose_streak_3", 3), ("win_streak_3", 3), ("rank_up", "Garyu", "Tenryu")]
    await channel.send("🔹 **--- TEST EVENTS ---**")
    for evt in scenarios:
        mock = (evt[0], evt[1], evt[2]) if len(evt) > 2 else (evt[0], evt[1])
        await bot.handle_event(channel, dummy, mock)
        await asyncio.sleep(1)

    # 2. DAILY REPORT
    await channel.send("🔹 **--- TEST DAILY ---**")
    mock_stats = [{'name': dummy, 'wins': 10, 'losses': 5, 'winrate': 66.6, 'rank': 'Garyu'}, {'name': 'Jean-Michel', 'wins': 2, 'losses': 20, 'winrate': 10.0, 'rank': 'Beginner'}]
    await bot.send_daily_report(channel, {'stats': mock_stats, 'awards': {'goat': (dummy, 60.2, 75), 'fraude': ('Jean-Michel', 20)}})
    
    # 3. WEEKLY REPORT (Avec Graphique Simulé)
    await channel.send("🔹 **--- TEST WEEKLY ---**")
    
    # Génération du graphique de test
    now = int(time.time())
    day = 86400
    fake_graph_data = {
        dummy: [(now - day*i, 'WIN' if i%2==0 else 'LOSS') for i in range(5)],
        'Jean-Michel': [(now - day*i, 'LOSS') for i in range(5)]
    }
    chart_bytes = None
    try:
        chart_bytes = create_weekly_graph(fake_graph_data)
    except Exception as e:
        await channel.send(f"Erreur graph: {e}")

    mock_weekly = [
        {'name': dummy, 'start_rank': 'Garyu', 'end_rank': 'Tenryu', 'wins': 45, 'losses': 30, 'winrate': 60.0, 'total_games': 75, 'prime_time': ("Soir", 75), 'clutch': (60, 10), 'nemesis': None, 'report_card': None, 'most_faced': ("Paul", 5, 20)},
        {'name': 'Jean-Michel', 'start_rank': 'Brawler', 'end_rank': 'Brawler', 'wins': 10, 'losses': 50, 'winrate': 16.6, 'total_games': 60, 'prime_time': None, 'clutch': (10, 5), 'nemesis': None, 'report_card': None, 'most_faced': ("Kazuya", 12, 45)}
    ]
    mock_awards = {'unlucky': {'name': 'Jean-Michel', 'count': 12}, 'locked_in': {'name': dummy, 'count': 8}, 'chomeur': {'name': dummy, 'count': 75}, 'goat': (dummy, 45), 'fraude': ('Jean-Michel', 50)}
    
    # On passe bien 'chart' ici
    await bot.send_weekly_report(channel, {'stats': mock_weekly, 'awards': mock_awards, 'chart': chart_bytes})
    await channel.send("✅ Tests finis.")

# -----------------------
# BOT CLASS
# -----------------------
class TekkenBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.pm = PlayerManager()

    async def setup_hook(self):
        self.tree.add_command(status)
        self.tree.add_command(test_events)
        self.tree.add_command(full_stats)
#        self.tree.add_command(force_daily)

        if STATUS_COMMAND_GUILD_IDS:
            for gid in STATUS_COMMAND_GUILD_IDS:
                guild = discord.Object(id=gid)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
            self.tree.clear_commands(guild=None)
            await self.tree.sync(guild=None)
        else:
            await self.tree.sync()
        self.loop.create_task(self.background_loop())

    async def on_ready(self):
        print(f"✅ Connecté: {self.user}")

    async def background_loop(self):
        await self.wait_until_ready()
        announce_ch = self.get_channel(ANNOUNCE_CHANNEL_ID)
        rank_ch = self.get_channel(RANK_UP_CHANNEL_ID)
        report_ch = self.get_channel(REPORT_CHANNEL_ID)
        
        while not self.is_closed():
            try:
                events = await self.pm.update_all()
                for p_name, event in events:
                    target = rank_ch if event[0] in ["rank_up", "derank"] else announce_ch
                    if target: await self.handle_event(target, p_name, event)

                now = datetime.now(TZ_PARIS)
                today = now.strftime("%Y-%m-%d")

                if now.hour == 23 and now.minute >= 55:
                    if any(p.last_daily_report_date != today for p in self.pm.players.values()):
                        data = self.pm.generate_daily_report(today)
                        if data and report_ch: await self.send_daily_report(report_ch, data)

                if now.weekday() == 6 and now.hour == 23 and now.minute >= 55:
                    if any(p.last_weekly_report_date != today for p in self.pm.players.values()):
                        data = self.pm.generate_weekly_report(today)
                        if data and report_ch: await self.send_weekly_report(report_ch, data)

                is_active_mode = False
                current_timestamp = datetime.now().timestamp()
                for p in self.pm.players.values():
                    if p.games:
                        if (current_timestamp - p.games[0]['timestamp_unix']) < ACTIVITY_THRESHOLD:
                            is_active_mode = True
                            break

                if is_active_mode:
                    sleep_time = INTERVAL_ACTIVE
                    print(f"Active mode. Refresh dans {sleep_time}s.")
                else:
                    if 3 <= now.hour < 10:
                        sleep_time = INTERVAL_SLEEP
                        print(f"Night Mode. Refresh dans {sleep_time}s.")

                    # Si on est à 23h, on force le bot à ne jamais dormir plus de 60 secondes
                    # pour être sûr de ne pas rater la fenêtre de 23h55.
                if now.hour == 23 and sleep_time > 200:
                    sleep_time = 200
                    print("⏰ Approche du rapport : sommeil forcé à 60s.")
                # -----------------------------------------------

            except Exception as e:
                print(f"Loop Error: {e}")
                await asyncio.sleep(1800)

    def get_random_video(self, video_list):
        if not video_list: return None
        valid = [v for v in video_list if os.path.exists(v)]
        return random.choice(valid) if valid else None

    async def handle_event(self, channel, p_name, event):
        if not channel: return
        mention_txt = f"<@{DISCORD_IDS.get(p_name)}>" if p_name in DISCORD_IDS else f"**{p_name}**"
        ping_content = mention_txt 
        evt = event[0]
        
        if channel.id == TEST_CHANNEL_ID and channel.id != ANNOUNCE_CHANNEL_ID: pass
        elif evt in ["rank_up", "derank"]: 
            rc = self.get_channel(RANK_UP_CHANNEL_ID)
            if rc: channel = rc

        try:
            embed, file_path = None, None
            def get_msg(msg_list, extra_data=None):
                if not msg_list: return "Pas de message configuré."
                txt = random.choice(msg_list)
                txt = txt.replace("{mention}", mention_txt)
                if extra_data: txt = txt.replace("{rank}", str(extra_data))
                return txt

            if evt == "king_picked":
                embed = discord.Embed(title="🐆 KING DETECTED 🐆", description=get_msg(MESSAGES_KING), color=discord.Color.orange())
                file_path = self.get_random_video(VIDEOS_KING_PICK)
            elif evt == "lose_streak_3":
                embed = discord.Embed(title="💀 Harr 💀", description=get_msg(MESSAGES_LOSE_3), color=0x8B0000)
                file_path = self.get_random_video(VIDEOS_LOSE_3)
            elif evt == "lose_streak_5":
                embed = discord.Embed(title="⚰️ Mega Merde ⚰️", description=get_msg(MESSAGES_LOSE_5), color=0x000000)
                file_path = self.get_random_video(VIDEOS_LOSE_5)
            elif evt == "lose_streak_8":
                embed = discord.Embed(title="🏴‍☠️ DESASTRE 🏴‍☠️", description=get_msg(MESSAGES_LOSE_8), color=0x000000)
                file_path = self.get_random_video(VIDEOS_LOSE_8)
            elif evt == "lose_streak_10":
                embed = discord.Embed(title="🏳️ ABANDONNE 🏳️", description=get_msg(MESSAGES_LOSE_10), color=0x000000)
                file_path = self.get_random_video(VIDEOS_LOSE_10)
            elif evt == "win_streak_3":
                embed = discord.Embed(title="🔥 Win Streak 🔥", description=get_msg(MESSAGES_WIN_3), color=discord.Color.gold())
                file_path = self.get_random_video(VIDEOS_WIN_3)
            elif evt == "win_streak_5":
                embed = discord.Embed(title="🚀 MEGA TEUB 🚀 ", description=get_msg(MESSAGES_WIN_5), color=discord.Color.teal())
                file_path = self.get_random_video(VIDEOS_WIN_5)
            elif evt == "win_streak_8":
                embed = discord.Embed(title="🌟 GOAT 🌟", description=get_msg(MESSAGES_WIN_8), color=discord.Color.purple())
                file_path = self.get_random_video(VIDEOS_WIN_8)
            elif evt == "win_streak_10":
                embed = discord.Embed(title="👑 IMMORTAL 👑", description=get_msg(MESSAGES_WIN_10), color=discord.Color.magenta())
                file_path = self.get_random_video(VIDEOS_WIN_10)
            elif evt == "rank_up":
                embed = discord.Embed(title="🎉 RANK UP 🎉 ", description=get_msg(MESSAGES_RANK_UP, event[2]), color=discord.Color.green())
                embed.set_thumbnail(url=f"https://www.ewgf.gg/static/rank-icons/{event[2].replace(' ', '')}T8.webp")
                file_path = self.get_random_video(VIDEOS_RANK_UP)
            elif evt == "derank":
                embed = discord.Embed(title="📉 DERANK 📉 ", description=get_msg(MESSAGES_DERANK, event[2]), color=discord.Color.red())
                file_path = self.get_random_video(VIDEOS_DERANK)

            if embed:
                await channel.send(content=ping_content, embed=embed)
                if file_path:
                    await asyncio.sleep(0.5)
                    await channel.send(file=discord.File(file_path))
        except Exception as e:
            print(f"Error sending event: {e}")

    # --- REPORTS ---
    async def send_daily_report(self, channel, data):
        embed = discord.Embed(title="📅 Daily Report", color=discord.Color.blue())
        files = []
        if os.path.exists(TEKKEN8_LOGO):
            files.append(discord.File(TEKKEN8_LOGO, filename="logo.png"))
            embed.set_thumbnail(url="attachment://logo.png")
        if os.path.exists(WIDE_SPACER_IMAGE):
            files.append(discord.File(WIDE_SPACER_IMAGE, filename="spacer.png"))
            embed.set_image(url="attachment://spacer.png")

        txt = ""
        for r in data['stats']:
            total_games = r['wins'] + r['losses']
            icon = "⚡" if r['winrate'] >= 55 else "✔" if r['winrate'] >= 50 else "🗿"
            # --- LOGIQUE D'AFFICHAGE DU RANG ---
            if r.get('start_rank') and r['start_rank'] != r['rank']:
                # S'il y a eu un changement dans la journée
                rank_display = f"{r['start_rank']} ➜ **{r['rank']}**"
            else:
                # Si le rang est resté le même
                rank_display = f"**{r['rank']}**"

            txt += f"\n {icon} **⮞ {r['name']}** • {rank_display}\n> **{r['wins']}W** - {r['losses']}L | **{total_games} Games** ({r['winrate']}%)\n\n"
        
        if txt: embed.add_field(name="\n📊 Stats\n", value=txt, inline=False)
        
        aw = data['awards']
        aw_l = []

        if aw.get('goat'): 
            # aw['goat'] est maintenant (Nom, Winrate, Games)
            aw_l.append(f"\n\n 🐐 **GOAT** 🐐 : {aw['goat'][0]} ({aw['goat'][1]}% WR)")
        if aw.get('fraude'): 
            # aw['fraude'] est maintenant (Nom, Winrate, Games)
            aw_l.append(f"🐒 **FRAUDE** 🐒 : {aw['fraude'][0]} ({aw['fraude'][1]}% WR)")
        
        if aw_l: embed.add_field(name="\n" + "\n 🏆 Awards\n", value="\n \n".join(aw_l), inline=False)
        await channel.send(embed=embed, files=files)

    # --- WEEKLY REPORT (CLEAN) ---
# --- WEEKLY REPORT (VISUEL AÉRÉ) ---
    async def send_weekly_report(self, channel, data):
        embed = discord.Embed(title="📆 Weekly Report\n", color=discord.Color.gold())
        files = []
        
        if os.path.exists(TEKKEN8_LOGO):
            files.append(discord.File(TEKKEN8_LOGO, filename="logo.png"))
            embed.set_thumbnail(url="attachment://logo.png")
            
        if data.get('chart'):
            files.append(discord.File(data['chart'], filename="chart.png"))
            embed.set_image(url="attachment://chart.png")
        elif os.path.exists(WIDE_SPACER_IMAGE):
            files.append(discord.File(WIDE_SPACER_IMAGE, filename="spacer.png"))
            embed.set_image(url="attachment://spacer.png")

        embed.add_field(name="\u200b", value="\u200b", inline=False)

        # --- BOUCLE DES JOUEURS ---
        for r in data['stats']:
            icon = " ➜ " if r['start_rank'] != r['end_rank'] else "»"
            
            # Construction du "Bloc" de texte
            # On utilise \n au début pour aérer par rapport au titre du joueur
            block_content = f"Rank: {r['start_rank']} {icon} **{r['end_rank']}**\n"
            block_content += f"Stats: **{r['wins']}W** - {r['losses']}L | {r['total_games']} Games ({r['winrate']}%)\n\n"
            
            if r['prime_time']:
                period, p_wr = r['prime_time']
                block_content += f"⌚ **Rythme :** Puissant le **{period}** ({p_wr}% WR).\n"
            else:
                block_content += "⌚ **Rythme :** Joueur irrégulier.\n"

            if r['clutch']:
                c_wr, c_total = r['clutch']
                if c_wr >= 60: mental_msg = f"A été goatesque sur {c_total} matchs close ({c_wr}%)."
                elif c_wr <= 40: mental_msg = f"A crashout sur {c_total} matchs close ({c_wr}%)."
                else: mental_msg = f"Mental solide sur {c_total} matchs close ({c_wr}%)."
                block_content += f"🧠 **Mental :** {mental_msg}\n"

            if r.get('most_faced'):
                char, count, wr = r['most_faced']
                block_content += f"🎯 **Harcèlement :** A affronté **{char}** {count} fois ({wr}% WR)."

            # Ajout du champ Joueur
            embed.add_field(name=f"** 🕹️  {r['name']}**", value=block_content, inline=False)
            
            # --- ASTUCE VISUELLE : Champ vide pour créer l'espace entre les joueurs ---
            # Cela crée une séparation nette avant le prochain joueur ou les awards
            #embed.add_field(name="\u200b", value="\u200b", inline=False)
            embed.add_field(name="\n", value="\n" + "\n", inline=False)


        # --- SECTION AWARDS ---
        aw = data['awards']
        aw_l = []
        
        if aw['locked_in'] and aw['locked_in']['name']: 
            aw_l.append(f"\n 🔒 **Locked in** : {aw['locked_in']['name']} ({aw['locked_in']['count']} victoires contre Rangs + élevés que le sien)")
        if aw['unlucky'] and aw['unlucky']['name']: 
            aw_l.append(f"💔 **Unlucky** : {aw['unlucky']['name']} ({aw['unlucky']['count']} défaites serrées)")
        if aw['chomeur'] and aw['chomeur']['name']: 
            aw_l.append(f"🛌 **Le chômeur** : {aw['chomeur']['name']} ({aw['chomeur']['count']} matchs joués dans la semaine)")
# --- MODIFICATION ICI ---
        if aw.get('goat'): 
            aw_l.append(f"🐐 **GOAT** 🐐 : {aw['goat'][0]} ({aw['goat'][1]}% WR)")
        if aw.get('fraude'): 
            aw_l.append(f"🐒 **FRAUDE** 🐒 : {aw['fraude'][0]} ({aw['fraude'][1]}% WR)")
        # ----------------------
        
        if aw_l: 
            embed.add_field(
                name="\u200b", 
                value="**✨ Awards**\n\n" + "\n".join(aw_l), 
                inline=False
            )
        
        await channel.send(embed=embed, files=files)

def run_bot():
    bot = TekkenBot()
    bot.run(DISCORD_TOKEN)
