"""Парсинг .lprof файлов line_profiler."""

import pickle
from typing import IO

import pandas as pd
import streamlit as st


def parse_lprof(uploaded_lprof: IO[bytes]) -> pd.DataFrame | None:
    """Парсинг lprof файла.

    Args:
        uploaded_lprof: файловый объект с содержимым .lprof

    Returns:
        DataFrame с колонками: file, func, start, lineno, hits, time_s
        или None при ошибке чтения.
    """
    try:
        uploaded_lprof.seek(0)
        data = pickle.load(uploaded_lprof)
        timings = data.timings if hasattr(data, "timings") else data["timings"]
    except Exception as e:
        st.error(f"Ошибка чтения .lprof: {e}")
        return None

    result = []

    for (fn, start, func), raw_lines in timings.items():
        if isinstance(raw_lines, dict):
            items = raw_lines.items()
        elif isinstance(raw_lines, list):
            items = [(ln, (h, t)) for (ln, h, t) in raw_lines]
        else:
            try:
                items = raw_lines.items()
            except Exception:
                st.warning(f"Неизвестный формат данных для {func} в {fn}, пропускаем.")
                continue

        for lineno, (hits, time_us) in items:
            result.append(
                {
                    "file": fn,
                    "func": func,
                    "start": start,
                    "lineno": lineno,
                    "hits": hits,
                    "time_s": time_us / 1_000_000,
                }
            )

    if not result:
        st.warning("Файл прочитан, но данных профилирования не найдено.")
        return None

    return pd.DataFrame(result)


def build_func_summary(df_profile: pd.DataFrame) -> pd.DataFrame:
    """Агрегация статистики по функциям.

    Args:
        df_profile: DataFrame из parse_lprof

    Returns:
        DataFrame с колонками: file, func, total_time_s, total_hits, pct
    """
    summary = (
        df_profile.groupby(["file", "func"])
        .agg(
            total_time_s=("time_s", "sum"),
            total_hits=("hits", "sum"),
        )
        .reset_index()
        .sort_values("total_time_s", ascending=False)
    )

    total = summary["total_time_s"].sum()
    summary["pct"] = (summary["total_time_s"] / total * 100).round(2) if total > 0 else 0.0

    return summary