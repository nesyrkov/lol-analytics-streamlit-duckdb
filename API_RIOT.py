import time
import sqlite3
import requests
import pandas as pd
from pathlib import Path
from typing import Any, Dict, Union, List


API_KEY = "___"

REGION = "euw1"
ROUTING_REGION = "europe"

def riot_get(url: str) -> Dict[str, Any]:

    """
    Отправляет GET‑запрос к API Riot Games с обработкой ограничения частоты запросов (rate limiting).

    При получении ответа с кодом 429 (Too Many Requests) функция ожидает указанное сервером время
    (из заголовка 'Retry-After') и повторяет запрос. Между успешными запросами делается пауза
    в 0.06 секунды для соблюдения лимитов API.

    Args:
        url (str): URL‑адрес эндпоинта API Riot Games, к которому выполняется запрос.

    Returns:
        Dict[str, Any]: JSON‑ответ от API в виде словаря Python.

    Raises:
        requests.exceptions.HTTPError: Если запрос завершился с HTTP‑ошибкой,
            отличной от 429 (например, 404, 500 и т. д.).
        ValueError: Если значение в заголовке 'Retry-After' не может быть преобразовано в целое число.
        requests.exceptions.RequestException: При других ошибках запросов (сетевые проблемы и т. п.).

    Example:
        >>> response_data = riot_get("https://api.riotgames.com/lol/summoner/v4/summoners/by-name/ExampleName")
        >>> print(response_data["name"])
        ExampleName
    """

    headers = {
        "X-Riot-Token": API_KEY
    }

    response = requests.get(
        url,
        headers=headers
    )

    if response.status_code == 429:
        retry_after = int(
            response.headers.get(
                "Retry-After",
                5
            )
        )

        print(
            f"Лимит API. Ждем {retry_after} секунд"
        )

        time.sleep(retry_after)

        return riot_get(url)

    response.raise_for_status()

    time.sleep(0.06)

    return response.json()

def get_challenger_players(
    region: str = REGION,
    queue: str = "RANKED_SOLO_5x5"
) -> List[Dict[str, Any]]:

    """
    Получает список игроков из лиги Challenger указанного региона и очереди в игре League of Legends.

    Функция формирует URL для запроса к API Riot Games, вызывает вспомогательную функцию `riot_get`
    для выполнения HTTP‑запроса и извлекает список записей игроков (`entries`) из полученного JSON‑ответа.

    Args:
        region (str): Код региона API Riot Games (например, 'euw1', 'na1').
            По умолчанию используется значение глобальной переменной `REGION`.
        queue (str): Тип очереди (игрового режима). По умолчанию — «RANKED_SOLO_5x5»
            (одиночный/парный рейтинг). Допустимые значения определяются API Riot Games.

    Returns:
        List[Dict[str, Any]]: Список словарей, где каждый словарь содержит данные об одном игроке
            из лиги Challenger. Структура элементов списка определяется API Riot Games и обычно включает:
            - 'summonerName' — имя призывателя (игрока);
            - 'leaguePoints' — очки лиги;
            - 'wins' — количество побед;
            - 'losses' — количество поражений;
            - другие метаданные игрока в текущей лиге.

    Raises:
        requests.exceptions.HTTPError: Если запрос к API завершился с HTTP‑ошибкой
            (например, 404, 500 и т. д.), отличной от 429 (обрабатывается внутри `riot_get`).
        ValueError: Если ответ API не содержит ожидаемого поля 'entries' или имеет некорректную структуру.
        requests.exceptions.RequestException: При сетевых ошибках или проблемах с подключением.


    Example:
        >>> players = get_challenger_players(region='euw1')
        >>> for player in players[:3]:  # выводим топ‑3 игрока
        ...     print(f"{player['summonerName']}: {player['leaguePoints']} LP")
        PlayerOne: 1250 LP
        PlayerTwo: 1180 LP
        PlayerThree: 1150 LP
    """

    url = (
        f"https://{region}.api.riotgames.com"
        f"/lol/league/v4/challengerleagues/by-queue/{queue}"
    )

    data = riot_get(url)

    return data["entries"]

