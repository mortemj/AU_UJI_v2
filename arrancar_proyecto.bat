@echo off
REM ============================================================================
REM ARRANCAR PROYECTO — TFM AU_UJI Dinámico (V2)
REM ============================================================================
REM Doble clic sobre este fichero para:
REM   1. Activar el entorno conda 'tfm_abandono'
REM   2. Lanzar Jupyter Notebook directamente en notebooks/fase0_configuracion/
REM
REM Si es la primera vez, primero hay que crear el entorno (ver manual_inicio.html).
REM ============================================================================

setlocal

REM Cambiar a la carpeta donde está este .bat (raíz del proyecto)
cd /d "%~dp0"

echo.
echo ============================================================================
echo  TFM AU_UJI Dinamico (V2) - Arrancar Proyecto
echo ============================================================================
echo.
echo  Carpeta del proyecto: %CD%
echo.

REM Detectar Anaconda en ubicaciones habituales
set "ANACONDA_PATH="
if exist "%USERPROFILE%\anaconda3\Scripts\activate.bat" set "ANACONDA_PATH=%USERPROFILE%\anaconda3"
if exist "%USERPROFILE%\Anaconda3\Scripts\activate.bat" set "ANACONDA_PATH=%USERPROFILE%\Anaconda3"
if exist "%USERPROFILE%\miniconda3\Scripts\activate.bat" set "ANACONDA_PATH=%USERPROFILE%\miniconda3"
if exist "C:\ProgramData\Anaconda3\Scripts\activate.bat" set "ANACONDA_PATH=C:\ProgramData\Anaconda3"

if "%ANACONDA_PATH%"=="" (
    echo  [ERROR] No se ha encontrado Anaconda/Miniconda.
    echo.
    echo  Si Anaconda esta instalado en una ubicacion no estandar:
    echo    1. Abre Anaconda Prompt manualmente.
    echo    2. cd "%CD%"
    echo    3. conda activate tfm_abandono
    echo    4. jupyter notebook notebooks\fase0_configuracion
    echo.
    pause
    exit /b 1
)

echo  Anaconda detectado en: %ANACONDA_PATH%
echo.
echo  Activando entorno 'tfm_abandono'...
call "%ANACONDA_PATH%\Scripts\activate.bat" tfm_abandono

if %ERRORLEVEL% neq 0 (
    echo.
    echo  [ERROR] No se ha podido activar el entorno 'tfm_abandono'.
    echo  Probablemente no esta creado.
    echo.
    echo  Para crearlo, abre Anaconda Prompt y ejecuta:
    echo    cd "%CD%"
    echo    conda create -n tfm_abandono python=3.11 -y
    echo    conda activate tfm_abandono
    echo    pip install -r notebooks\requirements.txt
    echo.
    pause
    exit /b 1
)

echo  Entorno activado correctamente.
echo.
echo  Lanzando Jupyter Notebook en notebooks\fase0_configuracion\
echo  (cierra esta ventana cuando hayas terminado de usar Jupyter).
echo.

jupyter notebook notebooks\fase0_configuracion

endlocal
