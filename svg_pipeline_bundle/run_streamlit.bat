@echo off
setlocal
cd /d %~dp0
python -m streamlit run svg_unificado_app.py