def get_puuid(
    summoner_id: str,
    region: str = REGION
) -> str:

    """
    Получает PUUID (Player Universally Unique ID) игрока по его Summoner ID через API Riot Games.

    Функция формирует URL для запроса к эндпоинту Summoner API, выполняет запрос через вспомогательную
    функцию `riot_get` и извлекает поле 'puuid' из полученного JSON‑ответа. PUUID — глобально
    уникальный идентификатор игрока, который не меняется при смене региона.

    Args:
        summoner_id (str): Уникальный идентификатор призывателя (Summoner ID) в игре League of Legends.
            Получается через другие эндпоинты API (например, поиск по имени игрока).
        region (str, optional): Код региона API Riot Games (например, 'euw1', 'na1', 'ru').
            По умолчанию используется значение глобальной переменной `REGION`.

    Returns:
        str: PUUID игрока — строка с глобально уникальным идентификатором. Используется для запросов
            к другим API Riot (например, Match API), где требуется этот тип ID.

    Raises:
        requests.exceptions.HTTPError: Если запрос к API завершился с HTTP‑ошибкой
            (например, 404 — игрок не найден, 500 — внутренняя ошибка сервера и т. д.),
            отличной от 429 (обрабатывается внутри `riot_get`).
        KeyError: Если в ответе API отсутствует поле 'puuid' (некорректная структура данных).
        ValueError: Если ответ API не может быть преобразован в JSON или имеет неожиданную структуру.
        requests.exceptions.RequestException: При сетевых ошибках, таймаутах или проблемах
            с подключением к API.

    Example:
        >>> puuid = get_puuid("abc123xyz", region="euw1")
        >>> print(puuid)
        '123e4567-e89b-12d3-a456-426614174000'

        >>> # Пример с использованием значения REGION по умолчанию
        >>> puuid = get_puuid("def456uvw")
        >>> print(f"Получен PUUID: {puuid}")
        Получен PUUID: 987e6543-d321-4321-b123-1234567890ab
    """

    url = (
        f"https://{region}.api.riotgames.com"
        f"/lol/summoner/v4/summoners/{summoner_id}"
    )

    data = riot_get(url)

    return data["puuid"]

def get_match_ids(
    puuid: str,
    count: int = 20,
    routing_region: str = ROUTING_REGION
) -> List[str]:

    """
    Получает список идентификаторов матчей (Match ID) для указанного игрока через Riot API.

    Функция формирует URL для запроса к эндпоинту Match API, выполняет запрос через вспомогательную
    функцию `riot_get` и возвращает список ID последних матчей игрока.


    Args:
        puuid (str): PUUID (Player Universally Unique ID) игрока — глобально уникальный
            идентификатор, используемый для запросов к Match API.
        count (int, optional): Количество запрашиваемых матчей. По умолчанию — 20.
            Максимальное значение, поддерживаемое API, — 100.
        routing_region (str, optional): Региональный маршрутизирующий домен API Riot Games
            (например, 'americas', 'europe', 'asia'). По умолчанию используется значение
            глобальной переменной `ROUTING_REGION`.


    Returns:
        List[str]: Список строк с идентификаторами матчей (Match ID) в формате, например:
            ['EUW1_5987369961', 'EUW1_5987334405', 'EUW1_5987297136', ...].
            Каждый ID соответствует одному матчу в истории игрока. При отсутствии матчей
            возвращается пустой список.

    Raises:
        requests.exceptions.HTTPError: Если запрос к API завершился с HTTP‑ошибкой
            (например, 404 — игрок не найден, 403 — неверный API‑ключ, 500 — внутренняя
            ошибка сервера и т. д.), отличной от 429 (обрабатывается внутри `riot_get`).
        KeyError: Если в ответе API отсутствует ожидаемая структура данных (например,
            ответ не является списком).
        ValueError: Если ответ API не может быть преобразован в JSON или имеет
            неожиданную структуру.
        requests.exceptions.RequestException: При сетевых ошибках, таймаутах или проблемах
            с подключением к API.

    Example:
        >>> match_ids = get_match_ids("123e4567-e89b-12d3-a456-426614174000", count=10, routing_region="europe")
        >>> print(f"Найдено матчей: {len(match_ids)}")
        Найдено матчей: 10
        >>> print("Первые 3 ID:", match_ids[:3])
        Первые 3 ID: ['EUW1_5987369961', 'EUW1_5987334405', 'EUW1_5987297136']

        >>> # Пример с использованием значений по умолчанию
        >>> recent_matches = get_match_ids("987e6543-d321-4321-b123-1234567890ab")
        >>> print(f"Последние {len(recent_matches)} матчей загружены")
        Последние 20 матчей загружены
    """

    url = (
        f"https://{routing_region}.api.riotgames.com"
        f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
        f"?start=0&count={count}"
    )

    return riot_get(url)

