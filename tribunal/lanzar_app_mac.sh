#!/bin/bash
# =============================================================================
# lanzar_app_mac.sh
# Lanza la app Streamlit del TFM en Mac o Linux
#
# USO:
#   bash lanzar_app_mac.sh
# REQUISITO:
#   Anaconda o Miniconda instalado
# =============================================================================

echo ""
echo " ============================================================"
echo "  TFM — Predicción de Abandono Universitario · UJI"
echo "  María José Morte Ruiz · UOC + UJI · 2026"
echo " ============================================================"
echo ""
echo " Iniciando la aplicación..."
echo " El navegador se abrirá automáticamente."
echo " Para cerrar la app: Ctrl+C en esta terminal."
echo ""

# ---------------------------------------------------------------------------
# Localizar conda
# ---------------------------------------------------------------------------
# En Mac/Linux conda puede estar en distintos sitios según la instalación.
# Probamos las rutas más habituales.

CONDA_PATHS=(
    "$HOME/anaconda3/etc/profile.d/conda.sh"
    "$HOME/miniconda3/etc/profile.d/conda.sh"
    "/opt/anaconda3/etc/profile.d/conda.sh"
    "/opt/miniconda3/etc/profile.d/conda.sh"
    "/usr/local/anaconda3/etc/profile.d/conda.sh"
)

CONDA_FOUND=false
for path in "${CONDA_PATHS[@]}"; do
    if [ -f "$path" ]; then
        source "$path"
        CONDA_FOUND=true
        break
    fi
done

if [ "$CONDA_FOUND" = false ]; then
    echo " ERROR: No se encontró la instalación de Conda."
    echo " Asegúrate de que Anaconda o Miniconda está instalado."
    echo ""
    exit 1
fi

# ---------------------------------------------------------------------------
# Activar entorno
# ---------------------------------------------------------------------------
conda activate tfm_abandono

if [ $? -ne 0 ]; then
    echo ""
    echo " ERROR: No se pudo activar el entorno 'tfm_abandono'."
    echo " Verifica que el entorno existe con: conda env list"
    echo ""
    exit 1
fi

# ---------------------------------------------------------------------------
# Ir a la carpeta de la app
# ---------------------------------------------------------------------------
# SCRIPT_DIR es el directorio donde está este script (tribunal/)
# Subimos un nivel con .. para llegar a AU_UJI/, luego entramos en app/

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/../app"

cd "$APP_DIR" || {
    echo " ERROR: No se encontró la carpeta app/."
    exit 1
}

if [ ! -f "main.py" ]; then
    echo " ERROR: No se encontró main.py en $APP_DIR"
    exit 1
fi

echo " Entorno: tfm_abandono"
echo " Carpeta: $(pwd)"
echo " Fichero: main.py"
echo ""
echo " Abriendo navegador en http://localhost:8501"
echo ""

# ---------------------------------------------------------------------------
# Lanzar Streamlit
# ---------------------------------------------------------------------------
streamlit run main.py --server.headless false --server.port 8501
