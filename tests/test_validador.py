# ============================================================================
# TEST_VALIDADOR.PY — Tests automáticos del paquete src.validacion
# ============================================================================
# TFM: Predicción de Abandono Universitario UJI
#
# PROPÓSITO
# ---------
# Verifica que el paquete `src.validacion` funciona correctamente sin
# necesidad de los Excel reales de la UJI. Todos los tests son
# autocontenidos: crean Excel temporales con casos sintéticos.
#
# COBERTURA
# ---------
# - Carga del contrato (CONTRATO_EXCEL, CRUCES_ESPERADOS)
# - Función auxiliar `hojas_esperadas()`
# - 5 funciones de validación (N1-N5) con casos de éxito y de fallo
# - Orquestador `ejecutar_validacion_completa()`
# - Generador HTML
#
# CÓMO EJECUTAR
# -------------
# Desde la raíz del proyecto (C:\\FF\\AU_UJI_v2\\):
#
#     conda activate tfm_abandono
#     pytest tests/test_validador.py -v
#
# O para ver salida detallada incluso si los tests pasan:
#
#     pytest tests/test_validador.py -v -s
#
# REQUISITOS
# ----------
# - pytest (incluido en el entorno tfm_abandono por defecto)
# - openpyxl (para crear Excel temporales)
# - El paquete src.validacion correctamente instalado
#
# NOTAS
# -----
# Los tests usan fixtures de pytest para crear Excel temporales en una carpeta
# `tmp_path` que pytest gestiona automáticamente (limpieza al terminar).
# NO modificamos los Excel reales bajo ninguna circunstancia.
# ============================================================================

import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

# --- ROOT robusto: subir hasta encontrar src/ ---
ROOT = Path(__file__).resolve().parent
while not (ROOT / "src").exists():
    if ROOT.parent == ROOT:
        raise RuntimeError("No se ha encontrado src/ subiendo niveles")
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

# --- Imports a testear ---
from src.validacion.contrato_excel import (
    CONTRATO_EXCEL,
    CONTRATO_EXCEL_PRINCIPAL,
    CONTRATO_EXCEL_PREINSCRIPCION,
    CRUCES_ESPERADOS,
    TIPO_NUMERICO,
    TIPO_TEXTO,
    TIPO_FECHA,
    TIPO_MIXTO,
    hojas_esperadas,
)
from src.validacion.validador_excel import (
    _normalizar,
    _existe_columna_case_insensitive,
    _dtype_pandas_a_categoria,
    validar_n1_existencia,
    validar_n2_hojas,
    validar_n3_columnas,
    validar_n4_tipos,
    validar_n5_volumen_y_cruces,
    ejecutar_validacion_completa,
)
from src.validacion.generar_html_validacion import (
    _formatear_mensaje_es,
    _bytes_a_mb,
    _numero_es,
    _clase_estado,
    _icono_estado,
    generar_html_validacion,
)


# ============================================================================
# 1. TESTS DEL CONTRATO (estructura estática)
# ============================================================================

