%%writefile app.py

import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from pathlib import Path
import os
from datetime import datetime


# ----------------------------
# Настройки страницы
# ----------------------------
st.set_page_config(
    page_title="LoL DuckDB Dashboard",
    layout="wide"
)


# ----------------------------
# Настройки проекта
# ----------------------------
DB_PATH = Path("duck.db")

st.title("LoL Dashboard на DuckDB")

st.sidebar.header("Управление")

st.sidebar.write("Запущенный файл:")
st.sidebar.code(__file__)

st.sidebar.write("Рабочая папка:")
st.sidebar.code(os.getcwd())

st.sidebar.write("Последний запуск:")
st.sidebar.code(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

if st.sidebar.button("Полностью обновить приложение"):
    st.cache_data.clear()
    st.cache_resource.clear()

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    st.rerun()

if not DB_PATH.exists():
    st.error("Файл duck.db не найден. Положите duck.db рядом с app.py")
    st.stop()


# ----------------------------
# Вспомогательные функции
# ----------------------------
def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def query_df(sql: str) -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute(sql).fetchdf()
    con.close()
    return df


# ----------------------------
# Названия таблиц в duck.db
# ----------------------------
PLAYERS_TABLE = "players_3regions"
PARTICIPANTS_TABLE = "participants_3regions"
MATCHES_TABLE = "matches_3regions"


# ----------------------------
# Проверка таблиц
# ----------------------------
tables_df = query_df("SHOW TABLES")
available_tables = tables_df["name"].tolist()

st.sidebar.header("Таблицы в duck.db")
st.sidebar.dataframe(tables_df, use_container_width=True)

required_tables = [
    PLAYERS_TABLE,
    PARTICIPANTS_TABLE,
    MATCHES_TABLE
]

missing_tables = [t for t in required_tables if t not in available_tables]

if missing_tables:
    st.error(f"В duck.db не найдены таблицы: {missing_tables}")
    st.stop()


# ----------------------------
# Вкладки
# ----------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Обзор",
    "Матчи",
    "Чемпионы",
    "Игроки",
    "Боевая статистика",
    "Качество данных",
    "Регионы"
])


# ----------------------------
# Вкладка 1. Обзор
# ----------------------------
with tab1:
    st.header("Обзор данных")

    overview_df = query_df(f"""
        SELECT
            COUNT(DISTINCT p.puuid) AS players_count,
            COUNT(DISTINCT m.match_id) AS matches_count,
            COUNT(*) AS participant_rows,
            COUNT(DISTINCT pr.champion) AS champions_count,
            ROUND(AVG(m.game_duration) / 60.0, 2) AS avg_match_duration_min,
            ROUND(100.0 * AVG(CASE WHEN pr.win THEN 1 ELSE 0 END), 2) AS avg_win_rate
        FROM {quote_ident(PARTICIPANTS_TABLE)} pr
        LEFT JOIN {quote_ident(PLAYERS_TABLE)} p
            ON pr.puuid = p.puuid
        LEFT JOIN {quote_ident(MATCHES_TABLE)} m
            ON pr.match_id = m.match_id
    """)

    row = overview_df.iloc[0]

    col1, col2, col3 = st.columns(3)
    col1.metric("Игроков", f"{row['players_count']:,}")
    col2.metric("Матчей", f"{row['matches_count']:,}")
    col3.metric("Строк участников", f"{row['participant_rows']:,}")

    col4, col5, col6 = st.columns(3)
    col4.metric("Чемпионов", f"{row['champions_count']:,}")
    col5.metric("Средняя длительность, мин", row["avg_match_duration_min"])
    col6.metric("Средний win rate, %", row["avg_win_rate"])

    st.subheader("Распределение побед и поражений")

    win_df = query_df(f"""
        SELECT
            CAST(win AS VARCHAR) AS win,
            COUNT(*) AS cnt
        FROM {quote_ident(PARTICIPANTS_TABLE)}
        GROUP BY win
        ORDER BY win DESC
    """)

    fig = px.bar(
        win_df,
        x="win",
        y="cnt",
        title="Количество записей по признаку win",
        labels={
            "win": "Победа",
            "cnt": "Количество записей"
        }
    )

    st.plotly_chart(fig, use_container_width=True)


