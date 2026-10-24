@echo off
setlocal
cd /d "%~dp0"
set "SCIV_EDITOR_PYTHON=%~dp0..\tools-external\castlevania-hd\.venv\Scripts\python.exe"
if not exist "%SCIV_EDITOR_PYTHON%" (
  echo Python-Umgebung fehlt. Bitte die vorhandene HD-Werkzeugumgebung einrichten.
  pause
  exit /b 1
)
cmake -S . -B build-lua -G Ninja -DCMAKE_BUILD_TYPE=Release -DSNESRECOMP_ENABLE_LUA=ON
if errorlevel 1 goto failed
cmake --build build-lua --target SuperCastlevaniaIvSNESRecomp -j 8
if errorlevel 1 goto failed
if not exist "artwork-local\enemy-library\library.json" (
  "%SCIV_EDITOR_PYTHON%" "%~dp0tools\enemy_workshop_library.py" --ensure
  if errorlevel 1 goto failed
)
"%SCIV_EDITOR_PYTHON%" "%~dp0tools\prepare_monster_resources.py" --ensure
if errorlevel 1 goto failed
"%SCIV_EDITOR_PYTHON%" "%~dp0tools\level_editor.py" --demo
if errorlevel 1 goto failed
exit /b 0
:failed
echo Der Level-Editor konnte nicht starten. Die Fehlermeldung steht oben.
pause
exit /b 1
