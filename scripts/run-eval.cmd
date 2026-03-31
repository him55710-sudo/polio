@echo off
setlocal
cd /d %~dp0\..
echo [Polio] Starting Evaluation Harness v1...
python eval\runner\eval_runner.py
if %ERRORLEVEL% NEQ 0 (
    echo [Polio] Evaluation run failed with error code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)
echo [Polio] Evaluation run successful.
pause
