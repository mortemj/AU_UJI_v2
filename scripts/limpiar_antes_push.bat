@echo off
REM ===========================================================================
REM limpiar_antes_push.bat - Lanzador Windows para limpiar_antes_push.py
REM Autora: Maria Jose Morte
REM Proyecto: TFM AU_UJI v2
REM Fecha: 04/05/2026
REM
REM Que hace:
REM   1. Activa el entorno conda 'tfm_abandono'
REM   2. Cambia a la raiz del proyecto
REM   3. Lanza el script Python (acepta flag --dry-run pasado al .bat)
REM   4. Pausa al final para que se vea la salida (cierra con tecla)
REM
REM Uso:
REM   limpiar_antes_push.bat              -> doble clic, modo interactivo
REM   limpiar_antes_push.bat --dry-run    -> desde cmd, solo muestra
REM ===========================================================================

setlocal

REM --- Cambiar a raiz del proyecto (un nivel arriba de scripts/) ---
cd /d "%~dp0\.."

echo.
echo ============================================================================
echo   Lanzando limpieza local ... (entorno conda: tfm_abandono)
echo ============================================================================
echo.

REM --- Activar conda y entorno ---
REM Si Anaconda no esta en el PATH del sistema, descomenta y ajusta esta linea:
REM call C:\ProgramData\Anaconda3\Scripts\activate.bat
call conda activate tfm_abandono

REM --- Verificar que la activacion fue OK ---
if errorlevel 1 (
    echo.
    echo [ERROR] No se ha podido activar el entorno 'tfm_abandono'.
    echo         Comprueba que conda esta en el PATH y el entorno existe.
    pause
    exit /b 1
)

REM --- Lanzar el script Python (pasa todos los argumentos del .bat) ---
python scripts\limpiar_antes_push.py %*

REM --- Pausa final para ver la salida ---
echo.
pause

endlocal