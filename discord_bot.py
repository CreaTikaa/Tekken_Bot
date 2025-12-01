# discord_bot.py
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime, timezone
import pytz
import os
import random

from config import (
    DISCORD_TOKEN, ANNOUNCE_CHANNEL_ID, RANK_UP_CHANNEL_ID, 
    REPORT_CHANNEL_ID, TEST_CHANNEL_ID, STATUS_COMMAND_GUILD_IDS, 
    INTERVAL_ACTIVE, INTERVAL_IDLE, INTERVAL_SLEEP, ACTIVITY_THRESHOLD,
    VIDEOS_LOSE_3, VIDEOS_LOSE_5, VIDEOS_LOSE_8, VIDEOS_LOSE_10,
    VIDEOS_WIN_3, VIDEOS_WIN_5, VIDEOS_WIN_8, VIDEOS_WIN_10, 
    VIDEOS_RANK_UP, VIDEOS_KING_PICK, VIDEOS_DERANK, 
    PLAYERS, DISCORD_IDS
)
from player_manager import PlayerManager

TZ_PARIS = pytz.timezone("Europe/Paris")
intents = discord.Intents.default()
intents.message_content = True

WIDE_SPACER_IMAGE = "images/spacer.png"
TEKKEN8_LOGO = "images/Tekken-8-Logo.png"

