# chart_generator.py
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import io

# NOUVELLE PALETTE (Sans Rouge pur ni Vert pur)
COLORS = [
    '#00FFFF', # Cyan (Bleu électrique)
    '#FF00FF', # Magenta (Rose fluo)
    '#FFFF00', # Jaune
    '#FFA500', # Orange
    '#FFFFFF', # Blanc
    '#1E90FF', # Dodger Blue (Bleu roi clair)
    '#FF69B4', # Hot Pink
    '#9370DB', # Medium Purple
    '#00FA9A'  # Medium Spring Green (Un vert menthe différent du "Vert Validé")
]

def create_weekly_graph(players_data):
    """
    players_data = {
        "Pseudo": [(timestamp, 'WIN'), (timestamp, 'LOSS'), ...],
        "Pseudo2": ...
    }
    """
    # Utiliser le style sombre pour Discord
    plt.style.use('dark_background')
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Pour chaque joueur
    for i, (name, games) in enumerate(players_data.items()):
        if not games: continue
        
        # On trie les games par date
        sorted_games = sorted(games, key=lambda x: x[0])
        
        dates = []
        scores = []
        current_score = 0
        
        # Point de départ (début de semaine à 0)
        if sorted_games:
            start_date = datetime.fromtimestamp(sorted_games[0][0])
            dates.append(start_date)
            scores.append(0)

        for ts, result in sorted_games:
            dt = datetime.fromtimestamp(ts)
            dates.append(dt)
            
            if result == 'WIN':
                current_score += 1
            else:
                current_score -= 1
            scores.append(current_score)
            
        # Couleur unique par joueur
        color = COLORS[i % len(COLORS)]
        
        # Tracer la ligne
        ax.plot(dates, scores, label=f"{name} ({current_score:+})", color=color, linewidth=2, marker='o', markersize=4)

    # Mise en forme du graphique
    ax.set_title("Évolution de la Semaine (Net Wins/Losses)", fontsize=16, color='white', pad=20)
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.legend(loc='upper left', frameon=True, facecolor='#2C2F33', edgecolor='white')
    
    # Formater les dates en bas (Jeu, Ven, Sam...)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%a'))
    
    # Ligne zéro (équilibre)
    ax.axhline(0, color='gray', linewidth=1, linestyle='-')

    # Sauvegarder en mémoire tampon (bytes)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=100, facecolor='#2C2F33')
    buf.seek(0)
    plt.close(fig) # Important pour libérer la mémoire
    
    return buf