def get_match(
    match_id: str,
    routing_region: str = ROUTING_REGION
) -> Dict[str, Any]:

    """
    Получает полную информацию о матче по его идентификатору через Riot API.

    Функция формирует URL для запроса к эндпоинту Match API (v5), выполняет запрос через
    вспомогательную функцию `riot_get` и возвращает JSON‑ответ с детальной информацией
    о матче (участники, статистика, события и т. д.).


    Args:
        match_id (str): Идентификатор матча (Match ID) в формате, например, 'EUW1_5987369961'.
            Получается через эндпоинт `/lol/match/v5/matches/by-puuid/{puuid}/ids`.
        routing_region (str, optional): Региональный маршрутизирующий домен API Riot Games
            (например, 'americas', 'europe', 'asia'). Определяет, к какому региону
            направляется запрос. По умолчанию используется значение глобальной переменной
            `ROUTING_REGION`.


    Returns:
        Dict[str, Any]: Словарь с полной информацией о матче в формате JSON. Содержит:
            - метаданные матча (metadata);
            - основную информацию (info): версия игры, режим, длительность, дата;
            - список участников (participants) с индивидуальной статистикой каждого игрока;
            - команды (teams) и их статистику;
            - другие детали матча.
            Структура определяется API Riot Games (Match V5).

    Raises:
        requests.exceptions.HTTPError: Если запрос к API завершился с HTTP‑ошибкой
            (например, 404 — матч не найден, 403 — неверный API‑ключ, 500 — внутренняя
            ошибка сервера и т. д.), отличной от 429 (обрабатывается внутри `riot_get`).
        ValueError: Если ответ API не может быть преобразован в JSON или имеет
            неожиданную структуру.
        requests.exceptions.RequestException: При сетевых ошибках, таймаутах или проблемах
            с подключением к API.

    Example:
        >>> match_data = get_match("EUW1_5987369961", routing_region="europe")
        >>> print(f"Матч длился {match_data['info']['gameDuration'] // 60} минут")
        Матч длился 32 минуты

        >>> # Пример с использованием значения по умолчанию для routing_region
        >>> another_match = get_match("NA1_123456789")
        >>> winner = next(
        ...     team for team in another_match['info']['teams']
        ...     if team['win']
        ... )
        >>> winning_team_id = winner['teamId']
        >>> print(f"Победившая команда: {winning_team_id}")
        Победившая команда: 100
    """

    url = (
        f"https://{routing_region}.api.riotgames.com"
        f"/lol/match/v5/matches/{match_id}"
    )

    return riot_get(url)

from typing import List, Dict, Any


def collect_players(
    players_count: int = 20  # я выбрал 10 топов для примера
) -> List[Dict[str, Any]]:

    """
    Собирает топ‑игроков из лиги Challenger, отсортированных по количеству очков лиги (LP).

    Функция получает список игроков из лиги Challenger через `get_challenger_players()`,
    сортирует их по убыванию очков лиги (leaguePoints) и возвращает указанное количество
    топ‑игроков.

    Args:
        players_count (int, optional): Количество игроков для возврата. По умолчанию — 10.
            Если значение превышает общее количество игроков в лиге, возвращается весь отсортированный список.
            Должно быть положительным целым числом.

    Returns:
        List[Dict[str, Any]]: Список словарей с данными топ‑игроков, отсортированный
            по убыванию очков лиги. Каждый словарь содержит информацию об игроке, включая:
            - 'summonerName' — имя призывателя (игрока);
            - 'leaguePoints' — очки лиги (LP);
            - 'wins' — количество побед;
            - 'losses' — количество поражений;
            - 'rank' — дивизион в рамках Challenger (например, 'I', 'II');
            - другие поля, возвращаемые API Riot Games.

    Raises:
        TypeError: Если параметр `players_count` не является целым числом.
        ValueError: Если `players_count` меньше 1.
        requests.exceptions.HTTPError: Если запрос к API (через `get_challenger_players`)
            завершился с HTTP‑ошибкой (например, 404, 500 и т. д.).
        KeyError: Если в данных игрока отсутствует поле 'leaguePoints', необходимое для сортировки.
        requests.exceptions.RequestException: При сетевых ошибках или проблемах
            с подключением к API.

    Example:
        >>> top_players = collect_players(players_count=5)
        >>> for i, player in enumerate(top_players, 1):
        ...     print(f"{i}. {player['summonerName']}: {player['leaguePoints']} LP")
        1. PlayerOne: 1250 LP
        2. PlayerTwo: 1180 LP
        3. PlayerThree: 1150 LP
        4. PlayerFour: 1120 LP
        5. PlayerFive: 1090 LP

        >>> # Пример с использованием значения по умолчанию (топ‑10)
        >>> challenger_top = collect_players()
        >>> print(f"Получено игроков: {len(challenger_top)}")
        Получено игроков: 10
    """

    if not isinstance(players_count, int):
        raise TypeError("Параметр `players_count` должен быть целым числом (int)")
    if players_count < 1:
        raise ValueError("Параметр `players_count` должен быть больше или равен 1")

    players = get_challenger_players()

    players = sorted(
        players,
        key=lambda x: x["leaguePoints"],
        reverse=True
    )

    return players[:players_count]

