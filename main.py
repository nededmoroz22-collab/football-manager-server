import time
import random
import threading
import os
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask

# 🔌 1. Создаем микро-сайт "для галочки", чтобы обмануть сканер портов Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Футбольный MMO-сервер работает!", 200

def run_flask():
    # Render сам выдает номер порта в переменную окружения PORT, берем его или ставим 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# Запускаем веб-заглушку в отдельном фоновом потоке
threading.Thread(target=run_flask, daemon=True).start()


# 🌐 2. Подключение к твоему Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://footballmanager-55784-default-rtdb.europe-west1.firebasedatabase.app'
})

print("🚀 Футбольный MMO-сервер успешно запущен и слушает Firebase...")

def update_league_table(league_name, team_name, gs, gc, pts):
    clean_name = team_name.strip().replace(".", "")
    ref = db.reference(f'leagues_data/{league_name}/table/{clean_name}')
    snapshot = ref.get()
    played = points = goals_s = goals_c = wins = draws = losses = 0
    
    if snapshot:
        played = snapshot.get('played', 0)
        points = snapshot.get('points', 0)
        goals_s = snapshot.get('gs', 0)
        goals_c = snapshot.get('gc', 0)
        wins = snapshot.get('wins', 0)
        draws = snapshot.get('draws', 0)
        losses = snapshot.get('losses', 0)
        
    played += 1
    points += pts
    goals_s += gs
    goals_c += gc
    
    if gs > gc: wins += 1
    elif gs == gc: draws += 1
    else: losses += 1
    
    ref.update({
        "clubName": team_name.strip(), "played": played, "points": points,
        "gs": goals_s, "gc": goals_c, "wins": wins, "draws": draws, "losses": losses
    })

def simulate_mmo_tour(league_name, current_tour):
    print(f"🏟️ Начинаю серверный расчет {current_tour} тура для лиги {league_name}...")
    lineups_ref = db.reference(f'leagues_data/{league_name}/lineups/tour_{current_tour}')
    teams_data = lineups_ref.get()
    
    if not teams_data:
        print("❌ Ошибка: Составы не найдены.")
        return
        
    all_teams = list(teams_data.keys())
    if len(all_teams) < 2: return
    
    random.shuffle(all_teams)
    busy_teams = set()
    free_teams = [t for t in all_teams if t not in busy_teams]
    
    fixtures_ref = db.reference(f'leagues_data/{league_name}/fixtures/tour_{current_tour}')
    
    while len(free_teams) >= 2:
        team_a = free_teams.pop(0)
        team_b = next((t for t in free_teams if t != team_a), None)
        
        if team_b:
            free_teams.remove(team_b)
            busy_teams.add(team_a)
            busy_teams.add(team_b)
            
            ovr_a = teams_data[team_a].get('attackOvr', 75)
            def_b = teams_data[team_b].get('defenseOvr', 75)
            ovr_b = teams_data[team_b].get('attackOvr', 75)
            def_a = teams_data[team_a].get('defenseOvr', 75)
            
            score_a = score_b = 0
            for _ in range(90):
                if random.randint(0, 100) < 23:
                    is_home_action = random.choice([True, False])
                    if is_home_action:
                        prob = max(12, min(35, 18 + (ovr_a - def_b)))
                        if random.randint(0, 100) < prob: score_a += 1
                    else:
                        prob = max(12, min(35, 18 + (ovr_b - def_a)))
                        if random.randint(0, 100) < prob: score_b += 1
                        
            pts_a = 3 if score_a > score_b else (1 if score_a == score_b else 0)
            pts_b = 3 if score_b > score_a else (1 if score_a == score_b else 0)
            
            update_league_table(league_name, team_a, score_a, score_b, pts_a)
            update_league_table(league_name, team_b, score_b, score_a, pts_b)
            
            fixtures_ref.push().set({
                "homeTeam": team_a, "awayTeam": team_b,
                "homeScore": score_a, "awayScore": score_b,
                "homeScorers": f"Игрок А. {score_a} гол(ов)" if score_a > 0 else "Нет голов",
                "awayScorers": f"Игрок Б. {score_b} гол(ов)" if score_b > 0 else "Нет голов"
            })
    print(f"✅ Расчет {current_tour} тура успешно завершен!")

# 🔄 Вечный цикл прослушивания Firebase
while True:
    try:
        trigger_ref = db.reference('sys_trigger')
        trigger_data = trigger_ref.get()
        
        if trigger_data and trigger_data.get('status') == 'REQUESTED':
            league = trigger_data.get('leagueName', 'La Liga')
            tour = trigger_data.get('tourNumber', 1)
            
            simulate_mmo_tour(league, tour)
            trigger_ref.update({'status': 'FINISHED'})
            
    except Exception as e:
        print(f"Ошибка: {e}")
        
    time.sleep(2)
