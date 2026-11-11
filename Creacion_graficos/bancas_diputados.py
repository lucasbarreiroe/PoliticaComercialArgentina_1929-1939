"""
Módulo de Normalización, Carga 3NF y Bancas Históricas por Jurisdicción (1929-1939)
===================================================================================
Provee las constantes institucionales del Congreso Nacional, funciones de
normalización intrínseca de texto (insensible a mayúsculas, tildes, puntos,
barras o guiones) y carga enriquecida desde el esquema relacional puro en 3NF
de Supabase (sin depender de vistas generadas).

En la Cámara de Diputados de la Nación (1929-1939), la distribución de
bancas se regía por el censo electoral (total: 158 bancas):
- Buenos Aires: 42
- Capital Federal: 32
- Santa Fe: 19
- Córdoba: 15
- Entre Ríos: 9
- Corrientes: 7
- Tucumán: 7
- Mendoza: 6
- Santiago del Estero: 6
- Salta: 3
- San Juan: 3
- San Luis: 3
- Catamarca: 2
- La Rioja: 2
- Jujuy: 2

En el Senado de la Nación, cada provincia y la Capital Federal tenían exactamente
2 senadores (total: 30 senadores), por lo que la proporción territorial era fija.
"""

import os
import re
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
import pandas as pd

# Distribución histórica oficial de bancas en la Cámara de Diputados (1929-1939)
BANCAS_DIPUTADOS_HISTORICAS: Dict[str, int] = {
    'Buenos Aires': 42,
    'Capital Federal': 32,
    'Ciudad Autónoma de Buenos Aires': 32,
    'CABA': 32,
    'Santa Fe': 19,
    'Córdoba': 15,
    'Cordoba': 15,
    'Entre Ríos': 9,
    'Entre Rios': 9,
    'Corrientes': 7,
    'Tucumán': 7,
    'Tucuman': 7,
    'Mendoza': 6,
    'Santiago del Estero': 6,
    'Salta': 3,
    'San Juan': 3,
    'San Luis': 3,
    'Catamarca': 2,
    'La Rioja': 2,
    'Jujuy': 2
}

TOTAL_BANCAS_DIPUTADOS: int = 158
BANCAS_SENADORES_POR_PROVINCIA: int = 2
TOTAL_BANCAS_SENADORES: int = 30

# Mapeo canónico para compatibilidad con GeoJSON IGN y consistencia general
MAPEO_PROVINCIAS_CANONICO: Dict[str, str] = {
    'CABA': 'Ciudad Autónoma de Buenos Aires',
    'Cdad. Autónoma de Bs. As.': 'Ciudad Autónoma de Buenos Aires',
    'Capital Federal': 'Ciudad Autónoma de Buenos Aires',
    'RíoNegro': 'Río Negro',
    'Rio Negro': 'Río Negro',
    'Stgo. del Estero': 'Santiago del Estero',
    'Santiago Del Estero': 'Santiago del Estero',
    'T. del Fuego': 'Tierra del Fuego, Antártida e Islas del Atlántico Sur',
    'Tucuman': 'Tucumán',
    'Entre Rios': 'Entre Ríos',
    'Cordoba': 'Córdoba'
}

PATRONES_TRAMITE = [
    r"se va a votar", r"se votará", r"resulta afirmativa", r"resulta negativa",
    r"queda levantada la sesión", r"queda abierta la sesión", r"se lee el artículo",
    r"tiene la palabra", r"leyendo:", r"queda aprobado", r"a la comisión de",
    r"votan \d+ señores diputados", r"se va a dar cuenta", r"concederá la palabra",
    r"orden del día", r"cuarto intermedio", r"asentimiento", r"se va a leer",
    r"mándela a la papelera", r"prosecretario", r"secretario", r"comuníquese al poder ejecutivo",
    r"dios guarde a vuestra honorabilidad", r"goce de dieta, la licencia",
    r"no haciéndose observación", r"nada en discusión", r"el texto proporcionado está vacío"
]