def collect_match_ids(
    players_count: int = 10,  # количество игроков
    matches_per_player: int = 5  # количество матчей на игрока
) -> List[str]:

    """
    Собирает идентификаторы матчей (Match ID) для топ‑игроков из лиги Challenger.


    Функция:
    1. Получает топ‑игроков через `collect_players()`.
    2. Для каждого игрока:
       - получает PUUID через `get_puuid()`;
       - запрашивает список последних матчей через `get_match_ids()`.
    3. Объединяет все ID матчей в один список.

    Args:
        players_count (int, optional): Количество топ‑игроков для сбора матчей.
            По умолчанию — 10. Должно быть положительным целым числом.
        matches_per_player (int, optional): Количество матчей для каждого игрока.
            По умолчанию — 5. Должно быть в диапазоне 1–100 (ограничение API).

    Returns:
        List[str]: Список строк с идентификаторами матчей (Match ID) в формате:
            ['EUW1_5987369961', 'EUW1_5987334405', ...].
            При отсутствии данных или ошибках для отдельных игроков возвращается
            частичный список (только успешные запросы).

    Raises:
        TypeError: Если любой из параметров не является целым числом.
        ValueError: Если `players_count` < 1 или `matches_per_player` < 1.

    Notes:
        - Ошибки на уровне отдельных игроков не прерывают выполнение функции:
          при ошибке выводится сообщение в консоль, а обработка продолжается
          со следующим игроком.
        - Общее количество возвращаемых матчей ≈ players_count × matches_per_player
          (может быть меньше из‑за ошибок или отсутствия данных у игроков).

    Example:
        >>> all_match_ids = collect_match_ids(players_count=3, matches_per_player=2)
        >>> print(f"Собрано матчей: {len(all_match_ids)}")
        Собрано матчей: 6
        >>> print("Первые 3 ID:", all_match_ids[:3])
        Первые 3 ID: ['EUW1_5987369961', 'EUW1_5987334405', 'EUW1_5987297136']

        >>> # Пример с параметрами по умолчанию
        >>> default_matches = collect_match_ids()
        >>> print(f"Всего собрано ID матчей: {len(default_matches)}")
        Всего собрано ID матчей: 50
    """

    # Валидация входных параметров
    if not isinstance(players_count, int):
        raise TypeError("Параметр `players_count` должен быть целым числом (int)")
    if not isinstance(matches_per_player, int):
        raise TypeError("Параметр `matches_per_player` должен быть целым числом (int)")
    if players_count < 1:
        raise ValueError("Параметр `players_count` должен быть больше или равен 1")
    if matches_per_player < 1:
        raise ValueError("Параметр `matches_per_player` должен быть больше или равен 1")

    result = []

    players = collect_players(players_count)

    for player in players:
        try:
            puuid = player["puuid"]
            match_ids = get_match_ids(puuid, count=matches_per_player)
            result.extend(match_ids)
        except Exception as e:
            print(f"Ошибка при обработке игрока {player.get('summonerName', 'Unknown')}: {e}")

    return result

