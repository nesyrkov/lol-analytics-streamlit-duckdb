from pathlib import Path
import json
import pandas as pd


BASE_DIR = Path(".")  # папка с notebook и файлами


def normalize_object_columns(df):
    """
    Если в ячейках есть dict/list, переводим их в JSON-строки,
    чтобы parquet сохранялся без ошибок.
    """
    df = df.copy()

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].map(
                lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True)
                if isinstance(x, (dict, list))
                else x
            )

    return df


def add_parquet_to_parquet(target_parquet_file, new_parquet_file):
    print(f"\nОбновляем: {target_parquet_file}")
    
    df_old = pd.read_parquet(BASE_DIR / target_parquet_file)
    df_new = pd.read_parquet(BASE_DIR / new_parquet_file)

    print(f"Старый parquet: {df_old.shape}")
    print(f"Новый parquet:  {df_new.shape}")

    df_all = pd.concat(
        [df_old, df_new],
        ignore_index=True,
        sort=False
    )

    rows_before = len(df_all)

    df_all = normalize_object_columns(df_all)
    df_all = df_all.drop_duplicates().reset_index(drop=True)

    rows_after = len(df_all)

    df_all.to_parquet(BASE_DIR / target_parquet_file, index=False)

    print(f"Итоговый parquet: {df_all.shape}")
    print(f"Удалено дубликатов: {rows_before - rows_after}")

    return df_all

players_3regions = add_parquet_to_parquet(
    target_parquet_file="players_3regions.parquet",
    new_parquet_file="players_jpn.parquet"
)

participants_3regions = add_parquet_to_parquet(
    target_parquet_file="participants_3regions.parquet",
    new_parquet_file="participants_jpn.parquet"
)

matches_3regions = add_parquet_to_parquet(
    target_parquet_file="matches_3regions.parquet",
    new_parquet_file="matches_jpn.parquet"
)
