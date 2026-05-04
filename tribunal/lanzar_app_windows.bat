@echo off
:: =============================================================================
:: lanzar_app_windows.bat
:: Lanza la app Streamlit del TFM en Windows
::
:: USO: doble clic sobre este fichero
:: REQUISITO: Anaconda instalado en el equipo
:: =============================================================================

title TFM — Predicción de Abandono UJI

echo.
echo  ============================================================
echo   TFM — Predicción de Abandono Universitario · UJI
echo   María José Morte · UOC + UJI · 2026
echo  ============================================================
echo.
echo  Iniciando la aplicación...
echo  El navegador se abrirá automáticamente.
echo  Para cerrar la app, cierra esta ventana.
echo.

:: Activamos el entorno conda con el que se entrenó el modelo
call conda activate tfm_abandono

:: Comprobamos que la activación fue correcta
if errorlevel 1 (
    echo.
    echo  ERROR: No se pudo activar el entorno "tfm_abandono".
    echo  Asegúrate de que Anaconda está instalado y el entorno existe.
    echo.
    pause
    exit /b 1
)

:: Nos movemos a la carpeta de la app
:: %~dp0 es la ruta del directorio donde está este .bat
cd /d "%~dp0..\app"

:: Comprobamos que main.py existe
if not exist "main.py" (
    echo.
    echo  ERROR: No se encontró main.py en la carpeta app/.
    echo  Verifica la estructura del proyecto.
    echo.
    pause
    exit /b 1
)

echo  Entorno: tfm_abandono
echo  Carpeta: %cd%
echo  Fichero: main.py
echo.
echo  Abriendo navegador en http://localhost:8501
echo.

:: Lanzamos Streamlit
:: --server.headless false  → abre el navegador automáticamente
:: --server.port 8501       → puerto por defecto
streamlit run main.py --server.headless false --server.port 8501

:: Si Streamlit se cierra, mostramos mensaje y esperamos
echo.
echo  La aplicación se ha cerrado.
pause