# -----------------------
# SLASH COMMANDS
# -----------------------
@app_commands.command(name="tekken_status", description="Afficher les stats d'un joueur")
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
    
    footer_text = f"Données : EWGF & Wavu • {p.name}"
    embed.set_footer(text=footer_text)
    
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="test_events", description="ADMIN: Tester events + reports")
async def test_events(interaction: discord.Interaction):
    bot = interaction.client
    channel = bot.get_channel(TEST_CHANNEL_ID)
    if not channel: return await interaction.response.send_message("Channel introuvable", ephemeral=True)
    
    await interaction.response.send_message("🧪 Tests lancés...", ephemeral=True)
    dummy = list(PLAYERS.keys())[0]
    
    # Liste complète des events
    scenarios = [
        ("king_picked", {}),
        ("lose_streak_3", 3),
        ("lose_streak_5", 5),
        ("lose_streak_8", 8),
        ("lose_streak_10", 10),
        ("win_streak_3", 3),
        ("win_streak_5", 5),
        ("win_streak_8", 8),
        ("win_streak_10", 10),
        ("rank_up", "Garyu", "Tenryu"),
        ("derank", "Tenryu", "Garyu")
    ]
    
    await channel.send("🔹 **--- TEST EVENTS ---**")
    for evt in scenarios:
        mock = (evt[0], evt[1], evt[2]) if len(evt) > 2 else (evt[0], evt[1])
        await bot.handle_event(channel, dummy, mock)
        await asyncio.sleep(2)

    # Daily Report (Simulé)
    await channel.send("🔹 **--- TEST DAILY ---**")
    mock_stats = [
        {'name': dummy, 'wins': 10, 'losses': 5, 'winrate': 66.6, 'rank': 'Garyu'},
        {'name': 'Jean-Michel', 'wins': 2, 'losses': 20, 'winrate': 10.0, 'rank': 'Beginner'}
    ]
    await bot.send_daily_report(channel, {'stats': mock_stats, 'awards': {'goat': (dummy, 10), 'fraude': ('Jean-Michel', 20)}})
    
    # Weekly Report (Simulé)
    await channel.send("🔹 **--- TEST WEEKLY ---**")
    mock_weekly = [
        {'name': dummy, 'start_rank': 'Garyu', 'end_rank': 'Tenryu', 'wins': 45, 'losses': 30, 'winrate': 60.0},
        {'name': 'Jean-Michel', 'start_rank': 'Brawler', 'end_rank': 'Brawler', 'wins': 10, 'losses': 50, 'winrate': 16.6}
    ]
    mock_awards = {
        'unlucky': {'name': 'Jean-Michel', 'count': 12},
        'locked_in': {'name': dummy, 'count': 8},
        'chomeur': {'name': dummy, 'count': 75}
    }
    await bot.send_weekly_report(channel, {'stats': mock_weekly, 'awards': mock_awards})

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
                        if data and report_ch: 
                            await self.send_daily_report(report_ch, data)

                if now.weekday() == 6 and now.hour == 23 and now.minute >= 55:
                    if any(p.last_weekly_report_date != today for p in self.pm.players.values()):
                        data = self.pm.generate_weekly_report(today)
                        if data and report_ch: 
                            await self.send_weekly_report(report_ch, data)

                # --- 3. DYNAMIC REFRESH LOGIC ---
                
                # Check if anyone is "Active" (played a game recently)
                is_active_mode = False
                current_timestamp = datetime.now().timestamp()
                
                for p in self.pm.players.values():
                    if p.games:
                        # Get timestamp of the very last game played
                        last_game_time = p.games[0]['timestamp_unix']
                        # If the game happened within the Activity Threshold (20 mins)
                        if (current_timestamp - last_game_time) < ACTIVITY_THRESHOLD:
                            is_active_mode = True
                            break # Found someone playing, no need to check others

                # Determine how long to sleep
                if is_active_mode:
                    sleep_time = INTERVAL_ACTIVE  # 20 seconds
                    print(f"Active mode. Refresh dans {sleep_time}s.")
                else:
                    # Check for Night Mode (2am to 10am Paris time)
                    if 2 <= now.hour < 10:
                        sleep_time = INTERVAL_SLEEP # 1 hour
                        print(f"Night Mode. Refresh dans {sleep_time}s.")
                    else:
                        sleep_time = INTERVAL_IDLE  # 20 minutes
                        print(f"Idle Mode. Refresh dans {sleep_time}s.")

                await asyncio.sleep(sleep_time)

            except Exception as e:
                print(f"Loop Error: {e}")
                # In case of error, default to a safe 30 min wait
                await asyncio.sleep(1800)

    # --- HELPERS ---
    def get_random_video(self, video_list):
        if not video_list: return None
        valid = [v for v in video_list if os.path.exists(v)]
        return random.choice(valid) if valid else None

    async def handle_event(self, channel, p_name, event):
        if not channel: return
        mention = f"<@{DISCORD_IDS.get(p_name)}>" if p_name in DISCORD_IDS else f"**{p_name}**"
        evt = event[0]
        
        # Redirection test
        if channel.id == TEST_CHANNEL_ID and channel.id != ANNOUNCE_CHANNEL_ID: pass
        elif evt in ["rank_up", "derank"]: 
            rc = self.get_channel(RANK_UP_CHANNEL_ID)
            if rc: channel = rc

        try:
            embed, file_path = None, None

            if evt == "king_picked":
                embed = discord.Embed(title="🐆 KING DETECTED 🐆", description=f"{mention} à pick KING !", color=discord.Color.orange())
                file_path = self.get_random_video(VIDEOS_KING_PICK)
            
            # --- LOSE STREAKS ---
            elif evt == "lose_streak_3":
                embed = discord.Embed(title="💀 Lose Streak 💀", description=f"{mention} enchaîne 3 défaites... c'est un peu une merde...", color=0x8B0000)
                file_path = self.get_random_video(VIDEOS_LOSE_3)
            elif evt == "lose_streak_5":
                embed = discord.Embed(title="⚰️ Lose Streak ⚰️", description=f"{mention} 5 défaites... Il est vraiment intankable...", color=0x000000)
                file_path = self.get_random_video(VIDEOS_LOSE_5)
            elif evt == "lose_streak_8":
                embed = discord.Embed(title="🏴‍☠️ DISASTER 🏴‍☠️", description=f"{mention} sombre totalement... 8 défaites. Il faut absolument consulter un médecin", color=0x000000)
                file_path = self.get_random_video(VIDEOS_LOSE_8)
            elif evt == "lose_streak_10":
                embed = discord.Embed(title="🏳️ ABANDONNE 🏳️", description=f"{mention} est à 10 défaites. https://www.suicide-ecoute.fr/", color=0x000000)
                file_path = self.get_random_video(VIDEOS_LOSE_10)

            # --- WIN STREAKS ---
            elif evt == "win_streak_3":
                embed = discord.Embed(title="🔥 Win Streak 🔥", description=f"{mention} enchaîne 3 victoires ! Belle bite", color=discord.Color.gold())
                file_path = self.get_random_video(VIDEOS_WIN_3)
            elif evt == "win_streak_5":
                embed = discord.Embed(title="🚀 MEGA TEUB 🚀 ", description=f"{mention} enchâine 5 victoires ! Le pénis est vraiment excessivement large !", color=discord.Color.teal())
                file_path = self.get_random_video(VIDEOS_WIN_5)
            elif evt == "win_streak_8":
                embed = discord.Embed(title="🌟 GOAT 🌟", description=f"{mention} est le GOAT ! 8 victoires ! Il a très bien regardé la vidéo de Review", color=discord.Color.purple())
                file_path = self.get_random_video(VIDEOS_WIN_8)
            elif evt == "win_streak_10":
                embed = discord.Embed(title="👑 IMMORTAL 👑", description=f"{mention} FUME LA GRAND MERE A ARSLAN ASH ! 10 VICTOIRES !", color=discord.Color.magenta())
                file_path = self.get_random_video(VIDEOS_WIN_10)

            elif evt == "rank_up":
                embed = discord.Embed(title="🎉 RANK UP 🎉 ", description=f"{mention} est passé **{event[2]}** En route pour devenir le goat ? ", color=discord.Color.green())
                embed.set_thumbnail(url=f"https://www.ewgf.gg/static/rank-icons/{event[2].replace(' ', '')}T8.webp")
                file_path = self.get_random_video(VIDEOS_RANK_UP)

            elif evt == "derank":
                embed = discord.Embed(title="📉 DERANK 📉 ", description=f"{mention} est retombé **{event[2]}** ! Faut réviser les combos frérot...", color=discord.Color.red())
                file_path = self.get_random_video(VIDEOS_DERANK)

            if embed:
                # NEW LINE: We pass 'mention' into the content parameter
                # This puts the ping OUTSIDE the embed to trigger the notification
                await channel.send(content=mention, embed=embed)
                
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
            icon = "🔥" if r['winrate'] >= 60 else "✅" if r['winrate'] >= 50 else "⚠️"
            txt += f"{icon} **{r['name']}** • {r['rank']}\n> {r['wins']}W - {r['losses']}L ({r['winrate']}%)\n\n"
        
        if txt: embed.add_field(name="📊 Stats", value=txt, inline=False)
        
        aw = data['awards']
        aw_l = []
        if aw['goat']: aw_l.append(f"\n 🐐 **GOAT** 🐐 : {aw['goat'][0]} ({aw['goat'][1]} wins)")
        if aw['fraude']: aw_l.append(f"🤡 **FRAUDE** 🤡 : {aw['fraude'][0]} ({aw['fraude'][1]} looses)")
        
        if aw_l: embed.add_field(name=" \n 🏆 Awards", value="\n \n".join(aw_l), inline=False)
        await channel.send(embed=embed, files=files)

    async def send_weekly_report(self, channel, data):
        embed = discord.Embed(title="📆 Weekly Report", color=discord.Color.gold())
        files = []
        if os.path.exists(TEKKEN8_LOGO):
            files.append(discord.File(TEKKEN8_LOGO, filename="logo.png"))
            embed.set_thumbnail(url="attachment://logo.png")
        if os.path.exists(WIDE_SPACER_IMAGE):
            files.append(discord.File(WIDE_SPACER_IMAGE, filename="spacer.png"))
            embed.set_image(url="attachment://spacer.png")

        for r in data['stats']:
            icon = " ⬩➤ " if r['start_rank'] != r['end_rank'] else "➜"
            val = f"Rank: {r['start_rank']} {icon} **{r['end_rank']}**\nStats: **{r['wins']}W** - {r['losses']}L ({r['winrate']}%) \n"
            embed.add_field(name=f"👤 {r['name']}", value=val, inline=False)
            
        aw = data['awards']
        stxt = ""
        if aw['locked_in'] and aw['locked_in']['name']: stxt += f"🔒 **LOCKED IN** 🔒 : {aw['locked_in']['name']}\n"
        if aw['unlucky'] and aw['unlucky']['name']: stxt += f"💔 **UNLUCKY** 💔 : {aw['unlucky']['name']}\n"
        if aw['chomeur'] and aw['chomeur']['name']: stxt += f"🛌 **CHÔMEUR** 🛌 : {aw['chomeur']['name']}\n"
        
        if stxt: embed.add_field(name="\n ✨ Awards", value=stxt, inline=False)
        await channel.send(embed=embed, files=files)

def run_bot():
    bot = TekkenBot()
    bot.run(DISCORD_TOKEN)