def collect_matches(
    players_count: int = 10,
    matches_per_player: int = 5
) -> List[Dict[str, Any]]:

    """
    Собирает полные данные о матчах для топ‑игроков из лиги Challenger.

    Функция:
    1. Получает список идентификаторов матчей через `collect_match_ids()`.
    2. Для каждого Match ID запрашивает полные данные матча через `get_match()`.
    3. Объединяет все данные в один список.

    Args:
        players_count (int, optional): Количество топ‑игроков для сбора матчей.
            По умолчанию — 10. Должно быть положительным целым числом.
        matches_per_player (int, optional): Количество матчей для каждого игрока.
            По умолчанию — 5. Должно быть в диапазоне 1–100 (ограничение API).

    Returns:
        List[Dict[str, Any]]: Список словарей с полными данными о матчах.
            Каждый словарь содержит всю информацию о матче от Riot API (Match V5), включая:
            - metadata: метаданные матча;
            - info: основную информацию (версия игры, режим, длительность, дата);
            - participants: список участников с индивидуальной статистикой;
            - teams: информацию о командах и их статистике.
            При ошибках для отдельных матчей возвращается частичный список
            (только успешно загруженные матчи).

    Raises:
        TypeError: Если любой из параметров не является целым числом.
        ValueError: Если `players_count` < 1 или `matches_per_player` < 1.

    Notes:
        - Ошибки на уровне отдельных матчей не прерывают выполнение функции:
          при ошибке выводится сообщение в консоль, а обработка продолжается
          со следующим матчем.
        - Общее количество возвращаемых матчей ≤ players_count × matches_per_player
          (может быть меньше из‑за ошибок, отсутствия данных или дубликатов).
        - Функция может занять значительное время из‑за множества последовательных
          запросов к API (каждый запрос имеет задержку 0.06 с внутри `riot_get`).

    Example:
        >>> all_matches = collect_matches(players_count=2, matches_per_player=3)
        >>> print(f"Загружено матчей: {len(all_matches)}")
        Загружено матчей: 6
        >>> if all_matches:
        ...     first_match = all_matches[0]
        ...     duration_min = first_match['info']['gameDuration'] // 60
        ...     print(f"Первый матч длился {duration_min} минут")
        Первый матч длился 32 минуты

        >>> # Пример с параметрами по умолчанию
        >>> default_matches = collect_matches()
        >>> print(f"Всего собрано полных данных о матчах: {len(default_matches)}")
        Всего собрано полных данных о матчах: 50
    """

    # Валидация входных параметров
    if not isinstance(players_count, int):
        raise TypeError("Параметр `players_count` должен быть целым числом (int)")
    if not isinstance(matches_per_player, int):
        raise TypeError("Параметр `matches_per_player` должен быть целым числом (int)")
    if players_count < 1:
        raise ValueError("Параметр `players_count` должен быть больше или равен 1")
    if matches_per_player < 1:
        raise ValueError("Параметр `matches_per_player` должен быть больше или равен 1")

    match_ids = collect_match_ids(players_count, matches_per_player)
    matches = []

    for match_id in match_ids:
        try:
            match_data = get_match(match_id)
            matches.append(match_data)
        except Exception as e:
            print(f"Ошибка при загрузке матча {match_id}: {e}")

    return matches

