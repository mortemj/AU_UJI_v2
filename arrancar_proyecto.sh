#!/usr/bin/env bash
# ============================================================================
# ARRANCAR PROYECTO — TFM AU_UJI Dinámico (V2)
# ============================================================================
# Para ejecutarlo:
#   1. Abre Terminal en la carpeta del proyecto.
#   2. Da permisos de ejecución la primera vez:  chmod +x arrancar_proyecto.sh
#   3. Ejecuta:  ./arrancar_proyecto.sh
#
# Si es la primera vez, primero hay que crear el entorno (ver manual_inicio.html).
# ============================================================================

set -e

# Cambiar a la carpeta donde está este script (raíz del proyecto)
cd "$(dirname "$0")"

echo ""
echo "============================================================================"
echo " TFM AU_UJI Dinámico (V2) - Arrancar Proyecto"
echo "============================================================================"
echo ""
echo " Carpeta del proyecto: $(pwd)"
echo ""

# Detectar conda
if ! command -v conda &> /dev/null; then
    # Intentar ubicaciones habituales
    for CANDIDATO in "$HOME/anaconda3/etc/profile.d/conda.sh" \
                     "$HOME/miniconda3/etc/profile.d/conda.sh" \
                     "/opt/anaconda3/etc/profile.d/conda.sh" \
                     "/opt/homebrew/anaconda3/etc/profile.d/conda.sh"; do
        if [ -f "$CANDIDATO" ]; then
            # shellcheck source=/dev/null
            source "$CANDIDATO"
            break
        fi
    done
fi

if ! command -v conda &> /dev/null; then
    echo " [ERROR] No se ha encontrado conda en el PATH."
    echo ""
    echo " Si Anaconda/Miniconda está instalado en una ubicación no estándar,"
    echo " inicializa conda manualmente y ejecuta:"
    echo "   conda activate tfm_abandono"
    echo "   jupyter notebook notebooks/fase0_configuracion"
    echo ""
    exit 1
fi

echo " conda detectado: $(which conda)"
echo ""
echo " Activando entorno 'tfm_abandono'..."

if ! conda activate tfm_abandono 2>/dev/null; then
    echo ""
    echo " [ERROR] No se ha podido activar el entorno 'tfm_abandono'."
    echo " Probablemente no está creado."
    echo ""
    echo " Para crearlo, ejecuta en Terminal:"
    echo "   cd $(pwd)"
    echo "   conda create -n tfm_abandono python=3.11 -y"
    echo "   conda activate tfm_abandono"
    echo "   pip install -r notebooks/requirements.txt"
    echo ""
    exit 1
fi

echo " Entorno activado correctamente."
echo ""
echo " Lanzando Jupyter Notebook en notebooks/fase0_configuracion/"
echo " (cierra esta terminal cuando hayas terminado de usar Jupyter)."
echo ""

jupyter notebook notebooks/fase0_configuracion
