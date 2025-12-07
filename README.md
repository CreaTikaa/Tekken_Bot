# Tekken 8 Discord Tracker Bot

> A Discord bot designed to track Tekken 8 player statistics, ranked progress, and streaks in (almost) real-time.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Discord.py](https://img.shields.io/badge/Discord.py-2.0+-blurple.svg)
![Tekken 8](https://img.shields.io/badge/Game-Tekken%208-red.svg)

> ⚠️ DISCLAIMER ⚠️ : This was completely "vibe-coded" as we say, with some (a lot) IA included. I'm still learning, and since both site didn't have an API with what i wanted, i had to generate some code mostly for the parsing and fetching data. Use at your own risks :p

## Project Structure

Here is the organization of the bot's file system:

```text
tekken_bot/
│
├── main.py                 → Entry point: initializes the bot and background loops
├── discord_bot.py          → UI Layer: Slash commands, Embed construction, Event handling
├── player_manager.py       → Logic Layer: Orchestrates updates for all players & cache cleaning
├── player.py               → Data Model: Player class, streak calculation, history management
├── data_fetcher.py         → Scraper: Async data fetching & HTML parsing (Wavu/EWGF)
├── config.py               → Configuration: Player IDs, URLs, Tokens, Video paths
│
├── data/                   → Persistence Layer
│   └── cache.json          → Stores match history and stats to survive restarts
│
├── videos/                 → Videos (mp4)
│   ├── win_streak_3.mp4
│   ├── lose_streak_5.mp4
│   ├── king_alert.mp4
│   └── ... (all reaction videos)
│
└── images/                 → Static Image 
    ├── spacer.png          → Used for wide embed formatting
    └── Tekken-8-Logo.png   → Thumbnail for reports
```

## Key Features
### Real-Time Tracking
The bot scrapes data from Wavu Wiki and EWGF every few minutes to keep stats fresh. It tracks Rank, Glicko Rating, and Main Character.

## Live Event Alerts
The bot sends immediate notifications to a dedicated channel when specific events occur:

- Win Streaks: Alerts when a player hits 3, 5, 8, or 10 wins in a row.
- Lose Streaks: Shame alerts when a player hits 3, 5, 8, or 10 losses in a row.
- Rank Updates: Beautiful embeds showing Promotion (Rank Up) or Demotion (Derank).
- King Detection: A funny, specific alert when a player shamelessly picks "King".

## Automated Reports : 

Daily Report (23:55): Summarizes the day's performance (Wins/Losses/Winrate) and awards titles like 🐐 LE GOAT and 🤡 LA FRAUDE.
Weekly Report (Sunday): A comprehensive weekly recap showing rank evolution and special awards:

- Locked In: Most wins against higher-ranked opponents.
- Unlucky: Most close defeats (2-3 scores).
- Le Chômeur: The player with the highest game count.

## Visuals & Media

Dynamic Video Responses: Plays different random video memes based on the event (Winning vs Losing).
Clean Embeds: Uses advanced formatting (spacers, thumbnails) to look great on Desktop and Mobile.

## How It Works (Architecture)

The Loop (main.py & discord_bot.py): The bot runs an asynchronous background loop defined by REFRESH_INTERVAL.
Data Fetching (data_fetcher.py): It performs parallel asynchronous requests (aiohttp) to scrape player profiles. It uses BeautifulSoup and Regex to extract hidden JSON data from web pages, retrieving match history and opponent ranks.
Data Processing (player.py): New matches are compared against the seen_game_ids set to avoid duplicates.
Streak Logic: The bot calculates streaks dynamically based only on the newly added games to prevent spamming notifications for old streaks.
Snapshotting: It saves daily and weekly snapshots to calculate progress over time.
State Management (player_manager.py): Handles the cache.json. It includes a Smart Cleaning feature that purges old match history every week to keep the database lightweight (<1MB) while preserving rank data.

## Installation & Setup

Prerequisites : 
- Python 3.9 or higher
- FFmpeg (if processing video, though discord handles the display)
- A Discord app with a Token

**1. Clone the repo**
```
git clone [https://github.com/YourUsername/Tekken_Bot.git](https://github.com/YourUsername/Tekken_Bot.git)
cd Tekken_Bot
```
**2. Install Dependencies**
```
pip install -r requirements.txt
```
**3. Configuration** 

Edit config.py:

- Add your DISCORD_TOKEN.
- Configure your Channel IDs (ANNOUNCE, REPORT, TEST).
- Add players to the PLAYERS dictionary with their Wavu/EWGF links.

**4. Run the Bot**
```
python main.py
``` 

## Commands

| Syntax | Description |
| ----------- | ----------- |
| /tekken_status [player] | Displays a detailed stat card for a specific player (Rank, Rating, Last 5 games).|
| /test_events | **Admin Only.** Simulates a full suite of events (Streaks, Rank up, Reports) to the test channel to verify videos and embeds. |

## Contributing

Feel free to submit issues or pull requests. Special thanks to the creators of Wavu Wiki and EWGF for providing the data sources.
Created for the love of Tekken (and shaming friends who keep loosing like me). 
