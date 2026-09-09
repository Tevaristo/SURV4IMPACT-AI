@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo A aplicacao ainda nao esta instalada neste computador.
  echo Execute primeiro o ficheiro instalar_aplicacao.bat.
  echo.
  pause
  exit /b 1
)

echo A iniciar o SURV4IMPACT AI...
echo O navegador devera abrir automaticamente.
echo Para terminar a aplicacao, feche esta janela.
echo.

".venv\Scripts\python.exe" -m streamlit run app.py

if errorlevel 1 (
  echo.
  echo A aplicacao terminou com um erro. Consulte o README.md.
  pause
)
