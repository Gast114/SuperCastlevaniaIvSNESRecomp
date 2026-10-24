@echo off
setlocal
cd /d "%~dp0"
set "SCIV_WORKSHOP_PYTHON=%~dp0..\tools-external\castlevania-hd\.venv\Scripts\python.exe"
if not exist "%SCIV_WORKSHOP_PYTHON%" (
  echo Python-Umgebung fehlt. Bitte die vorhandene HD-Werkzeugumgebung einrichten.
  pause
  exit /b 1
)
cmake -S . -B build-lua -G Ninja -DCMAKE_BUILD_TYPE=Release -DSNESRECOMP_ENABLE_LUA=ON
if errorlevel 1 goto failed
cmake --build build-lua --target SuperCastlevaniaIvSNESRecomp -j 8
if errorlevel 1 goto failed
"%SCIV_WORKSHOP_PYTHON%" "%~dp0tools\enemy_workshop_library.py" --ensure
if errorlevel 1 goto failed
"%SCIV_WORKSHOP_PYTHON%" "%~dp0tools\prepare_sprite_library.py" --ensure
if errorlevel 1 goto failed
"%SCIV_WORKSHOP_PYTHON%" "%~dp0tools\prepare_monster_resources.py" --ensure
if errorlevel 1 goto failed
"%SCIV_WORKSHOP_PYTHON%" "%~dp0tools\enemy_workshop.py" --prepare-library
if errorlevel 1 goto failed
"%SCIV_WORKSHOP_PYTHON%" "%~dp0tools\monster_workshop.py"
if errorlevel 1 goto failed
exit /b 0
:failed
echo Die Gegner-Werkstatt konnte nicht starten. Die Fehlermeldung steht oben.
pause
exit /b 1
