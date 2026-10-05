@echo off
setlocal
cd /d "%~dp0"
title Semaforo Inteligente

where py >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON=py -3"
) else (
    set "PYTHON=python"
)

%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo Python nao foi encontrado.
    echo Instale o Python 3.12 ou 3.13 marcando "Add Python.exe to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Criando o ambiente do projeto...
    %PYTHON% -m venv .venv
)

echo Instalando/verificando as dependencias...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo Nao foi possivel instalar as dependencias.
    pause
    exit /b 1
)

echo Abrindo o painel em http://localhost:5000
start "" http://localhost:5000
echo Para encerrar, feche esta janela ou pressione Ctrl+C.
.venv\Scripts\python.exe run.py --port 5000 --source 0
pause
