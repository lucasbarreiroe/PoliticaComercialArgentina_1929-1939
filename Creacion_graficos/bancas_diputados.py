"""
Módulo de Normalización y Bancas Históricas por Jurisdicción (1929-1939)
========================================================================
Provee las constantes institucionales del Congreso Nacional y funciones
para per-capitalizar métricas legislativas en la Cámara de Diputados.

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
import pandas as pd
from typing import Dict, Optional, Tuple

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


def cargar_datos_intervenciones(
    supabase_client,
    ruta_cache: Optional[str] = None,
    forzar_recarga: bool = False
) -> pd.DataFrame:
    """
    Descarga o lee de caché local el conjunto de intervenciones parlamentarias (1929-1939)
    con enriquecimiento de sesiones (fecha, cámara) y parlamentarios (rol, provincia, partido).
    """
    if ruta_cache is None:
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_cache = os.path.join(directorio_actual, "cache_intervenciones_enriquecidas.pkl.gz")

    if not forzar_recarga and os.path.exists(ruta_cache):
        try:
            print(f"[+] Cargando datos desde caché local: '{ruta_cache}'...")
            df = pd.read_pickle(ruta_cache, compression='gzip')
            print(f"    -> {len(df)} registros cargados al instante.")
            return df
        except Exception as e:
            print(f"[!] Error leyendo caché ({e}). Re-descargando desde Supabase...")

    print("[+] Descargando intervenciones con sesiones y parlamentarios desde Supabase...")
    todas_las_filas = []
    inicio = 0
    tamaño_lote = 1000

    while True:
        respuesta = supabase_client.table("intervenciones") \
            .select("id_intervencion, id_parlamentario, texto_gemini, texto_limpio, sesiones(fecha, camara), parlamentarios(partido_politico, distrito_provincia, rol)") \
            .range(inicio, inicio + tamaño_lote - 1) \
            .execute()

        filas = respuesta.data
        if not filas:
            break

        for f in filas:
            ses = f.get("sesiones") or {}
            par = f.get("parlamentarios") or {}

            f["fecha"] = ses.get("fecha")
            f["camara"] = ses.get("camara") or "Desconocida"

            f["partido"] = par.get("partido_politico") or "No Identificado"
            f["provincia_cruda"] = par.get("distrito_provincia") or "No Identificada"
            f["rol"] = par.get("rol") or "Desconocido"

            if "sesiones" in f:
                del f["sesiones"]
            if "parlamentarios" in f:
                del f["parlamentarios"]

        todas_las_filas.extend(filas)
        inicio += tamaño_lote
        print(f"  ... Descargados {len(todas_las_filas)} registros...")

    df = pd.DataFrame(todas_las_filas)

    # Lógica de texto final
    def _obtener_texto_final(r):
        tg = r.get('texto_gemini')
        tl = r.get('texto_limpio')
        tg = '' if pd.isna(tg) or tg is None else str(tg).strip()
        tl = '' if pd.isna(tl) or tl is None else str(tl).strip()
        if tg and tg != 'OMITIDO_POR_LARGO':
            return tg
        return tl

    df['texto_final'] = df.apply(_obtener_texto_final, axis=1)
    df = df[df['texto_final'] != '']
    df['num_palabras'] = df['texto_final'].apply(lambda x: len(str(x).split()))

    # Fechas y años (1929-1939)
    df['fecha_dt'] = pd.to_datetime(df['fecha'], errors='coerce')
    df['anio'] = df['fecha_dt'].dt.year
    df = df.dropna(subset=['anio'])
    df['anio'] = df['anio'].astype(int)
    df = df[(df['anio'] >= 1929) & (df['anio'] <= 1939)]

    # Homologación de provincias
    df['provincia'] = df['provincia_cruda'].apply(lambda p: normalizar_provincia(p, para_geojson=False))
    df['provincia_geojson'] = df['provincia_cruda'].apply(lambda p: normalizar_provincia(p, para_geojson=True))

    # Filtrar trámite
    df['partido_limpio'] = df.apply(
        lambda r: clasificar_intervencion_tramite(r['texto_final'], r['partido']), axis=1
    )

    # Guardar en caché comprimido
    try:
        os.makedirs(os.path.dirname(ruta_cache), exist_ok=True)
        df.to_pickle(ruta_cache, compression='gzip')
        print(f"[OK] Datos procesados y guardados en cache local: '{ruta_cache}'.")
    except Exception as e:
        print(f"[!] Aviso: No se pudo guardar cache ({e}).")

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
    
    # Filtrar por cámara y rol correspondiente
    if camara == 'Diputados':
        sub = df[(df['camara'] == 'Diputados') | (df['rol'] == 'Diputado')].copy()
        total_bancas_camara = TOTAL_BANCAS_DIPUTADOS
    elif camara == 'Senadores':
        sub = df[(df['camara'] == 'Senadores') | (df['rol'] == 'Senador')].copy()
        total_bancas_camara = TOTAL_BANCAS_SENADORES
    else:
        sub = df.copy()
        total_bancas_camara = TOTAL_BANCAS_DIPUTADOS + TOTAL_BANCAS_SENADORES

    # Excluir intervenciones procedimentales de secretaría/mesa y sin provincia
    sub = sub[~sub['partido_limpio'].isin(["Trámite", "No Identificado (Real)"])]
    sub = sub[sub[col_prov] != 'No Identificada']

    # Agrupación por año y provincia
    agrup = sub.groupby(['anio', col_prov]).agg(
        ints=('id_intervencion', 'count'),
        pals=('num_palabras', 'sum'),
        legisladores_activos=('id_parlamentario', 'nunique')
    ).reset_index()

    # Asignar bancas institucionales
    if camara == 'Diputados':
        agrup['bancas'] = agrup[col_prov].apply(obtener_bancas_diputados)
    elif camara == 'Senadores':
        agrup['bancas'] = BANCAS_SENADORES_POR_PROVINCIA
    else:
        agrup['bancas'] = agrup[col_prov].apply(lambda p: obtener_bancas_diputados(p) + 2)

    agrup['pct_bancas'] = (agrup['bancas'] / float(total_bancas_camara)) * 100.0

    # Métricas per cápita institucionales
    agrup['ints_per_capita'] = (agrup['ints'] / agrup['bancas']).round(2)
    agrup['pals_per_capita'] = (agrup['pals'] / agrup['bancas']).round(1)

    # Métricas per cápita por legislador activo efectivo
    agrup['ints_por_legislador_activo'] = (agrup['ints'] / agrup['legisladores_activos'].clip(lower=1)).round(2)
    agrup['pals_por_legislador_activo'] = (agrup['pals'] / agrup['legisladores_activos'].clip(lower=1)).round(1)

    # Totales anuales para sacar porcentajes
    totales_anio = agrup.groupby('anio').agg(
        tot_ints_anio=('ints', 'sum'),
        tot_pals_anio=('pals', 'sum'),
        tot_ints_pc_anio=('ints_per_capita', 'sum'),
        tot_pals_pc_anio=('pals_per_capita', 'sum')
    ).reset_index()

    agrup = pd.merge(agrup, totales_anio, on='anio')

    # Porcentajes de participación
    agrup['pct_ints_bruto'] = ((agrup['ints'] / agrup['tot_ints_anio']) * 100.0).round(2)
    agrup['pct_pals_bruto'] = ((agrup['pals'] / agrup['tot_pals_anio']) * 100.0).round(2)

    # Participación porcentual normalizada per cápita (nivelando las bancadas)
    agrup['pct_ints_per_capita'] = ((agrup['ints_per_capita'] / agrup['tot_ints_pc_anio'].clip(lower=1e-6)) * 100.0).round(2)
    agrup['pct_pals_per_capita'] = ((agrup['pals_per_capita'] / agrup['tot_pals_pc_anio'].clip(lower=1e-6)) * 100.0).round(2)

    # Ratios de Sobrerrepresentación Discursiva (% Voz Real / % Bancas)
    # > 1.0 = habla más de lo que le corresponde por su peso electoral
    # < 1.0 = habla menos de lo que le corresponde por su peso electoral
    agrup['ratio_intensidad_ints'] = (agrup['pct_ints_bruto'] / agrup['pct_bancas'].clip(lower=1e-6)).round(2)
    agrup['ratio_intensidad_pals'] = (agrup['pct_pals_bruto'] / agrup['pct_bancas'].clip(lower=1e-6)).round(2)

    agrup = agrup.rename(columns={col_prov: 'provincia'})
    return agrup
