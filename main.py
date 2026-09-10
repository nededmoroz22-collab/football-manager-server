import os
import random
import time
import requests
from flask import Flask

# 🔐 Токен авторизации, скопированный из Database Secrets в Firebase
DATABASE_SECRET = "xgEDutCHwe6LmCCoLDzKxjGQ05JZOJvUCmvqgvZa"
FIREBASE_URL = "https://footballmanager-55784-default-rtdb.europe-west1.firebasedatabase.app"

print("🚀 Запуск всеядного MMO-сервера по токену...")

app = Flask(__name__)

def update_league_table(league_name, team_name, gs, gc, pts):
    clean_name = team_name.strip().replace(".", "").replace("#", "").replace("$", "")
    url = f"{FIREBASE_URL}/leagues_data/{league_name}/table/{clean_name}.json?auth={DATABASE_SECRET}"
    try:
        response = requests.get(url)
        snapshot = response.json() if response.status_code == 200 else None
    except Exception:
        snapshot = None

    played = points = goals_s = goals_c = wins = draws = losses = 0
    if snapshot and isinstance(snapshot, dict):
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
    
    data = {
        "clubName": team_name.strip(), "played": played, "points": points,
        "gs": goals_s, "gc": goals_c, "wins": wins, "draws": draws, "losses": losses
    }
    requests.patch(url, json=data)

def simulate_mmo_tour(league_name, current_tour, clubs_list):
    print(f"🏟️ Начинаю серверный расчет {current_tour} тура для лиги {league_name}...")
    lineups_url = f"{FIREBASE_URL}/leagues_data/{league_name}/lineups/tour_{current_tour}.json?auth={DATABASE_SECRET}"
    user_lineups = requests.get(lineups_url).json() or {}
    
    all_teams = list(clubs_list) if clubs_list else []
    if not all_teams:
        table_url = f"{FIREBASE_URL}/leagues_data/{league_name}/table.json?auth={DATABASE_SECRET}"
        table_data = requests.get(table_url).json() or {}
        all_teams = list(table_data.keys())

    if not all_teams:
        print("❌ Ошибка: Список команд не найден.")
        return

    all_teams = [t.strip() for t in all_teams if t]
    if len(all_teams) % 2 != 0: all_teams.append("ОТДЫХ")
    
    teams_count = len(all_teams)
    rounds_count = (teams_count - 1) * 2
    tour_index = (current_tour - 1) % rounds_count

    fixed = all_teams
    moving = all_teams[1:]
    offset = tour_index % (teams_count - 1)
    rotated = moving[-offset:] + moving[:-offset] if offset > 0 else moving
    round_teams = [fixed] + rotated

    fixtures_url = f"{FIREBASE_URL}/leagues_data/{league_name}/fixtures/tour_{current_tour}.json?auth={DATABASE_SECRET}"

    for i in range(teams_count // 2):
        is_second_round = tour_index >= (teams_count - 1)
        home = round_teams[i] if not is_second_round else round_teams[teams_count - 1 - i]
        away = round_teams[teams_count - 1 - i] if not is_second_round else round_teams[i]

        clean_home = home.lower().replace(".", "").replace(" ", "")
        
        current_fixtures = requests.get(fixtures_url).json() or {}
        already_played = False
        if current_fixtures and isinstance(current_fixtures, dict):
            for f_val in current_fixtures.values():
                if isinstance(f_val, dict):
                    f_home = str(f_val.get('homeTeam', '')).lower().replace(".", "").replace(" ", "")
                    if f_home == clean_home: already_played = True; break
        
        if already_played or home == "ОТДЫХ" or away == "ОТДЫХ": continue

        home_data = user_lineups.get(home, user_lineups.get(home.replace(".", ""), {})) if isinstance(user_lineups, dict) else {}
        away_data = user_lineups.get(away, user_lineups.get(away.replace(".", ""), {})) if isinstance(user_lineups, dict) else {}
        
        ovr_a = home_data.get('attackOvr', random.randint(72, 84)) if isinstance(home_data, dict) else random.randint(72, 84)
        def_b = away_data.get('defenseOvr', random.randint(72, 82)) if isinstance(away_data, dict) else random.randint(72, 82)
        ovr_b = away_data.get('attackOvr', random.randint(72, 84)) if isinstance(away_data, dict) else random.randint(72, 84)
        def_a = home_data.get('defenseOvr', random.randint(72, 82)) if isinstance(home_data, dict) else random.randint(72, 82)
        
        score_a = score_b = 0
        for _ in range(90):
            if random.randint(0, 100) < 23:
                if random.choice([True, False]):
                    prob = max(12, min(35, 18 + (ovr_a - def_b)))
                    if random.randint(0, 100) < prob: score_a += 1
                else:
                    prob = max(12, min(35, 18 + (ovr_b - def_a)))
                    if random.randint(0, 100) < prob: score_b += 1
                        
        pts_a = 3 if score_a > score_b else (1 if score_a == score_b else 0)
        pts_b = 3 if score_b > score_a else (1 if score_a == score_b else 0)
        
        update_league_table(league_name, home, score_a, score_b, pts_a)
        update_league_table(league_name, away, score_b, score_a, pts_b)
        
        match_data = {
            "homeTeam": home, "awayTeam": away,
            "homeScore": score_a, "awayScore": score_b,
            "homeScorers": f"Игрок А. {score_a} гол(ов)" if score_a > 0 else "Нет голов",
            "awayScorers": f"Игрок Б. {score_b} гол(ов)" if score_b > 0 else "Нет голов"
        }
        requests.post(fixtures_url, json=match_data)
    print(f"✅ Расчет {current_tour} тура успешно завершен!")


# 🔄 🔥 НОВЫЙ БЕЗОПАСНЫЙ ПОТОК: Каждые 3 секунды самостоятельно проверяет базу данных Firebase
def background_firebase_polling():
    trigger_url = f"{FIREBASE_URL}/sys_trigger.json?auth={DATABASE_SECRET}"
    while True:
        try:
            response = requests.get(trigger_url)
            if response.status_code == 200:
                trigger_data = response.json()
                if trigger_data and trigger_data.get('status') == 'REQUESTED':
                    league = trigger_data.get('leagueName', 'La Liga')
                    tour = trigger_data.get('tourNumber', 1)
                    clubs_list = trigger_data.get('clubsList', [])
                    
                    simulate_mmo_tour(league, tour, clubs_list)
                    requests.patch(trigger_url, json={'status': 'FINISHED'})
        except Exception as e:
            pass
        time.sleep(3)

# Запускаем фоновый таймер опроса при старте сервера
threading.Thread(target=background_firebase_polling, daemon=True).start()


@app.route('/', methods=['GET', 'HEAD'])
def home_ping_check():
    return "Футбольный MMO-сервер активен и слушает порты!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