def create_participants_df(matches: List[Dict[str, Any]]) -> pd.DataFrame:

    """
    Создаёт DataFrame с данными об участниках матчей из сырых данных API Riot Games.

    Функция обрабатывает список матчей, извлекая информацию об отдельных игроках
    и их статистике в каждом матче.

    Args:
        matches (List[Dict[str, Any]]): Список словарей с полными данными о матчах,
            полученными через Riot API (Match V5). Каждый элемент списка должен содержать:
            - 'metadata': метаданные матча (включая 'matchId');
            - 'info': основную информацию о матче;
            - 'participants': список участников с индивидуальной статистикой.

    Returns:
        pd.DataFrame: DataFrame с одной строкой на каждого участника матча.
            Столбцы:
            - 'match_id' (str): идентификатор матча;
            - 'puuid' (str): уникальный идентификатор игрока;
            - 'champion' (str): имя чемпиона, за которого играл участник;
            - 'kills' (int): количество убийств;
            - 'deaths' (int): количество смертей;
            - 'assists' (int): количество ассистов;
            - 'gold' (int): заработанное золото;
            - 'damage' (int): урон, нанесённый чемпионам;
            - 'vision_score' (int): очки обзора;
            - 'win' (bool): победа (True) или поражение (False).

    Raises:
        KeyError: Если в данных отсутствует ожидаемое поле (например, 'matchId',
            'participants' или любое поле статистики игрока).
        TypeError: Если входной параметр `matches` не является списком или элементы списка
            не являются словарями.
        ValueError: Если список `matches` пуст.

    Example:
        >>> matches = collect_matches(players_count=2, matches_per_player=1)
        >>> df = create_participants_df(matches)
        >>> print(f"Обработано участников: {len(df)}")
        Обработано участников: 20
        >>> print("Первые 3 строки:")
        >>> print(df[["match_id", "champion", "kills", "deaths"]].head(3))
               match_id   champion  kills  deaths
        0  EUW1_5987369961  Ahri        5       2
        1  EUW1_5987369961  Garen       3       4
        2  EUW1_5987369961  Leona     2       3

        >>> # Статистика по всем матчам
        >>> avg_kills = df["kills"].mean()
        >>> print(f"Среднее количество убийств на игрока: {avg_kills:.1f}")
        Среднее количество убийств на игрока: 4.2
    """

    # Валидация входных данных
    if not isinstance(matches, list):
        raise TypeError("Параметр `matches` должен быть списком (List)")
    if len(matches) == 0:
        raise ValueError("Список `matches` не должен быть пустым")

    rows = []

    for match in matches:
        try:
            match_id = match["metadata"]["matchId"]
            participants = match["info"]["participants"]

            for player in participants:
                rows.append({
                    "match_id": match_id,
                    "puuid": player["puuid"],
                    "champion": player["championName"],
            "kills": player["kills"],
            "deaths": player["deaths"],
            "assists": player["assists"],
            "gold": player["goldEarned"],
            "damage": player["totalDamageDealtToChampions"],
            "vision_score": player["visionScore"],
            "win": player["win"]
                })
        except KeyError as e:
            print(f"Пропущен матч {match.get('metadata', {}).get('matchId', 'Unknown')}: отсутствует поле {e}")
            continue

    return pd.DataFrame(rows)

matches = collect_matches(
    players_count=500,
    matches_per_player=10
)

df = create_participants_df(
    matches
)

df.head()

# TRANSFORM: таблица игроков
# Игрок — это уникальная сущность: один puuid = один человек.
# Из df берём только уникальные puuid — каждый игрок один раз.

df_players = (
    df[["puuid"]]          # берём только столбец с id игрока
    .drop_duplicates()     # оставляем уникальные записи (один игрок = одна строка)
    .reset_index(drop=True)  # перенумеровываем индекс с нуля
)

print(f"Уникальных игроков: {len(df_players)}")
df_players.head()

# TRANSFORM: таблица матчей
# Матч — отдельная сущность: один match_id = один матч.
# Из сырых данных (matches) достаём метаданные каждого матча.
# В df_participants мы потом будем ссылаться на match_id как на внешний ключ.

rows = []

for match in matches:
    info = match["info"]  # блок info содержит основную информацию о матче

    rows.append({
        "match_id":       match["metadata"]["matchId"],  # уникальный id матча
        "game_mode":      info.get("gameMode"),          # режим игры (CLASSIC, ARAM и т.д.)
        "game_version":   info.get("gameVersion"),       # версия патча
        "game_duration":  info.get("gameDuration"),      # длительность в секундах
        "game_start_ts":  info.get("gameStartTimestamp"),# время начала (unix timestamp)
    })

df_matches = (
    pd.DataFrame(rows)
    .drop_duplicates(subset="match_id")  # на случай если один матч попал дважды
    .reset_index(drop=True)
)

print(f"Уникальных матчей: {len(df_matches)}")
df_matches.head()

print(f"Всего записей участников: {len(df_participants)}")
print(f"Столбцы: {list(df_participants.columns)}")
df_participants.head()

# LOAD: сохраняем три таблицы в CSV
# CSV — самый простой способ сохранить данные.
# Каждая сущность — отдельный файл.
# index=False — не пишем индекс pandas в файл, он нам не нужен.

df_players.to_parquet("players_nan.parquet", index=False)
df_matches.to_csv("matches_nan.parquet", index=False)
df_participants.to_csv("participants_nan.parquet", index=False)

print("Итого:")
print(f"  players_nan.parquet      — {len(df_players)} строк")
print(f"  matches_nan.parquet      — {len(df_matches)} строк")
print(f"  participants_nan.parquet — {len(df_participants)} строк")