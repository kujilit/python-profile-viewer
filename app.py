import streamlit as st

from parser import parse_lprof
from ui import render_func_summary, render_function_viewer, render_line_details

st.set_page_config(page_title="LProf Viewer", layout="wide")
st.title("Аналитика lprof файлов профилировщика Python")

upload_cols = st.columns(2)

with upload_cols[0]:
    lprof_file = st.file_uploader("Загрузите .lprof файл", type="lprof")

with upload_cols[1]:
    src_files_uploaded = st.file_uploader(
        "Загрузите исходники (.py файлы)", type="py", accept_multiple_files=True
    )

src_files: dict[str, list[str]] = {}
if src_files_uploaded:
    for f in src_files_uploaded:
        src_files[f.name] = f.getvalue().decode("utf-8").splitlines()


if not lprof_file:
    st.stop()

df_profile = parse_lprof(lprof_file)

if df_profile is None or df_profile.empty:
    st.stop()

func_summary = render_func_summary(df_profile)
render_line_details(df_profile, src_files)
render_function_viewer(df_profile, func_summary, src_files)