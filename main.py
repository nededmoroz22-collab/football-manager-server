import os
import random
import time
from datetime import datetime
import requests
from flask import Flask

DATABASE_SECRET = "xgEDutCHwe6LmCCoLDzKxjGQ05JZOJvUCmvqgvZa"
FIREBASE_URL = "https://footballmanager-55784-default-rtdb.europe-west1.firebasedatabase.app"

print(f"🚀 Старт REST-сервера. URL базы: {FIREBASE_URL}", flush=True)

app = Flask(__name__)


def fb_get(path):
    """Читает данные из Firebase по пути."""
    url = f"{FIREBASE_URL}/{path}.json?auth={DATABASE_SECRET}"
    for _ in range(3):
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                return r.json()
            return None
        except Exception:
            time.sleep(1)
    return None


def fb_patch(path, data):
    """Обновляет данные в Firebase по пути."""
    url = f"{FIREBASE_URL}/{path}.json?auth={DATABASE_SECRET}"
    for _ in range(3):
        try:
            r = requests.patch(url, json=data, timeout=15)
            if r.status_code == 200:
                return True
        except Exception:
            time.sleep(1)
    return False


def fb_post(path, data):
    """Добавляет новую запись в Firebase по пути."""
    url = f"{FIREBASE_URL}/{path}.json?auth={DATABASE_SECRET}"
    try:
        requests.post(url, json=data, timeout=15)
    except Exception:
        pass


def clean_node(name):
    return str(name).strip().replace(".", "").replace("#", "").replace("$", "")


def update_league_table(league_name, team_name, gs, gc, pts):
    node = clean_node(team_name)
    path = f"leagues_data/{str(league_name).strip()}/table/{node}"
    snapshot = fb_get(path)

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

    if gs > gc:
        wins += 1
    elif gs == gc:
        draws += 1
    else:
        losses += 1

    fb_patch(path, {
        "clubName": str(team_name).strip(), "played": played, "points": points,
        "gs": goals_s, "gc": goals_c, "wins": wins, "draws": draws, "losses": losses
    })


def get_lineup(lineups, club_name):
    """Берёт состав клуба. Если человек не подтвердил — возвращает средние значения бота."""
    node = clean_node(club_name)
    if lineups and isinstance(lineups, dict) and node in lineups:
        data = lineups[node]
        if isinstance(data, dict):
            att = int(data.get('attackOvr', 75))
            dfn = int(data.get('defenseOvr', 75))
            is_human = bool(data.get('isHuman', False))
            return att, dfn, is_human
    # Бот или игрок, не подтвердивший состав
    return random.randint(72, 82), random.randint(72, 82), False


def play_match(att_home, def_home, att_away, def_away):
    """Симулирует матч на основе силы атаки/защиты обеих команд."""
    score_h = score_a = 0
    for _ in range(90):
        if random.randint(0, 100) < 23:
            if random.choice([True, False]):
                prob = max(8, min(40, 18 + (att_home - def_away)))
                if random.randint(0, 100) < prob:
                    score_h += 1
            else:
                prob = max(8, min(40, 18 + (att_away - def_home)))
                if random.randint(0, 100) < prob:
                    score_a += 1
    return score_h, score_a


def build_round_pairs(all_teams, tour_number):
    """Строит пары матчей для конкретного тура (круговая система)."""
    teams = [str(t).strip() for t in all_teams if t]
    if len(teams) % 2 != 0:
        teams.append("ОТДЫХ")

    count = len(teams)
    rounds_count = (count - 1) * 2
    tour_index = (tour_number - 1) % rounds_count

    fixed = teams[0]
    moving = teams[1:]
    offset = tour_index % (count - 1)
    rotated = moving[-offset:] + moving[:-offset] if offset > 0 else moving
    round_teams = [fixed] + rotated

    pairs = []
    is_second_round = tour_index >= (count - 1)
    for i in range(count // 2):
        home = round_teams[i] if not is_second_round else round_teams[count - 1 - i]
        away = round_teams[count - 1 - i] if not is_second_round else round_teams[i]
        if home == "ОТДЫХ" or away == "ОТДЫХ":
            continue
        pairs.append((home, away))
    return pairs


def run_scheduled_tour(trigger_data):
    """Рассчитывает весь тур: все пары, с учётом подтверждённых составов."""
    league_name = str(trigger_data.get('leagueName', 'La Liga')).strip()
    current_tour = int(trigger_data.get('tourNumber', 1))
    clubs_list = trigger_data.get('clubsList', [])

    if not clubs_list:
        print("⚠️ Список клубов пуст, расчёт отменён.", flush=True)
        return

    print(f"🏟️ СЕРВЕР: Запускаю тур {current_tour} лиги '{league_name}' по расписанию...", flush=True)

    # Загружаем все подтверждённые составы этого тура одним запросом
    lineups = fb_get(f"leagues_data/{league_name}/lineups/tour_{current_tour}")

    pairs = build_round_pairs(clubs_list, current_tour)
    fixtures_path = f"leagues_data/{league_name}/fixtures/tour_{current_tour}"

    for home, away in pairs:
        att_h, def_h, human_h = get_lineup(lineups, home)
        att_a, def_a, human_a = get_lineup(lineups, away)

        score_h, score_a = play_match(att_h, def_h, att_a, def_a)

        pts_h = 3 if score_h > score_a else (1 if score_h == score_a else 0)
        pts_a = 3 if score_a > score_h else (1 if score_h == score_a else 0)

        update_league_table(league_name, home, score_h, score_a, pts_h)
        update_league_table(league_name, away, score_a, score_h, pts_a)

        fb_post(fixtures_path, {
            "homeTeam": home,
            "awayTeam": away,
            "homeScore": score_h,
            "awayScore": score_a,
            "homeScorers": f"{score_h} гол(ов)" if score_h > 0 else "Нет голов",
            "awayScorers": f"{score_a} гол(ов)" if score_a > 0 else "Нет голов",
            "homeIsHuman": human_h,
            "awayIsHuman": human_a
        })

    # Тур сыгран: гасим расписание, увеличиваем номер тура
    fb_patch("sys_trigger", {
        "status": "FINISHED",
        "nextTourTime": "",
        "tourNumber": current_tour + 1,
        "lastPlayedTour": current_tour
    })

    print(f"✅ Тур {current_tour} лиги '{league_name}' рассчитан. Матчей: {len(pairs)}", flush=True)


def is_time_to_play(next_tour_time):
    """Проверяет, наступило ли назначенное время тура. Формат: 2026-09-15 20:00"""
    if not next_tour_time:
        return False
    try:
        target = datetime.strptime(str(next_tour_time).strip(), "%Y-%m-%d %H:%M")
        return datetime.now() >= target
    except Exception as e:
        print(f"⚠️ Не удалось прочитать время тура '{next_tour_time}': {e}", flush=True)
        return False


@app.route('/', methods=['GET', 'HEAD'])
def home_ping_check():
    trigger_data = fb_get("sys_trigger")

    if trigger_data and isinstance(trigger_data, dict):
        next_time = trigger_data.get('nextTourTime', '')

        if is_time_to_play(next_time):
            try:
                run_scheduled_tour(trigger_data)
                return "Тур рассчитан по расписанию!", 200
            except Exception as e:
                print(f"Сбой расчёта тура: {e}", flush=True)
                fb_patch("sys_trigger", {"status": "ERROR", "errorText": str(e)})
                return f"Ошибка расчёта: {e}", 200

    return "Футбольный MMO-сервер активен. Ждём времени тура.", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
