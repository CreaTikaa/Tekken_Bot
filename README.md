tekken_bot/
│
├── main.py                 → starts bot + background tasks
├── discord_bot.py          → discord commands + event posting
├── player_manager.py       → manages all Player objects
├── player.py               → Player class (rank, wins, history, detection)
├── data_fetcher.py         → curl scraper + parser
└── config.py               → player list, refresh interval, URLs
