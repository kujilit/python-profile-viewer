import streamlit as st
import pickle
import re
from pathlib import Path
import pandas as pd
import plotly.express as px

from typing import Any

st.set_page_config(page_title="LProf Viewer", layout="wide")
st.title("Аналитика lprof файлов профилировщика Python")


cols = st.columns(2)

with cols[0]:
    lprof_file = st.file_uploader("Загрузите .lprof файл", type="lprof")

with cols[1]:
    src_files_uploaded = st.file_uploader(
        "Загрузите исходники (.py файлы)", type="py", accept_multiple_files=True
    )

src_files = {}

if src_files_uploaded:
    for f in src_files_uploaded:
        src_files[f.name] = f.getvalue().decode("utf-8").splitlines()


def get_source_line_from_loaded(fn, lineno, src_files):
    resolved = resolve_source_file(fn, src_files)

    src_lines = src_files.get(resolved)

    if not src_lines:
        try:
            with open(resolved, "r", encoding="utf-8") as f:
                src_lines = f.read().splitlines()
        except:
            return ""

    if 0 < lineno <= len(src_lines):
        return src_lines[lineno - 1]

    return ""


def resolve_source_file(profile_filename, src_files):
    p = Path(profile_filename)
    pf = p.as_posix()
    base = p.name

    if pf in src_files:
        return pf

    if base in src_files:
        return base

    parts = pf.split("/")
    for length in range(len(parts), 0, -1):
        sub = "/".join(parts[-length:])
        if sub in src_files:
            return sub

    for key in src_files.keys():
        if base.lower() == Path(key).name.lower():
            return key

    return pf


def extract_function_by_indent(src_lines: list[str], start_line: int) -> list[str]:
    """Извлечение функции из исходника

    Args:
        src_lines (list[str]): список строк исходника
        start_line (int): начало функции

    Returns:
        list[str]: строки функции
    """

    i = start_line - 1

    while i < len(src_lines) and src_lines[i].strip().startswith("@"):
        i += 1

    while i < len(src_lines) and not src_lines[i].strip().startswith("def "):
        i += 1

    if i >= len(src_lines):
        return []

    def_line_index = i
    def_line = src_lines[def_line_index]
    indent_def = len(def_line) - len(def_line.lstrip())

    func_lines = []

    for j in range(start_line - 1, def_line_index + 1):
        func_lines.append((j + 1, src_lines[j]))

    for k in range(def_line_index + 1, len(src_lines)):
        line = src_lines[k]
        stripped = line.strip()

        if stripped == "":
            func_lines.append((k + 1, line))
            continue

        current_indent = len(line) - len(line.lstrip())

        if current_indent <= indent_def:
            break

        func_lines.append((k + 1, line))

    return func_lines


def parse_lprof(uploaded_lprof: Any) -> pd.DataFrame:
    """Парсинг lprof файла

    Args:
        uploaded_lprof (UploadedFile): загруженный файл

    Returns:
        pd.DataFrame: Датафрейм с данными line_profiler
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
            except:
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

    return pd.DataFrame(result)


def main():
    if not lprof_file:
        st.stop()

    df_profile = parse_lprof(lprof_file)

    if df_profile is None or df_profile.empty:
        st.stop()

    with cols[0]:
        st.markdown("## 📊 Статистика по функциям")

        func_summary = (
            df_profile.groupby(["file", "func"])
            .agg(
                total_time_s=("time_s", "sum"),
                total_hits=("hits", "sum"),
            )
            .reset_index()
            .sort_values("total_time_s", ascending=False)
        )

        func_summary["pct"] = func_summary["total_time_s"] / func_summary["total_time_s"].sum() * 100

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


    st.markdown("## 🔍 Детали по строкам")

    min_time = st.slider("Мин время (s)", 0.0, float(df_profile["time_s"].max()), 0.0)

    filtered = df_profile[df_profile["time_s"] >= min_time].copy()

    filtered["Code"] = filtered.apply(
        lambda r: get_source_line_from_loaded(r["file"], r["lineno"], src_files), axis=1
    )

    st.dataframe(
        filtered[["file", "func", "lineno", "hits", "time_s", "Code"]].sort_values(
            by="time_s", ascending=False
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("## 📌 Просмотр кода функции")

    sel_func = st.selectbox("Выберите функцию", func_summary["func"].unique())

    if sel_func:
        df_func = df_profile[df_profile["func"] == sel_func]

        grouped = df_func.groupby(["file", "start"])

        for (file_name, start_line), df_one_func in grouped:
            resolved = resolve_source_file(file_name, src_files)

            src_lines = src_files.get(resolved)

            if not src_lines:
                try:
                    with open(resolved, "r", encoding="utf-8") as f:
                        src_lines = f.read().splitlines()
                except:
                    src_lines = None

            if not src_lines:
                st.warning(f"Исходник для {file_name} не найден.")
                continue

            func_lines = extract_function_by_indent(src_lines, int(start_line))

            code_rows = []
            max_time = df_one_func["time_s"].max()

            for ln, text in func_lines:
                prof_row = df_one_func[df_one_func["lineno"] == ln]
                time_s = float(prof_row["time_s"]) if not prof_row.empty else 0.0
                hits = int(prof_row["hits"]) if not prof_row.empty else 0

                code_rows.append(
                    {"Line": ln, "Hits": hits, "Time (s)": time_s, "Code": text}
                )

            df_code = pd.DataFrame(code_rows)

            with st.expander(f"📂 {sel_func} — {file_name}:{start_line}"):

                highlighted = ""
                for _, row in df_code.iterrows():
                    color_style = ""
                    if row["Time (s)"] > 0 and max_time > 0:
                        hue = row["Time (s)"] / max_time
                        red = int(255 * hue)
                        color_style = f"background-color: rgba({red}, 80, 80, 0.35);"

                    time_label = f"{row['Time (s)']:.4f}s" if row["Time (s)"] > 0 else "        "
                    hits_label = f"×{row['Hits']}" if row["Hits"] > 0 else "   "

                    highlighted += (
                        f"<div style='{color_style} font-family: monospace; padding: 1px 6px; white-space: pre;'>"
                        f"<span style='color: #888; user-select: none;'>{row['Line']:4d}  "
                        f"{time_label:>10}  {hits_label:>6}  </span>"
                        f"{row['Code']}"
                        f"</div>"
                    )

                st.markdown(highlighted, unsafe_allow_html=True)

                fig2 = px.bar(
                    df_code[df_code["Time (s)"] > 0],
                    x="Line",
                    y="Time (s)",
                    hover_data=["Hits", "Code"],
                    title="Нагрузка по строкам",
                    color="Time (s)",
                    color_continuous_scale="Reds",
                )
                fig2.update_layout(showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)


if __name__ == "__main__":
    main()