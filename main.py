import os
import random
import time
import requests
from flask import Flask

# 🔐 Токен авторизации, скопированный из Database Secrets в Firebase
DATABASE_SECRET = "xgEDutCHwe6LmCCoLDzKxjGQ05JZOJvUCmvqgvZa"
FIREBASE_URL = "https://footballmanager-55784-default-rtdb.europe-west1.firebasedatabase.app"

print(f"🚀 Старт REST-сервера. URL базы: {FIREBASE_URL}")

app = Flask(__name__)

def update_league_table(league_name, team_name, gs, gc, pts):
    if not FIREBASE_URL or not DATABASE_SECRET: return
    clean_league = str(league_name).strip()
    clean_team = str(team_name).strip().replace(".", "").replace("#", "").replace("$", "")

    url = f"{FIREBASE_URL}/leagues_data/{clean_league}/table/{clean_team}.json?auth={DATABASE_SECRET}"
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
        "clubName": str(team_name).strip(), "played": played, "points": points,
        "gs": goals_s, "gc": goals_c, "wins": wins, "draws": draws, "losses": losses
    }
    try: requests.patch(url, json=data)
    except Exception: pass

def simulate_mmo_tour(trigger_data):
    if not FIREBASE_URL or not DATABASE_SECRET: return
    league_name = str(trigger_data.get('leagueName', 'La Liga')).strip()
    current_tour = int(trigger_data.get('tourNumber', 1))
    clubs_list = trigger_data.get('clubsList', [])

    my_club = str(trigger_data.get('myClub', '')).strip()
    opponent_club = str(trigger_data.get('opponentClub', '')).strip()
    home_score = int(trigger_data.get('homeScore', 0))
    away_score = int(trigger_data.get('awayScore', 0))
    home_scorers = str(trigger_data.get('homeScorers', 'Нет голов')).strip()
    away_scorers = str(trigger_data.get('awayScorers', 'Нет голов')).strip()

    print(f"🏟️ СЕРВЕР: Начинаю расчет {current_tour} тура для лиги '{league_name}'...")

    fixtures_url = f"{FIREBASE_URL}/leagues_data/{league_name}/fixtures/tour_{current_tour}.json?auth={DATABASE_SECRET}"
    try:
        my_pts = 3 if home_score > away_score else (1 if home_score == away_score else 0)
        opp_pts = 3 if away_score > home_score else (1 if home_score == away_score else 0)
        update_league_table(league_name, my_club, home_score, away_score, my_pts)
        update_league_table(league_name, opponent_club, away_score, home_score, opp_pts)
    except Exception: pass

    all_teams = list(clubs_list) if clubs_list else []
    if not all_teams: return

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

    clean_my_club = my_club.lower().replace(".", "").replace(" ", "")
    clean_opp_club = opponent_club.lower().replace(".", "").replace(" ", "")

    for i in range(teams_count // 2):
        is_second_round = tour_index >= (teams_count - 1)
        home = round_teams[i] if not is_second_round else round_teams[teams_count - 1 - i]
        away = round_teams[teams_count - 1 - i] if not is_second_round else round_teams[i]

        clean_home = home.lower().replace(".", "").replace(" ", "")
        clean_away = away.lower().replace(".", "").replace(" ", "")

        if clean_home == clean_my_club or clean_away == clean_my_club or clean_home == clean_opp_club or clean_away == clean_opp_club:
            continue
        if home == "ОТДЫХ" or away == "ОТДЫХ": continue

        ovr_a, def_b = random.randint(72, 84), random.randint(72, 82)
        ovr_b, def_a = random.randint(72, 84), random.randint(72, 82)

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
            "homeTeam": home, "awayTeam": away, "homeScore": score_a, "awayScore": score_b,
            "homeScorers": f"Игрок А. {score_a} гол(ов)" if score_a > 0 else "Нет голов",
            "awayScorers": f"Игрок Б. {score_b} гол(ов)" if score_b > 0 else "Нет голов"
        }
        try: requests.post(fixtures_url, json=match_data)
        except Exception: pass

    print(f"✅ Расчет {current_tour} тура для лиги '{league_name}' успешно завершен!")


@app.route('/', methods=['GET', 'HEAD'])
def home_ping_check():
    if not FIREBASE_URL or not DATABASE_SECRET:
        return "Критическая ошибка: Переменные окружения на Render не настроены!", 500

    trigger_url = f"{FIREBASE_URL}/sys_trigger.json?auth={DATABASE_SECRET}"
    try:
        response = requests.get(trigger_url)
        if response.status_code == 200:
            trigger_data = response.json()
            if trigger_data and trigger_data.get('status') == 'REQUESTED':
                try: simulate_mmo_tour(trigger_data)
                except Exception as inner: print(f"Сбой симуляции: {inner}")
                finally:
                    # Принудительно гасим триггер в базе по секретному токену
                    requests.patch(trigger_url, json={'status': 'FINISHED'})
                    return "Расчет завершен!", 200
    except Exception as e:
        print(f"Ошибка проверки триггера: {e}")

    return "Футбольный MMO-сервер активен!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
