"""UI-компоненты Streamlit для LProf Viewer."""

import pandas as pd
import plotly.express as px
import streamlit as st

from source import SrcFilesDict, extract_function_by_indent, get_source_line, load_src_lines
from parser import build_func_summary


def render_func_summary(df_profile: pd.DataFrame) -> pd.DataFrame:
    """Отображает таблицу и бар-чарт статистики по функциям.

    Args:
        df_profile: DataFrame из parse_lprof

    Returns:
        func_summary DataFrame для использования в других секциях.
    """
    func_summary = build_func_summary(df_profile)

    cols = st.columns(2)

    with cols[0]:
        st.markdown("## 📊 Статистика по функциям")
        st.dataframe(func_summary, use_container_width=True)

    with cols[1]:
        fig = px.bar(
            func_summary,
            x="func",
            y="total_time_s",
            color="file",
            title="Время исполнения по функциям (сек)",
        )
        st.plotly_chart(fig, use_container_width=True)

    return func_summary


def render_line_details(df_profile: pd.DataFrame, src_files: SrcFilesDict) -> None:
    """Отображает таблицу деталей профилирования по строкам с фильтром.

    Args:
        df_profile: DataFrame из parse_lprof
        src_files: словарь загруженных исходников
    """
    st.markdown("## 🔍 Детали по строкам")

    if not src_files:
        st.info("💡 Загрузите .py файлы, чтобы видеть код в колонке Code.")

    min_time = st.slider("Мин время (s)", 0.0, float(df_profile["time_s"].max()), 0.0)

    filtered = df_profile[df_profile["time_s"] >= min_time].copy()
    filtered["Code"] = filtered.apply(
        lambda r: get_source_line(r["file"], r["lineno"], src_files), axis=1
    )

    st.dataframe(
        filtered[["file", "func", "lineno", "hits", "time_s", "Code"]].sort_values(
            by="time_s", ascending=False
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "📥 Скачать CSV",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name="profile_lines.csv",
        mime="text/csv",
    )


def render_function_viewer(
    df_profile: pd.DataFrame,
    func_summary: pd.DataFrame,
    src_files: SrcFilesDict,
) -> None:
    """Отображает секцию просмотра кода выбранной функции.

    Args:
        df_profile: DataFrame из parse_lprof
        func_summary: DataFrame из build_func_summary
        src_files: словарь загруженных исходников
    """
    st.markdown("## 📌 Просмотр кода функции")

    sel_func = st.selectbox("Выберите функцию", func_summary["func"].unique())

    if not sel_func:
        return

    df_func = df_profile[df_profile["func"] == sel_func]

    for (file_name, start_line), df_one_func in df_func.groupby(["file", "start"]):
        src_lines = load_src_lines(file_name, src_files)

        if not src_lines:
            st.warning(f"Исходник для {file_name} не найден.")
            continue

        func_lines = extract_function_by_indent(src_lines, int(start_line))
        df_code = _build_code_df(func_lines, df_one_func)

        with st.expander(f"📂 {sel_func} — {file_name}:{start_line}"):
            _render_heatmap(df_code)
            _render_line_chart(df_code)


def _build_code_df(
    func_lines: list[tuple[int, str]],
    df_one_func: pd.DataFrame,
) -> pd.DataFrame:
    """Собирает DataFrame строк функции с данными профилировщика.

    Args:
        func_lines: список (номер_строки, текст) из extract_function_by_indent
        df_one_func: строки профиля только для этой функции

    Returns:
        DataFrame с колонками: Line, Hits, Time (s), Code
    """
    rows = []
    for ln, text in func_lines:
        prof_row = df_one_func[df_one_func["lineno"] == ln]
        time_s = float(prof_row["time_s"].iloc[0]) if not prof_row.empty else 0.0
        hits = int(prof_row["hits"].iloc[0]) if not prof_row.empty else 0
        rows.append({"Line": ln, "Hits": hits, "Time (s)": time_s, "Code": text})

    return pd.DataFrame(rows)


def _render_heatmap(df_code: pd.DataFrame) -> None:
    """Рендерит HTML-тепловую карту строк кода.

    Строки окрашиваются в красный пропорционально времени исполнения.
    Рядом с каждой строкой показывается время и количество хитов.

    Args:
        df_code: DataFrame из _build_code_df
    """
    max_time = df_code["Time (s)"].max()

    highlighted = ""
    for _, row in df_code.iterrows():
        color_style = ""
        if row["Time (s)"] > 0 and max_time > 0:
            hue = row["Time (s)"] / max_time
            red = int(255 * hue)
            color_style = f"background-color: rgba({red}, 80, 80, 0.35);"

        time_label = f"{row['Time (s)']:.4f}s" if row["Time (s)"] > 0 else " " * 10
        hits_label = f"×{row['Hits']}" if row["Hits"] > 0 else "   "

        highlighted += (
            f"<div style='{color_style} font-family: monospace; padding: 1px 6px; white-space: pre;'>"
            f"<span style='color: #888; user-select: none;'>"
            f"{row['Line']:4d}  {time_label:>10}  {hits_label:>6}  "
            f"</span>"
            f"{row['Code']}"
            f"</div>"
        )

    st.markdown(highlighted, unsafe_allow_html=True)


def _render_line_chart(df_code: pd.DataFrame) -> None:
    """Рендерит бар-чарт нагрузки по строкам функции.

    Args:
        df_code: DataFrame из _build_code_df
    """
    df_nonzero = df_code[df_code["Time (s)"] > 0]

    if df_nonzero.empty:
        return

    fig = px.bar(
        df_nonzero,
        x="Line",
        y="Time (s)",
        hover_data=["Hits", "Code"],
        title="Нагрузка по строкам",
        color="Time (s)",
        color_continuous_scale="Reds",
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)