@echo off
REM =============================================================================
REM comprimir_modelo_app.bat
REM
REM Comprime data/05_modelado/models/Stacking__balanced.pkl con joblib (compress=3)
REM para que pese ~23 MB en vez de 80 MB y entre con holgura en GitHub.
REM
REM USO:
REM   Doble clic sobre este fichero, o desde PowerShell/CMD:
REM     comprimir_modelo_app.bat
REM
REM CUANDO USARLO:
REM   - Despues de reentrenar el Stacking__balanced en Fase 5
REM   - Antes de hacer push del modelo a GitHub
REM
REM SEGURIDAD:
REM   - Hace una copia de seguridad antes de comprimir (.bak)
REM   - Verifica que el modelo se carga correctamente despues
REM   - Si algo falla, conserva el original
REM =============================================================================

setlocal

REM Activar entorno conda
call conda activate tfm_abandono
if errorlevel 1 (
    echo [ERROR] No se pudo activar el entorno conda 'tfm_abandono'.
    echo         Ejecuta este script desde Anaconda Prompt o asegurate de
    echo         que conda esta en el PATH.
    pause
    exit /b 1
)

REM Lanzar el script Python que hace el trabajo
python "%~dp0comprimir_modelo_app.py"
set EXITCODE=%errorlevel%

echo.
if %EXITCODE%==0 (
    echo [OK] Modelo comprimido correctamente.
) else (
    echo [ERROR] Algo fallo. Revisa el mensaje de arriba.
)

pause
endlocal
exit /b %EXITCODE%