class TestContratoExcel:
    """Verifica la integridad del contrato CONTRATO_EXCEL."""

    def test_contrato_tiene_9_hojas(self):
        """El contrato consolidado debe tener 8 + 1 = 9 hojas."""
        assert len(CONTRATO_EXCEL) == 9

    def test_contrato_principal_tiene_8_hojas(self):
        """El Excel principal tiene 8 hojas."""
        assert len(CONTRATO_EXCEL_PRINCIPAL) == 8

    def test_contrato_preinscripcion_tiene_1_hoja(self):
        """El Excel preinscripción tiene 1 hoja (Hoja1)."""
        assert len(CONTRATO_EXCEL_PREINSCRIPCION) == 1
        assert "Hoja1" in CONTRATO_EXCEL_PREINSCRIPCION

    def test_clave_principal_esta_en_columnas_obligatorias(self):
        """La clave_principal de cada hoja debe estar en sus columnas obligatorias."""
        for nombre_hoja, contrato in CONTRATO_EXCEL.items():
            clave = contrato["clave_principal"]
            cols = contrato["columnas_obligatorias"]
            assert clave in cols, (
                f"Hoja {nombre_hoja}: clave {clave!r} no está en columnas obligatorias"
            )

    def test_todas_columnas_tienen_tipo(self):
        """Cada columna obligatoria debe tener un tipo definido."""
        for nombre_hoja, contrato in CONTRATO_EXCEL.items():
            tipos = contrato["tipos_esperados"]
            for col in contrato["columnas_obligatorias"]:
                assert col in tipos, (
                    f"Hoja {nombre_hoja}: columna {col!r} sin tipo definido"
                )

    def test_tipo_solo_acepta_4_categorias(self):
        """Los tipos esperados deben ser uno de los 4 valores válidos."""
        validos = {TIPO_NUMERICO, TIPO_TEXTO, TIPO_FECHA, TIPO_MIXTO}
        for nombre_hoja, contrato in CONTRATO_EXCEL.items():
            for col, tipo in contrato["tipos_esperados"].items():
                assert tipo in validos, (
                    f"Hoja {nombre_hoja}, col {col}: tipo {tipo!r} no válido"
                )

    def test_titulaciones_es_catalogo(self):
        """La hoja Titulaciones es la única de tipo 'catalogo'."""
        catalogos = [
            n for n, c in CONTRATO_EXCEL.items() if c["tipo"] == "catalogo"
        ]
        assert catalogos == ["Titulaciones"]

    def test_circunstancias_usa_F_mayuscula(self):
        """La hoja Circunstancias usa Per_id_Ficticio con F mayúscula (caso conocido)."""
        cols = CONTRATO_EXCEL["Circunstancias"]["columnas_obligatorias"]
        assert "Per_id_Ficticio" in cols

    def test_min_filas_son_positivos(self):
        """Todos los min_filas deben ser positivos."""
        for nombre_hoja, contrato in CONTRATO_EXCEL.items():
            assert contrato["min_filas"] > 0, (
                f"Hoja {nombre_hoja}: min_filas debe ser > 0"
            )


class TestCrucesEsperados:
    """Verifica la estructura de CRUCES_ESPERADOS."""

    def test_cruces_es_lista(self):
        assert isinstance(CRUCES_ESPERADOS, list)

    def test_cruces_no_vacia(self):
        assert len(CRUCES_ESPERADOS) > 0

    def test_cada_cruce_tiene_campos_requeridos(self):
        for cruce in CRUCES_ESPERADOS:
            for campo in ("origen", "destino", "columna", "umbral_pct"):
                assert campo in cruce, f"Cruce sin campo {campo}"

    def test_origen_y_destino_existen_en_contrato(self):
        for cruce in CRUCES_ESPERADOS:
            assert cruce["origen"] in CONTRATO_EXCEL, (
                f"Origen {cruce['origen']} no está en CONTRATO_EXCEL"
            )
            assert cruce["destino"] in CONTRATO_EXCEL, (
                f"Destino {cruce['destino']} no está en CONTRATO_EXCEL"
            )

    def test_umbral_es_porcentaje_valido(self):
        for cruce in CRUCES_ESPERADOS:
            assert 0 < cruce["umbral_pct"] <= 100


class TestHojasEsperadas:
    """Verifica la función hojas_esperadas()."""

    def test_principal_devuelve_8(self):
        assert len(hojas_esperadas("principal")) == 8

    def test_preinscripcion_devuelve_1(self):
        assert len(hojas_esperadas("preinscripcion")) == 1

    def test_fichero_invalido_lanza_value_error(self):
        with pytest.raises(ValueError):
            hojas_esperadas("inexistente")


# ============================================================================
# 2. TESTS DE UTILIDADES INTERNAS DEL VALIDADOR
# ============================================================================

