# main.py
from discord_bot import run_bot

if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        print("Bot arrêté.")