# ----------------------------
# Вкладка 2. Матчи
# ----------------------------
with tab2:
    st.header("Аналитика по матчам")

    matches_df = query_df(f"""
        SELECT
            match_id,
            game_mode,
            game_version,
            game_duration,
            ROUND(game_duration / 60.0, 2) AS duration_min,
            CASE
                WHEN game_start_ts > 1000000000000
                THEN to_timestamp(game_start_ts / 1000.0)
                ELSE to_timestamp(game_start_ts)
            END AS game_start_time
        FROM {quote_ident(MATCHES_TABLE)}
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Распределение длительности матчей")

        fig = px.histogram(
            matches_df,
            x="duration_min",
            nbins=40,
            title="Длительность матчей, минут",
            labels={
                "duration_min": "Длительность, минут"
            }
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Режимы игры")

        game_modes_df = query_df(f"""
            SELECT
                game_mode,
                COUNT(*) AS cnt
            FROM {quote_ident(MATCHES_TABLE)}
            GROUP BY game_mode
            ORDER BY cnt DESC
        """)

        fig = px.bar(
            game_modes_df,
            x="game_mode",
            y="cnt",
            title="Количество матчей по режимам",
            labels={
                "game_mode": "Режим игры",
                "cnt": "Количество матчей"
            }
        )

        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Топ версий игры")

    versions_df = query_df(f"""
        SELECT
            game_version,
            COUNT(*) AS cnt
        FROM {quote_ident(MATCHES_TABLE)}
        GROUP BY game_version
        ORDER BY cnt DESC
        LIMIT 20
    """)

    fig = px.bar(
        versions_df,
        x="game_version",
        y="cnt",
        title="Топ-20 версий игры",
        labels={
            "game_version": "Версия игры",
            "cnt": "Количество матчей"
        }
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Матчи по дням")

    matches_by_day = query_df(f"""
        WITH m AS (
            SELECT
                CASE
                    WHEN game_start_ts > 1000000000000
                    THEN to_timestamp(game_start_ts / 1000.0)
                    ELSE to_timestamp(game_start_ts)
                END AS game_start_time
            FROM {quote_ident(MATCHES_TABLE)}
        )
        SELECT
            CAST(date_trunc('day', game_start_time) AS DATE) AS game_date,
            COUNT(*) AS matches_count
        FROM m
        GROUP BY game_date
        ORDER BY game_date
    """)

    fig = px.line(
        matches_by_day,
        x="game_date",
        y="matches_count",
        title="Количество матчей по датам",
        labels={
            "game_date": "Дата",
            "matches_count": "Количество матчей"
        }
    )

    st.plotly_chart(fig, use_container_width=True)


# ----------------------------
# Вкладка 3. Чемпионы
# ----------------------------
with tab3:
    st.header("Аналитика по чемпионам")

    min_games = st.slider(
        "Минимальное количество игр на чемпиона",
        min_value=1,
        max_value=100,
        value=10,
        key="champions_min_games"
    )

    top_n_champions = st.slider(
        "Сколько чемпионов показать",
        min_value=10,
        max_value=100,
        value=30,
        key="champions_top_n"
    )

    champions_df = query_df(f"""
        SELECT
            champion,
            COUNT(*) AS games,
            ROUND(100.0 * AVG(CASE WHEN win THEN 1 ELSE 0 END), 2) AS win_rate,
            ROUND(AVG(kills), 2) AS avg_kills,
            ROUND(AVG(deaths), 2) AS avg_deaths,
            ROUND(AVG(assists), 2) AS avg_assists,
            ROUND((SUM(kills) + SUM(assists)) * 1.0 / NULLIF(SUM(deaths), 0), 2) AS kda,
            ROUND(AVG(gold_earned), 2) AS avg_gold,
            ROUND(AVG(total_damage_to_champions), 2) AS avg_damage,
            ROUND(AVG(vision_score), 2) AS avg_vision
        FROM {quote_ident(PARTICIPANTS_TABLE)}
        GROUP BY champion
        HAVING COUNT(*) >= {int(min_games)}
        ORDER BY games DESC
        LIMIT {int(top_n_champions)}
    """)

    st.dataframe(champions_df, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            champions_df.sort_values("games", ascending=True),
            x="games",
            y="champion",
            orientation="h",
            title="Популярность чемпионов",
            labels={
                "games": "Количество игр",
                "champion": "Чемпион"
            }
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            champions_df.sort_values("win_rate", ascending=True),
            x="win_rate",
            y="champion",
            orientation="h",
            title="Win rate по чемпионам",
            labels={
                "win_rate": "Win rate, %",
                "champion": "Чемпион"
            }
        )

        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Средний урон и win rate")

    fig = px.scatter(
        champions_df,
        x="avg_damage",
        y="win_rate",
        size="games",
        hover_name="champion",
        title="Связь среднего урона и win rate",
        labels={
            "avg_damage": "Средний урон",
            "win_rate": "Win rate, %"
        }
    )

    st.plotly_chart(fig, use_container_width=True)


# ----------------------------
# Вкладка 4. Игроки
# ----------------------------
with tab4:
    st.header("Аналитика по игрокам")

    min_player_games = st.slider(
        "Минимальное количество матчей игрока",
        min_value=1,
        max_value=50,
        value=5,
        key="players_min_games"
    )

    top_n_players = st.slider(
        "Сколько игроков показать",
        min_value=10,
        max_value=100,
        value=30,
        key="players_top_n"
    )

    players_df = query_df(f"""
        SELECT
            puuid,
            COUNT(DISTINCT match_id) AS games,
            ROUND(100.0 * AVG(CASE WHEN win THEN 1 ELSE 0 END), 2) AS win_rate,
            SUM(kills) AS kills,
            SUM(deaths) AS deaths,
            SUM(assists) AS assists,
            ROUND((SUM(kills) + SUM(assists)) * 1.0 / NULLIF(SUM(deaths), 0), 2) AS kda,
            ROUND(AVG(gold_earned), 2) AS avg_gold,
            ROUND(AVG(total_damage_to_champions), 2) AS avg_damage,
            ROUND(AVG(vision_score), 2) AS avg_vision
        FROM {quote_ident(PARTICIPANTS_TABLE)}
        GROUP BY puuid
        HAVING COUNT(DISTINCT match_id) >= {int(min_player_games)}
        ORDER BY games DESC
        LIMIT {int(top_n_players)}
    """)

    players_df["puuid_short"] = players_df["puuid"].astype(str).str[:12] + "..."

    st.dataframe(players_df, use_container_width=True)

    fig = px.bar(
        players_df.sort_values("games", ascending=True),
        x="games",
        y="puuid_short",
        orientation="h",
        title="Топ игроков по количеству матчей",
        labels={
            "games": "Количество матчей",
            "puuid_short": "Игрок"
        }
    )

    st.plotly_chart(fig, use_container_width=True)

    fig = px.scatter(
        players_df,
        x="kda",
        y="win_rate",
        size="games",
        hover_name="puuid_short",
        title="KDA vs Win rate игроков",
        labels={
            "kda": "KDA",
            "win_rate": "Win rate, %"
        }
    )

    st.plotly_chart(fig, use_container_width=True)


# ----------------------------
# Вкладка 5. Боевая статистика
# ----------------------------
with tab5:
    st.header("Боевая статистика")

    combat_df = query_df(f"""
        SELECT
            champion,
            COUNT(*) AS games,
            ROUND(AVG(kills), 2) AS avg_kills,
            ROUND(AVG(deaths), 2) AS avg_deaths,
            ROUND(AVG(assists), 2) AS avg_assists,
            ROUND(AVG(total_damage_to_champions), 2) AS avg_damage,
            ROUND(AVG(gold_earned), 2) AS avg_gold,
            ROUND(AVG(vision_score), 2) AS avg_vision
        FROM {quote_ident(PARTICIPANTS_TABLE)}
        GROUP BY champion
        HAVING COUNT(*) >= 10
        ORDER BY avg_damage DESC
        LIMIT 30
    """)

    st.dataframe(combat_df, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            combat_df.sort_values("avg_damage", ascending=True),
            x="avg_damage",
            y="champion",
            orientation="h",
            title="Топ чемпионов по среднему урону",
            labels={
                "avg_damage": "Средний урон",
                "champion": "Чемпион"
            }
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.scatter(
            combat_df,
            x="avg_gold",
            y="avg_damage",
            size="games",
            hover_name="champion",
            title="Среднее золото vs средний урон",
            labels={
                "avg_gold": "Среднее золото",
                "avg_damage": "Средний урон"
            }
        )

        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Vision score по чемпионам")

    vision_df = combat_df.sort_values("avg_vision", ascending=False).head(30)

    fig = px.bar(
        vision_df.sort_values("avg_vision", ascending=True),
        x="avg_vision",
        y="champion",
        orientation="h",
        title="Топ чемпионов по vision score",
        labels={
            "avg_vision": "Средний vision score",
            "champion": "Чемпион"
        }
    )

    st.plotly_chart(fig, use_container_width=True)


# ----------------------------
# Вкладка 6. Качество данных
# ----------------------------
with tab6:
    st.header("Качество данных")

    quality_df = query_df(f"""
        SELECT
            'players_3regions' AS table_name,
            COUNT(*) AS rows_count,
            COUNT(DISTINCT puuid) AS unique_key_count,
            COUNT(*) - COUNT(DISTINCT puuid) AS duplicate_key_count
        FROM {quote_ident(PLAYERS_TABLE)}

        UNION ALL

        SELECT
            'matches_3regions' AS table_name,
            COUNT(*) AS rows_count,
            COUNT(DISTINCT match_id) AS unique_key_count,
            COUNT(*) - COUNT(DISTINCT match_id) AS duplicate_key_count
        FROM {quote_ident(MATCHES_TABLE)}

        UNION ALL

        SELECT
            'participants_3regions' AS table_name,
            COUNT(*) AS rows_count,
            COUNT(DISTINCT match_id || '|' || puuid) AS unique_key_count,
            COUNT(*) - COUNT(DISTINCT match_id || '|' || puuid) AS duplicate_key_count
        FROM {quote_ident(PARTICIPANTS_TABLE)}
    """)

    st.subheader("Дубли ключей")
    st.dataframe(quality_df, use_container_width=True)

    links_df = query_df(f"""
        SELECT
            'participants без match_id в matches' AS check_name,
            COUNT(*) AS problem_rows
        FROM {quote_ident(PARTICIPANTS_TABLE)} pr
        LEFT JOIN {quote_ident(MATCHES_TABLE)} m
            ON pr.match_id = m.match_id
        WHERE m.match_id IS NULL

        UNION ALL

        SELECT
            'participants без puuid в players' AS check_name,
            COUNT(*) AS problem_rows
        FROM {quote_ident(PARTICIPANTS_TABLE)} pr
        LEFT JOIN {quote_ident(PLAYERS_TABLE)} p
            ON pr.puuid = p.puuid
        WHERE p.puuid IS NULL
    """)

    st.subheader("Проверка связей между таблицами")
    st.dataframe(links_df, use_container_width=True)

    participants_per_match = query_df(f"""
        SELECT
            participants_count,
            COUNT(*) AS matches_count
        FROM (
            SELECT
                match_id,
                COUNT(*) AS participants_count
            FROM {quote_ident(PARTICIPANTS_TABLE)}
            GROUP BY match_id
        ) q
        GROUP BY participants_count
        ORDER BY participants_count
    """)

    st.subheader("Количество участников на матч")

    fig = px.bar(
        participants_per_match,
        x="participants_count",
        y="matches_count",
        title="Распределение количества участников в матче",
        labels={
            "participants_count": "Количество участников",
            "matches_count": "Количество матчей"
        }
    )

    st.plotly_chart(fig, use_container_width=True)


# ----------------------------
# Вкладка 7. Регионы
# ----------------------------
with tab7:
    st.header("Аналитика по регионам")

    st.markdown("""
    Регион определяется по префиксу `match_id`:

    - `EUW1` → Europe
    - `NA1` → North America
    - `JP1` → Japan
    """)

    # ----------------------------
    # Общая статистика по регионам
    # ----------------------------
    region_summary_df = query_df(f"""
        WITH participants_region AS (
            SELECT
                CASE UPPER(SPLIT_PART(match_id, '_', 1))
                    WHEN 'EUW1' THEN 'Europe'
                    WHEN 'NA1' THEN 'North America'
                    WHEN 'JP1' THEN 'Japan'
                    ELSE 'Other'
                END AS region,
                match_id,
                puuid,
                champion,
                win
            FROM {quote_ident(PARTICIPANTS_TABLE)}
        ),

        participants_summary AS (
            SELECT
                region,
                COUNT(*) AS participant_rows,
                COUNT(DISTINCT match_id) AS matches_from_participants,
                COUNT(DISTINCT puuid) AS players_count,
                COUNT(DISTINCT champion) AS champions_count,
                ROUND(100.0 * AVG(CASE WHEN win THEN 1 ELSE 0 END), 2) AS win_rate
            FROM participants_region
            GROUP BY region
        ),

        matches_region AS (
            SELECT
                CASE UPPER(SPLIT_PART(match_id, '_', 1))
                    WHEN 'EUW1' THEN 'Europe'
                    WHEN 'NA1' THEN 'North America'
                    WHEN 'JP1' THEN 'Japan'
                    ELSE 'Other'
                END AS region,
                match_id,
                game_duration
            FROM {quote_ident(MATCHES_TABLE)}
        ),

        matches_summary AS (
            SELECT
                region,
                COUNT(DISTINCT match_id) AS matches_count,
                ROUND(AVG(game_duration) / 60.0, 2) AS avg_match_duration_min
            FROM matches_region
            GROUP BY region
        )

        SELECT
            p.region,
            COALESCE(m.matches_count, p.matches_from_participants) AS matches_count,
            p.participant_rows,
            p.players_count,
            p.champions_count,
            p.win_rate,
            m.avg_match_duration_min
        FROM participants_summary p
        LEFT JOIN matches_summary m
            ON p.region = m.region
        ORDER BY
            CASE p.region
                WHEN 'Europe' THEN 1
                WHEN 'North America' THEN 2
                WHEN 'Japan' THEN 3
                ELSE 4
            END
    """)

    st.subheader("Общая статистика по регионам")
    st.dataframe(region_summary_df, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            region_summary_df,
            x="region",
            y="matches_count",
            title="Количество матчей по регионам",
            labels={
                "region": "Регион",
                "matches_count": "Количество матчей"
            }
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            region_summary_df,
            x="region",
            y="players_count",
            title="Количество игроков по регионам",
            labels={
                "region": "Регион",
                "players_count": "Количество игроков"
            }
        )
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        fig = px.bar(
            region_summary_df,
            x="region",
            y="champions_count",
            title="Количество уникальных чемпионов по регионам",
            labels={
                "region": "Регион",
                "champions_count": "Количество чемпионов"
            }
        )
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        fig = px.bar(
            region_summary_df,
            x="region",
            y="avg_match_duration_min",
            title="Средняя длительность матча по регионам",
            labels={
                "region": "Регион",
                "avg_match_duration_min": "Средняя длительность, мин"
            }
        )
        st.plotly_chart(fig, use_container_width=True)

    # --------