class TestUtilidadesValidador:
    """Verifica las funciones auxiliares internas."""

    def test_normalizar_minusculas(self):
        assert _normalizar("Per_id_Ficticio") == "per_id_ficticio"
        assert _normalizar("PER_ID_FICTICIO") == "per_id_ficticio"
        assert _normalizar("  Per_id_ficticio  ") == "per_id_ficticio"

    def test_existe_columna_case_insensitive_match(self):
        cols = ["Per_id_ficticio", "Curso_Aca", "Nombre"]
        # Match exacto
        assert _existe_columna_case_insensitive(cols, "Per_id_ficticio") == "Per_id_ficticio"
        # Match con mayúsculas distintas
        assert _existe_columna_case_insensitive(cols, "per_id_ficticio") == "Per_id_ficticio"
        assert _existe_columna_case_insensitive(cols, "PER_ID_FICTICIO") == "Per_id_ficticio"

    def test_existe_columna_case_insensitive_no_match(self):
        cols = ["Per_id_ficticio", "Curso_Aca"]
        assert _existe_columna_case_insensitive(cols, "Inexistente") is None

    def test_dtype_pandas_a_categoria(self):
        """
        Verifica el mapeo dtype → categoría.
        NOTA: La detección de strings depende de la versión de pandas.
        En pandas >= 2.x el dtype puede ser 'object', 'string' o 'str'.
        El validador detecta los 2 primeros; 'str' (raro) caería en MIXTO.
        Aquí solo testeamos los casos garantizados (int, float, datetime).
        """
        # Numéricos siempre detectados
        assert _dtype_pandas_a_categoria(pd.Series([1, 2, 3]).dtype) == TIPO_NUMERICO
        assert _dtype_pandas_a_categoria(pd.Series([1.5, 2.5]).dtype) == TIPO_NUMERICO

        # Datetime siempre detectado
        assert _dtype_pandas_a_categoria(
            pd.to_datetime(pd.Series(["2024-01-01"])).dtype
        ) == TIPO_FECHA

        # Object explícito → texto (caso clásico, dtype='O')
        s_obj = pd.Series(["a", "b"], dtype=object)
        assert _dtype_pandas_a_categoria(s_obj.dtype) == TIPO_TEXTO


# ============================================================================
# 3. TESTS DE LAS FUNCIONES DE VALIDACIÓN N1-N5
# ============================================================================
# Para no depender de los Excel reales, estos tests "monkeypatchean" las
# constantes EXCEL_PRINCIPAL y EXCEL_PREINSCRIPCION del módulo validador
# con Excel temporales sintéticos.

