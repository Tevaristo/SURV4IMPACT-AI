@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo  Instalacao do SURV4IMPACT AI - Revisor de Questionarios
echo ============================================================
echo.

where py >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_CMD=py"
  goto :python_found
)

where python >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_CMD=python"
  goto :python_found
)

echo Python nao foi encontrado.
echo.
echo Instale primeiro o Python 3.14 de 64 bits e ative a opcao
echo "Add Python to PATH" durante a instalacao.
echo Depois, execute novamente este ficheiro.
echo.
pause
exit /b 1

:python_found
echo Python encontrado. A verificar a versao...
%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 (
  echo.
  echo E necessario Python 3.11 ou mais recente.
  echo Recomenda-se Python 3.14 de 64 bits.
  echo.
  pause
  exit /b 1
)

if exist ".venv\Scripts\python.exe" (
  echo Foi encontrado um ambiente anterior.
  set /p RECREATE="Pretende recria-lo? [s/N]: "
  if /I "!RECREATE!"=="s" (
    rmdir /s /q ".venv"
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo A criar o ambiente privado da aplicacao...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto :install_error
)

echo.
echo A instalar as dependencias. E necessaria ligacao a Internet...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :install_error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :install_error

echo.
echo ============================================================
echo  Instalacao concluida com sucesso.
echo ============================================================
echo.
echo Para iniciar, use o ficheiro iniciar_aplicacao.bat.
echo.
pause
exit /b 0

:install_error
echo.
echo A instalacao nao foi concluida. Verifique a ligacao a Internet
echo e consulte as instrucoes no ficheiro README.md.
echo.
pause
exit /b 1
