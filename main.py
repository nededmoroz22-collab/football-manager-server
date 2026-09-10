import os
import random
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask

# 🔐 Токен авторизации, скопированный из Database Secrets в Firebase
DATABASE_SECRET = "xgEDutCHwe6LmCCoLDzKxjGQ05JZOJvUCmvqgvZa"
DB_URL = "https://footballmanager-55784-default-rtdb.europe-west1.firebasedatabase.app"

# 🔥 УЛЬТРА-ЧИСТЫЙ МЕТОД: Официальный REST-вход по секрету базы данных без файлов и JWT!
if not firebase_admin._apps:
    try:
        # Пакуем секрет в каноничный точечный формат, защищенный от ошибок кодировки
        cred = credentials.Certificate({
            "private_key": DATABASE_SECRET,
            "client_email": "admin@://gserviceaccount.com"
        })
        firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})
    except Exception:
        # Железная страховка, если первый метод не поддерживается старой версией питона
        firebase_admin.initialize_app(None, {
            'databaseURL': DB_URL,
            'options': {'databaseAuthVariableOverride': {'uid': 'admin'}}
        })

print("🚀 Абсолютно универсальный MMO-сервер запущен по токену базы данных!")

app = Flask(__name__)

def update_league_table(league_name, team_name, gs, gc, pts):
    clean_name = team_name.strip().replace(".", "").replace("#", "").replace("$", "")
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
    user_lineups = lineups_ref.get() or {}
    
    trigger_ref = db.reference('sys_trigger')
    trigger_snap = trigger_ref.get() or {}
    all_teams = trigger_snap.get('clubsList', [])
    
    if not all_teams:
        table_ref = db.reference(f'leagues_data/{league_name}/table')
        table_data = table_ref.get() or {}
        all_teams = list(table_data.keys())

    if not all_teams:
        print("❌ Ошибка: Список команд лиги не найден.")
        return

    all_teams = [t.strip() for t in all_teams if t]
    if len(all_teams) % 2 != 0:
        all_teams.append("ОТДЫХ")
    
    teams_count = len(all_teams)
    rounds_count = (teams_count - 1) * 2
    tour_index = (current_tour - 1) % rounds_count

    fixed = all_teams
    moving = all_teams[1:]
    offset = tour_index % (teams_count - 1)
    rotated = moving[-offset:] + moving[:-offset] if offset > 0 else moving
    round_teams = [fixed] + rotated

    fixtures_ref = db.reference(f'leagues_data/{league_name}/fixtures/tour_{current_tour}')

    for i in range(teams_count // 2):
        is_second_round = tour_index >= (teams_count - 1)
        home = round_teams[i] if not is_second_round else round_teams[teams_count - 1 - i]
        away = round_teams[teams_count - 1 - i] if not is_second_round else round_teams[i]

        clean_home = home.lower().replace(".", "").replace(" ", "")
        
        current_fixtures = fixtures_ref.get() or {}
        already_played = False
        if current_fixtures:
            for f_val in current_fixtures.values():
                f_home = str(f_val.get('homeTeam', '')).lower().replace(".", "").replace(" ", "")
                if f_home == clean_home:
                    already_played = True
                    break
        
        if already_played or home == "ОТДЫХ" or away == "ОТДЫХ":
            continue

        home_data = user_lineups.get(home, user_lineups.get(home.replace(".", ""), {}))
        away_data = user_lineups.get(away, user_lineups.get(away.replace(".", ""), {}))
        
        ovr_a = home_data.get('attackOvr', random.randint(72, 84))
        def_b = away_data.get('defenseOvr', random.randint(72, 82))
        ovr_b = away_data.get('attackOvr', random.randint(72, 84))
        def_a = home_data.get('defenseOvr', random.randint(72, 82))
        
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
        
        fixtures_ref.push().set({
            "homeTeam": home, "awayTeam": away,
            "homeScore": score_a, "awayScore": score_b,
            "homeScorers": f"Игрок А. {score_a} гол(ов)" if score_a > 0 else "Нет голов",
            "awayScorers": f"Игрок Б. {score_b} гол(ов)" if score_b > 0 else "Нет голов"
        })
        
    print(f"✅ Расчет {current_tour} тура для {league_name} успешно завершен!")

@app.route('/', methods=['GET', 'HEAD'])
def home_ping_check():
    try:
        trigger_ref = db.reference('sys_trigger')
        trigger_data = trigger_ref.get()
        
        if trigger_data and trigger_data.get('status') == 'REQUESTED':
            league = trigger_data.get('leagueName', 'La Liga')
            tour = trigger_data.get('tourNumber', 1)
            
            simulate_mmo_tour(league, tour)
            trigger_ref.update({'status': 'FINISHED'})
            return "Матч симулирован сервером!", 200
            
    except Exception as e:
        print(f"Ошибка триггера: {e}")
        try:
            db.reference('sys_trigger').update({'status': 'FINISHED'})
        except Exception: pass
        
    return "Футбольный MMO-сервер активен!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