# Expresiones precompiladas para normalización intrínseca de búsqueda y corpus
_RE_MILES_PUNTO = re.compile(r"(?<=\d)\.(?=\d{3}\b)")
_RE_SIGLAS_PUNTOS = re.compile(r"\b([a-z])\s*\.\s*([a-z])(?:\s*\.\s*([a-z]))?(?:\s*\.\s*([a-z]))?(?:\s*\.\s*([a-z]))?\.?")
_RE_LEY_PREFIJO = re.compile(r"\bley\s+(?:n[°ºo\.]*|nro\.?|num\.?|numero)\s*(?=\d)")
_RE_NO_ALFANUM = re.compile(r"[^a-z0-9\s]+")
_RE_ESPACIOS = re.compile(r"\s+")


def normalizar_texto_busqueda(texto: Optional[str]) -> str:
    """
    Normaliza intrínsecamente tanto las palabras buscadas como el texto de las intervenciones:
    1. Pasa a minúsculas.
    2. Elimina tildes y diacríticos Unicode (á->a, é->e, í->i, ó->o, ú->u, ü->u, ñ->n).
    3. Unifica números con punto de miles (ej. '11.693' -> '11693').
    4. Unifica siglas con puntos o barras (ej. 'U.C.R.' o 'U. C. R.' -> 'ucr', 'Y.P.F.' -> 'ypf').
    5. Homologa referencias a leyes ('ley n° 11.693', 'ley numero 11693' -> 'ley 11693').
    6. Reemplaza puntos, barras (/), guiones (-, –, —) y signos de puntuación por espacios simples.
    """
    if not texto or pd.isna(texto):
        return ""
    s = str(texto).lower().strip()
    if not s:
        return ""

    # Eliminar diacríticos Unicode (NFD)
    s = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

    # Colapsar puntos de miles en números (ej. 11.693 -> 11693)
    s = _RE_MILES_PUNTO.sub("", s)

    # Colapsar siglas separadas por puntos (ej. u.c.r. -> ucr, u.i.a. -> uia)
    def _unir_sigla(m):
        return "".join(g for g in m.groups() if g)

    s = _RE_SIGLAS_PUNTOS.sub(_unir_sigla, s)

    # Homologar prefijos de leyes ('ley n° 11693' / 'ley nro 11693' -> 'ley 11693')
    s = _RE_LEY_PREFIJO.sub("ley ", s)

    # Reemplazar puntos, barras, guiones y cualquier símbolo no alfanumérico por espacio
    s = _RE_NO_ALFANUM.sub(" ", s)
    return _RE_ESPACIOS.sub(" ", s).strip()


def construir_patron_termino_normalizado(termino_norm: str, permitir_plural: bool = True) -> re.Pattern:
    """
    Construye una expresión regular sobre texto ya normalizado por `normalizar_texto_busqueda`.
    Permite coincidencias exactas de palabra/frase e incluye plurales regulares ('s'/'es')
    para sustantivos y adjetivos de 4 o más letras.
    """
    tokens = [t for t in termino_norm.split() if t]
    if not tokens:
        return re.compile(r"^\b$")

    partes_regex = []
    for tok in tokens:
        esc = re.escape(tok)
        if permitir_plural and len(tok) >= 4 and tok.isalpha() and not tok.endswith("s"):
            partes_regex.append(rf"{esc}(?:s|es)?")
        else:
            partes_regex.append(esc)

    patron_str = r"\b" + r"\s+".join(partes_regex) + r"\b"
    return re.compile(patron_str)


def normalizar_provincia(nombre: Optional[str], para_geojson: bool = False) -> str:
    """Homologa nombres de provincias resolviendo variaciones ortográficas y CABA."""
    if not nombre or pd.isna(nombre):
        return "No Identificada"
    nom = str(nombre).strip()
    if nom in MAPEO_PROVINCIAS_CANONICO:
        nom = MAPEO_PROVINCIAS_CANONICO[nom]
    if not para_geojson and nom == 'Ciudad Autónoma de Buenos Aires':
        return 'Capital Federal'
    return nom


def obtener_bancas_diputados(provincia: str) -> int:
    """Devuelve las bancas históricas de diputados para una provincia (1929-1939)."""
    prov_limpia = str(provincia).strip()
    if prov_limpia in BANCAS_DIPUTADOS_HISTORICAS:
        return BANCAS_DIPUTADOS_HISTORICAS[prov_limpia]
    prov_norm = normalizar_provincia(prov_limpia, para_geojson=False)
    return BANCAS_DIPUTADOS_HISTORICAS.get(prov_norm, 1)


