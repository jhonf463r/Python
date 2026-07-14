@echo off
setlocal
cd /d %~dp0
python -m pip install -r requirements.txt
pyinstaller --noconfirm --clean --onefile --name SVG_Pipeline_Unificado --add-data "svg_origen.py;." --add-data "svg_optimizer.py;." svg_unificado_app.py
echo.
echo Ejecutable creado en dist\SVG_Pipeline_Unificado.exe
pause
