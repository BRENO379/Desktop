@echo off
REM ============================================================
REM  Caderno de Provas - Quantitativo de ACS/ACE (SCNES + e-Gestor)
REM  Duplo clique para rodar. O caderno sai na Area de Trabalho.
REM ============================================================
chcp 65001 >nul
setlocal
title Caderno de Provas ACS/ACE
cd /d "%~dp0"

REM ---------- 1. Python instalado? ----------
where python >nul 2>nul
if errorlevel 1 (
  echo [ERRO] Python nao encontrado.
  echo Instale em https://www.python.org/downloads/ marcando "Add python.exe to PATH".
  pause
  exit /b 1
)

REM ---------- 2. Bibliotecas (instala so o que faltar) ----------
echo Verificando bibliotecas...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo [ERRO] Falha ao instalar as bibliotecas. Verifique a internet e tente de novo.
  pause
  exit /b 1
)

REM ---------- 3. Perguntas ----------
echo.
set "MUN="
set "UF="
set "INI="
set "FIM="
set /p MUN=Municipio (ex.: Ponte Nova): 
set /p UF=UF (ex.: MG): 
set /p INI=Competencia inicial AAAAMM (Enter = ultimos 5 anos): 
set /p FIM=Competencia final AAAAMM (Enter = ultima publicada): 
if "%MUN%"=="" (
  echo [ERRO] Informe o municipio.
  pause
  exit /b 1
)

set ARGS=--municipio "%MUN%" --uf %UF%
if not "%INI%"=="" set ARGS=%ARGS% --inicio %INI%
if not "%FIM%"=="" set ARGS=%ARGS% --fim %FIM%

REM ---------- 4. Pasta de saida = Area de Trabalho (funciona com OneDrive) ----------
set "DESK="
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESK=%%D"
if "%DESK%"=="" set "DESK=%USERPROFILE%\Desktop"

REM ---------- 5. Rodar ----------
python scripts\caderno.py %ARGS% --saida "%DESK%"
echo.
echo Pronto. A pasta CADERNO_ACS_ACE_... esta na sua Area de Trabalho.
pause