@pytest.fixture
def excel_minimo_valido(tmp_path):
    """
    Crea un par de Excel mínimos pero válidos (1 fila por hoja, columnas OK).
    Devuelve (ruta_principal, ruta_preinscripcion).
    """
    ruta_p = tmp_path / "principal_test.xlsx"
    ruta_pre = tmp_path / "preinscripcion_test.xlsx"

    # --- Excel principal: 8 hojas con 1 fila válida cada una ---
    with pd.ExcelWriter(ruta_p, engine="openpyxl") as writer:
        # Titulaciones (catálogo)
        pd.DataFrame({
            "Exp_Tit_Id": [100, 200, 300],
            "Titulacion": ["Grado A", "Grado B", "Grado C"],
            "Rama": ["SO", "TE", "SA"],
            "Cred_Titulacion": [240, 240, 240],
            "Tipo": [1, 1, 1],
            "Tipo_Estudio": ["G", "G", "G"],
        }).to_excel(writer, sheet_name="Titulaciones", index=False)

        # Recibos
        pd.DataFrame({
            "Per_id_ficticio": [1, 2, 3],
            "Curso_Aca": [2020, 2020, 2021],
            "Nombre_recibos": ["A", "B", "C"],
            "Forma_De_Pago": ["D", "N", "D"],
            "Numero_Pagos": [2, 1, 2],
        }).to_excel(writer, sheet_name="Recibos", index=False)

        # Domicilios
        pd.DataFrame({
            "Per_id_ficticio": [1, 2, 3],
            "Poblacion": ["Castelló", "Valencia", "Onda"],
            "Provincia": ["Castelló", "Valencia", "Castelló"],
            "Pais": ["España", "España", "España"],
            "Curso_Aca": [2020, 2020, 2021],
            "Tipo_Domicilio": ["F", "C", "F"],
        }).to_excel(writer, sheet_name="Domicilios", index=False)

        # Expedientes
        pd.DataFrame({
            "Per_id_ficticio": [1, 2, 3],
            "Exp_Tit_Id": [100, 200, 300],
            "Curso_Aca_Ini": [2020, 2020, 2021],
            "Curso_Aca": [2020, 2020, 2021],
            "Curso_Aca_Fin": ["-", "-", "-"],
            "Nota": ["-", "-", "-"],
            "Nombre": ["General", "General", "General"],
            "Seguro": ["N", "N", "N"],
            "Nota_selectividad": [6.5, 7.0, 8.0],
            "Nota_Acceso": ["6.5", "7.0", "8.0"],
            "Cred_Matriculados": [60.0, 60.0, 60.0],
            "Cred_Superados": [54.0, 60.0, 48.0],
            "Egresado": ["N", "N", "N"],
            "Nuevo": ["S", "S", "S"],
            "Media_Curso": [6.5, 7.0, 5.5],
        }).to_excel(writer, sheet_name="Expedientes", index=False)

        # Nac-Sexo_Nacionalidad
        pd.DataFrame({
            "Per_id_ficticio": [1, 2, 3],
            "Sexo": [1, 2, 1],
            "Fecha_nacimiento": pd.to_datetime(
                ["2000-01-01", "2001-06-15", "2000-12-31"]
            ),
            "Id_Pais": ["E", "E", "E"],
            "Pais_Nombre": ["España", "España", "España"],
        }).to_excel(writer, sheet_name="Nac-Sexo_Nacionalidad", index=False)

        # Circunstancias (¡F mayúscula intencional!)
        pd.DataFrame({
            "Per_id_Ficticio": [1, 2],   # F mayúscula
            "Id_beca": [1, 2],
            "Nombre_beca": ["Becario", "MEC"],
            "Mat_Curso_Aca": [2020, 2020],
        }).to_excel(writer, sheet_name="Circunstancias", index=False)

        # Trabajo
        pd.DataFrame({
            "Per_id_ficticio": [1, 2, 3],
            "Exp_Tit_Id": [100, 200, 300],
            "Nombre_trabajo": ["Inactivo", "Inactivo", "Activo"],
            "Mat_Curso_Aca": [2020, 2020, 2021],
        }).to_excel(writer, sheet_name="Trabajo", index=False)

        # Notas
        pd.DataFrame({
            "Per_id_ficticio": [1, 2, 3],
            "Curso_Aca": [2020, 2020, 2021],
            "Exp_Tit_Id": [100, 200, 300],
            "Media_Titulacion_Curso": [6.5, 7.0, 5.5],
            "Media_Titulacion_Alumno": [7.0, 7.5, 6.0],
        }).to_excel(writer, sheet_name="Notas", index=False)

    # --- Excel preinscripción ---
    with pd.ExcelWriter(ruta_pre, engine="openpyxl") as writer:
        pd.DataFrame({
            "ANO": [2020, 2020, 2020],
            "UNIVERSIDAD": ["UJI", "UJI", "UJI"],
            "MUNICIPIO": ["Castelló", "Valencia", "Onda"],
            "CP": [12001, 46001, 12200],
            "ORDEN_TITULACION": [1, 2, 1],
            "CUPO": [1, 1, 1],
            "NOM_CUPO": ["General", "General", "General"],
            "ESTADO": ["*", "*", "*"],
            "NOTA_TXT": [9.0, 8.5, 7.5],
            "SOLICITUD_ID": [100, 200, 300],
            "COD_ESTUDIOS": [10, 11, 12],
            "VIA_ESTUDIOS": ["PAU", "PAU", "PAU"],
            "CONVOCATORIA": [1, 1, 1],
            "NOTA_1": [9000, 8500, 7500],
            "NOTA_2": [None, None, None],
            "ANO_1": [2020, 2020, 2020],
            "CON_1": [1, 1, 1],
            "TITULACION_CENTRO": [221, 222, 223],
            "ESTADO_TITULACION": [3, 3, 3],
            "UNI_ID": [27, 27, 27],
            "NOMBRE_UNIVERSIDAD": ["UJI", "UJI", "UJI"],
            "ESTUDIO": ["A", "B", "C"],
            "Per_id_ficticio": [1, 2, 3],
            "MATRICULADO": ["Sí", "Sí", "Sí"],
        }).to_excel(writer, sheet_name="Hoja1", index=False)

    return ruta_p, ruta_pre


@pytest.fixture
def parchear_rutas(monkeypatch, excel_minimo_valido):
    """Sustituye las rutas de los Excel reales por las del fixture."""
    ruta_p, ruta_pre = excel_minimo_valido

    # Parchear en ambos módulos donde se usan
    import src.validacion.validador_excel as mod_v
    monkeypatch.setattr(mod_v, "EXCEL_PRINCIPAL", ruta_p)
    monkeypatch.setattr(mod_v, "EXCEL_PREINSCRIPCION", ruta_pre)

    yield ruta_p, ruta_pre


