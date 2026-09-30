@echo off
rem Offline evaluation: run with ALL network connections off (airplane mode).
rem Refuses to run if the internet is reachable. Everything is logged to evidence\offline\offline-run-log.txt
cd /d "%~dp0"
set LOG=evidence\offline\offline-run-log.txt
if not exist evidence\offline mkdir evidence\offline

curl -s -m 5 -o NUL https://www.google.com
if %errorlevel%==0 (
  echo The internet is still reachable. Turn on airplane mode or disconnect every network, then run this again.
  pause
  exit /b 1
)

echo Offline confirmed. Running, this takes about 5 minutes. Do not reconnect until you see DONE.
> %LOG% echo == %date% %time% offline run
>> %LOG% echo == internet check: google.com NOT reachable (curl failed), machine is offline
>> %LOG% ipconfig | findstr /i "IPv4 adapter disconnected"
>> %LOG% echo == ollama version:
>> %LOG% curl -s -m 5 http://localhost:11434/api/version
>> %LOG% echo.
>> %LOG% echo == wiki help
.venv\Scripts\python.exe -m wiki help >> %LOG% 2>&1
>> %LOG% echo == wiki search Vercel hosting
.venv\Scripts\python.exe -m wiki search Vercel hosting -k 3 >> %LOG% 2>&1
>> %LOG% echo == wiki ingest vault\raw\Draft Copilot.md --force
.venv\Scripts\python.exe -m wiki ingest "vault\raw\Draft Copilot.md" --force >> %LOG% 2>&1
>> %LOG% echo == evaluation: 4 ask tests + mode checks
.venv\Scripts\python.exe tests\run_eval.py --label offline >> %LOG% 2>&1
>> %LOG% echo == finished %date% %time%

type %LOG%
echo.
echo DONE. Take a screenshot showing this window and the no-network icon, then reconnect.
pause
