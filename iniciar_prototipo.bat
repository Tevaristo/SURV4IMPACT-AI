@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente .venv nao encontrado. Consulte README_PROTOTIPO.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m streamlit run app_prototipo.py --server.address 127.0.0.1 --server.port 8502 --browser.gatherUsageStats false
endlocal
