@echo off
setlocal
cd /d "%~dp0"
set "SCIV_IMPORT_PYTHON=%~dp0..\tools-external\castlevania-hd\.venv\Scripts\python.exe"
if exist "%SCIV_IMPORT_PYTHON%" (
  "%SCIV_IMPORT_PYTHON%" "%~dp0tools\hd\import_workspace.py"
) else (
  py -3 "%~dp0tools\hd\import_workspace.py"
)
if errorlevel 1 (
  echo Der HD-Import benoetigt Python mit Pillow, NumPy und Tkinter.
  pause
)
