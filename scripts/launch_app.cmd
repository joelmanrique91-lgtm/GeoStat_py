@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"
set "CONDA_BAT="

echo [GeoStat] Repo: %REPO_ROOT%

if defined CONDA_EXE (
  for %%I in ("%CONDA_EXE%") do set "CONDA_EXE_DIR=%%~dpI"
  if exist "!CONDA_EXE_DIR!..\condabin\conda.bat" set "CONDA_BAT=!CONDA_EXE_DIR!..\condabin\conda.bat"
)

if not defined CONDA_BAT if exist "%USERPROFILE%\anaconda3\condabin\conda.bat" set "CONDA_BAT=%USERPROFILE%\anaconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "%USERPROFILE%\miniconda3\condabin\conda.bat" set "CONDA_BAT=%USERPROFILE%\miniconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "C:\ProgramData\anaconda3\condabin\conda.bat" set "CONDA_BAT=C:\ProgramData\anaconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "C:\ProgramData\miniconda3\condabin\conda.bat" set "CONDA_BAT=C:\ProgramData\miniconda3\condabin\conda.bat"

if not defined CONDA_BAT (
  for /f "delims=" %%I in ('where conda.bat 2^>nul') do (
    set "CONDA_BAT=%%I"
    goto :conda_found
  )
)

:conda_found
if not defined CONDA_BAT (
  echo [ERROR] No se encontro conda.bat. Instala/abre Anaconda o Miniconda y vuelve a intentar.
  echo [ERROR] Se aborta porque no se puede activar el environment geostat-py.
  pause
  exit /b 1
)

echo [GeoStat] Usando conda: %CONDA_BAT%
call "%CONDA_BAT%" activate geostat-py
if errorlevel 1 (
  echo [ERROR] No se pudo activar el environment "geostat-py".
  echo [ERROR] Verifica que exista: conda env list
  pause
  exit /b 1
)

cd /d "%REPO_ROOT%"
python "%REPO_ROOT%\scripts\update_and_run.py"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo [ERROR] El launcher termino con codigo %EXIT_CODE%.
  pause
)

exit /b %EXIT_CODE%
