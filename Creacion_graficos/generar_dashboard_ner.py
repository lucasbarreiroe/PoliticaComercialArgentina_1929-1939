#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Este script genera el dashboard interactivo de análisis temático y NER (1929-1939).

A partir de una lista de términos o entidades clave (por ejemplo: Roca-Runciman,
frigoríficos, control de cambios, Banco Central, cuota de carnes):
1. Normaliza las palabras y busca todas las coincidencias en los discursos legislativos.
2. Cruza cada mención con el año, fecha exacta, tomo PDF, página, partido y provincia del orador.
3. Genera un dashboard interactivo en HTML con gráficos sincronizados (evolución anual,
   participación por partido, mapa por provincia) y una tabla documental completa con
   filtros dinámicos en vivo.
"""

import os
import sys
import re
import json
import argparse
from collections import Counter
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Directorios del proyecto
DIR_ACTUAL = os.path.dirname(os.path.abspath(__file__))
DIR_GRAFICOS = os.path.join(DIR_ACTUAL, "graficos")
os.makedirs(DIR_GRAFICOS, exist_ok=True)

RUTA_PADRE = os.path.abspath(os.path.join(DIR_ACTUAL, ".."))
if RUTA_PADRE not in sys.path:
    sys.path.insert(0, RUTA_PADRE)
RUTA_DB = os.path.abspath(os.path.join(RUTA_PADRE, "base_de_datos"))
if RUTA_DB not in sys.path:
    sys.path.insert(0, RUTA_DB)
if DIR_ACTUAL not in sys.path:
    sys.path.insert(0, DIR_ACTUAL)

from bancas_diputados import (
    BANCAS_DIPUTADOS_HISTORICAS,
    TOTAL_BANCAS_DIPUTADOS,
    BANCAS_SENADORES_POR_PROVINCIA,
    cargar_datos_intervenciones,
    normalizar_provincia,
    normalizar_texto_busqueda,
    construir_patron_termino_normalizado,
)


# Lista de palabras por defecto para ejemplificar la reproducibilidad del módulo
PALABRAS_DEFAULT_COMERCIO_EXTERIOR: List[str] = [
    "Roca-Runciman",
    "Convenio de Londres",
    "Ley 11.693",
    "Misión Roca",
    "Chilled beef",
    "Frigorífico",
    "Junta Nacional de Carnes",
    "Ley 11.747",
    "Control de cambios",
    "Conferencia de Ottawa",
    "Coordinación de transportes",
    "Comprar a quien nos compra",
    "Banco Central",
]

# Catálogo en memoria de entidades NER del proyecto (módulo independiente de la base de datos)
CATALOGO_ENTIDADES_MEMORIA: List[Tuple[str, str, List[str]]] = [
    # Instituciones económicas oficiales y privadas
    ("Banco Central (BCRA)", "Instituciones económicas", ["banco central", "bcra"]),
    ("Junta Nacional de Carnes", "Instituciones económicas", ["junta nacional de carnes", "junta de carnes"]),
    ("Junta Reguladora de Granos", "Instituciones económicas", ["junta reguladora de granos", "junta de granos"]),
    ("Junta Reguladora de Vinos", "Instituciones económicas", ["junta reguladora de vinos", "junta de vinos"]),
    ("Junta Nacional del Algodón", "Instituciones económicas", ["junta nacional del algodon", "junta del algodon"]),
    ("Comisión de Control de Cambios", "Instituciones económicas", ["control de cambios", "comision de control de cambios"]),
    ("Caja de Conversión", "Instituciones económicas", ["caja de conversion"]),
    ("Banco de la Nación Argentina", "Instituciones económicas", ["banco de la nacion"]),
    ("Corporación Argentina de Productores (CAP)", "Instituciones económicas", ["corporacion argentina de productores", "corporacion de productores de carnes"]),
    ("Sociedad Rural Argentina (SRA)", "Instituciones económicas", ["sociedad rural", "sra"]),
    ("Unión Industrial Argentina (UIA)", "Instituciones económicas", ["union industrial", "uia"]),
    ("Federación Agraria Argentina", "Instituciones económicas", ["federacion agraria"]),
    ("Bolsa de Comercio", "Instituciones económicas", ["bolsa de comercio"]),
    ("Bolsa de Cereales", "Instituciones económicas", ["bolsa de cereales"]),
    ("Cámara Argentina de Comercio", "Instituciones económicas", ["camara argentina de comercio", "camara de comercio"]),
    ("CARBAP", "Instituciones económicas", ["carbap", "confederacion de asociaciones rurales"]),
    ("YPF", "Instituciones económicas", ["yacimientos petroliferos fiscales", "ypf"]),
    ("Frigoríficos Extranjeros (Swift / Anglo / Armour)", "Instituciones económicas", ["swift", "armour", "frigorifico anglo", "smithfield", "wilson"]),
    # Unidades políticas extranjeras
    ("Gran Bretaña / Reino Unido", "Unidades políticas extranjeras", ["gran bretana", "reino unido", "inglaterra", "imperio britanico"]),
    ("Estados Unidos", "Unidades políticas extranjeras", ["estados unidos", "norteamerica"]),
    ("Alemania", "Unidades políticas extranjeras", ["alemania"]),
    ("Italia", "Unidades políticas extranjeras", ["italia"]),
    ("Brasil", "Unidades políticas extranjeras", ["brasil"]),
    ("Sociedad de las Naciones", "Unidades políticas extranjeras", ["sociedad de las naciones", "liga de las naciones", "liga de naciones"]),
    # Fenómenos, tratados y procesos
    ("Pacto Roca-Runciman / Convenio de Londres", "Tratados y fenómenos económicos", ["roca runciman", "convenio de londres", "tratado de londres", "ley 11693", "mision roca"]),
    ("Conferencia de Ottawa", "Tratados y fenómenos económicos", ["ottawa", "preferencia imperial"]),
    ("Gran Depresión / Crisis Mundial", "Tratados y fenómenos económicos", ["gran depresion", "crisis mundial", "wall street"]),
]

_PATRONES_ENTIDADES_MEMORIA = [
    (
        nom_can,
        cat_can,
        re.compile(
            r"\b(?:" + "|".join(re.escape(normalizar_texto_busqueda(v)) for v in variantes) + r")\b"
        ),
    )
    for nom_can, cat_can, variantes in CATALOGO_ENTIDADES_MEMORIA
]


def normalizar_lista_palabras(lista_palabras: List[str]) -> List[Dict[str, str]]:
    """
    Recibe una lista arbitraria de palabras o frases y devuelve una lista depurada
    y deduplicada de diccionarios con:
    - 'etiqueta': representación limpia para visualización en el dashboard
    - 'normalizado': forma canónica normalizada (sin mayúsculas, tildes, puntos, barras ni guiones)
    - 'patron': expresión regular compilada sobre el texto normalizado
    """
    resultado = []
    vistos = set()

    for item in lista_palabras:
        if not item or not str(item).strip():
            continue
        etiqueta = re.sub(r"\s+", " ", str(item).strip())
        norm = normalizar_texto_busqueda(etiqueta)
        if not norm or norm in vistos:
            continue
        vistos.add(norm)
        resultado.append({
            "etiqueta": etiqueta,
            "normalizado": norm,
            "patron": construir_patron_termino_normalizado(norm, permitir_plural=True),
        })

    return resultado


def _extraer_ventana_contexto(
    texto_original: str,
    terminos_etiquetas: List[str],
    max_chars: int = 850
) -> str:
    """
    Extrae un fragmento legible del texto original centrado en la primera aparición
    de cualquiera de los términos buscados (insensible a mayúsculas, tildes, puntos o barras).
    Si el discurso es breve (<= max_chars), devuelve el texto completo.
    """
    texto_limpio = re.sub(r"\s+", " ", str(texto_original or "").strip())
    if len(texto_limpio) <= max_chars:
        return texto_limpio

    # Buscar posición aproximada del primer término coincidente
    pos_match = -1
    for etq in terminos_etiquetas:
        tokens = [t for t in normalizar_texto_busqueda(etq).split() if len(t) >= 3]
        if not tokens:
            continue
        # Construir patrón tolerante a acentos y signos entre palabras
        tok_pat = []
        for tk in tokens:
            chars_flex = []
            for ch in tk:
                if ch == "a":
                    chars_flex.append("[aáàä]")
                elif ch == "e":
                    chars_flex.append("[eéèë]")
                elif ch == "i":
                    chars_flex.append("[iíìï]")
                elif ch == "o":
                    chars_flex.append("[oóòö]")
                elif ch == "u":
                    chars_flex.append("[uúùü]")
                elif ch == "n":
                    chars_flex.append("[nñ]")
                else:
                    chars_flex.append(re.escape(ch))
            tok_pat.append("".join(chars_flex))
        rx = re.compile(r"[\s\.\-\–\—\/]+".join(tok_pat), re.I)
        m = rx.search(texto_limpio)
        if m:
            pos_match = m.start()
            break

    if pos_match == -1:
        return texto_limpio[:max_chars].rsplit(" ", 1)[0] + "…"

    mitad = max_chars // 2
    inicio = max(0, pos_match - mitad)
    fin = min(len(texto_limpio), inicio + max_chars)
    if fin == len(texto_limpio):
        inicio = max(0, fin - max_chars)

    fragmento = texto_limpio[inicio:fin]
    if inicio > 0:
        fragmento = "…" + fragmento.split(" ", 1)[-1]
    if fin < len(texto_limpio):
        fragmento = fragmento.rsplit(" ", 1)[0] + "…"
    return fragmento


def procesar_intervenciones_por_palabras(
    df: pd.DataFrame,
    lista_palabras: List[str],
    max_caracteres_extracto: int = 850
) -> Dict:
    """
    Filtra y analiza el DataFrame enriquecido de intervenciones a partir de `lista_palabras`.
    Normaliza intrínsecamente tanto la consulta como las intervenciones y devuelve la estructura
    estandarizada lista para renderizar el dashboard HTML interactivo.
    """
    terminos_info = normalizar_lista_palabras(lista_palabras)
    if not terminos_info:
        raise ValueError("La lista de palabras recibida está vacía o no contiene términos válidos.")

    if "texto_normalizado" not in df.columns:
        df = df.copy()
        df["texto_normalizado"] = df["texto_final"].apply(normalizar_texto_busqueda)

    print(f"[+] Buscando {len(terminos_info)} términos normalizados sobre {len(df):,d} intervenciones...")

    registros_dashboard = []
    frecuencia_terminos_global = Counter()
    menciones_terminos_global = Counter()

    # Iteración vectorizada/optimizada sobre las columnas necesarias
    for row in df.itertuples(index=False):
        txt_norm = getattr(row, "texto_normalizado", "") or ""
        if not txt_norm:
            continue

        terminos_hallados = []
        menciones_en_discurso = {}

        for t_item in terminos_info:
            pat = t_item["patron"]
            coincidencias = pat.findall(txt_norm)
            if coincidencias:
                etq = t_item["etiqueta"]
                cant_menc = len(coincidencias)
                terminos_hallados.append(etq)
                menciones_en_discurso[etq] = cant_menc
                frecuencia_terminos_global[etq] += 1
                menciones_terminos_global[etq] += cant_menc

        if not terminos_hallados:
            continue

        txt_orig = getattr(row, "texto_final", "") or ""
        extracto = _extraer_ventana_contexto(txt_orig, terminos_hallados, max_chars=max_caracteres_extracto)

        entidades_limpias = []
        for nom_e, cat_e, rx_e in _PATRONES_ENTIDADES_MEMORIA:
            hits_e = rx_e.findall(txt_norm)
            if hits_e:
                entidades_limpias.append({"e": nom_e, "c": cat_e, "f": len(hits_e)})

        leyes_lista = getattr(row, "leyes_filtro", None) or [getattr(row, "ley_tratada", "Debate general / Sin ley específica")]

        registros_dashboard.append({
            "id": int(getattr(row, "id_intervencion")),
            "anio": int(getattr(row, "anio")),
            "fecha": str(getattr(row, "fecha_sesion", getattr(row, "fecha", ""))),
            "sesion": str(getattr(row, "sesion_label", f"Sesión #{getattr(row, 'id_sesion', '')}")),
            "archivo": str(getattr(row, "archivo_sesion", "Sin archivo")),
            "pag": int(getattr(row, "nro_pagina", 1) or 1),
            "camara": str(getattr(row, "camara", "Desconocida")),
            "prov": str(getattr(row, "provincia", "No Identificada")),
            "parl": str(getattr(row, "nombre_parl", "No Identificado")),
            "partido": str(getattr(row, "partido", "No Identificado")),
            "rol": str(getattr(row, "rol", "Desconocido")),
            "ley": str(getattr(row, "ley_tratada", "Debate general / Sin ley específica")),
            "leyes": list(leyes_lista),
            "pals": int(getattr(row, "num_palabras", 0) or 0),
            "terminos": terminos_hallados,
            "menciones": menciones_en_discurso,
            "ner": entidades_limpias,
            "texto": extracto,
        })

    # Ordenar cronológicamente y por orden de diálogo/ID
    registros_dashboard.sort(key=lambda r: (r["fecha"], r["id"]))

    resumen_terminos = [
        {
            "etiqueta": t["etiqueta"],
            "normalizado": t["normalizado"],
            "intervenciones": int(frecuencia_terminos_global.get(t["etiqueta"], 0)),
            "menciones": int(menciones_terminos_global.get(t["etiqueta"], 0)),
        }
        for t in terminos_info
    ]
    resumen_terminos.sort(key=lambda x: (x["intervenciones"], x["menciones"]), reverse=True)

    print(f"    -> {len(registros_dashboard):,d} intervenciones coincidentes encontradas.")

    return {
        "total_corpus_3nf": int(len(df)),
        "terminos_buscados": resumen_terminos,
        "bancas_diputados": BANCAS_DIPUTADOS_HISTORICAS,
        "total_bancas_diputados": TOTAL_BANCAS_DIPUTADOS,
        "bancas_senadores_por_prov": BANCAS_SENADORES_POR_PROVINCIA,
        "intervenciones": registros_dashboard,
    }


def construir_html_dashboard_estandarizado(
    datos_dashboard: Dict,
    titulo_dashboard: str = "Dashboard Analítico Reproducible de Intervenciones y NER (1929–1939)",
    subtitulo_dashboard: Optional[str] = None,
) -> str:
    """
    Construye el archivo HTML interactivo estandarizado a partir de los resultados de
    `procesar_intervenciones_por_palabras`.
    Incluye:
    - Barra de filtros combinables por Año, Cámara, Provincia, Partido Político,
      Ley tratada, Sesión, Fecha de la sesión, Archivo PDF de la sesión y Palabra buscada.
    - Tabla plana documental (Fecha, Archivo de la sesión, N° Página, Provincia,
      Parlamentario, Ley tratada, Intervención con resaltado automático).
    - Pestañas dinámicas de Palabras y Entidades NER, Parlamentarios y Partidos,
      Provincias ponderadas por bancas y Leyes/Sesiones/Evolución anual.
    """
    if not subtitulo_dashboard:
        lista_etq = [t["etiqueta"] for t in datos_dashboard["terminos_buscados"]]
        muestra_etq = ", ".join(lista_etq[:8]) + (f" (+{len(lista_etq) - 8} más)" if len(lista_etq) > 8 else "")
        subtitulo_dashboard = (
            f"Búsqueda normalizada e insensible a mayúsculas, tildes, puntos o barras sobre "
            f"{datos_dashboard['total_corpus_3nf']:,d} intervenciones en 3NF · Términos: {muestra_etq}"
        ).replace(",", ".")

    payload_js = json.dumps(datos_dashboard, ensure_ascii=False)

    return f'''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{titulo_dashboard}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body {{
      background-color: #f8fafc;
      color: #0f172a;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }}
    .tab-btn.active {{
      background-color: #0f172a;
      color: #ffffff;
      border-color: #0f172a;
    }}
    .filter-select {{
      background-color: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 0.5rem;
      padding: 0.35rem 0.55rem;
      font-size: 0.75rem;
      color: #1e293b;
      width: 100%;
      min-width: 0;
      max-width: 100%;
      text-overflow: ellipsis;
      white-space: nowrap;
      overflow: hidden;
      outline: none;
      transition: border-color 0.15s, box-shadow 0.15s;
    }}
    .filter-select:focus {{
      border-color: #1d4ed8;
      box-shadow: 0 0 0 2px rgba(29, 78, 216, 0.15);
    }}
    mark.hl-term {{
      background-color: #fef08a;
      color: #713f12;
      font-weight: 700;
      padding: 0 2px;
      border-radius: 3px;
    }}
    .custom-scrollbar::-webkit-scrollbar {{
      width: 6px;
      height: 6px;
    }}
    .custom-scrollbar::-webkit-scrollbar-thumb {{
      background-color: #cbd5e1;
      border-radius: 3px;
    }}
  </style>
</head>
<body class="p-3 md:p-5 text-slate-800">
  <div class="max-w-7xl mx-auto space-y-4">

    <!-- CABECERA ESTANDARIZADA -->
    <header class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col lg:flex-row lg:items-center justify-between gap-3">
      <div>
        <div class="flex flex-wrap items-center gap-2 mb-1">
          <span class="text-[11px] font-bold uppercase tracking-wider text-blue-800 bg-blue-50 px-2.5 py-0.5 rounded border border-blue-200">
            Congreso Nacional Argentino (1929–1939) · UNSAM
          </span>
        </div>
        <h1 class="text-xl md:text-2xl font-black text-slate-900 tracking-tight">
          {titulo_dashboard}
        </h1>
        <p class="text-xs text-slate-500 mt-0.5">
          {subtitulo_dashboard}
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2 shrink-0">
        <button onclick="resetFilters()" class="px-3 py-1.5 text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-lg transition">
          ↺ Limpiar Filtros
        </button>
        <button onclick="exportFilteredCSV()" class="px-3 py-1.5 text-xs font-bold text-white bg-blue-800 hover:bg-blue-900 rounded-lg shadow-sm transition">
          ⬇ Exportar Tabla Plana (CSV)
        </button>
      </div>
    </header>

    <!-- PANEL MULTIDIMENSIONAL DE FILTROS INTERACTIVOS -->
    <section class="bg-white border border-slate-200 rounded-xl p-3.5 shadow-sm space-y-3">
      <div class="flex items-center justify-between border-b border-slate-100 pb-2">
        <div class="flex items-center gap-2">
          <span class="text-xs font-bold uppercase tracking-wider text-slate-700">🎛️ Filtros Multidimensionales de Intervenciones</span>
          <span id="active-filters-badge" class="hidden text-[11px] font-bold bg-amber-100 text-amber-900 border border-amber-300 px-2 py-0.5 rounded">
            Filtros activos
          </span>
        </div>
        <span id="filter-count-summary" class="text-xs font-mono font-bold text-blue-900"></span>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-4 gap-2.5">
        <!-- 1. Palabra / Término de la lista -->
        <div>
          <label class="block text-[10px] font-bold uppercase text-slate-500 mb-1">Palabra / Término Buscado</label>
          <select id="f-termino" onchange="applyFilters()" class="filter-select"></select>
        </div>

        <!-- 2. Año -->
        <div>
          <label class="block text-[10px] font-bold uppercase text-slate-500 mb-1">Año de la Sesión</label>
          <select id="f-anio" onchange="applyFilters()" class="filter-select"></select>
        </div>

        <!-- 3. Cámara -->
        <div>
          <label class="block text-[10px] font-bold uppercase text-slate-500 mb-1">Cámara Legislativa</label>
          <select id="f-camara" onchange="applyFilters()" class="filter-select"></select>
        </div>

        <!-- 4. Provincia -->
        <div>
          <label class="block text-[10px] font-bold uppercase text-slate-500 mb-1">Provincia / Distrito</label>
          <select id="f-provincia" onchange="applyFilters()" class="filter-select"></select>
        </div>

        <!-- 5. Partido Político -->
        <div>
          <label class="block text-[10px] font-bold uppercase text-slate-500 mb-1">Partido Político</label>
          <select id="f-partido" onchange="applyFilters()" class="filter-select"></select>
        </div>

        <!-- 6. Sesión en la que se trata -->
        <div>
          <label class="block text-[10px] font-bold uppercase text-slate-500 mb-1">Sesión / Reunión</label>
          <select id="f-sesion" onchange="applyFilters()" class="filter-select"></select>
        </div>

        <!-- 7. Fecha exacta de la sesión -->
        <div>
          <label class="block text-[10px] font-bold uppercase text-slate-500 mb-1">Fecha de la Sesión</label>
          <select id="f-fecha" onchange="applyFilters()" class="filter-select"></select>
        </div>

        <!-- 8. Archivo PDF de la sesión -->
        <div>
          <label class="block text-[10px] font-bold uppercase text-slate-500 mb-1">Archivo de la Sesión (PDF)</label>
          <select id="f-archivo" onchange="applyFilters()" class="filter-select"></select>
        </div>
      </div>

      <!-- Buscador libre adicional por Parlamentario o Texto -->
      <div class="pt-1 flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
        <div class="relative flex-1">
          <input
            type="text"
            id="f-busqueda-texto"
            oninput="applyFilters()"
            placeholder="🔎 Filtrar por nombre de parlamentario o cualquier palabra dentro de la intervención (insensible a mayúsculas, tildes, puntos o barras)..."
            class="w-full text-xs border border-slate-300 rounded-lg px-3 py-1.5 focus:border-blue-700 focus:outline-none"
          />
        </div>
      </div>
    </section>

    <!-- TARJETAS KPI ESTANDARIZADAS (RECALCULADAS EN VIVO) -->
    <section class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      <div class="bg-white border border-slate-200 rounded-xl p-3 shadow-sm min-w-0">
        <span class="text-[10px] font-bold text-slate-400 uppercase block truncate">Intervenciones Filtradas</span>
        <div class="text-2xl font-black text-blue-900 mt-0.5 truncate" id="kpi-ints">0</div>
        <div class="text-[11px] text-slate-500 font-medium mt-0.5 truncate" id="kpi-camaras">0 Dip. · 0 Sen.</div>
      </div>

      <div class="bg-white border border-slate-200 rounded-xl p-3 shadow-sm min-w-0">
        <span class="text-[10px] font-bold text-slate-400 uppercase block truncate">Palabras Debatidas</span>
        <div class="text-2xl font-black text-slate-800 mt-0.5 truncate" id="kpi-pals">0</div>
        <div class="text-[11px] text-emerald-700 font-semibold mt-0.5 truncate" id="kpi-pals-prom">0 palabras / intervención</div>
      </div>

      <div class="bg-white border border-slate-200 rounded-xl p-3 shadow-sm min-w-0">
        <span class="text-[10px] font-bold text-slate-400 uppercase block truncate">Sesiones y Tomos PDF</span>
        <div class="text-2xl font-black text-amber-700 mt-0.5 truncate" id="kpi-sesiones">0</div>
        <div class="text-[11px] text-slate-500 font-medium mt-0.5 truncate" id="kpi-archivos">0 archivos de sesión</div>
      </div>

      <div class="bg-white border border-slate-200 rounded-xl p-3 shadow-sm min-w-0">
        <span class="text-[10px] font-bold text-slate-400 uppercase block truncate">Leyes Identificadas</span>
        <div class="text-2xl font-black text-indigo-800 mt-0.5 truncate" id="kpi-leyes">0</div>
        <div class="text-[11px] text-slate-500 font-medium mt-0.5 truncate" id="kpi-ley-top">—</div>
      </div>

      <div class="bg-white border border-slate-200 rounded-xl p-3 shadow-sm col-span-2 sm:col-span-1 min-w-0">
        <span class="text-[10px] font-bold text-slate-400 uppercase block truncate">Provincia Líder (Ponderada)</span>
        <div class="text-lg font-black text-purple-900 mt-0.5 truncate" id="kpi-prov-lider">—</div>
        <div class="text-[11px] text-purple-800 font-semibold mt-0.5 truncate" id="kpi-prov-ratio">—</div>
      </div>
    </section>

    <!-- BARRA DE PESTAÑAS ESTANDARIZADA -->
    <nav class="bg-white border border-slate-200 rounded-xl p-1 shadow-sm flex flex-wrap gap-1">
      <button onclick="switchTab('tab-tabla')" id="btn-tab-tabla" class="tab-btn active px-3.5 py-1.5 rounded-lg text-xs md:text-sm font-bold border border-transparent transition">
        📋 1. Tabla Plana de Intervenciones
      </button>
      <button onclick="switchTab('tab-palabras')" id="btn-tab-palabras" class="tab-btn px-3.5 py-1.5 rounded-lg text-xs md:text-sm font-bold border border-transparent text-slate-600 hover:text-slate-900 transition">
        🔤 2. Palabras Buscadas y Entidades NER
      </button>
      <button onclick="switchTab('tab-oradores')" id="btn-tab-oradores" class="tab-btn px-3.5 py-1.5 rounded-lg text-xs md:text-sm font-bold border border-transparent text-slate-600 hover:text-slate-900 transition">
        👥 3. Parlamentarios y Partidos Políticos
      </button>
      <button onclick="switchTab('tab-provincias')" id="btn-tab-provincias" class="tab-btn px-3.5 py-1.5 rounded-lg text-xs md:text-sm font-bold border border-transparent text-slate-600 hover:text-slate-900 transition">
        🗺️ 4. Provincias Ponderadas por Banca
      </button>
      <button onclick="switchTab('tab-leyes-sesiones')" id="btn-tab-leyes-sesiones" class="tab-btn px-3.5 py-1.5 rounded-lg text-xs md:text-sm font-bold border border-transparent text-slate-600 hover:text-slate-900 transition">
        ⚖️ 5. Leyes Tratadas, Sesiones y Evolución Anual
      </button>
    </nav>

    <!-- PESTAÑA 1: TABLA PLANA DOCUMENTAL DE INTERVENCIONES                    -->
    <!-- Columnas: Fecha | Archivo de la sesión | N° Página | Provincia |       -->
    <!--           Parlamentario (y Partido/Ley) | Intervención                 -->
    <div id="tab-tabla" class="tab-content space-y-3">
      <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 class="text-sm font-bold text-slate-900">
              Explorador en Tabla Plana de Intervenciones Parlamentarias
            </h2>
            <p class="text-xs text-slate-500">
              Registro plano con Fecha, Archivo de la Sesión, N° de Página, Provincia, Parlamentario, Ley tratada e Intervención.
            </p>
          </div>

          <!-- Controles de ordenamiento y paginación -->
          <div class="flex flex-wrap items-center gap-2 text-xs">
            <label class="text-slate-500 font-semibold">Ordenar por:</label>
            <select id="sort-by" onchange="renderFlatTable()" class="border border-slate-300 rounded px-2 py-1 text-xs bg-white">
              <option value="fecha_asc">Fecha (1929 → 1939)</option>
              <option value="fecha_desc">Fecha (1939 → 1929)</option>
              <option value="pals_desc">Extensión (Más palabras)</option>
              <option value="pag_asc">N° de Página (Ascendente)</option>
              <option value="parl_asc">Parlamentario (A → Z)</option>
              <option value="prov_asc">Provincia (A → Z)</option>
            </select>

            <select id="page-size" onchange="changePageSize()" class="border border-slate-300 rounded px-2 py-1 text-xs bg-white">
              <option value="25">25 filas / pág.</option>
              <option value="50" selected>50 filas / pág.</option>
              <option value="100">100 filas / pág.</option>
              <option value="250">250 filas / pág.</option>
            </select>
          </div>
        </div>

        <div class="overflow-x-auto custom-scrollbar border border-slate-200 rounded-lg">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-100 text-slate-600 font-bold uppercase text-[11px] border-b border-slate-200">
              <tr>
                <th class="py-2.5 px-3 whitespace-nowrap">Fecha</th>
                <th class="py-2.5 px-3 whitespace-nowrap">Archivo de la Sesión / Reunión</th>
                <th class="py-2.5 px-2.5 text-center whitespace-nowrap">N° Página</th>
                <th class="py-2.5 px-3 whitespace-nowrap">Provincia</th>
                <th class="py-2.5 px-3 whitespace-nowrap">Parlamentario / Partido / Ley</th>
                <th class="py-2.5 px-3 min-w-[340px]">Intervención (Texto y Palabras Detectadas)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-200" id="tbody-plana"></tbody>
          </table>
        </div>

        <!-- Paginador inferior -->
        <div class="flex flex-col sm:flex-row items-center justify-between gap-2 pt-1 text-xs text-slate-600">
          <div id="pagination-info" class="font-medium"></div>
          <div class="flex items-center gap-1.5">
            <button onclick="prevPage()" id="btn-prev-page" class="px-3 py-1 rounded border border-slate-300 bg-white hover:bg-slate-100 disabled:opacity-40 font-semibold">
              ← Anterior
            </button>
            <span id="page-indicator" class="px-2 font-mono font-bold text-slate-800"></span>
            <button onclick="nextPage()" id="btn-next-page" class="px-3 py-1 rounded border border-slate-300 bg-white hover:bg-slate-100 disabled:opacity-40 font-semibold">
              Siguiente →
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- PESTAÑA 2: PALABRAS BUSCADAS Y ENTIDADES NER CO-OCURRENTES             -->
    <div id="tab-palabras" class="tab-content hidden space-y-4">
      <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-sm font-bold text-slate-900">Frecuencia de las Palabras Recibidas (Búsqueda Normalizada)</h3>
            <p class="text-xs text-slate-500">Hacé clic en cualquier palabra para filtrar automáticamente todo el dashboard por ese término.</p>
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5" id="grid-palabras-buscadas"></div>
      </div>

      <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <div>
          <h3 class="text-sm font-bold text-slate-900">Entidades Nombradas (NER 3NF) Co-ocurrentes en las Intervenciones Filtradas</h3>
          <p class="text-xs text-slate-500">Instituciones económicas, países, fenómenos, actores políticos y personalidades detectadas dentro del subconjunto activo.</p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3" id="grid-categorias-ner"></div>
      </div>
    </div>

    <!-- PESTAÑA 3: PARLAMENTARIOS Y PARTIDOS POLITICOS                         -->
    <div id="tab-oradores" class="tab-content hidden space-y-4">
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-bold text-slate-900">Diputados con más Intervenciones</h3>
            <span class="text-[11px] font-semibold text-blue-800 bg-blue-50 px-2 py-0.5 rounded">Cámara de Diputados</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs">
              <thead class="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                <tr>
                  <th class="py-1.5 px-2">Parlamentario</th>
                  <th class="py-1.5 px-2">Partido</th>
                  <th class="py-1.5 px-2">Provincia</th>
                  <th class="py-1.5 px-2 text-right">Ints.</th>
                  <th class="py-1.5 px-2 text-right">Palabras</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100" id="tbody-diputados"></tbody>
            </table>
          </div>
        </div>

        <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-bold text-slate-900">Senadores con más Intervenciones</h3>
            <span class="text-[11px] font-semibold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded">Cámara de Senadores</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs">
              <thead class="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                <tr>
                  <th class="py-1.5 px-2">Parlamentario</th>
                  <th class="py-1.5 px-2">Partido</th>
                  <th class="py-1.5 px-2">Provincia</th>
                  <th class="py-1.5 px-2 text-right">Ints.</th>
                  <th class="py-1.5 px-2 text-right">Palabras</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100" id="tbody-senadores"></tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Distribución por Partido Político -->
      <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h3 class="text-sm font-bold text-slate-900">Participación por Partido Político</h3>
            <p class="text-xs text-slate-500">Hacé clic en una fila para filtrar las intervenciones de ese partido político.</p>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th class="py-1.5 px-2">Partido Político</th>
                <th class="py-1.5 px-2 text-right">Intervenciones</th>
                <th class="py-1.5 px-2 text-right">% Intervenciones</th>
                <th class="py-1.5 px-2 text-right">Palabras Pronunciadas</th>
                <th class="py-1.5 px-2">Proporción Visual</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100" id="tbody-partidos"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- PESTAÑA 4: PROVINCIAS PONDERADAS POR BANCAS CONSTITUCIONALES           -->
    <div id="tab-provincias" class="tab-content hidden space-y-3">
      <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
          <div>
            <h3 class="text-sm font-bold text-slate-900">Participación Provincial Bruta y Ponderada Per Cápita (Bancas Históricas)</h3>
            <p class="text-xs text-slate-500">
              Ponderado por la asignación constitucional de 158 bancas en Diputados (Censo Nacional de 1914) y 2 senadores por distrito. Hacé clic en una provincia para filtrarla.
            </p>
          </div>
          <span class="text-xs font-mono font-bold text-purple-900 bg-purple-50 px-2.5 py-1 rounded border border-purple-200">
            158 Bancas Dip. · 30 Bancas Sen.
          </span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
              <tr>
                <th class="py-2 px-2.5">Provincia / Distrito</th>
                <th class="py-2 px-2.5 text-right">Total Ints.</th>
                <th class="py-2 px-2.5 text-right">Ints. Diputados</th>
                <th class="py-2 px-2.5 text-right">Bancas Dip. (158)</th>
                <th class="py-2 px-2.5 text-right font-bold text-blue-900">Ints. Dip. / Banca</th>
                <th class="py-2 px-2.5 text-right">Palabras / Banca Dip.</th>
                <th class="py-2 px-2.5 text-right">Ints. Senado</th>
                <th class="py-2 px-2.5">Intensidad Per Cápita (Dip.)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100" id="tbody-provincias"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- PESTAÑA 5: LEYES TRATADAS, SESIONES, FECHAS Y EVOLUCIÓN ANUAL          -->
    <div id="tab-leyes-sesiones" class="tab-content hidden space-y-4">
      <!-- Evolución anual -->
      <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h3 class="text-sm font-bold text-slate-900">Evolución Anual de las Intervenciones (1929–1939)</h3>
            <p class="text-xs text-slate-500">Hacé clic en cualquier año para filtrar las intervenciones de ese período legislativo.</p>
          </div>
          <span class="text-xs font-mono font-bold text-slate-700 bg-slate-100 px-2.5 py-0.5 rounded" id="badge-anios-total"></span>
        </div>
        <div class="space-y-2" id="bars-evolucion-anual"></div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- Leyes tratadas / citadas -->
        <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <div>
              <h3 class="text-sm font-bold text-slate-900">Leyes Tratadas o Citadas durante las Intervenciones</h3>
              <p class="text-xs text-slate-500">Hacé clic en una ley para ver únicamente las intervenciones vinculadas a ella.</p>
            </div>
          </div>
          <div class="overflow-x-auto max-h-96 custom-scrollbar">
            <table class="w-full text-left text-xs">
              <thead class="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 sticky top-0">
                <tr>
                  <th class="py-1.5 px-2">Ley Nacional / Tratamiento en Recinto</th>
                  <th class="py-1.5 px-2 text-right">Intervenciones</th>
                  <th class="py-1.5 px-2 text-right">Palabras</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100" id="tbody-leyes"></tbody>
            </table>
          </div>
        </div>

        <!-- Sesiones, fechas y archivos PDF -->
        <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <div>
              <h3 class="text-sm font-bold text-slate-900">Sesiones, Fechas y Archivos PDF del Diario de Sesiones</h3>
              <p class="text-xs text-slate-500">Hacé clic en cualquier sesión o archivo para filtrar sus intervenciones.</p>
            </div>
          </div>
          <div class="overflow-x-auto max-h-96 custom-scrollbar">
            <table class="w-full text-left text-xs">
              <thead class="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 sticky top-0">
                <tr>
                  <th class="py-1.5 px-2">Fecha</th>
                  <th class="py-1.5 px-2">Sesión / Cámara</th>
                  <th class="py-1.5 px-2">Archivo de la Sesión</th>
                  <th class="py-1.5 px-2 text-right">Ints.</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100" id="tbody-sesiones"></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <footer class="text-center text-[11px] text-slate-400 py-2 border-t border-slate-200">
      Dashboard Analítico Reproducible · Normalización Intrínseca de Texto y Consultas · Esquema Relacional Puro 3NF en Supabase (1929–1939).
    </footer>
  </div>

  <script>
    const DASHBOARD_DATA = {payload_js};
    const ALL_ROWS = DASHBOARD_DATA.intervenciones || [];
    const BANCAS_DIP = DASHBOARD_DATA.bancas_diputados || {{}};

    let filteredRows = [...ALL_ROWS];
    let currentPage = 1;
    let pageSize = 50;

    // Normalizador intrínseco en JS (idéntico al de Python: sin mayúsculas, tildes, puntos, barras ni guiones)
    function normalizeTextJS(str) {{
      if (!str) return '';
      return String(str)
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\\u0300-\\u036f]/g, '')
        .replace(/(?<=\\d)\\.(?=\\d{{3}}\\b)/g, '')
        .replace(/\\b([a-z])\\s*\\.\\s*([a-z])(?:\\s*\\.\\s*([a-z]))?(?:\\s*\\.\\s*([a-z]))?\\.?/g, '$1$2$3$4')
        .replace(/\\bley\\s+(?:n[°ºo\\.]*|nro\\.?|num\\.?|numero)\\s*(?=\\d)/g, 'ley ')
        .replace(/[^a-z0-9\\s]+/g, ' ')
        .replace(/\\s+/g, ' ')
        .trim();
    }}

    function escapeHtml(str) {{
      return String(str || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }}

    // Construye un patrón tolerante a acentos, puntos, guiones y barras para resaltar en el texto original
    function buildHighlightRegex(terms) {{
      const patterns = [];
      for (const rawTerm of terms) {{
        const norm = normalizeTextJS(rawTerm);
        if (!norm) continue;
        const tokens = norm.split(' ').filter(Boolean);
        if (!tokens.length) continue;
        const tokRegexes = tokens.map(tk => {{
          let out = '';
          for (const ch of tk) {{
            if (ch === 'a') out += '[aáàä]';
            else if (ch === 'e') out += '[eéèë]';
            else if (ch === 'i') out += '[iíìï]';
            else if (ch === 'o') out += '[oóòö]';
            else if (ch === 'u') out += '[uúùü]';
            else if (ch === 'n') out += '[nñ]';
            else if (/\\d/.test(ch)) out += ch + '\\\\.?';
            else out += ch.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&');
          }}
          if (tk.length >= 4 && /^[a-z]+$/.test(tk) && !tk.endsWith('s')) {{
            out += '(?:s|es)?';
          }}
          return out;
        }});
        patterns.push(tokRegexes.join('[\\\\s\\\\.\\\\-\\\\–\\\\—\\\\/°º]+'));
      }}
      if (!patterns.length) return null;
      try {{
        return new RegExp('(' + patterns.join('|') + ')', 'gi');
      }} catch (e) {{
        return null;
      }}
    }}

    function highlightText(text, terms) {{
      const safe = escapeHtml(text);
      const rx = buildHighlightRegex(terms);
      if (!rx) return safe;
      return safe.replace(rx, '<mark class="hl-term">$1</mark>');
    }}

    function populateInitialDropdowns() {{
      // 1. Términos buscados
      const selTerm = document.getElementById('f-termino');
      selTerm.innerHTML = '<option value="ALL">Todas las palabras buscadas (' + DASHBOARD_DATA.terminos_buscados.length + ')</option>';
      DASHBOARD_DATA.terminos_buscados.forEach(t => {{
        const opt = document.createElement('option');
        opt.value = t.etiqueta;
        opt.textContent = `${{t.etiqueta}} (${{t.intervenciones}} ints · ${{t.menciones}} menc.)`;
        selTerm.appendChild(opt);
      }});

      updateCascadingDropdowns(ALL_ROWS, true);
    }}

    function fillSelectWithCounts(selectId, allLabel, countsMap, currentVal, sortNumeric = false) {{
      const sel = document.getElementById(selectId);
      let entries = Object.entries(countsMap);
      if (sortNumeric) {{
        entries.sort((a, b) => String(a[0]).localeCompare(String(b[0])));
      }} else {{
        entries.sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])));
      }}
      sel.innerHTML = `<option value="ALL">${{allLabel}} (${{entries.length}})</option>`;
      for (const [val, cnt] of entries) {{
        const opt = document.createElement('option');
        opt.value = val;
        opt.textContent = `${{val}} (${{cnt}})`;
        sel.appendChild(opt);
      }}
      if (currentVal && currentVal !== 'ALL' && countsMap[currentVal]) {{
        sel.value = currentVal;
      }} else if (currentVal && currentVal !== 'ALL') {{
        const opt = document.createElement('option');
        opt.value = currentVal;
        opt.textContent = `${{currentVal}} (0)`;
        sel.appendChild(opt);
        sel.value = currentVal;
      }} else {{
        sel.value = 'ALL';
      }}
    }}

    function updateCascadingDropdowns(rowsSubset) {{
      const vAnio = document.getElementById('f-anio').value || 'ALL';
      const vCam = document.getElementById('f-camara').value || 'ALL';
      const vProv = document.getElementById('f-provincia').value || 'ALL';
      const vPart = document.getElementById('f-partido').value || 'ALL';
      const vSes = document.getElementById('f-sesion').value || 'ALL';
      const vFec = document.getElementById('f-fecha').value || 'ALL';
      const vArc = document.getElementById('f-archivo').value || 'ALL';

      const cAnio = {{}}, cCam = {{}}, cProv = {{}}, cPart = {{}}, cSes = {{}}, cFec = {{}}, cArc = {{}};
      for (const r of rowsSubset) {{
        cAnio[r.anio] = (cAnio[r.anio] || 0) + 1;
        cCam[r.camara] = (cCam[r.camara] || 0) + 1;
        cProv[r.prov] = (cProv[r.prov] || 0) + 1;
        cPart[r.partido] = (cPart[r.partido] || 0) + 1;
        cSes[r.sesion] = (cSes[r.sesion] || 0) + 1;
        cFec[r.fecha] = (cFec[r.fecha] || 0) + 1;
        cArc[r.archivo] = (cArc[r.archivo] || 0) + 1;
      }}

      fillSelectWithCounts('f-anio', 'Todos los años', cAnio, vAnio, true);
      fillSelectWithCounts('f-camara', 'Todas las cámaras', cCam, vCam, false);
      fillSelectWithCounts('f-provincia', 'Todas las provincias', cProv, vProv, false);
      fillSelectWithCounts('f-partido', 'Todos los partidos', cPart, vPart, false);
      fillSelectWithCounts('f-sesion', 'Todas las sesiones', cSes, vSes, false);
      fillSelectWithCounts('f-fecha', 'Todas las fechas', cFec, vFec, true);
      fillSelectWithCounts('f-archivo', 'Todos los archivos PDF', cArc, vArc, true);
    }}

    function applyFilters() {{
      const fTerm = document.getElementById('f-termino').value || 'ALL';
      const fAnio = document.getElementById('f-anio').value || 'ALL';
      const fCam = document.getElementById('f-camara').value || 'ALL';
      const fProv = document.getElementById('f-provincia').value || 'ALL';
      const fPart = document.getElementById('f-partido').value || 'ALL';
      const fSes = document.getElementById('f-sesion').value || 'ALL';
      const fFec = document.getElementById('f-fecha').value || 'ALL';
      const fArc = document.getElementById('f-archivo').value || 'ALL';
      const rawQuery = document.getElementById('f-busqueda-texto').value || '';
      const normQuery = normalizeTextJS(rawQuery);

      filteredRows = ALL_ROWS.filter(r => {{
        if (fTerm !== 'ALL' && (!r.terminos || !r.terminos.includes(fTerm))) return false;
        if (fAnio !== 'ALL' && String(r.anio) !== String(fAnio)) return false;
        if (fCam !== 'ALL' && r.camara !== fCam) return false;
        if (fProv !== 'ALL' && r.prov !== fProv) return false;
        if (fPart !== 'ALL' && r.partido !== fPart) return false;
        if (fSes !== 'ALL' && r.sesion !== fSes) return false;
        if (fFec !== 'ALL' && r.fecha !== fFec) return false;
        if (fArc !== 'ALL' && r.archivo !== fArc) return false;
        if (normQuery) {{
          const haystack = normalizeTextJS(r.parl + ' ' + r.partido + ' ' + r.prov + ' ' + r.ley + ' ' + r.texto);
          if (!haystack.includes(normQuery)) return false;
        }}
        return true;
      }});

      const anyActive = (
        fTerm !== 'ALL' || fAnio !== 'ALL' || fCam !== 'ALL' || fProv !== 'ALL' ||
        fPart !== 'ALL' || fSes !== 'ALL' || fFec !== 'ALL' ||
        fArc !== 'ALL' || normQuery !== ''
      );
      const badge = document.getElementById('active-filters-badge');
      if (anyActive) badge.classList.remove('hidden');
      else badge.classList.add('hidden');

      document.getElementById('filter-count-summary').textContent =
        `Mostrando ${{filteredRows.length.toLocaleString('es-AR')}} de ${{ALL_ROWS.length.toLocaleString('es-AR')}} intervenciones coincidentes`;

      updateCascadingDropdowns(filteredRows);
      currentPage = 1;
      renderAllViews();
    }}

    function resetFilters() {{
      ['f-termino', 'f-anio', 'f-camara', 'f-provincia', 'f-partido', 'f-sesion', 'f-fecha', 'f-archivo'].forEach(id => {{
        const el = document.getElementById(id);
        if (el) el.value = 'ALL';
      }});
      document.getElementById('f-busqueda-texto').value = '';
      updateCascadingDropdowns(ALL_ROWS);
      applyFilters();
    }}

    function quickFilter(selectId, value) {{
      const el = document.getElementById(selectId);
      if (!el) return;
      // Asegurar que la opción exista antes de asignarla
      let exists = Array.from(el.options).some(o => o.value === String(value));
      if (!exists) {{
        const opt = document.createElement('option');
        opt.value = String(value);
        opt.textContent = String(value);
        el.appendChild(opt);
      }}
      el.value = String(value);
      applyFilters();
    }}

    function switchTab(tabId) {{
      document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
      document.getElementById(tabId).classList.remove('hidden');
      document.querySelectorAll('.tab-btn').forEach(btn => {{
        btn.classList.remove('active', 'bg-slate-900', 'text-white');
        btn.classList.add('text-slate-600');
      }});
      const activeBtn = document.getElementById('btn-' + tabId);
      activeBtn.classList.add('active', 'bg-slate-900', 'text-white');
      activeBtn.classList.remove('text-slate-600');
    }}

    function renderAllViews() {{
      renderKPIs();
      renderFlatTable();
      renderPalabrasYNER();
      renderOradoresYPartidos();
      renderProvinciasPonderadas();
      renderLeyesSesionesAnios();
    }}

    // 1. KPIs Dinámicos
    function renderKPIs() {{
      const totalInts = filteredRows.length;
      let dip = 0, sen = 0, totalPals = 0;
      const sesSet = new Set(), arcSet = new Set(), leyCounts = {{}}, provDipCounts = {{}};

      for (const r of filteredRows) {{
        if (r.camara === 'Diputados') {{
          dip++;
          if (r.prov && r.prov !== 'No Identificada') {{
            provDipCounts[r.prov] = (provDipCounts[r.prov] || 0) + 1;
          }}
        }} else if (r.camara === 'Senadores') {{
          sen++;
        }}
        totalPals += (r.pals || 0);
        sesSet.add(r.fecha + '|' + r.sesion);
        arcSet.add(r.archivo);
        if (Array.isArray(r.leyes)) {{
          for (const l of r.leyes) {{
            if (l && !l.startsWith('Debate general')) leyCounts[l] = (leyCounts[l] || 0) + 1;
          }}
        }}
      }}

      document.getElementById('kpi-ints').textContent = totalInts.toLocaleString('es-AR');
      document.getElementById('kpi-camaras').textContent = `${{dip.toLocaleString('es-AR')}} Dip. · ${{sen.toLocaleString('es-AR')}} Sen.`;
      document.getElementById('kpi-pals').textContent = totalPals.toLocaleString('es-AR');
      const prom = totalInts > 0 ? Math.round(totalPals / totalInts) : 0;
      document.getElementById('kpi-pals-prom').textContent = `${{prom.toLocaleString('es-AR')}} palabras / discurso`;

      document.getElementById('kpi-sesiones').textContent = sesSet.size.toLocaleString('es-AR');
      document.getElementById('kpi-archivos').textContent = `${{arcSet.size.toLocaleString('es-AR')}} archivos PDF`;

      const leyEntries = Object.entries(leyCounts).sort((a, b) => b[1] - a[1]);
      document.getElementById('kpi-leyes').textContent = leyEntries.length.toLocaleString('es-AR');
      document.getElementById('kpi-ley-top').textContent = leyEntries.length > 0
        ? `${{leyEntries[0][0]}} (${{leyEntries[0][1]}})`
        : 'Debate general';

      let bestProv = '—', bestRatio = 0;
      for (const [pr, cnt] of Object.entries(provDipCounts)) {{
        const bancas = BANCAS_DIP[pr] || 1;
        const ratio = cnt / bancas;
        if (ratio > bestRatio) {{
          bestRatio = ratio;
          bestProv = pr;
        }}
      }}
      document.getElementById('kpi-prov-lider').textContent = bestProv;
      document.getElementById('kpi-prov-ratio').textContent = bestRatio > 0
        ? `${{bestRatio.toFixed(2)}} ints/banca en Diputados`
        : 'Sin intervenciones en Diputados';
    }}

    // 2. Tabla Plana Documental (Fecha | Archivo | N° Página | Provincia | Parlamentario | Intervención)
    function renderFlatTable() {{
      const sortBy = document.getElementById('sort-by').value || 'fecha_asc';
      const sorted = [...filteredRows];

      if (sortBy === 'fecha_asc') sorted.sort((a, b) => a.fecha.localeCompare(b.fecha) || a.pag - b.pag);
      else if (sortBy === 'fecha_desc') sorted.sort((a, b) => b.fecha.localeCompare(a.fecha) || a.pag - b.pag);
      else if (sortBy === 'pals_desc') sorted.sort((a, b) => b.pals - a.pals);
      else if (sortBy === 'pag_asc') sorted.sort((a, b) => a.pag - b.pag || a.fecha.localeCompare(b.fecha));
      else if (sortBy === 'parl_asc') sorted.sort((a, b) => a.parl.localeCompare(b.parl));
      else if (sortBy === 'prov_asc') sorted.sort((a, b) => a.prov.localeCompare(b.prov));

      const total = sorted.length;
      const totalPages = Math.max(1, Math.ceil(total / pageSize));
      if (currentPage > totalPages) currentPage = totalPages;

      const startIdx = (currentPage - 1) * pageSize;
      const pageItems = sorted.slice(startIdx, startIdx + pageSize);

      const tbody = document.getElementById('tbody-plana');
      tbody.innerHTML = '';

      const fTerm = document.getElementById('f-termino').value || 'ALL';
      const rawQuery = document.getElementById('f-busqueda-texto').value || '';

      if (pageItems.length === 0) {{
        tbody.innerHTML = `
          <tr>
            <td colspan="6" class="py-8 text-center text-slate-400 font-medium">
              No se encontraron intervenciones que coincidan con la combinación de filtros seleccionada.
            </td>
          </tr>`;
      }} else {{
        for (const r of pageItems) {{
          const tr = document.createElement('tr');
          tr.className = 'hover:bg-slate-50/90 transition align-top';

          const termsToHighlight = fTerm !== 'ALL' ? [fTerm] : [...(r.terminos || [])];
          if (rawQuery.trim()) termsToHighlight.push(rawQuery.trim());

          const pillsTerminos = (r.terminos || []).map(t => {{
            const cnt = (r.menciones && r.menciones[t]) ? r.menciones[t] : 1;
            return `<button onclick="quickFilter('f-termino', '${{escapeHtml(t)}}')" class="text-[10px] font-bold bg-amber-100 hover:bg-amber-200 text-amber-900 border border-amber-300 px-1.5 py-0.5 rounded transition">${{escapeHtml(t)}} (${{cnt}})</button>`;
          }}).join(' ');

          const camBadgeClass = r.camara === 'Diputados'
            ? 'bg-blue-50 text-blue-800 border-blue-200'
            : 'bg-emerald-50 text-emerald-800 border-emerald-200';

          tr.innerHTML = `
            <td class="py-2.5 px-3 font-mono font-bold text-slate-800 whitespace-nowrap">
              <button onclick="quickFilter('f-fecha', '${{escapeHtml(r.fecha)}}')" class="hover:text-blue-700 hover:underline">
                ${{escapeHtml(r.fecha)}}
              </button>
              <div class="text-[10px] font-normal text-slate-400 mt-0.5">Año ${{r.anio}}</div>
            </td>
            <td class="py-2.5 px-3 whitespace-nowrap">
              <button onclick="quickFilter('f-archivo', '${{escapeHtml(r.archivo)}}')" class="font-mono font-bold text-blue-900 hover:underline block">
                📄 ${{escapeHtml(r.archivo)}}
              </button>
              <button onclick="quickFilter('f-sesion', '${{escapeHtml(r.sesion)}}')" class="text-[11px] text-slate-600 hover:text-blue-700 block mt-0.5">
                ${{escapeHtml(r.sesion)}}
              </button>
              <span class="inline-block mt-1 text-[10px] font-semibold px-1.5 py-0.2 rounded border ${{camBadgeClass}}">
                ${{escapeHtml(r.camara)}}
              </span>
            </td>
            <td class="py-2.5 px-2.5 text-center font-mono font-bold text-slate-700 whitespace-nowrap">
              Pág. ${{r.pag}}
            </td>
            <td class="py-2.5 px-3 whitespace-nowrap">
              <button onclick="quickFilter('f-provincia', '${{escapeHtml(r.prov)}}')" class="font-bold text-slate-800 hover:text-blue-700 hover:underline">
                ${{escapeHtml(r.prov)}}
              </button>
            </td>
            <td class="py-2.5 px-3">
              <div class="font-bold text-slate-900">${{escapeHtml(r.parl)}}</div>
              <button onclick="quickFilter('f-partido', '${{escapeHtml(r.partido)}}')" class="text-[11px] text-slate-600 hover:text-blue-700 hover:underline block">
                ${{escapeHtml(r.partido)}}
              </button>
              <div class="mt-1">
                <span class="text-[10px] font-medium bg-indigo-50 text-indigo-900 border border-indigo-200 px-1.5 py-0.5 rounded text-left line-clamp-2 inline-block" title="${{escapeHtml(r.ley)}}">
                  ⚖️ ${{escapeHtml(r.ley)}}
                </span>
              </div>
            </td>
            <td class="py-2.5 px-3 text-slate-700 leading-relaxed">
              <div class="flex flex-wrap items-center gap-1 mb-1.5">
                ${{pillsTerminos}}
                <span class="text-[10px] font-mono text-slate-400 ml-auto">${{r.pals.toLocaleString('es-AR')}} palabras · ID #${{r.id}}</span>
              </div>
              <p class="text-xs text-slate-800 leading-relaxed">${{highlightText(r.texto, termsToHighlight)}}</p>
            </td>
          `;
          tbody.appendChild(tr);
        }}
      }}

      document.getElementById('pagination-info').textContent =
        total > 0
          ? `Mostrando filas ${{(startIdx + 1).toLocaleString('es-AR')}} a ${{Math.min(startIdx + pageSize, total).toLocaleString('es-AR')}} de ${{total.toLocaleString('es-AR')}} intervenciones`
          : '0 intervenciones';
      document.getElementById('page-indicator').textContent = `Página ${{currentPage}} de ${{totalPages}}`;
      document.getElementById('btn-prev-page').disabled = currentPage <= 1;
      document.getElementById('btn-next-page').disabled = currentPage >= totalPages;
    }}

    function prevPage() {{
      if (currentPage > 1) {{
        currentPage--;
        renderFlatTable();
      }}
    }}

    function nextPage() {{
      const totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize));
      if (currentPage < totalPages) {{
        currentPage++;
        renderFlatTable();
      }}
    }}

    function changePageSize() {{
      pageSize = parseInt(document.getElementById('page-size').value || '50', 10);
      currentPage = 1;
      renderFlatTable();
    }}

    // 3. Pestaña 2: Frecuencia de Palabras Buscadas y Entidades NER Co-ocurrentes
    function renderPalabrasYNER() {{
      const termInts = {{}}, termMenc = {{}};
      const nerByCategory = {{}};

      for (const r of filteredRows) {{
        if (Array.isArray(r.terminos)) {{
          for (const t of r.terminos) {{
            termInts[t] = (termInts[t] || 0) + 1;
            termMenc[t] = (termMenc[t] || 0) + ((r.menciones && r.menciones[t]) ? r.menciones[t] : 1);
          }}
        }}
        if (Array.isArray(r.ner)) {{
          for (const item of r.ner) {{
            const cat = item.c || 'Otras Entidades';
            if (!nerByCategory[cat]) nerByCategory[cat] = {{}};
            nerByCategory[cat][item.e] = (nerByCategory[cat][item.e] || 0) + (item.f || 1);
          }}
        }}
      }}

      const gridWords = document.getElementById('grid-palabras-buscadas');
      gridWords.innerHTML = '';
      const maxWordInts = Math.max(1, ...Object.values(termInts));

      DASHBOARD_DATA.terminos_buscados.forEach(tObj => {{
        const etq = tObj.etiqueta;
        const ints = termInts[etq] || 0;
        const menc = termMenc[etq] || 0;
        const pct = Math.round((ints / maxWordInts) * 100);

        const card = document.createElement('div');
        card.className = 'border border-slate-200 rounded-lg p-3 bg-slate-50/70 hover:bg-blue-50/50 cursor-pointer transition';
        card.onclick = () => quickFilter('f-termino', etq);
        card.innerHTML = `
          <div class="flex items-center justify-between">
            <span class="font-bold text-xs text-slate-900">${{escapeHtml(etq)}}</span>
            <span class="text-[11px] font-mono font-bold text-blue-900 bg-blue-100 px-2 py-0.5 rounded">${{ints.toLocaleString('es-AR')}} ints</span>
          </div>
          <div class="flex items-center justify-between text-[11px] text-slate-500 mt-1">
            <span>Forma normalizada: <code class="text-slate-700">${{escapeHtml(tObj.normalizado)}}</code></span>
            <span class="font-mono">${{menc.toLocaleString('es-AR')}} menciones</span>
          </div>
          <div class="w-full bg-slate-200 rounded-full h-1.5 mt-2 overflow-hidden">
            <div class="bg-blue-700 h-full rounded-full" style="width: ${{pct}}%"></div>
          </div>
        `;
        gridWords.appendChild(card);
      }});

      const gridNER = document.getElementById('grid-categorias-ner');
      gridNER.innerHTML = '';
      const catEntries = Object.entries(nerByCategory);
      if (catEntries.length === 0) {{
        gridNER.innerHTML = '<div class="text-xs text-slate-400 col-span-3 py-4">Sin entidades NER registradas para este subconjunto.</div>';
      }} else {{
        for (const [catName, entMap] of catEntries) {{
          const sortedEnts = Object.entries(entMap).sort((a, b) => b[1] - a[1]).slice(0, 10);
          const maxEnt = sortedEnts.length > 0 ? sortedEnts[0][1] : 1;
          const rowsHtml = sortedEnts.map(([eName, cnt]) => {{
            const w = Math.round((cnt / maxEnt) * 100);
            return `
              <div class="space-y-0.5">
                <div class="flex justify-between text-[11px]">
                  <span class="font-medium text-slate-700 truncate" title="${{escapeHtml(eName)}}">${{escapeHtml(eName)}}</span>
                  <span class="font-mono font-bold text-slate-900 ml-2">${{cnt.toLocaleString('es-AR')}}</span>
                </div>
                <div class="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                  <div class="bg-indigo-700 h-full rounded-full" style="width: ${{w}}%"></div>
                </div>
              </div>
            `;
          }}).join('');

          const box = document.createElement('div');
          box.className = 'border border-slate-200 rounded-xl p-3.5 bg-white shadow-sm space-y-2';
          box.innerHTML = `
            <div class="flex items-center justify-between border-b border-slate-100 pb-1.5">
              <span class="text-xs font-bold text-slate-900 uppercase">${{escapeHtml(catName)}}</span>
              <span class="text-[10px] font-mono text-slate-400">Menciones</span>
            </div>
            <div class="space-y-1.5">${{rowsHtml}}</div>
          `;
          gridNER.appendChild(box);
        }}
      }}
    }}

    // 4. Pestaña 3: Parlamentarios y Partidos Políticos
    function renderOradoresYPartidos() {{
      const dipMap = {{}}, senMap = {{}}, partMap = {{}};

      for (const r of filteredRows) {{
        const pKey = r.partido || 'No Identificado';
        if (!partMap[pKey]) partMap[pKey] = {{ ints: 0, pals: 0 }};
        partMap[pKey].ints++;
        partMap[pKey].pals += (r.pals || 0);

        if (r.parl && r.parl !== 'No Identificado') {{
          const target = r.camara === 'Diputados' ? dipMap : senMap;
          if (!target[r.parl]) {{
            target[r.parl] = {{ parl: r.parl, partido: r.partido, prov: r.prov, ints: 0, pals: 0 }};
          }}
          target[r.parl].ints++;
          target[r.parl].pals += (r.pals || 0);
        }}
      }}

      const fillOradores = (tbodyId, mapObj, colorClass) => {{
        const tbody = document.getElementById(tbodyId);
        tbody.innerHTML = '';
        const list = Object.values(mapObj).sort((a, b) => b.ints - a.ints || b.pals - a.pals).slice(0, 15);
        if (!list.length) {{
          tbody.innerHTML = '<tr><td colspan="5" class="py-4 text-center text-slate-400">Sin registros</td></tr>';
          return;
        }}
        for (const item of list) {{
          const tr = document.createElement('tr');
          tr.className = 'hover:bg-slate-50 cursor-pointer transition';
          tr.onclick = () => {{
            document.getElementById('f-busqueda-texto').value = item.parl;
            applyFilters();
          }};
          tr.innerHTML = `
            <td class="py-1.5 px-2 font-bold text-slate-900">${{escapeHtml(item.parl)}}</td>
            <td class="py-1.5 px-2 text-slate-600 text-[11px]">${{escapeHtml(item.partido)}}</td>
            <td class="py-1.5 px-2 text-slate-600">${{escapeHtml(item.prov)}}</td>
            <td class="py-1.5 px-2 font-mono font-bold ${{colorClass}} text-right">${{item.ints.toLocaleString('es-AR')}}</td>
            <td class="py-1.5 px-2 font-mono text-slate-500 text-right">${{item.pals.toLocaleString('es-AR')}}</td>
          `;
          tbody.appendChild(tr);
        }}
      }};

      fillOradores('tbody-diputados', dipMap, 'text-blue-900');
      fillOradores('tbody-senadores', senMap, 'text-emerald-900');

      const tbodyPart = document.getElementById('tbody-partidos');
      tbodyPart.innerHTML = '';
      const partList = Object.entries(partMap).sort((a, b) => b[1].ints - a[1].ints);
      const totalInts = Math.max(1, filteredRows.length);
      const maxPartInts = partList.length > 0 ? partList[0][1].ints : 1;

      for (const [pName, st] of partList) {{
        const pct = ((st.ints / totalInts) * 100).toFixed(1);
        const barW = Math.round((st.ints / maxPartInts) * 100);
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-50 cursor-pointer transition';
        tr.onclick = () => quickFilter('f-partido', pName);
        tr.innerHTML = `
          <td class="py-1.5 px-2 font-bold text-slate-900">${{escapeHtml(pName)}}</td>
          <td class="py-1.5 px-2 font-mono font-bold text-blue-900 text-right">${{st.ints.toLocaleString('es-AR')}}</td>
          <td class="py-1.5 px-2 font-mono text-slate-600 text-right">${{pct}}%</td>
          <td class="py-1.5 px-2 font-mono text-slate-500 text-right">${{st.pals.toLocaleString('es-AR')}}</td>
          <td class="py-1.5 px-2 w-40">
            <div class="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div class="bg-blue-700 h-full rounded-full" style="width: ${{barW}}%"></div>
            </div>
          </td>
        `;
        tbodyPart.appendChild(tr);
      }}
    }}

    // 5. Pestaña 4: Provincias Ponderadas por Bancas Constitucionales
    function renderProvinciasPonderadas() {{
      const provMap = {{}};
      for (const r of filteredRows) {{
        if (!r.prov || r.prov === 'No Identificada') continue;
        if (!provMap[r.prov]) {{
          provMap[r.prov] = {{ prov: r.prov, totalInts: 0, dipInts: 0, dipPals: 0, senInts: 0 }};
        }}
        provMap[r.prov].totalInts++;
        if (r.camara === 'Diputados') {{
          provMap[r.prov].dipInts++;
          provMap[r.prov].dipPals += (r.pals || 0);
        }} else if (r.camara === 'Senadores') {{
          provMap[r.prov].senInts++;
        }}
      }}

      const list = Object.values(provMap).map(item => {{
        const bancas = BANCAS_DIP[item.prov] || 1;
        return {{
          ...item,
          bancas,
          ratioInts: item.dipInts / bancas,
          ratioPals: Math.round(item.dipPals / bancas),
        }};
      }});

      list.sort((a, b) => b.ratioInts - a.ratioInts || b.totalInts - a.totalInts);
      const maxRatio = list.length > 0 ? Math.max(list[0].ratioInts, 0.01) : 1;

      const tbody = document.getElementById('tbody-provincias');
      tbody.innerHTML = '';
      for (const p of list) {{
        const barW = Math.round((p.ratioInts / maxRatio) * 100);
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-50 cursor-pointer transition';
        tr.onclick = () => quickFilter('f-provincia', p.prov);
        tr.innerHTML = `
          <td class="py-1.5 px-2.5 font-bold text-slate-900">${{escapeHtml(p.prov)}}</td>
          <td class="py-1.5 px-2.5 font-mono text-right text-slate-700">${{p.totalInts.toLocaleString('es-AR')}}</td>
          <td class="py-1.5 px-2.5 font-mono text-right text-slate-700 font-semibold">${{p.dipInts.toLocaleString('es-AR')}}</td>
          <td class="py-1.5 px-2.5 font-mono text-right text-slate-500">${{p.bancas}}</td>
          <td class="py-1.5 px-2.5 font-mono text-right font-bold text-blue-900">${{p.ratioInts.toFixed(2)}}</td>
          <td class="py-1.5 px-2.5 font-mono text-right text-slate-600">${{p.ratioPals.toLocaleString('es-AR')}}</td>
          <td class="py-1.5 px-2.5 font-mono text-right text-emerald-800">${{p.senInts.toLocaleString('es-AR')}}</td>
          <td class="py-1.5 px-2.5 w-36">
            <div class="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div class="bg-purple-700 h-full rounded-full" style="width: ${{barW}}%"></div>
            </div>
          </td>
        `;
        tbody.appendChild(tr);
      }}
    }}

    // 6. Pestaña 5: Leyes Tratadas, Sesiones, Fechas y Evolución Anual
    function renderLeyesSesionesAnios() {{
      const anioCounts = {{}};
      for (let y = 1929; y <= 1939; y++) anioCounts[y] = 0;
      const leyMap = {{}}, sesMap = {{}};

      for (const r of filteredRows) {{
        anioCounts[r.anio] = (anioCounts[r.anio] || 0) + 1;

        const leyesArr = Array.isArray(r.leyes) && r.leyes.length ? r.leyes : [r.ley];
        for (const l of leyesArr) {{
          if (!leyMap[l]) leyMap[l] = {{ ley: l, ints: 0, pals: 0 }};
          leyMap[l].ints++;
          leyMap[l].pals += (r.pals || 0);
        }}

        const sKey = `${{r.fecha}}||${{r.sesion}}||${{r.camara}}||${{r.archivo}}`;
        if (!sesMap[sKey]) {{
          sesMap[sKey] = {{ fecha: r.fecha, sesion: r.sesion, camara: r.camara, archivo: r.archivo, ints: 0 }};
        }}
        sesMap[sKey].ints++;
      }}

      document.getElementById('badge-anios-total').textContent = `${{filteredRows.length.toLocaleString('es-AR')}} intervenciones`;
      const barsContainer = document.getElementById('bars-evolucion-anual');
      barsContainer.innerHTML = '';
      const maxAnio = Math.max(1, ...Object.values(anioCounts));

      for (const [yr, cnt] of Object.entries(anioCounts)) {{
        const pct = Math.round((cnt / maxAnio) * 100);
        const div = document.createElement('div');
        div.className = 'flex items-center gap-2 text-xs cursor-pointer hover:bg-slate-50 p-1 rounded transition';
        div.onclick = () => quickFilter('f-anio', yr);
        div.innerHTML = `
          <span class="w-12 font-mono font-bold text-slate-700">${{yr}}</span>
          <div class="flex-1 bg-slate-100 rounded-full h-3 overflow-hidden">
            <div class="bg-blue-700 h-full rounded-full transition-all duration-300" style="width: ${{pct}}%"></div>
          </div>
          <span class="w-20 font-mono font-bold text-slate-800 text-right">${{cnt.toLocaleString('es-AR')}}</span>
        `;
        barsContainer.appendChild(div);
      }}

      const tbodyLeyes = document.getElementById('tbody-leyes');
      tbodyLeyes.innerHTML = '';
      const leyList = Object.values(leyMap).sort((a, b) => b.ints - a.ints);
      for (const item of leyList.slice(0, 60)) {{
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-50 transition';
        tr.innerHTML = `
          <td class="py-1.5 px-2 font-medium text-slate-800">${{escapeHtml(item.ley)}}</td>
          <td class="py-1.5 px-2 font-mono font-bold text-indigo-900 text-right">${{item.ints.toLocaleString('es-AR')}}</td>
          <td class="py-1.5 px-2 font-mono text-slate-500 text-right">${{item.pals.toLocaleString('es-AR')}}</td>
        `;
        tbodyLeyes.appendChild(tr);
      }}

      const tbodySes = document.getElementById('tbody-sesiones');
      tbodySes.innerHTML = '';
      const sesList = Object.values(sesMap).sort((a, b) => b.ints - a.ints || a.fecha.localeCompare(b.fecha));
      for (const s of sesList.slice(0, 60)) {{
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-50 transition';
        tr.innerHTML = `
          <td class="py-1.5 px-2 font-mono font-bold text-slate-700 whitespace-nowrap">
            <button onclick="quickFilter('f-fecha', '${{escapeHtml(s.fecha)}}')" class="hover:text-blue-700 hover:underline">${{escapeHtml(s.fecha)}}</button>
          </td>
          <td class="py-1.5 px-2 text-slate-700">
            <button onclick="quickFilter('f-sesion', '${{escapeHtml(s.sesion)}}')" class="hover:text-blue-700 hover:underline font-medium">${{escapeHtml(s.sesion)}}</button>
            <span class="text-[10px] text-slate-400 block">${{escapeHtml(s.camara)}}</span>
          </td>
          <td class="py-1.5 px-2 font-mono text-blue-900">
            <button onclick="quickFilter('f-archivo', '${{escapeHtml(s.archivo)}}')" class="hover:underline">📄 ${{escapeHtml(s.archivo)}}</button>
          </td>
          <td class="py-1.5 px-2 font-mono font-bold text-slate-900 text-right">${{s.ints.toLocaleString('es-AR')}}</td>
        `;
        tbodySes.appendChild(tr);
      }}
    }}

    // Exportación de la Tabla Plana filtrada a CSV (UTF-8 con BOM para Excel)
    function exportFilteredCSV() {{
      const headers = [
        'id_intervencion', 'fecha_sesion', 'anio', 'camara', 'sesion',
        'archivo_sesion', 'numero_pagina', 'provincia', 'parlamentario',
        'partido_politico', 'ley_tratada', 'palabras_detectadas', 'num_palabras', 'intervencion'
      ];
      const csvRows = [headers.join(',')];
      for (const r of filteredRows) {{
        const vals = [
          r.id,
          `"${{String(r.fecha).replace(/"/g, '""')}}"`,
          r.anio,
          `"${{String(r.camara).replace(/"/g, '""')}}"`,
          `"${{String(r.sesion).replace(/"/g, '""')}}"`,
          `"${{String(r.archivo).replace(/"/g, '""')}}"`,
          r.pag,
          `"${{String(r.prov).replace(/"/g, '""')}}"`,
          `"${{String(r.parl).replace(/"/g, '""')}}"`,
          `"${{String(r.partido).replace(/"/g, '""')}}"`,
          `"${{String(r.ley).replace(/"/g, '""')}}"`,
          `"${{String((r.terminos || []).join('; ')).replace(/"/g, '""')}}"`,
          r.pals,
          `"${{String(r.texto).replace(/"/g, '""')}}"`
        ];
        csvRows.push(vals.join(','));
      }}
      const blob = new Blob(['\\uFEFF' + csvRows.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'intervenciones_filtradas_ner_3nf.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }}

    document.addEventListener('DOMContentLoaded', () => {{
      populateInitialDropdowns();
      applyFilters();
    }});
  </script>
</body>
</html>
'''


def generar_dashboard_desde_palabras(
    lista_palabras: List[str],
    titulo_dashboard: str = "Dashboard Analítico Reproducible de Intervenciones y NER (1929–1939)",
    subtitulo_dashboard: Optional[str] = None,
    ruta_salida: Optional[str] = None,
    forzar_recarga_supabase: bool = False,
    max_caracteres_extracto: int = 850,
) -> str:
    """
    Función principal reproducible que recibe una lista de palabras (`lista_palabras`),
    normaliza intrínsecamente los términos recibidos y el corpus de 64.636 intervenciones
    parlamentarias en 3NF, y genera el Dashboard HTML interactivo estandarizado.

    Parámetros:
    -----------
    lista_palabras : List[str]
        Lista de palabras, siglas, números de ley o frases a buscar (ej. ["Roca-Runciman", "Ley 11.693", "U.I.A."]).
    titulo_dashboard : str
        Título principal del dashboard HTML generado.
    subtitulo_dashboard : Optional[str]
        Subtítulo descriptivo opcional.
    ruta_salida : Optional[str]
        Ruta del archivo HTML de salida. Por defecto guarda en `Creacion_graficos/graficos/dashboard_roca_runciman_ner.html`.
    forzar_recarga_supabase : bool
        Si es True, re-descarga las tablas 3NF desde Supabase ignorando el caché local.
    max_caracteres_extracto : int
        Longitud máxima en caracteres del fragmento contextual de cada intervención en la tabla plana.

    Retorna:
    --------
    str : Ruta absoluta del archivo HTML generado.
    """
    from database_connection import supabase

    if ruta_salida is None:
        ruta_salida = os.path.join(DIR_GRAFICOS, "dashboard_roca_runciman_ner.html")

    df = cargar_datos_intervenciones(supabase, forzar_recarga=forzar_recarga_supabase)
    datos_dashboard = procesar_intervenciones_por_palabras(
        df=df,
        lista_palabras=lista_palabras,
        max_caracteres_extracto=max_caracteres_extracto,
    )
    html_content = construir_html_dashboard_estandarizado(
        datos_dashboard=datos_dashboard,
        titulo_dashboard=titulo_dashboard,
        subtitulo_dashboard=subtitulo_dashboard,
    )

    os.makedirs(os.path.dirname(os.path.abspath(ruta_salida)), exist_ok=True)
    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(
        f"[OK] Dashboard estandarizado generado exitosamente en: '{ruta_salida}' "
        f"({len(datos_dashboard['intervenciones']):,d} intervenciones · {len(html_content):,d} bytes)"
    )
    return ruta_salida


# Alias para retrocompatibilidad e importación directa
generar_dashboard_ner = generar_dashboard_desde_palabras


def main():
    parser = argparse.ArgumentParser(
        description="Generador reproducible de Dashboard Analítico NER a partir de una lista de palabras (1929-1939)"
    )
    parser.add_argument(
        "--palabras",
        nargs="+",
        default=None,
        help="Lista de palabras o frases a buscar (ej. --palabras 'Roca-Runciman' 'Ley 11.693' 'Frigorífico' 'U.I.A.')",
    )
    parser.add_argument(
        "--titulo",
        type=str,
        default="Dashboard Analítico Reproducible de Intervenciones y NER (1929–1939)",
        help="Título del dashboard HTML.",
    )
    parser.add_argument(
        "--salida",
        type=str,
        default=os.path.join(DIR_GRAFICOS, "dashboard_roca_runciman_ner.html"),
        help="Ruta del archivo HTML de salida.",
    )
    parser.add_argument(
        "--recalcular",
        action="store_true",
        help="Fuerza la recarga de las tablas 3NF desde Supabase ignorando el caché local.",
    )
    args = parser.parse_args()

    palabras_a_usar = args.palabras if args.palabras else PALABRAS_DEFAULT_COMERCIO_EXTERIOR
    generar_dashboard_desde_palabras(
        lista_palabras=palabras_a_usar,
        titulo_dashboard=args.titulo,
        ruta_salida=args.salida,
        forzar_recarga_supabase=args.recalcular,
    )


if __name__ == "__main__":
    main()