# ----------------------------------------------------------------------------
# Tests de N1 — existencia
# ----------------------------------------------------------------------------

class TestN1Existencia:
    """Tests para validar_n1_existencia()."""

    def test_n1_pasa_con_excel_validos(self, parchear_rutas):
        resultado = validar_n1_existencia()
        assert resultado["pasa"] is True
        assert resultado["nivel"] == "N1"
        assert resultado["tipo"] == "bloqueante"

    def test_n1_falla_si_no_existe(self, monkeypatch, tmp_path):
        """Si los ficheros no existen, N1 debe fallar."""
        import src.validacion.validador_excel as mod_v
        monkeypatch.setattr(mod_v, "EXCEL_PRINCIPAL", tmp_path / "no_existe.xlsx")
        monkeypatch.setattr(mod_v, "EXCEL_PREINSCRIPCION", tmp_path / "no_existe2.xlsx")

        resultado = validar_n1_existencia()
        assert resultado["pasa"] is False
        assert len(resultado["mensajes_error"]) >= 2


# ----------------------------------------------------------------------------
# Tests de N2 — hojas
# ----------------------------------------------------------------------------

class TestN2Hojas:
    """Tests para validar_n2_hojas()."""

    def test_n2_pasa_con_8_hojas_correctas(self, parchear_rutas):
        resultado = validar_n2_hojas()
        assert resultado["pasa"] is True
        assert resultado["nivel"] == "N2"

    def test_n2_falla_si_falta_hoja(self, tmp_path, monkeypatch):
        """Si falta una hoja esperada, N2 debe fallar."""
        ruta_p = tmp_path / "principal_falta_hoja.xlsx"
        ruta_pre = tmp_path / "preinscripcion_test.xlsx"

        # Solo 7 hojas (falta Notas)
        with pd.ExcelWriter(ruta_p, engine="openpyxl") as writer:
            for h in ["Titulaciones", "Recibos", "Domicilios", "Expedientes",
                      "Nac-Sexo_Nacionalidad", "Circunstancias", "Trabajo"]:
                pd.DataFrame({"a": [1]}).to_excel(writer, sheet_name=h, index=False)

        with pd.ExcelWriter(ruta_pre, engine="openpyxl") as writer:
            pd.DataFrame({"a": [1]}).to_excel(writer, sheet_name="Hoja1", index=False)

        import src.validacion.validador_excel as mod_v
        monkeypatch.setattr(mod_v, "EXCEL_PRINCIPAL", ruta_p)
        monkeypatch.setattr(mod_v, "EXCEL_PREINSCRIPCION", ruta_pre)

        resultado = validar_n2_hojas()
        assert resultado["pasa"] is False


# ----------------------------------------------------------------------------
# Tests de N3 — columnas
# ----------------------------------------------------------------------------

class TestN3Columnas:
    """Tests para validar_n3_columnas()."""

    def test_n3_pasa_con_columnas_completas(self, parchear_rutas):
        resultado = validar_n3_columnas()
        assert resultado["pasa"] is True

    def test_n3_acepta_F_mayuscula_circunstancias(self, parchear_rutas):
        """La F mayúscula intencional NO debe fallar (case-insensitive)."""
        resultado = validar_n3_columnas()
        # No debe haber errores relacionados con Per_id_Ficticio
        errores_circunstancias = [
            m for m in resultado["mensajes_error"]
            if "Circunstancias" in m and "Per_id" in m
        ]
        assert len(errores_circunstancias) == 0


# ----------------------------------------------------------------------------
# Tests de N4 — tipos
# ----------------------------------------------------------------------------

class TestN4Tipos:
    """Tests para validar_n4_tipos()."""

    def test_n4_es_warning_no_bloqueante(self, parchear_rutas):
        resultado = validar_n4_tipos()
        assert resultado["tipo"] == "warning"
        # 'pasa' es True siempre (los warnings no bloquean)
        assert resultado["pasa"] is True


# ----------------------------------------------------------------------------
# Tests de N5 — volumen y cruces
# ----------------------------------------------------------------------------