def clasificar_intervencion_tramite(texto: str, partido: str) -> str:
    """Clasifica si una intervención es meramente de trámite procedimental de mesa."""
    t_lower = str(texto).lower()
    if partido not in ["No Identificado", "NO IDENTIFICADO / FUNCIONARIO"]:
        return partido
    for p in PATRONES_TRAMITE:
        if re.search(p, t_lower):
            return "Trámite"
    return "No Identificado (Real)"


def _formatear_etiqueta_ley(ley_dict: dict, max_len: int = 85) -> str:
    """Genera una etiqueta legible y estandarizada para una ley del catálogo 3NF."""
    num = str(ley_dict.get("numero_ley") or "").strip()
    anio = ley_dict.get("anio_sancion")
    denom = str(ley_dict.get("denominacion") or "").strip()
    # Limpiar prefijos redundantes en denominación
    denom_limpia = re.sub(r"^Ley\s+Nacional\s+N[°º]\s*[\d\.]+\s*(?:\([^\)]+\))?\s*[:\-—]*\s*", "", denom, flags=re.I).strip()
    if not denom_limpia or denom_limpia.lower().startswith("sancion"):
        return f"Ley N° {num}" + (f" ({anio})" if anio else "")
    if len(denom_limpia) > max_len:
        denom_limpia = denom_limpia[:max_len - 1].rstrip() + "…"
    return f"Ley N° {num}" + (f" ({anio})" if anio else "") + f" — {denom_limpia}"


def cargar_padron_parlamentarios_3nf(supabase_client) -> pd.DataFrame:
    """
    Reconstruye el padrón de legisladores directamente desde las tablas 3NF:
    personas + mandatos_legislativos + partidos_politicos + provincias.
    """
    personas = {
        p["id_persona"]: p
        for p in (supabase_client.table("personas").select("*").execute().data or [])
    }
    partidos = {
        pt["id_partido"]: pt
        for pt in (supabase_client.table("partidos_politicos").select("*").execute().data or [])
    }
    provincias = {
        pr["id_provincia"]: pr
        for pr in (supabase_client.table("provincias").select("*").execute().data or [])
    }
    mandatos = supabase_client.table("mandatos_legislativos").select("*").execute().data or []

    filas = []
    for m in mandatos:
        per = personas.get(m.get("id_persona"), {})
        pt = partidos.get(m.get("id_partido"), {})
        pr = provincias.get(m.get("id_provincia"), {})
        cargo_raw = str(m.get("cargo_especifico") or m.get("camara") or "Desconocido")
        rol_norm = "Diputado" if "Diputad" in cargo_raw else ("Senador" if "Senad" in cargo_raw else cargo_raw)
        filas.append({
            "id_parlamentario": m["id_mandato"],
            "id_persona": m.get("id_persona"),
            "nombre_apellido": per.get("nombre_completo") or "No Identificado",
            "rol": rol_norm,
            "partido_politico": pt.get("nombre_oficial") or "No Identificado",
            "coalicion_general": pt.get("coalicion_general") or "Sin Especificar",
            "distrito_provincia": pr.get("nombre") or "No Identificada",
            "anio_inicio": m.get("anio_inicio"),
            "anio_fin": m.get("anio_fin")
        })
    return pd.DataFrame(filas)


def _descargar_tabla_paginada(supabase_client, nombre_tabla: str, columnas: str, col_orden: str) -> list:
    """Descarga todos los registros de una tabla mediana en lotes de 1.000."""
    acumulado = []
    offset = 0
    while True:
        lote = (
            supabase_client.table(nombre_tabla)
            .select(columnas)
            .order(col_orden)
            .range(offset, offset + 999)
            .execute()
            .data
            or []
        )
        if not lote:
            break
        acumulado.extend(lote)
        if len(lote) < 1000:
            break
        offset += 1000
    return acumulado


