import duckdb
from pathlib import Path

DB_PATH = Path("data/duck.db")

PLAYERS_PARQUET = Path("data/players_3regions.parquet")
PARTICIPANTS_PARQUET = Path("data/participants_3regions.parquet")
MATCHES_PARQUET = Path("data/matches_3regions.parquet")

required_files = [
    PLAYERS_PARQUET,
    PARTICIPANTS_PARQUET,
    MATCHES_PARQUET,
]

for file_path in required_files:
    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

con = duckdb.connect(str(DB_PATH))

con.execute("DROP TABLE IF EXISTS players_3regions")
con.execute("DROP TABLE IF EXISTS participants_3regions")
con.execute("DROP TABLE IF EXISTS matches_3regions")

con.execute("""
    CREATE TABLE players_3regions AS
    SELECT *
    FROM read_parquet('data/players_3regions.parquet')
""")

con.execute("""
    CREATE TABLE participants_3regions AS
    SELECT *
    FROM read_parquet('data/participants_3regions.parquet')
""")

con.execute("""
    CREATE TABLE matches_3regions AS
    SELECT *
    FROM read_parquet('data/matches_3regions.parquet')
""")

print("Таблицы в duck.db:")
print(con.execute("SHOW TABLES").fetchdf())

print("\nКоличество строк:")
print(con.execute("""
    SELECT 'players_3regions' AS table_name, COUNT(*) AS rows_count FROM players_3regions
    UNION ALL
    SELECT 'participants_3regions' AS table_name, COUNT(*) AS rows_count FROM participants_3regions
    UNION ALL
    SELECT 'matches_3regions' AS table_name, COUNT(*) AS rows_count FROM matches_3regions
""").fetchdf())

con.close()

print("\nФайл data/duck.db успешно создан.")