class TestN5VolumenYCruces:
    """Tests para validar_n5_volumen_y_cruces()."""

    def test_n5_es_warning(self, parchear_rutas):
        resultado = validar_n5_volumen_y_cruces()
        assert resultado["tipo"] == "warning"

    def test_n5_detecta_volumen_bajo(self, parchear_rutas):
        """Con solo 3 filas por hoja, N5 debe avisar (min_filas son ~50.000)."""
        resultado = validar_n5_volumen_y_cruces()
        # Debe haber al menos 1 aviso de volumen
        assert len(resultado["mensajes_error"]) > 0


# ============================================================================
# 4. TESTS DEL ORQUESTADOR
# ============================================================================

class TestOrquestador:
    """Tests para ejecutar_validacion_completa()."""

    def test_orquestador_devuelve_dict_correcto(self, parchear_rutas):
        resultado = ejecutar_validacion_completa(verbose=False)

        # Estructura esperada
        for clave in ("resultados", "bloqueante_fallido", "todos_ok",
                      "resumen_corto"):
            assert clave in resultado

        assert isinstance(resultado["resultados"], list)
        assert isinstance(resultado["bloqueante_fallido"], bool)
        assert isinstance(resultado["todos_ok"], bool)
        assert isinstance(resultado["resumen_corto"], str)

    def test_orquestador_ejecuta_5_niveles(self, parchear_rutas):
        resultado = ejecutar_validacion_completa(verbose=False)
        # Debe haber 5 resultados (N1-N5) o menos si hubo bloqueante temprano
        niveles = [r["nivel"] for r in resultado["resultados"]]
        assert "N1" in niveles
        assert "N2" in niveles
        assert "N3" in niveles


# ============================================================================
# 5. TESTS DEL GENERADOR HTML
# ============================================================================

class TestFormateoEspanol:
    """Tests para las utilidades de formato (estilo español)."""

    def test_bytes_a_mb(self):
        assert _bytes_a_mb(1_048_576) == "1,0 MB"  # 1 MB exacto
        assert _bytes_a_mb(29_197_213) == "27,8 MB"

    def test_numero_es(self):
        assert _numero_es(1_000) == "1.000"
        assert _numero_es(109_568) == "109.568"
        assert _numero_es(1_234_567) == "1.234.567"

    def test_formatear_mensaje_bytes(self):
        m = _formatear_mensaje_es("Fichero de 29,197,213 bytes")
        assert "27,8 MB" in m
        assert "29,197,213" not in m

    def test_formatear_mensaje_miles(self):
        m = _formatear_mensaje_es("114,454 filas (≥ 50,000)")
        assert "114.454" in m
        assert "50.000" in m

    def test_formatear_no_rompe_decimales(self):
        m = _formatear_mensaje_es("100.0% de match (≥99.0%)")
        # Decimales con punto deben permanecer intactos
        assert "100.0%" in m


class TestRenderizadoHTML:
    """Tests para el generador HTML completo."""

    def test_clase_estado_ok(self):
        r = {"pasa": True, "mensajes_error": []}
        assert _clase_estado(r) == "ok"

    def test_clase_estado_aviso(self):
        r = {"pasa": True, "mensajes_error": ["aviso x"]}
        assert _clase_estado(r) == "aviso"

    def test_clase_estado_error(self):
        r = {"pasa": False}
        assert _clase_estado(r) == "error"

    def test_clase_estado_no_ejecutado(self):
        r = {"pasa": None}
        assert _clase_estado(r) == "noejec"

    def test_genera_html_completo(self, parchear_rutas, tmp_path):
        """El HTML debe generarse y contener elementos esperados."""
        resultado = ejecutar_validacion_completa(verbose=False)
        ruta_html = tmp_path / "test_validacion.html"
        ruta_generada = generar_html_validacion(resultado, ruta_salida=ruta_html)

        assert ruta_generada.exists()
        contenido = ruta_generada.read_text(encoding="utf-8")

        # Comprobaciones básicas
        assert "<!DOCTYPE html>" in contenido
        assert "Validación de Excel" in contenido
        assert "OPP" in contenido
        assert "UADTI" in contenido
        # Cards de los 5 niveles
        assert "N1" in contenido and "N2" in contenido
        assert "N3" in contenido and "N4" in contenido and "N5" in contenido
