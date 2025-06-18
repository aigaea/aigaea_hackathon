@echo off
cd /d "%~dp0"

@REM echo *%VIRTUAL_ENV%*
if '%VIRTUAL_ENV%' neq '' (
    call .venv/Scripts/deactivate.bat
)

set PYTHON_HOME=%LOCALAPPDATA%\Programs\Python\Python311
echo %PATH% | findstr /C:%PYTHON_HOME% >nul
if %ERRORLEVEL% == 1 (
    echo %PYTHON_HOME%
    set PATH=%PYTHON_HOME%;%PYTHON_HOME%\Scripts;C:\WINDOWS\system32;C:\WINDOWS
)

@REM Read configuration into the environment
set UVICORN_PORT=8000
setlocal enabledelayedexpansion
for /f "delims=" %%i in ('type ".env" ^|find /i "UVICORN_PORT="') do ( set %%i )
@REM echo Port=%UVICORN_PORT%

if "%1%"=="init" (
    if exist .venv (
        echo Virtual Environment already exists
        call .venv/Scripts/activate.bat
        pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    ) else (
        echo Install Virtual Environment ...
        python -m venv .venv
        call .venv/Scripts/activate.bat
        pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    )
    @REM pause>nul
) else if "%1%"=="clear" (
    rmdir /s/q "__pycache__"
) else (
    @REM Check whether the port is occupied
    echo Port Occupation Detection ...
    if %UVICORN_PORT% GTR 100 (
        for /f "tokens=1-5" %%i in ('netstat -ano ^|findstr ":%UVICORN_PORT%" ^|findstr "LISTENING"') do (
            echo The port %%i:%UVICORN_PORT% already used!
            exit /b
        )
    )

    echo Virtual Environment Activation ...
    call .venv/Scripts/activate.bat

    echo Launch main.py ...
    python main.py %1 %2 %3 %4 %5 %6
)