def cargar_datos_intervenciones(
    supabase_client,
    ruta_cache: Optional[str] = None,
    forzar_recarga: bool = False
) -> pd.DataFrame:
    """
    Descarga o lee de caché local el conjunto completo de intervenciones parlamentarias (1929-1939)
    cruzando directamente las tablas base en 3NF de Supabase (sin vistas SQL):
    - intervenciones (incluyendo nro_pagina, id_sumario, texto_canonico)
    - sesiones (fecha_exacta, numero_reunion, tipo_sesion)
    - tomos_diarios_sesiones (codigo_tomo, archivo_pdf_origen, camara, anio_legislativo)
    - mandatos_legislativos + personas + partidos_politicos + provincias
    - leyes + intervenciones_leyes_mencionadas + iniciativas_legislativas (ley tratada en recinto/intervención)
    - catalogo_entidades + intervencion_entidades (NER 3NF)
    """
    if ruta_cache is None:
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_cache = os.path.join(directorio_actual, "cache_intervenciones_enriquecidas.pkl.gz")

    columnas_requeridas = {
        "id_intervencion", "fecha_sesion", "anio", "archivo_sesion", "nro_pagina",
        "sesion_label", "ley_tratada", "leyes_filtro", "texto_normalizado"
    }

    if not forzar_recarga and os.path.exists(ruta_cache):
        try:
            print(f"[+] Cargando datos desde caché local: '{ruta_cache}'...")
            df = pd.read_pickle(ruta_cache, compression='gzip')
            if columnas_requeridas.issubset(set(df.columns)):
                print(f"    -> {len(df)} registros enriquecidos cargados al instante.")
                return df
            print("[!] Actualizando caché local con las columnas de leyes, páginas y archivos...")
        except Exception as e:
            print(f"[!] Error leyendo caché ({e}). Re-descargando desde Supabase...")

    print("[+] Descargando las 13 tablas del corpus parlamentario desde Supabase...")

    # 1. Catálogos de Tomos, Sesiones, Personas, Partidos, Provincias, Mandatos
    tomos_map = {
        t["id_tomo"]: t
        for t in (supabase_client.table("tomos_diarios_sesiones").select("*").execute().data or [])
    }

    sesiones_lista = _descargar_tabla_paginada(
        supabase_client, "sesiones",
        "id_sesion, id_tomo, fecha_exacta, numero_reunion, tipo_sesion, observaciones",
        "id_sesion"
    )
    sesiones_map = {s["id_sesion"]: s for s in sesiones_lista}

    personas_map = {
        p["id_persona"]: p
        for p in (supabase_client.table("personas").select("id_persona, nombre_completo").execute().data or [])
    }
    partidos_map = {
        pt["id_partido"]: pt
        for pt in (supabase_client.table("partidos_politicos").select("id_partido, nombre_oficial, coalicion_general").execute().data or [])
    }
    provincias_map = {
        pr["id_provincia"]: pr
        for pr in (supabase_client.table("provincias").select("id_provincia, nombre").execute().data or [])
    }
    mandatos_map = {
        m["id_mandato"]: m
        for m in (
            supabase_client.table("mandatos_legislativos")
            .select("id_mandato, id_persona, camara, cargo_especifico, id_provincia, id_partido")
            .execute()
            .data
            or []
        )
    }

    # 2. Catálogo de Leyes, Menciones Directas e Iniciativas por Sesión
    leyes_lista = _descargar_tabla_paginada(
        supabase_client, "leyes",
        "id_ley, numero_ley, anio_sancion, denominacion",
        "id_ley"
    )
    leyes_label_map = {l["id_ley"]: _formatear_etiqueta_ley(l) for l in leyes_lista}

    ilm_lista = _descargar_tabla_paginada(
        supabase_client, "intervenciones_leyes_mencionadas",
        "id_intervencion, id_ley",
        "id_intervencion"
    )
    interv_a_leyes: Dict[int, List[str]] = defaultdict(list)
    for row in ilm_lista:
        lbl = leyes_label_map.get(row["id_ley"])
        if lbl and lbl not in interv_a_leyes[row["id_intervencion"]]:
            interv_a_leyes[row["id_intervencion"]].append(lbl)

    iniciativas_lista = _descargar_tabla_paginada(
        supabase_client, "iniciativas_legislativas",
        "id_iniciativa, id_sesion, id_ley_sancionada, tipo_iniciativa, instancia_legislativa, titulo_iniciativa",
        "id_iniciativa"
    )
    sesion_iniciativas_ley = defaultdict(list)
    for ini in iniciativas_lista:
        id_ses = ini.get("id_sesion")
        id_ley = ini.get("id_ley_sancionada")
        if id_ses and id_ley and id_ley in leyes_label_map:
            sesion_iniciativas_ley[id_ses].append(leyes_label_map[id_ley])

    # Filtrar sesiones que son catálogos de fin de tomo (>10 leyes sancionadas juntas)
    sesion_leyes_recinto: Dict[int, List[str]] = {}
    for id_ses, lista_l in sesion_iniciativas_ley.items():
        unicas = list(dict.fromkeys(lista_l))
        if 1 <= len(unicas) <= 8:
            sesion_leyes_recinto[id_ses] = unicas

    # 3. Descarga paralela de las 64.636 intervenciones por rangos de clave primaria
    r_max = (
        supabase_client.table("intervenciones")
        .select("id_intervencion")
        .order("id_intervencion", desc=True)
        .limit(1)
        .execute()
        .data
    )
    max_id = int(r_max[0]["id_intervencion"]) if r_max else 65000
    rangos = [(inicio, min(inicio + 999, max_id)) for inicio in range(1, max_id + 1, 1000)]

    def _descargar_rango_intervenciones(rango_ids: Tuple[int, int]) -> list:
        ini_id, fin_id = rango_ids
        for intento in range(3):
            try:
                resp = (
                    supabase_client.table("intervenciones")
                    .select("id_intervencion, id_sesion, id_persona, id_mandato, id_sumario, nro_pagina, texto_canonico")
                    .gte("id_intervencion", ini_id)
                    .lte("id_intervencion", fin_id)
                    .order("id_intervencion")
                    .limit(1000)
                    .execute()
                )
                return resp.data or []
            except Exception:
                if intento == 2:
                    raise
        return []

    filas_crudas = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futuros = {executor.submit(_descargar_rango_intervenciones, r): r for r in rangos}
        completados = 0
        for fut in as_completed(futuros):
            filas_crudas.extend(fut.result())
            completados += 1
            if completados % 15 == 0 or completados == len(rangos):
                print(f"  ... Descargados {len(filas_crudas):,d} / {max_id:,d} discursos desde Supabase 3NF...")

    filas_crudas.sort(key=lambda x: x["id_intervencion"])

    # Calcular leyes dominantes por sesión a partir de las menciones directas de sus intervenciones
    conteo_leyes_por_sesion: Dict[int, Counter] = defaultdict(Counter)
    for f in filas_crudas:
        id_int = f["id_intervencion"]
        id_ses = f.get("id_sesion")
        if id_ses and id_int in interv_a_leyes:
            for l_lbl in interv_a_leyes[id_int]:
                conteo_leyes_por_sesion[id_ses][l_lbl] += 1

    todas_las_filas = []
    for f in filas_crudas:
        id_int = f["id_intervencion"]
        id_ses = f.get("id_sesion")
        ses = sesiones_map.get(id_ses, {})
        tomo = tomos_map.get(ses.get("id_tomo"), {})
        mand = mandatos_map.get(f.get("id_mandato"), {})
        per = personas_map.get(f.get("id_persona") or mand.get("id_persona"), {})
        pt = partidos_map.get(mand.get("id_partido"), {})
        pr = provincias_map.get(mand.get("id_provincia"), {})

        anio_leg = tomo.get("anio_legislativo")
        fecha_ex = ses.get("fecha_exacta") or (f"{anio_leg}-01-01" if anio_leg else "1930-01-01")
        camara_str = tomo.get("camara") or mand.get("camara") or "Desconocida"
        codigo_tomo = tomo.get("codigo_tomo") or "S/D"
        archivo_pdf = tomo.get("archivo_pdf_origen") or (f"{codigo_tomo}.pdf" if codigo_tomo != "S/D" else "Sin archivo")
        nro_reunion = ses.get("numero_reunion")
        tipo_ses = ses.get("tipo_sesion") or "Ordinaria"
        sesion_lbl = f"Reunión {nro_reunion} ({tipo_ses})" if nro_reunion is not None else f"Sesión #{id_ses} ({tipo_ses})"

        rol_raw = str(mand.get("cargo_especifico") or "Desconocido")
        rol_norm = "Diputado" if "Diputad" in rol_raw else ("Senador" if "Senad" in rol_raw else rol_raw)
        texto_can = str(f.get("texto_canonico") or "").strip()
        if not texto_can or texto_can == "OMITIDO_POR_LARGO":
            continue

        # Determinación de la ley tratada (directa en la intervención o tratada en la sesión)
        leyes_dir = interv_a_leyes.get(id_int, [])
        if leyes_dir:
            ley_tratada_str = " | ".join(leyes_dir[:2])
            leyes_filtro_list = list(leyes_dir)
        else:
            leyes_ses = sesion_leyes_recinto.get(id_ses, [])
            if not leyes_ses and id_ses in conteo_leyes_por_sesion:
                leyes_ses = [k for k, _ in conteo_leyes_por_sesion[id_ses].most_common(2)]
            if leyes_ses:
                ley_tratada_str = f"{leyes_ses[0]} (en sesión)"
                leyes_filtro_list = [leyes_ses[0]]
            else:
                ley_tratada_str = "Debate general / Sin ley específica"
                leyes_filtro_list = ["Debate general / Sin ley específica"]

        todas_las_filas.append({
            "id_intervencion": id_int,
            "id_sesion": id_ses,
            "numero_reunion": nro_reunion,
            "tipo_sesion": tipo_ses,
            "sesion_label": sesion_lbl,
            "id_tomo": ses.get("id_tomo"),
            "codigo_tomo": codigo_tomo,
            "archivo_sesion": archivo_pdf,
            "nro_pagina": int(f.get("nro_pagina") or 1),
            "id_persona": f.get("id_persona"),
            "id_mandato": f.get("id_mandato"),
            "id_parlamentario": f.get("id_mandato") or f.get("id_persona"),
            "nombre_parl": per.get("nombre_completo") or "No Identificado",
            "fecha": fecha_ex,
            "fecha_sesion": fecha_ex,
            "camara": camara_str,
            "partido": pt.get("nombre_oficial") or "No Identificado",
            "coalicion": pt.get("coalicion_general") or "Sin Especificar",
            "provincia_cruda": pr.get("nombre") or "No Identificada",
            "rol": rol_norm,
            "ley_tratada": ley_tratada_str,
            "leyes_filtro": leyes_filtro_list,
            "texto_canonico": texto_can,
            "texto_gemini": texto_can,
            "texto_limpio": texto_can,
            "texto_final": texto_can,
        })

    df = pd.DataFrame(todas_las_filas)
    print("[+] Normalizando intrínsecamente los textos de las intervenciones...")
    df["texto_normalizado"] = df["texto_final"].apply(normalizar_texto_busqueda)
    df["num_palabras"] = df["texto_final"].apply(lambda x: len(str(x).split()))

    # Fechas y años (1929-1939)
    df["fecha_dt"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["anio"] = df["fecha_dt"].dt.year
    df = df.dropna(subset=["anio"])
    df["anio"] = df["anio"].astype(int)
    df = df[(df["anio"] >= 1929) & (df["anio"] <= 1939)]

    # Homologación de provincias
    df["provincia"] = df["provincia_cruda"].apply(lambda p: normalizar_provincia(p, para_geojson=False))
    df["provincia_geojson"] = df["provincia_cruda"].apply(lambda p: normalizar_provincia(p, para_geojson=True))

    # Filtrar trámite
    df["partido_limpio"] = df.apply(
        lambda r: clasificar_intervencion_tramite(r["texto_final"], r["partido"]), axis=1
    )

    try:
        os.makedirs(os.path.dirname(ruta_cache), exist_ok=True)
        df.to_pickle(ruta_cache, compression="gzip")
        print(f"[OK] Datos enriquecidos 3NF guardados en caché local: '{ruta_cache}'.")
    except Exception as e:
        print(f"[!] Aviso: No se pudo guardar caché ({e}).")

    return df


def calcular_metricas_provinciales_por_anio(
    df: pd.DataFrame,
    camara: str = 'Diputados',
    usar_nombres_geojson: bool = False
) -> pd.DataFrame:
    """
    Calcula para cada año y provincia:
    - Métricas brutas: intervenciones, palabras
    - Bancas institucionales (158 para Diputados, 2 c/u para Senado)
    - Métricas normalizadas per cápita: intervenciones por diputado, palabras por diputado
    - Participación porcentual bruta vs normalizada per cápita
    - Ratio de intensidad / sobrerrepresentación discursiva (% Voz Real / % Bancas)
    - Diputados activos que participaron efectivamente ese año
    """
    col_prov = 'provincia_geojson' if usar_nombres_geojson else 'provincia'

    if camara == 'Diputados':
        sub = df[(df['camara'] == 'Diputados') | (df['rol'] == 'Diputado')].copy()
        total_bancas_camara = TOTAL_BANCAS_DIPUTADOS
    elif camara == 'Senadores':
        sub = df[(df['camara'] == 'Senadores') | (df['rol'] == 'Senador')].copy()
        total_bancas_camara = TOTAL_BANCAS_SENADORES
    else:
        sub = df.copy()
        total_bancas_camara = TOTAL_BANCAS_DIPUTADOS + TOTAL_BANCAS_SENADORES

    sub = sub[~sub['partido_limpio'].isin(["Trámite", "No Identificado (Real)"])]
    sub = sub[sub[col_prov] != 'No Identificada']

    agrup = sub.groupby(['anio', col_prov]).agg(
        ints=('id_intervencion', 'count'),
        pals=('num_palabras', 'sum'),
        legisladores_activos=('id_parlamentario', 'nunique')
    ).reset_index()

    if camara == 'Diputados':
        agrup['bancas'] = agrup[col_prov].apply(obtener_bancas_diputados)
    elif camara == 'Senadores':
        agrup['bancas'] = BANCAS_SENADORES_POR_PROVINCIA
    else:
        agrup['bancas'] = agrup[col_prov].apply(lambda p: obtener_bancas_diputados(p) + 2)

    agrup['pct_bancas'] = (agrup['bancas'] / float(total_bancas_camara)) * 100.0

    agrup['ints_per_capita'] = (agrup['ints'] / agrup['bancas']).round(2)
    agrup['pals_per_capita'] = (agrup['pals'] / agrup['bancas']).round(1)

    agrup['ints_por_legislador_activo'] = (agrup['ints'] / agrup['legisladores_activos'].clip(lower=1)).round(2)
    agrup['pals_por_legislador_activo'] = (agrup['pals'] / agrup['legisladores_activos'].clip(lower=1)).round(1)

    totales_anio = agrup.groupby('anio').agg(
        tot_ints_anio=('ints', 'sum'),
        tot_pals_anio=('pals', 'sum'),
        tot_ints_pc_anio=('ints_per_capita', 'sum'),
        tot_pals_pc_anio=('pals_per_capita', 'sum')
    ).reset_index()

    agrup = pd.merge(agrup, totales_anio, on='anio')

    agrup['pct_ints_bruto'] = ((agrup['ints'] / agrup['tot_ints_anio']) * 100.0).round(2)
    agrup['pct_pals_bruto'] = ((agrup['pals'] / agrup['tot_pals_anio']) * 100.0).round(2)

    agrup['pct_ints_per_capita'] = ((agrup['ints_per_capita'] / agrup['tot_ints_pc_anio'].clip(lower=1e-6)) * 100.0).round(2)
    agrup['pct_pals_per_capita'] = ((agrup['pals_per_capita'] / agrup['tot_pals_pc_anio'].clip(lower=1e-6)) * 100.0).round(2)

    agrup['ratio_intensidad_ints'] = (agrup['pct_ints_bruto'] / agrup['pct_bancas'].clip(lower=1e-6)).round(2)
    agrup['ratio_intensidad_pals'] = (agrup['pct_pals_bruto'] / agrup['pct_bancas'].clip(lower=1e-6)).round(2)

    agrup = agrup.rename(columns={col_prov: 'provincia'})
    return agrup
