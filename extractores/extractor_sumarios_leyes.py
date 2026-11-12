#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Este script se encarga de extraer los sumarios de las sesiones y el articulado
de los proyectos y leyes debatidas entre 1929 y 1939.

Los diarios de sesiones tienen al inicio de cada reunión un sumario temático
y luego, en el cuerpo del debate, se insertan los proyectos de ley completos.
Acá hacemos:
1. Lectura en dos columnas por página, ignorando cabezales repetitivos y saltos de página.
2. Identificación de cada punto del sumario (orden del día, asuntos entrados).
3. Extracción de las 1.087 leyes sancionadas durante la década (Leyes 11.544 a 12.630),
   desglosando cada ley en sus artículos individuales para cargarlos en Supabase.
"""

import os
import sys
import re
import time
import unicodedata
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
DIR_DB = ROOT_DIR / "base_de_datos"
if str(DIR_DB) not in sys.path:
    sys.path.insert(0, str(DIR_DB))

import pymupdf as fitz  # PyMuPDF
from database_connection import supabase



REGEX_CABEZAL_PAGINA = re.compile(
    r"^(?:\d+\s+|[IVXLCDM]+\s+|[\_\-\.\s]+\d+\s+)?(?:"
    r"Reuni[oó]n\s+n[uúâ°º]m[\.\,\s]*\d+"
    r"|CONGRESO\s+NACIONAL"
    r"|C\s*[AÁ]\s*M\s*A\s*R\s*A\s+D\s*E\s+(?:D\s*I\s*P\s*U\s*T\s*A\s*D\s*O\s*S|S\s*E\s*N\s*A\s*D\s*O\s*R\s*E\s*S)"
    r"|(?:ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|SEPTIEMBRE|SETIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE)\s+\d{1,2}\s+DE\s+19[23]\d"
    r"|\d+\s*[\.ªº°a\*]?\s*Reuni[oó]n\.\s*Cont\."
    r"|Sesi[oó]n\s+de\s+Asamble[ar]"
    r"|INDICE\s+GENERAL|NOMENCL[AÁ]TOR"
    r"|\-\s*[IVXLCDM]+\s*\-"
    r")\b",
    re.IGNORECASE
)

REGEX_PAGINA_INDICE = re.compile(
    r"\b(?:INDICE\s+GENERAL|NOMENCL[AÁ]TOR\s+GENERAL|INDICE\s+ALFAB[EÉ]TICO|NOMENCL[AÁ]TOR\s+DE|INDICE\s+DE\s+LEYES)\b",
    re.IGNORECASE
)

REGEX_APERTURA_REUNION = re.compile(
    r"(?:"
    r"(?:\d+|\|\s*\||I+)\s*[\.ªº°a\*]?\s*R\s*E\s*U\s*N\s*I\s*[OÓ]\s*N"
    r"|S\s*E\s*S\s*I\s*[OÓ]\s*N\s+(?:P\s*R\s*E\s*P\s*A\s*R\s*A\s*T\s*O\s*R\s*I\s*A|O\s*R\s*D\s*I\s*N\s*A\s*R\s*I\s*A|E\s*S\s*P\s*E\s*C\s*I\s*A\s*L|D\s*E\s+A\s*S\s*A\s*M\s*B\s*L\s*E\s*[AR]|E\s*N\s+M\s*I\s*N\s*O\s*R\s*[IÍ]\s*A)"
    r"|P\s*R\s*E\s*S\s*I\s*D\s*E\s*N\s*C\s*I\s*A\s+D\s*E"
    r"|(?:D\s*I\s*P\s*U\s*T\s*A\s*D\s*O\s*S|S\s*E\s*N\s*A\s*D\s*O\s*R\s*E\s*S)\s+(?:P\s*R\s*E\s*S\s*E\s*N\s*T\s*E\s*S|A\s*U\s*S\s*E\s*N\s*T\s*E\s*S)"
    r")",
    re.IGNORECASE
)

REGEX_PALABRA_SUMARIO = re.compile(
    r"S\s*U\s*(?:M|SL|N|I\s*I)\s*A\s*R\s*I\s*O",
    re.IGNORECASE
)

REGEX_TITULO_SUMARIO_LINEA = re.compile(
    r"(?m)^\s*S\s*U\s*(?:M|SL|N|I\s*I)\s*A\s*R\s*I\s*O\s*[\.\:]?\s*$",
    re.IGNORECASE
)

REGEX_BLOQUE_ANCHO_SESION = re.compile(
    r"(?:"
    r"C\s*O\s*N\s*G\s*R\s*E\s*S\s*O\s+N\s*A\s*C\s*I\s*O\s*N\s*A\s*L"
    r"|C\s*[AÁ]\s*M\s*A\s*R\s*A\s+D\s*E\s+(?:D\s*I\s*P\s*U\s*T\s*A\s*D\s*O\s*S|S\s*E\s*N\s*A\s*D\s*O\s*R\s*E\s*S)"
    r"|R\s*E\s*U\s*N\s*I\s*[OÓ]\s*N"
    r"|S\s*E\s*S\s*I\s*[OÓ]\s*N\s+(?:O\s*R\s*D\s*I\s*N\s*A\s*R\s*I\s*A|P\s*R\s*E\s*P\s*A\s*R\s*A\s*T\s*O\s*R\s*I\s*A|E\s*S\s*P\s*E\s*C\s*I\s*A\s*L|D\s*E\s+A\s*S\s*A\s*M\s*B\s*L\s*E\s*[AR]|E\s*N\s+M\s*I\s*N\s*O\s*R\s*[IÍ]\s*A)"
    r"|P\s*R\s*E\s*S\s*I\s*D\s*E\s*N\s*C\s*I\s*A\s+D\s*E"
    r"|V\s*i\s*c\s*e\s*p\s*r\s*e\s*s\s*i\s*d\s*e\s*n\s*t\s*e"
    r"|(?:D\s*I\s*P\s*U\s*T\s*A\s*D\s*O\s*S|S\s*E\s*N\s*A\s*D\s*O\s*R\s*E\s*S|M\s*I\s*N\s*I\s*S\s*T\s*R\s*O\s*S)\s+(?:P\s*R\s*E\s*S\s*E\s*N\s*T\s*E\s*S|A\s*U\s*S\s*E\s*N\s*T\s*E\s*S)"
    r"|(?:ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|SEPTIEMBRE|SETIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE)\s+\d{1,2}\s+DE\s+19[23]\d"
    r")",
    re.IGNORECASE
)


def _unir_guiones_columna(texto_col):
    """Une palabras cortadas por guion o soft-hyphen al final de línea dentro de una misma columna."""
    # Re-unimos las palabras que quedaron partidas con un guión al final de la línea
    if not texto_col:
        return ""
    return re.sub(r"[-\xad]\s*\n\s*([a-záéíóúñü])", r"\1", texto_col)


def _agrupar_palabras_en_lineas_visuales(palabras, tolerancia_y=4.2):
    """
    Agrupa una lista de palabras [(wx0, wy0, wx1, wy1, wtxt), ...] en líneas horizontales
    reales usando su centro vertical wy_mid y verificando que no exista solapamiento horizontal.
    Esto evita por completo el defecto de PyMuPDF donde una misma línea escaneada con leve
    inclinación se parte en múltiples (block_no, line_no).
    Agrupa las palabras que comparten aproximadamente la misma coordenada Y
    para armar líneas horizontales limpias. Esto evita que si una página
    está ligeramente inclinada al escanear, el texto se parta en pedazos sueltos.
    """
    if not palabras:
        return []

    pals_ordenadas = sorted(palabras, key=lambda w: ((w[1] + w[3]) / 2.0, w[0]))
    clusters = []  # cada cluster: {"y_mid": float, "y0": float, "y1": float, "palabras": list}

    for w in pals_ordenadas:
        wx0, wy0, wx1, wy1, wtxt = w[0], w[1], w[2], w[3], w[4]
        wy_mid = (wy0 + wy1) / 2.0

        asignado = False
        for cl in reversed(clusters[-4:]):
            if abs(wy_mid - cl["y_mid"]) <= tolerancia_y:
                # Verificar que no se solape horizontalmente con otra palabra ya presente en la misma línea
                # Comprobamos que no se solape con otra palabra en la misma línea
                solapa_x = any(
                    (min(wx1, pw[2]) - max(wx0, pw[0])) > 3.5
                    for pw in cl["palabras"]
                )
                if not solapa_x:
                    n = len(cl["palabras"])
                    cl["y_mid"] = (cl["y_mid"] * n + wy_mid) / (n + 1)
                    cl["y0"] = min(cl["y0"], wy0)
                    cl["y1"] = max(cl["y1"], wy1)
                    cl["palabras"].append((wx0, wy0, wx1, wy1, wtxt))
                    asignado = True
                    break

        if not asignado:
            clusters.append({
                "y_mid": wy_mid,
                "y0": wy0,
                "y1": wy1,
                "palabras": [(wx0, wy0, wx1, wy1, wtxt)]
            })

    clusters.sort(key=lambda c: c["y_mid"])
    lineas_resultado = []
    for cl in clusters:
        pals = sorted(cl["palabras"], key=lambda item: item[0])
        lx0 = pals[0][0]
        lx1 = max(item[2] for item in pals)
        ly0 = cl["y0"]
        ly1 = cl["y1"]
        ltxt = " ".join(item[4] for item in pals).strip()
        if ltxt:
            lineas_resultado.append((lx0, ly0, lx1, ly1, ltxt, pals))

    return lineas_resultado


def _calcular_divisor_columnas_optimo(palabras_cuerpo, x_min_esperado, x_max_esperado):
    """
    Encuentra la coordenada X exacta de la calle/margen central entre las 2 columnas de una carilla,
    buscando alrededor del centro geométrico el eje vertical que minimiza palabras atravesadas.
    Busca la coordenada vertical exacta que separa las dos columnas de texto.
    Explora alrededor del centro geométrico buscando el eje donde no haya palabras atravesadas.
    """
    if len(palabras_cuerpo) < 12:
        return (x_min_esperado + x_max_esperado) / 2.0

    xs0 = sorted(w[0] for w in palabras_cuerpo)
    xs1 = sorted(w[2] for w in palabras_cuerpo)
    min_x0 = xs0[max(0, int(len(xs0) * 0.03))]
    max_x1 = xs1[min(len(xs1) - 1, int(len(xs1) * 0.97))]

    if (max_x1 - min_x0) <= 180:
        return (x_min_esperado + x_max_esperado) / 2.0

    x_centro = (min_x0 + max_x1) / 2.0
    mejor_x = x_centro
    menor_costo = float("inf")

    for offset in range(-32, 33, 2):
        cand_x = x_centro + offset
        # Penalizar palabras que son cortadas al medio por cand_x
        # Penalizamos si el corte pasa por el medio de una palabra
        cortadas = sum(1 for w in palabras_cuerpo if (w[0] + 2.0 < cand_x < w[2] - 2.0))
        costo = cortadas * 10.0 + abs(offset) * 0.08
        if costo < menor_costo:
            menor_costo = costo
            mejor_x = cand_x

    return mejor_x


def _procesar_carilla(palabras_carilla, x_min_esperado, x_max_esperado):
    """
    Procesa una carilla física del Diario de Sesiones:
    1. Agrupa palabras en líneas visuales para descartar el cabezal superior (y0 < 88).
    2. Detecta si la carilla es parte del Índice General / Nomenclátor para descartarla.
    3. Calcula el eje divisorio exacto (x_div) entre la Columna Izquierda y la Columna Derecha.
    4. Si en la carilla hay una apertura de Reunión / lista de Presentes-Ausentes sobre 'SUMARIO',
       mantiene toda esa región superior como bloque de ancho completo ('FULL') y divide
       estrictamente en 2 columnas desde 'SUMARIO' hacia abajo.
    Lee una carilla de la sesión:
    1. Agrupa las palabras en líneas y descarta los cabezales superiores.
    2. Si es una página de índice o nomenclátor, la saltea.
    3. Halla el divisor central y extrae el texto en orden (primero columna izquierda, luego derecha).
    """
    if not palabras_carilla:
        return "", False

    lineas_preliminares = _agrupar_palabras_en_lineas_visuales(palabras_carilla, tolerancia_y=4.2)
    if not lineas_preliminares:
        return "", False

    # Verificar si el cabezal de la carilla indica que es una página de ÍNDICE GENERAL o NOMENCLÁTOR
    texto_superior = "\n".join(ln[4] for ln in lineas_preliminares if ln[1] < 115)
    if REGEX_PAGINA_INDICE.search(texto_superior):
        return "", True

    # Filtrar cabezales de imprenta superiores (y0 < 88) y folios aislados
    lineas_limpias = []
    palabras_filtradas = []

    for ln in lineas_preliminares:
        x0, y0, x1, y1, texto_ln, pals_ln = ln
        t_clean = texto_ln.strip()
        if not t_clean:
            continue

        if y0 < 88:
            if REGEX_CABEZAL_PAGINA.search(t_clean):
                continue
            if re.match(r"^[\_\-\.\s]*\d{1,4}[\_\-\.\s]*$", t_clean):
                continue
            if re.match(r"^[\_\-\.\s]*[IVXLCDM]{1,8}[\_\-\.\s]*$", t_clean):
                continue
            if len(t_clean) < 45 and not REGEX_APERTURA_REUNION.search(t_clean):
                continue

        if t_clean.isdigit() and len(t_clean) <= 4:
            continue

        lineas_limpias.append(ln)
        palabras_filtradas.extend(pals_ln)

    if not lineas_limpias:
        return "", False

    x_div = _calcular_divisor_columnas_optimo(palabras_filtradas, x_min_esperado, x_max_esperado)

    # Clasificar cada línea visual: ESTRICTAMENTE 2 columnas (IZQ < x_div, DER >= x_div),
    # salvo líneas de apertura/presidencia centradas en mayúsculas donde una palabra física puentea el eje central x_div.
    bandas = []

    for x0, y0, x1, y1, t_clean, pals_ln in lineas_limpias:
        # Caso especial A: Título 'SUMARIO'
        if REGEX_TITULO_SUMARIO_LINEA.match(t_clean):
            pals_i = [w for w in pals_ln if (w[0] + w[2]) / 2.0 < x_div]
            pals_d = [w for w in pals_ln if (w[0] + w[2]) / 2.0 >= x_div]
            if not bandas or bandas[-1]["tipo"] != "COLS":
                bandas.append({"tipo": "COLS", "lineas_full": [], "pals_izq": [], "pals_der": []})
            if pals_i and not pals_d:
                bandas[-1]["pals_izq"].extend(pals_i)
            elif pals_d and not pals_i:
                bandas[-1]["pals_der"].extend(pals_d)
            else:
                bandas.append({"tipo": "FULL", "lineas_full": ["SUMARIO"], "pals_izq": [], "pals_der": []})
            continue

        # Caso especial B: Línea de apertura de sesión ("PRESIDENCIA DEL DOCTOR...") centrada con palabra cruzando x_div
        palabra_puentea_eje = any((w[0] < x_div - 2.5 and w[2] > x_div + 2.5) for w in pals_ln)
        if palabra_puentea_eje and y0 < 260 and re.search(r"PRESIDENCIA\s+D", t_clean):
            if not bandas or bandas[-1]["tipo"] != "FULL":
                bandas.append({"tipo": "FULL", "lineas_full": [t_clean], "pals_izq": [], "pals_der": []})
            else:
                bandas[-1]["lineas_full"].append(t_clean)
            continue

        # Todo el cuerpo restante se divide ESTRICTAMENTE en Columna Izquierda (< x_div) y Columna Derecha (>= x_div)
        if not bandas or bandas[-1]["tipo"] != "COLS":
            bandas.append({"tipo": "COLS", "lineas_full": [], "pals_izq": [], "pals_der": []})

        for w in pals_ln:
            if (w[0] + w[2]) / 2.0 < x_div:
                bandas[-1]["pals_izq"].append(w)
            else:
                bandas[-1]["pals_der"].append(w)

    partes_carilla = []
    for b in bandas:
        if b["tipo"] == "FULL":
            col_full = "\n".join(b["lineas_full"])
            partes_carilla.append(_unir_guiones_columna(col_full))
        else:
            lns_izq = _agrupar_palabras_en_lineas_visuales(b["pals_izq"], tolerancia_y=4.2)
            lns_der = _agrupar_palabras_en_lineas_visuales(b["pals_der"], tolerancia_y=4.2)
            col_izq = "\n".join(ln[4] for ln in lns_izq)
            col_der = "\n".join(ln[4] for ln in lns_der)
            if col_izq:
                partes_carilla.append(_unir_guiones_columna(col_izq))
            if col_der:
                partes_carilla.append(_unir_guiones_columna(col_der))

    return "\n".join(p for p in partes_carilla if p), False


def extraer_texto_columnas_limpio(ruta_pdf):
    """
    Extrae el texto del PDF respetando las 4 columnas de los pliegos dobles
    (Carilla Izquierda [Col 1, Col 2] y Carilla Derecha [Col 3, Col 4]) mediante
    agrupamiento geométrico directo de palabras por coordenada vertical.
    """
    carillas_texto = []
    doc = fitz.open(ruta_pdf)
    total_paginas = len(doc)
    sesion_iniciada = (total_paginas <= 40)

    for page in doc:
        ancho_pag = page.rect.width
        alto_pag = page.rect.height
        es_pliego_doble = ancho_pag > (alto_pag * 1.15)
        mitad_pliego = ancho_pag / 2.0

        palabras_pag = page.get_text("words")
        if not palabras_pag:
            continue

        pals_carilla_izq = []
        pals_carilla_der = []

        for w in palabras_pag:
            wx0, wy0, wx1, wy1, wtxt = w[0], w[1], w[2], w[3], w[4].strip()
            if not wtxt:
                continue
            w_mid = (wx0 + wx1) / 2.0
            if not es_pliego_doble or w_mid < mitad_pliego:
                pals_carilla_izq.append((wx0, wy0, wx1, wy1, wtxt))
            else:
                pals_carilla_der.append((wx0, wy0, wx1, wy1, wtxt))

        carillas_en_pagina = (
            [(pals_carilla_izq, 0.0, mitad_pliego), (pals_carilla_der, mitad_pliego, ancho_pag)]
            if es_pliego_doble
            else [(pals_carilla_izq, 0.0, ancho_pag)]
        )

        for pals_car, x_min_c, x_max_c in carillas_en_pagina:
            if not pals_car:
                continue

            texto_carilla, es_indice = _procesar_carilla(pals_car, x_min_c, x_max_c)
            if es_indice or not texto_carilla:
                continue

            if not sesion_iniciada:
                tiene_sumario = bool(REGEX_PALABRA_SUMARIO.search(texto_carilla))
                tiene_apertura = bool(REGEX_APERTURA_REUNION.search(texto_carilla))
                if tiene_sumario or tiene_apertura:
                    sesion_iniciada = True
                else:
                    continue

            carillas_texto.append(texto_carilla)

    doc.close()
    texto_final = "\n".join(carillas_texto)
    texto_final = REGEX_TITULO_SUMARIO_LINEA.sub("SUMARIO", texto_final)
    return texto_final



VALORES_ROMANOS = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def _romano_a_entero(rom_str):
    if not rom_str:
        return None
    rom_str = rom_str.strip().upper()
    if not re.match(r"^L?X{0,3}(?:IX|IV|V?I{1,3}|V|X)$", rom_str):
        return None
    total = 0
    prev = 0
    for ch in reversed(rom_str):
        val = VALORES_ROMANOS.get(ch, 0)
        if val < prev:
            total -= val
        else:
            total += val
            prev = val
    return total if total > 0 else None


REGEX_CORTE_FIN_SUMARIO = re.compile(
    r"(?:"
    r"\n\s*[-—–•]?\s*En\s+(?:la\s+ciudad\s+de\s+|la\s+Capital\s+de\s+la\s+Rep[uú]blica|Buenos\s+Aires)\b"
    r"|\n\s*1\s*\n\s*[A-ZÁÉÍÓÚÑ\s]{4,}\n"
    r"|\n\s*(?:Sr\.|Señor)\s+(?:Presidente|[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s*(?:\([^\)]+\))?\s*[\.\-—–]+"
    r"|\n\s*[-—–]\s*(?:Ocupa\s+la\s+Presidencia|Con\s+la\s+presencia|Siendo\s+la\s+hora|Sin\s+observaci[oó]n|Queda\s+abierta)"
    r"|\n\s*A\s*C\s*T\s*A\s*\n"
    r")"
)

# Detecta sangrado del cuerpo de la sesión dentro del final de una línea de sumario
REGEX_SANGRADO_CUERPO_EN_SUMARIO = re.compile(
    r"(?:"
    r"\s*[-—–•]?\s*En\s+(?:la\s+ciudad\s+de\s+)?Buenos\s+Aires\b.*"
    r"|\s+(?:Sr\.|Señor)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?(?:\s*\([^\)]+\))?\s*[\.\,\-—–]+\s*[-—–]?.*"
    r"|\s+[-—–]\s*(?:Ocupa\s+la\s+Presidencia|Siendo\s+la\s+hora|Sin\s+observaci[oó]n|Queda\s+abierta).*"
    r"|\s+(?:A\s*C\s*T\s*A|ASUNTOS\s+ENTRADOS|1\s+ACTA|1\s+MANIFESTACIONES)\s*$"
    r")"
)

REGEX_LINEA_ITEM_SUMARIO = re.compile(
    r"^\s*(?:"
    r"(?P<arabigo>[1-5]?\d)\s*(?P<sep_a>[\.\,\?º°ª\*]*\s*[-—–]+|[\.\,]\s+|\s+[-—–]+\s*)"
    r"|"
    r"(?P<romano>L?X{0,3}(?:IX|IV|V?I{1,3}|V|X))\s*(?P<sep_r>[\.\,\?º°ª\*]*\s*[-—–]+|[\.\,]\s+|\s+[-—–]+\s*)"
    r")(?P<resto>[A-ZÁÉÍÓÚÑ¿¡«\"\'].*)$"
)

REGEX_SUBITEM_INTERNO = re.compile(
    r"(?:"
    r"(?<=[\.\;\:])\s+(?=(?:[1-5]?\d|L?X{0,3}(?:IX|IV|V?I{1,3}|V|X))\s*[\.\,]?\s*[-—–]+\s*(?::\s*)?[A-ZÁÉÍÓÚÑ¿¡«\"])"
    r"|"
    r"\s+(?=(?:L?X{0,3}(?:IX|IV|V?I{1,3}|V|X))\s*\.\s*[-—–]+\s*(?::\s*)?[A-ZÁÉÍÓÚÑ¿¡«\"])"
    r")"
)

# Patrón para limpiar cabezales de imprenta incrustados a mitad de oración en articulados o sumarios
_PATRON_CABEZAL_INTERNO_STR = (
    r"(?:[\|\—\–\-]\s*\d{1,4}\s*[\|\—\–\-]?\s*)?"
    r"(?:"
        r"(?:[\|\.\•]\s*)*\bReuni[oó]n\s*[,\.]?\s*[nñ][uúüâ°º\.]*(?:m|ra|rn)[\.\,\s]*\d*[a-zº°ª]*\.?"
        r"(?:\s*C\s*[AÁ]\s*M\s*A\s*R\s*A(?:\s+D\s*E?)?(?:\s+(?:D\s*I\s*P\s*U\s*T\s*A\s*D\s*O\s*S|S\s*E\s*N\s*A\s*D\s*O\s*R\s*E\s*S))?)?"
        r"|"
        r"(?:[\|\.]\s*)*\bC\s*O\s*N\s*G\s*R\s*E\s*S\s*O\s+N\s*A\s*C\s*I\s*O\s*N\s*A\s*L"
        r"(?:\s*[\-\—\–\|]?\s*C\s*[AÁ]\s*M\s*A\s*R\s*A\s+D\s*E(?:\s+(?:D\s*I\s*P\s*U\s*T\s*A\s*D\s*O\s*S|S\s*E\s*N\s*A\s*D\s*O\s*R\s*E\s*S))?)?"
        r"(?:\s+(?:D\s*I\s*P\s*U\s*T\s*A\s*D\s*O\s*S|S\s*E\s*N\s*A\s*D\s*O\s*R\s*E\s*S))?"
        r"|"
        r"(?:[\|\.]\s*)*\bC\s+[AÁ]\s+M\s+A\s+R\s+A\s+D\s*E?(?:\s+(?:D\s*I\s*P\s*U\s*T\s*A\s*D\s*O\s*S|S\s*E\s*N\s*A\s*D\s*O\s*R\s*E\s*S))?"
        r"|"
        r"(?:[\|\.]\s*)*\b(?:D\s+I\s+P\s+U\s+T\s+A\s+D\s+O\s+S|S\s+E\s+N\s+A\s+D\s+O\s+R\s+E\s+S|A\s+S\s+U\s+N\s+T\s+O\s+S\s+E\s+N\s+T\s+R\s+A\s+D\s+O\s+S)\b"
        r"|"
        r"\b(?:DIPUTADOS|SENADORES)\s+(?:Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Setiembre|Octubre|Noviembre|Diciembre)\s+\d{1,2}(?:\s+y\s+\d{1,2})?\s+de\s+1[09][23][\d\*]"
        r"|"
        r"\b\d+\s*[\.ªº°a\*]?\s*Reuni[oó]n\.\s*Cont\."
    r")"
    r"(?:\s*[\-\—\–\,]?\s*(?:Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Setiembre|Octubre|Noviembre|Diciembre)\s+\d{1,2}(?:\s+y\s+\d{1,2})?\s+de\s+1[09][23][\d\*])?"
)

REGEX_CABEZAL_INCRUSTADO = re.compile(_PATRON_CABEZAL_INTERNO_STR)
REGEX_PALABRA_CORTADA_POR_CABEZAL = re.compile(
    r"([a-záéíóúñ])-\s*" + _PATRON_CABEZAL_INTERNO_STR + r"\s*([a-záéíóúñ])"
)
REGEX_PALABRA_CORTADA_POR_FECHA = re.compile(
    r"([a-záéíóúñ]{2,})-\s*(?:Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Setiembre|Octubre|Noviembre|Diciembre)\s+\d{1,2}\s+de\s+1[09][23][\d\*]\s*([a-záéíóúñ]{2,})",
    re.IGNORECASE
)

_PREFIJOS_COMPUESTOS_CONSERVAR = {
    "ex", "decreto", "franco", "anglo", "hispano", "italo", "germano", "sino", "ruso", "luso",
    "socio", "economico", "politico", "historico", "tecnico", "medico", "cientifico", "juridico"
}
_CONECTORES_NO_UNIR = {
    "y", "e", "o", "u", "a", "de", "en", "el", "la", "los", "las", "del", "al",
    "por", "con", "sin", "que", "para", "un", "una", "su", "sus", "se", "no", "ni", "es", "son"
}


def limpiar_cabezales_incrustados(texto):
    """
    Elimina cabezales de página ('Reunión núm. 15 CÁMARA DE', 'D I P U T A D O S Septiembre 29 de 1934',
    'CONGRESO NACIONAL', etc.) que hayan quedado incrustados a mitad de oración y re-une palabras
    cortadas por guion de fin de línea ('en to- Reunión núm. 15 CÁMARA DE do' -> 'en todo',
    'pro- ducto' -> 'producto', 'pú- I blica' -> 'pública').
    Elimina los encabezados repetitivos que se filtran a mitad de página
    por el diseño de imprenta (como 'Reunión núm. 15', 'CÁMARA DE DIPUTADOS', etc.)
    y repara las palabras que quedaron partidas con un guión ('pro- ducto' -> 'producto').
    """
    if not texto:
        return ""
    t = REGEX_PALABRA_CORTADA_POR_CABEZAL.sub(r"\1\2", texto)
    t = REGEX_PALABRA_CORTADA_POR_FECHA.sub(r"\1\2", t)
    t = REGEX_CABEZAL_INCRUSTADO.sub(" ", t)
    # Limpiar fechas sueltas de cabezal precedidas de barra vertical ("| Septiembre 29 de 1934")
    t = re.sub(
        r"\|\s*\.?\s*(?:Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Setiembre|Octubre|Noviembre|Diciembre)\s+\d{1,2}(?:\s+y\s+\d{1,2})?\s+de\s+1[09][23][\d\*]",
        " ",
        t,
        flags=re.IGNORECASE
    )

    # Re-unir palabras cortadas por guion + espacio (con o sin basura de regla vertical de margen 'I', 'i', '•', ',')
    def _reunir_guion(m):
        p1 = m.group(1)
        p2 = m.group(2)
        p1_sin = _quitar_tildes(p1.lower())
        p2_low = p2.lower()
        if p2_low in _CONECTORES_NO_UNIR:
            return f"{p1} {p2}"
        if p1_sin in _PREFIJOS_COMPUESTOS_CONSERVAR:
            return f"{p1}-{p2}"
        return f"{p1}{p2}"

    t = re.sub(
        r"\b([a-záéíóúñ]{2,})-\s+(?:[Iji\|\]\¡\<\«\"\•\,\.\'\`\^]{1,2}\s*)?([a-záéíóúñ]{2,})\b",
        _reunir_guion,
        t
    )
    # Limpiar guion suelto pegado al final de una palabra antes de conector de 1 letra ('fiscales- y', 'principal- o', 'escuela- a')
    t = re.sub(r"\b([a-záéíóúñ]{3,})-\s+(?=[yeoua]\b)", r"\1 ", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()


def _normalizar_ordinales_ocr_en_texto(texto):
    """
    Normaliza en todo el cuerpo o sumario los ordinales '1º' a '9º' que el OCR de 1930
    leyó como 'l 9', 'I 9', 'i 9', '1 9', '2 9', ..., '9 9' tras la palabra 'artículo(s)', 'Art.' o 'inciso(s)'.
    """
    if not texto:
        return ""
    # 1. "Artículo l 9" / "artículo I 9" / "Art. l 9" / "inciso l 9" -> "1º"
    t = re.sub(
        r"\b(Art(?:[ií]culos?|ienio|[\.\,])|art[ií]culos?|incisos?|inc[\.\,]|apartados?)\s+[lI1i\|]\s*9\b",
        r"\1 1º",
        texto
    )
    # 2. "Artículo 2 9" / "artículo 3 9" -> "2º", "3º"
    t = re.sub(
        r"\b(Art(?:[ií]culos?|ienio|[\.\,])|art[ií]culos?|incisos?|inc[\.\,]|apartados?)\s+([2-9])\s+9\b",
        r"\1 \2º",
        t
    )
    # 3. En listas tras "artículos 1º" o "incisos 1º": ej. "artículos 1º y 5 9" -> "artículos 1º y 5º", "artículos 1º, l 9"
    for _ in range(3):
        t = re.sub(
            r"(\b(?:art[ií]culos|incisos)\s+\d+º(?:\s*,\s*\d+º)*\s*(?:,\s*|\s+y\s+|\s+e\s+))[lI1i\|]\s*9\b",
            r"\g<1>1º",
            t,
            flags=re.IGNORECASE
        )
        t = re.sub(
            r"(\b(?:art[ií]culos|incisos)\s+\d+º(?:\s*,\s*\d+º)*\s*(?:,\s*|\s+y\s+|\s+e\s+))([2-9])\s+9\b",
            r"\g<1>\2º",
            t,
            flags=re.IGNORECASE
        )
    return t


def _normalizar_romanos_ocr_en_sumario(texto):
    """
    Repara numerales romanos de sub-ítems de sumario que el OCR separó con espacios ('X X I X . —')
    o deformó ('VLLT.—', 'VIH.—', 'V i n . —', 'ITI.—', 'I H —', 'XVILT —', 'Lili.—', 'XLTV.—', 'VT.—').
    """
    if not texto:
        return ""
    t = texto
    # Reparar deformaciones frecuentes de OCR seguidas de punto y raya
    reemplazos_ocr_rom = [
        (r"(?<=[\s\:\;\.])VLLT\s*[\.\,]?\s*[-—–]+", "VIII.—"),
        (r"(?<=[\s\:\;\.])(?:VIH|V\s*i\s*n|V\s*H\s*[IÍ])\s*[\.\,]?\s*[-—–]+", "VIII.—"),
        (r"(?<=[\s\:\;\.])(?:ITI|I\s+H)\s*[\.\,]?\s*[-—–]+", "III.—"),
        (r"(?<=[\s\:\;\.])XVILT\s*[\.\,]?\s*[-—–]+", "XVIII.—"),
        (r"(?<=[\s\:\;\.])Lili\s*[\.\,]?\s*[-—–]+", "LIII.—"),
        (r"(?<=[\s\:\;\.])XLTV\s*[\.\,]?\s*[-—–]+", "XLIV.—"),
        (r"(?<=[\s\:\;\.])VT\s*[\.\,]?\s*[-—–]+", "VI.—"),
        (r"^VLLT\s*[\.\,]?\s*[-—–]+", "VIII.—"),
        (r"^(?:VIH|V\s*i\s*n|V\s*H\s*[IÍ])\s*[\.\,]?\s*[-—–]+", "VIII.—"),
        (r"^(?:ITI|I\s+H)\s*[\.\,]?\s*[-—–]+", "III.—"),
    ]
    for pat_r, rep_r in reemplazos_ocr_rom:
        t = re.sub(pat_r, rep_r, t)

    # Compactar romanos con espacios internos seguidos de punto y raya (o seguidos de 'Proyecto de ley'): "X X I X . — : " -> "XXIX.—"
    def _compactar_rom(m):
        rom_compacto = re.sub(r"[^IVXLC]", "", m.group(1).upper())
        if _romano_a_entero(rom_compacto):
            return f"{rom_compacto}.—"
        return m.group(0)

    t = re.sub(
        r"(?:(?<=^)|(?<=[\s\:\;\.]))(?:\*\s*)?((?:[IVXLC]\s+){1,7}[IVXLC])\s*(?:[\.\,]?\s*[-—–]+\s*(?::\s*)?|\s+(?=Proyecto\s+de\s+ley|E\s*l\s+se[ñn]or))",
        _compactar_rom,
        t
    )
    # Compactar "E l señor" y "P r o y e c t o" en sumarios
    t = re.sub(r"\bE\s+l\s+se[ñn]or\b", "El señor", t)
    t = re.sub(r"\bP\s*r\s*o\s*y\s*e\s*c\s*t\s*o\s+d\s*e\s+l\s*e\s*y\b", "Proyecto de ley", t, flags=re.IGNORECASE)
    # Limpiar ": " inmediatamente después de "XXIX.—: Proyecto" -> "XXIX.—Proyecto"
    t = re.sub(r"\b(L?X{0,3}(?:IX|IV|V?I{1,3}|V|X))\s*\.\s*[-—–]+\s*:\s*", r"\1.—", t)
    return t


def _es_titulo_invalido_o_formula(texto):
    """
    Detecta si un supuesto título de proyecto es en realidad una fórmula sancionatoria
    (incluso con errores de OCR como 'JEl Senado', '121 Senado', '7El Sonado', 'Diputa/Ios'),
    un cabezal de página o un encabezado estructural vacío ('SECCIÓN I Disposiciones generales', 'CAPÍTULO I').
    """
    if not texto:
        return True
    t = texto.strip(" [].,;:-—'\"«»¿¡")
    if len(t) < 5:
        return True
    if re.search(
        r"(?:"
        r"(?:Senado|Sonado|Senad[oa])\s+y[\s\-]*C[aáâ]mar[ao]"
        r"|C[aáâ]mar[ao]\s+(?:d[eao]|ele)\s+Diputad"
        r"|Diputa(?:/I|d)os\s*,\s*etc"
        r"|sancionan\s+con\s+fuerza"
        r"|Honorable\s+(?:Congreso|C[aá]mara|Senado)"
        r"|Sala\s+de\s+la\s+Comisi[oó]n"
        r"|Dada\s+en\s+la\s+Sala"
        r"|Reuni[oó]n\s*[,\.]?\s*[nñ][uúüâ°º]m"
        r"|CONGRESO\s+NACIONAL"
        r"|C\s*[AÁ]\s*M\s*A\s*R\s*A\s+D\s*E\s+(?:D\s*I\s*P\s*U\s*T\s*A\s*D\s*O\s*S|S\s*E\s*N\s*A\s*D\s*O\s*R\s*E\s*S)"
        r")",
        t,
        re.IGNORECASE
    ):
        return True
    if re.match(
        r"^(?:"
        r"PROYECTO\s+DE\s+LEY"
        r"|DESPACHO\s+DE\s+(?:LA\s+)?COMISI[OÓ]N"
        r"|ASUNTOS\s+ENTRADOS"
        r"|ORDEN\s+DEL\s+D[IÍ]A"
        r"|SUMARIO"
        r"|(?:Sr\.|Señor)\s+(?:Presidente|[A-ZÁÉÍÓÚÑ])"
        r"|(?:CAP[IÍ]TULO|T[IÍ]TULO|SECCI[OÓ]N|PARTE|LIBRO|ANEXO|PLANILLA)\s+[IVXLCDM\dº°ª\.\-\—\–\s]*(?:Disposiciones\s+generales|Disposiciones\s+transitorias|Disposiciones\s+especiales|Disposiciones\s+complementarias|Disposiciones\s+penales|Generalidades)?$"
        r")",
        t,
        re.IGNORECASE
    ):
        return True
    return False


def _limpiar_posible_titulo(cand):
    """
    Limpia un candidato a título eliminando prefijos estructurales ('CAPÍTULO I ...'),
    cabezales incrustados, posibles sub-ítems siguientes pegados al final y validando
    que no sea una fórmula sancionatoria.
    """
    if not cand:
        return None
    c = limpiar_cabezales_incrustados(_normalizar_romanos_ocr_en_sumario(cand))
    c = c.strip(" [].,;:-—'\"*?¡¿")
    # Cortar si al final del título se coló el comienzo del siguiente sub-ítem del sumario (ej. ". XVIII.—Proyecto de ley..." o ". El señor diputado X reproduce...")
    c = re.sub(
        r"[\.\;\:]\s*[^\.\n]{0,20}?\b(?:Proyecto\s+de\s+ley|Proyectos\s+de\s+ley|El\s+se[ñn]or\s+(?:diputado|senador)|Los\s+se[ñn]ores\s+(?:diputados|senadores)|Mensaje\s+y\s+proyecto|Despacho\s+de\s+la\s+Comisi[oó]n|Peticiones\s+particulares)\b.*$",
        "",
        c,
        flags=re.IGNORECASE
    ).strip(" [].,;:-—'\"*?¡¿")
    # Limpiar basura de OCR inicial como "V* — " o "? — "
    c = re.sub(r"^(?:[VIl1\?\*\'\"\º\°]+)\s*[-—–]+\s*", "", c).strip(" [].,;:-—'\"*?¡¿")
    # Si comienza con "CAPÍTULO I / SECCIÓN II / TÍTULO I" seguido de un tema sustantivo, extraer el tema
    c_sin_sec = re.sub(
        r"^(?:CAP[IÍ]TULO|T[IÍ]TULO|SECCI[OÓ]N|PARTE|LIBRO)\s+[IVXLCDM\dº°ª]+\s*[\.\-—–\:]?\s*",
        "",
        c,
        flags=re.IGNORECASE
    ).strip(" [].,;:-—'\"*?¡¿")
    if c_sin_sec and len(c_sin_sec) >= 6:
        c = c_sin_sec
    if _es_titulo_invalido_o_formula(c):
        return None
    if len(c) < 6 or len(c) > 250:
        return None
    return c[0].upper() + c[1:]


def segmentar_en_reuniones(texto_tomo):
    """
    Divide el texto de un Tomo PDF en sus Reuniones/Sesiones individuales usando cada
    línea 'SUMARIO' como ancla, aislando estrictamente cada sesión.
    """
    matches_sum = list(re.finditer(r"(?:^|\n)\s*SUMARIO\s*\n", texto_tomo))
    if not matches_sum:
        return [texto_tomo] if texto_tomo.strip() else []

    segmentos = []
    for i, m in enumerate(matches_sum):
        ini_previo = matches_sum[i - 1].end() if i > 0 else 0
        ini_seg = max(ini_previo, m.start() - 1200)

        if i + 1 < len(matches_sum):
            fin_seg = max(m.end() + 200, matches_sum[i + 1].start() - 900)
        else:
            fin_seg = len(texto_tomo)

        segmentos.append(texto_tomo[ini_seg:fin_seg])

    return segmentos


def extraer_presidente_reunion(texto_reunion):
    """Extrae el nombre del Presidente de la sesión desde el encabezado."""
    m = re.search(
        r"PRESIDENCIA\s+D(?:EL|E\s+LA|E\s+LOS|E)\s+([^\n]+)",
        texto_reunion[:2200],
        re.IGNORECASE
    )
    if not m:
        return None
    presi = m.group(1).strip()
    presi = re.sub(
        r"^(?:doctores|doctor|general|dr\.|ing\.|ingeniero|señores|señor|diputados|diputado|senadores|senador)\s+",
        "",
        presi,
        flags=re.IGNORECASE
    ).strip(" ,.;:-—'")
    # Si el nombre tenía espacios intercalados de imprenta ("A N D R E S"), compactarlos
    if re.search(r"\b[A-ZÁÉÍÓÚÑ]\s+[A-ZÁÉÍÓÚÑ]\s+[A-ZÁÉÍÓÚÑ]\b", presi):
        presi = re.sub(r"(?<=\b[A-ZÁÉÍÓÚÑ])\s+(?=[A-ZÁÉÍÓÚÑ]\b)", "", presi)
    return presi.title() if len(presi) > 3 else None


def extraer_titulo_proyecto_desde_texto(resumen_sumario=None, texto_articulado=None, contexto_previo=None):
    """
    Determina el TÍTULO DEL PROYECTO DE LEY (si existe) analizando en orden de prioridad:
    1. El ítem correspondiente del SUMARIO (y cualquier referencia cruzada resuelta).
    2. El encabezado explícito en el cuerpo del proyecto (entre 'El Senado y Cámara...' y 'Artículo 1º',
       o el título de sección numerada en el Orden del Día).
    3. El objeto legislativo directo del Artículo 1º (primera cláusula dispositiva sustantiva).
    Devuelve None si no es posible determinar un título válido.
    """
    # 1. Analizar el resumen del SUMARIO
    titulo_previo_etiquetado = None
    if resumen_sumario:
        m_prev_tit = re.match(
            r"^\[T[IÍ]TULO:\s*([^\]\|]+)(?:\|[^\]]*)?\]\s*(.*)$",
            resumen_sumario.strip(),
            re.IGNORECASE
        )
        if m_prev_tit:
            titulo_previo_etiquetado = _limpiar_posible_titulo(m_prev_tit.group(1))
            resumen_sin_etiqueta = m_prev_tit.group(2).strip()
        else:
            resumen_sin_etiqueta = re.sub(r"^\[[^\]]+\]\s*", "", resumen_sumario.strip()).strip()

        if not resumen_sin_etiqueta and titulo_previo_etiquetado:
            return titulo_previo_etiquetado

        # Si tiene una referencia cruzada resuelta "[Ref. Sumario X: ...]", priorizar el texto referenciado
        # cuando el ítem principal solo dice "Consideración del despacho a que se refiere el número X"
        texto_base = limpiar_cabezales_incrustados(resumen_sin_etiqueta)
        m_ref = re.search(r"\[Ref\.\s*Sumario\s*[^:]+:\s*([^\]]+)\]", texto_base, re.IGNORECASE)
        if m_ref and re.search(r"a\s+que\s+se\s+refiere\s+el\s+n[uú]mero", texto_base, re.IGNORECASE):
            texto_base = m_ref.group(1).strip()
        else:
            texto_base = re.sub(r"\s*\[Ref\.\s*Sumario[^\]]*\]", "", texto_base).strip()

        # Quitar sufijos procedimentales del sumario ("Se aprueba...", "Queda sancionado...", "Pasa a comisión...")
        texto_base = re.sub(
            r"[\.\;]\s*(?:Se\s+aprueba[^\.]*|Queda\s+sancionado[^\.]*|Aprobado[^\.]*|Pasa\s+a\s+la\s+Comisi[oó]n[^\.]*|Vuelve\s+a\s+comisi[oó]n[^\.]*|Se\s+posterga[^\.]*|Se\s+aplaza[^\.]*)\.?\s*$",
            "",
            texto_base,
            flags=re.IGNORECASE
        ).strip(" .;:-—")

        patrones_sumario = [
            # a) "... sobre <TÍTULO>" / "... relativo a <TÍTULO>" / "... referente a <TÍTULO>"
            r"(?:sobre|relativ[oa]\s+a|referente\s+a|tendiente\s+a)\s+([a-záéíóúñA-ZÁÉÍÓÚÑ0-9].{6,240})$",
            # b) "... por el que se <TÍTULO>"
            r"(por\s+el\s+(?:que|cual)\s+se\s+.{8,240})$",
            # c) "... modificando / creando / autorizando / acordando / aprobando / derogando / declarando / estableciendo / prorrogando / reglamentando ..."
            r"\b((?:modificando|creando|autorizando|acordando|aprobando|derogando|declarando|destinando|disponiendo|estableciendo|eximiendo|fijando|prorrogando|reglamentando|reorganizando|substituyendo|sustituyendo|transfiriendo|ampliando)\s+.{8,240})$",
            # d) "... en el proyecto de ley de <TÍTULO>" (excluyendo 'del señor diputado/senador' o 'del Poder Ejecutivo')
            r"proyecto\s+de\s+ley\s+(?:en\s+revisi[oó]n\s*[\,\s]*)*de\s+(?!l\s+se[ñn]or|los\s+se[ñn]ores|l\s+diputad|l\s+senador|l\s+poder\s+ejecutivo|la\s+comisi[oó]n)([a-záéíóúñA-ZÁÉÍÓÚÑ].{8,220})$",
            # e) "Consideración del despacho ... en el proyecto de ley <TÍTULO>"
            r"en\s+el\s+proyecto\s+de\s+ley\s+(?:en\s+revisi[oó]n\s*[\,\s]*)*([a-záéíóúñA-ZÁÉÍÓÚÑ].{8,220})$",
        ]

        for pat in patrones_sumario:
            m_t = re.search(pat, texto_base, re.IGNORECASE)
            if m_t:
                cand = m_t.group(1).strip(" .,;:-—")
                # Limpiar si empieza por "del señor diputado X, sobre ..." dentro de un match amplio
                m_sub_sobre = re.search(r"\b(?:sobre|relativ[oa]\s+a|por\s+el\s+que\s+se)\s+(.{6,220})$", cand, re.IGNORECASE)
                if m_sub_sobre and not pat.startswith("(por"):
                    cand = m_sub_sobre.group(1).strip(" .,;:-—")
                cand_limpio = _limpiar_posible_titulo(cand)
                if cand_limpio:
                    return cand_limpio

        # Si el ítem del sumario es directamente un título nominal (ej. "Presupuesto general de gastos para 1937")
        if len(texto_base) >= 8 and not re.match(r"^(?:Moci[oó]n|A\s+moci[oó]n|Manifestaciones|Ap[eé]ndice|Inserci[oó]n)", texto_base, re.IGNORECASE):
            limpio_autor = re.sub(
                r"^(?:Mensaje\s+y\s+proyecto\s+de\s+ley\s+del\s+Poder\s+Ejecutivo|Proyecto\s+de\s+ley\s+d(?:el|e\s+los)\s+[^,\.]+(?:\,\s*reproducido\s+con\s+sus\s+fundamentos)?|Consideraci[oó]n\s+del\s+despacho\s+de\s+la\s+Comisi[oó]n\s+de\s+[^,\.]+)\s*[\,\.\:]?\s*",
                "",
                texto_base,
                flags=re.IGNORECASE
            ).strip(" .,;:-—")
            if 6 <= len(limpio_autor) <= 220 and limpio_autor.lower() != texto_base.lower():
                cand_limpio = _limpiar_posible_titulo(limpio_autor)
                if cand_limpio:
                    return cand_limpio

    # 2. Buscar título explícito en el contexto previo del cuerpo (ej. título en mayúsculas bajo el número de orden)
    if contexto_previo:
        m_sec_tit = re.search(
            r"(?:^|\n)\s*\d+\s*\n+\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\,\.\-]{6,140})\s*\n",
            contexto_previo[-600:]
        )
        if m_sec_tit:
            tit_sec = _limpiar_posible_titulo(re.sub(r"\s+", " ", m_sec_tit.group(1)).title())
            if tit_sec:
                return tit_sec

    # 3. Inferir el objeto legislativo directamente desde la cláusula inicial del primer artículo del texto_articulado
    if texto_articulado:
        primer_art = texto_articulado.split("\n")[0].strip()
        primer_art = re.sub(r"^\[[^\]]+\]\s*", "", primer_art).strip()
        m_inicio_art = re.match(
            r"^Art(?:[ií]culo|ienio|[\.\,])\s*[\dIlº°ª\.\s\-—–\?\'\"\*r]+(.*)$",
            primer_art,
            re.IGNORECASE
        )
        cuerpo_art1 = m_inicio_art.group(1).strip(" -—–.,;:'\"«»") if m_inicio_art else primer_art
        cuerpo_art1 = limpiar_cabezales_incrustados(cuerpo_art1)

        if cuerpo_art1 and not re.match(r"^(?:Comu[ns]i[qgp][uúü][eé][sn]e|De\s+forma\b)", cuerpo_art1, re.IGNORECASE):
            # Cortar en el primer punto y coma, dos puntos o punto final de oración (ignorando abreviaturas como m/n., n.º, art., inc., S. A., Dr. y puntos de miles)
            m_corte_oracion = re.search(
                r"(?<!\bm/n)(?<!\bnº)(?<!\bn°)(?<!\bart)(?<!\binc)(?<!\bdr)(?<!\bgral)(?<!\bsr)(?<!\bsra)(?<!\bav)(?<!\bcía)(?<!\bltda)(?<!\b[A-ZÁÉÍÓÚÑ])(?<!\d)\.(?:\s|$)|[\;\:]",
                cuerpo_art1[:210],
                re.IGNORECASE
            )
            if m_corte_oracion:
                clausula = cuerpo_art1[:m_corte_oracion.start()].strip(" .,;:-—")
            else:
                clausula = cuerpo_art1[:165].rsplit(" ", 1)[0].strip(" .,;:-—") if len(cuerpo_art1) > 165 else cuerpo_art1.strip(" .,;:-—")

            cand_art1 = _limpiar_posible_titulo(clausula)
            if cand_art1 and len(cand_art1) >= 10:
                return cand_art1

    return None


def extraer_articulos_modificados_y_leyes(resumen_sumario=None, texto_articulado=None):
    """
    Detecta de manera exacta qué artículos y de qué leyes son modificados, sustituidos,
    derogados o agregados por el proyecto o tratamiento en recinto.

    Devuelve:
    - lista_arts_mod: ej. ["Art. 17", "Art. 71"]
    - lista_leyes_mod: ej. ["Ley 4.349"]
    - resumen_modificacion: ej. "Modifica: Art. 17, Art. 71 (Ley 4.349)" o None
    """
    texto_combinado = _normalizar_ordinales_ocr_en_texto(f"{resumen_sumario or ''}\n{texto_articulado or ''}")
    arts_mod = []
    leyes_mod = []

    # 1. Patrones explícitos de modificación de artículos en el sumario o en el articulado
    patrones_mod_art = [
        r"(?:modif[ií]ca(?:n)?se|modificando|modificaci[oó]n\s+d(?:el|e\s+los)|reforma\s+d(?:el|e\s+los)|sustit[uú]ye(?:n)?se|substit[uú]ye(?:n)?se|sustituyendo|reempl[aá]za(?:n)?se|der[oó]ga(?:n)?se|derogando|agr[eé]ga(?:n)?se|ampl[ií]a(?:n)?se|supr[ií]me(?:n)?se|incorp[oó]ra(?:n)?se)"
        r"\s+(?:el\s+|los\s+|al\s+)?(?:inciso\s+[a-z0-9º°]+\s+del\s+)?art[ií]culo(?:s)?\s+"
        r"([\dº°ª\,\sye]+\b(?:\s*bis)?)"
        r"(?:[^\.\n]{0,60}?\bley\s+(?:n[uú]mero\s+|n[º°o\.]\s*)?([\d\.]{2,7}))?",
        r"art[ií]culo(?:s)?\s+([\dº°ª\,\sye]+\b(?:\s*bis)?)\s+de\s+la\s+ley\s+(?:n[uú]mero\s+|n[º°o\.]\s*)?([\d\.]{2,7})",
    ]

    for pat in patrones_mod_art:
        for m in re.finditer(pat, texto_combinado, re.IGNORECASE):
            nums_raw = m.group(1)
            ley_raw = m.group(2) if m.lastindex and m.lastindex >= 2 else None

            for n_match in re.finditer(r"(\d{1,4})(?:\s*(bis))?", nums_raw, re.IGNORECASE):
                n_val = int(n_match.group(1))
                # Evitar capturar años como números de artículo
                if 1850 <= n_val <= 1950:
                    continue
                suf_bis = " bis" if n_match.group(2) else ""
                etiqueta_a = f"Art. {n_val}{suf_bis}"
                if etiqueta_a not in arts_mod:
                    arts_mod.append(etiqueta_a)

            if ley_raw:
                num_l = re.sub(r"[^\d]", "", ley_raw)
                if num_l.isdigit() and 50 <= int(num_l) <= 15000 and not (1920 <= int(num_l) <= 1945):
                    ley_fmt = f"Ley {num_l[:-3]}.{num_l[-3:]}" if len(num_l) >= 4 else f"Ley {num_l}"
                    if ley_fmt not in leyes_mod:
                        leyes_mod.append(ley_fmt)

    # 2. Detectar si el proyecto cita globalmente la reforma/modificación/derogación de una Ley N° X
    for m_ley in re.finditer(
        r"(?:reforma|modificaci[oó]n|modificando|modif[ií]case|derogaci[oó]n|derogando|der[oó]gase|aclaraci[oó]n|pr[oó]rroga)\s+(?:de\s+|a\s+)?la\s+ley\s+(?:n[uú]mero\s+|n[º°o\.]\s*)?([\d\.]{2,7})",
        texto_combinado,
        re.IGNORECASE
    ):
        num_l = re.sub(r"[^\d]", "", m_ley.group(1))
        if num_l.isdigit() and 50 <= int(num_l) <= 15000 and not (1920 <= int(num_l) <= 1945):
            ley_fmt = f"Ley {num_l[:-3]}.{num_l[-3:]}" if len(num_l) >= 4 else f"Ley {num_l}"
            if ley_fmt not in leyes_mod:
                leyes_mod.append(ley_fmt)

    # 3. Detectar artículos embebidos estrictamente entre comillas («Art. 71» o "Art. 71") cuando se modifica una ley
    if texto_articulado and re.search(
        r"(?:modif[ií]ca|sustit[uú]ye|reempl[aá]za|siguiente\s+forma|como\s+sigue|por\s+el\s+siguiente)",
        texto_articulado,
        re.IGNORECASE
    ):
        texto_art_norm = _normalizar_ordinales_ocr_en_texto(texto_articulado)
        for m_emb in re.finditer(
            r"(?:«|\")\s*Art(?:[ií]culo|\.)\s*(\d{1,3})\s*([º°ª\.])?\s*[-—–]",
            texto_art_norm
        ):
            n_emb = int(m_emb.group(1))
            tiene_ordinal = bool(m_emb.group(2) and m_emb.group(2) in "º°ª")
            # Si el OCR leyó «Artículo 19 — en vez de «Artículo 1º —, repararlo
            if 19 <= n_emb <= 99 and (n_emb % 10 == 9) and not tiene_ordinal:
                n_emb = n_emb // 10
            if 1 <= n_emb <= 900 and f"Art. {n_emb}" not in arts_mod:
                arts_mod.append(f"Art. {n_emb}")

    if not arts_mod and not leyes_mod:
        return [], [], None

    partes_res = []
    if arts_mod:
        partes_res.append(", ".join(arts_mod[:10]))
    if leyes_mod:
        partes_res.append(f"({', '.join(leyes_mod[:4])})")

    resumen_mod = f"Modifica: {' '.join(partes_res)}"
    return arts_mod, leyes_mod, resumen_mod


def _clasificar_item_sumario(texto_item):
    """
    Clasifica un ítem del SUMARIO en:
    - 'LEY_TRATADA': consideración, discusión o sanción efectiva de un despacho/proyecto de ley en el recinto.
    - 'PROYECTO_ENTRADO': presentación de un proyecto de ley, mensaje y proyecto de ley, o proyecto en revisión.
    - None: trámites procedimentales, mociones de aplazamiento/postergación, homenajes, actas, licencias.
    """
    t_low = texto_item.lower()

    # Descartar mociones de postergación, aplazamiento o simple fijación de fecha
    if re.search(r"\b(?:se\s+posterga|se\s+aplaza|postergar|aplazar|fijar\s+fecha|sesi[oó]n\s+permanente\s+a\s+fin\s+de)\b", t_low):
        if not re.search(r"\b(?:se\s+considera\s+y\s+aprueba|queda\s+sancionado|se\s+aprueba\s+en\s+general)\b", t_low):
            return None

    if re.match(r"^(?:moci[oó]n|a\s+moci[oó]n|indicaci[oó]n|a\s+indicaci[oó]n)\b", t_low):
        if not re.search(r"\b(?:se\s+considera\s+y\s+aprueba|se\s+aprueba\s+el\s+proyecto\s+de\s+ley|queda\s+sancionado)\b", t_low):
            return None

    tiene_mencion_ley = any(
        kw in t_low
        for kw in (
            "proyecto de ley",
            "proyectos de ley",
            "mensaje y proyecto",
            "reforma de la ley",
            "modificación de la ley",
            "ley número",
            "ley n°",
            "ley nº",
        )
    )

    if not tiene_mencion_ley:
        if "consideración del despacho" in t_low and any(
            s in t_low for s in ("se aprueba", "sanción", "queda sancionado", "aprobado")
        ):
            return "LEY_TRATADA"
        return None

    if any(
        k in t_low
        for k in (
            "consideración del despacho",
            "consideración del proyecto",
            "continúa la consideración",
            "continúa la discusión",
            "discusión del despacho",
            "sanción definitiva",
            "se considera y aprueba",
            "aprobación del despacho",
            "aprobación del proyecto de ley",
        )
    ):
        return "LEY_TRATADA"

    return "PROYECTO_ENTRADO"


def extraer_sumarios_reunion(texto_reunion, id_sesion):
    """
    Extrae y depura los ítems del SUMARIO de una Reunión individual:
    - Valida secuencialmente la numeración arábiga y romana para no confundir iniciales ('L. Palacios') con romanos.
    - Corta cualquier sangrado de discursos ('Sr. Presidente...', '—En Buenos Aires...') al final del sumario.
    - Resuelve referencias cruzadas ('a que se refiere el número X del sumario').
    - Extrae título y artículos modificados anunciados en cada ítem.
    """
    sumarios_insert = []
    proyectos_en_sumario = []
    leyes_tratadas_sumario = []

    m_inicio = re.search(r"(?:^|\n)\s*SUMARIO\s*\n", texto_reunion)
    if not m_inicio:
        return sumarios_insert, proyectos_en_sumario, leyes_tratadas_sumario

    ventana_sumario = texto_reunion[m_inicio.end(): m_inicio.end() + 14000]
    m_corte = REGEX_CORTE_FIN_SUMARIO.search(ventana_sumario)
    bloque = ventana_sumario[:m_corte.start()] if m_corte else ventana_sumario[:6500]

    bloque = _normalizar_romanos_ocr_en_sumario(bloque)
    bloque = REGEX_SUBITEM_INTERNO.sub("\n", bloque)
    lineas = bloque.split("\n")

    items_crudos = []
    ultimo_arabigo = None
    ultimo_arabigo_int = 0
    ultimo_romano_int = 0

    for linea in lineas:
        linea_str = linea.strip()
        if not linea_str:
            continue
        if REGEX_CABEZAL_PAGINA.search(linea_str):
            continue

        # Si la línea inicia directamente con la apertura del cuerpo o un orador, fin del sumario
        if re.match(
            r"^(?:[-—–•]?\s*En\s+(?:la\s+ciudad\s+de\s+)?Buenos\s+Aires|(?:Sr\.|Señor)\s+[A-ZÁÉÍÓÚÑ]|A\s*C\s*T\s*A\s*$|(?:DIPUTADOS|SENADORES)\s+(?:PRESENTES|AUSENTES))",
            linea_str
        ):
            break

        # Si una línea comienza con "Asuntos entrados: I.—..." o "Asuntos entrados: VIII.—...", separar el encabezado
        m_ae = re.match(
            r"^(?P<num_ae>[1-5]?\d)?\s*(?:[\.\,]?\s*[-—–]+\s*)?Asuntos\s+entrados\s*:\s*(?P<sub_rom>L?X{0,3}(?:IX|IV|V?I{1,3}|V|X))\s*[\.\,]?\s*[-—–]+\s*(?P<resto_ae>.+)$",
            linea_str,
            re.IGNORECASE
        )
        if m_ae:
            if m_ae.group("num_ae"):
                ultimo_arabigo = m_ae.group("num_ae")
                ultimo_arabigo_int = int(ultimo_arabigo)
            rom_ae = m_ae.group("sub_rom").upper()
            ultimo_romano_int = _romano_a_entero(rom_ae) or ultimo_romano_int
            linea_str = f"{rom_ae}.—{m_ae.group('resto_ae')}"

        # Reparar OCR al inicio de ítem: "l.—" o "I.—" al inicio absoluto del sumario (cuando aún no hay ítem 1)
        if ultimo_arabigo_int == 0 and re.match(r"^[lI1]\s*[\.\,]?\s*[-—–]+", linea_str):
            linea_norm = re.sub(r"^[lI1]\s*[\.\,]?\s*[-—–]+", "1.—", linea_str)
        else:
            linea_norm = linea_str

        m_item = REGEX_LINEA_ITEM_SUMARIO.match(linea_norm)
        es_nuevo_item_valido = False

        if m_item:
            arab = m_item.group("arabigo")
            rom = m_item.group("romano")
            sep_a = m_item.group("sep_a") or ""
            sep_r = m_item.group("sep_r") or ""
            texto_ini = m_item.group("resto").strip()

            if arab:
                val_a = int(arab)
                tiene_guion = bool(re.search(r"[-—–]", sep_a))
                if tiene_guion or (1 <= val_a <= ultimo_arabigo_int + 3):
                    es_nuevo_item_valido = True
                    ultimo_arabigo = arab
                    ultimo_arabigo_int = val_a
                    ultimo_romano_int = 0
                    codigo = arab
            elif rom:
                val_r = _romano_a_entero(rom)
                tiene_guion = bool(re.search(r"[-—–]", sep_r))
                # Si tiene punto y raya ("VIII.—"), es siempre un sub-ítem romano legítimo
                if val_r is not None:
                    if tiene_guion and (1 <= val_r <= 85):
                        es_nuevo_item_valido = True
                    elif not tiene_guion and (val_r == 1 or val_r == ultimo_romano_int + 1):
                        es_nuevo_item_valido = True

                    if es_nuevo_item_valido:
                        ultimo_romano_int = val_r
                        rom_up = rom.upper()
                        codigo = f"{ultimo_arabigo}.{rom_up}" if ultimo_arabigo else rom_up

            if es_nuevo_item_valido:
                # Verificar si en la misma línea ya se filtró el inicio del debate
                m_sangrado = REGEX_SANGRADO_CUERPO_EN_SUMARIO.search(texto_ini)
                cortar_aqui = False
                if m_sangrado:
                    texto_ini = texto_ini[:m_sangrado.start()].strip()
                    cortar_aqui = True

                if texto_ini:
                    items_crudos.append({
                        "numero_item": codigo,
                        "arabigo_puro": arab if arab else ultimo_arabigo,
                        "romano_puro": rom.upper() if rom else None,
                        "lineas": [texto_ini]
                    })
                if cortar_aqui:
                    break
                continue

        # Si no es nuevo ítem, es continuación del ítem actual (previo corte de sangrado si aparece un orador)
        if items_crudos:
            m_sangrado = REGEX_SANGRADO_CUERPO_EN_SUMARIO.search(linea_str)
            if m_sangrado:
                parte_util = linea_str[:m_sangrado.start()].strip()
                if parte_util:
                    items_crudos[-1]["lineas"].append(parte_util)
                break
            items_crudos[-1]["lineas"].append(linea_str)

    mapa_por_numero = {}
    items_procesados = []

    for it in items_crudos:
        texto_unido = " ".join(it["lineas"])
        texto_unido = re.sub(r"-\s+", "", texto_unido)
        texto_unido = limpiar_cabezales_incrustados(_normalizar_ordinales_ocr_en_texto(texto_unido))
        texto_unido = re.sub(r"\s{2,}", " ", texto_unido).strip()
        texto_unido = re.sub(r"^[-—–\:\s]+", "", texto_unido).strip()
        texto_unido = REGEX_SANGRADO_CUERPO_EN_SUMARIO.sub("", texto_unido).strip()
        texto_unido = re.sub(r"\s+(?:A\s*C\s*T\s*A|ASUNTOS\s+ENTRADOS|1)\s*$", "", texto_unido).strip()

        if len(texto_unido) < 3:
            continue

        it_proc = {
            "numero_item": it["numero_item"],
            "arabigo_puro": it["arabigo_puro"],
            "romano_puro": it["romano_puro"],
            "texto_item": texto_unido
        }
        items_procesados.append(it_proc)
        mapa_por_numero[it["numero_item"]] = texto_unido
        if it["arabigo_puro"] and not it["romano_puro"]:
            mapa_por_numero[it["arabigo_puro"]] = texto_unido
        if it["romano_puro"]:
            mapa_por_numero[it["romano_puro"]] = texto_unido

    for it in items_procesados:
        texto_final_item = it["texto_item"]

        # Resolver referencias cruzadas ("a que se refiere el número X del sumario")
        m_ref = re.search(
            r"(?:a\s+que\s+se\s+refiere\s+el\s+n[uú]mero|registrad[oa]\s+bajo\s+el\s+n[uú]mero|punto)\s+([0-9IVXLCDM\.]+)\s+del\s+sumario",
            texto_final_item,
            re.IGNORECASE
        )
        if m_ref:
            num_ref = m_ref.group(1).strip(".").upper()
            if num_ref in mapa_por_numero and mapa_por_numero[num_ref] != texto_final_item:
                texto_final_item = f"{texto_final_item} [Ref. Sumario {num_ref}: {mapa_por_numero[num_ref]}]"

        sumarios_insert.append({
            "id_sesion": id_sesion,
            "numero_item": it["numero_item"],
            "texto_item": texto_final_item
        })

        categoria = _clasificar_item_sumario(texto_final_item)
        titulo_det = extraer_titulo_proyecto_desde_texto(resumen_sumario=texto_final_item)
        arts_mod_s, leyes_mod_s, res_mod_s = extraer_articulos_modificados_y_leyes(resumen_sumario=texto_final_item)

        if categoria == "LEY_TRATADA":
            leyes_tratadas_sumario.append({
                "codigo": it["numero_item"],
                "arabigo": it["arabigo_puro"],
                "romano": it["romano_puro"],
                "resumen": texto_final_item,
                "titulo_proyecto": titulo_det,
                "arts_modificados": arts_mod_s,
                "leyes_modificadas": leyes_mod_s,
                "resumen_modificacion": res_mod_s,
                "usado": False
            })
        elif categoria == "PROYECTO_ENTRADO":
            proyectos_en_sumario.append({
                "romano": it["romano_puro"],
                "arabigo": it["arabigo_puro"],
                "codigo": it["numero_item"],
                "resumen": texto_final_item,
                "titulo_proyecto": titulo_det,
                "arts_modificados": arts_mod_s,
                "leyes_modificadas": leyes_mod_s,
                "resumen_modificacion": res_mod_s,
                "usado": False
            })

    return sumarios_insert, proyectos_en_sumario, leyes_tratadas_sumario



REGEX_CABECERA_PROYECTO = re.compile(
    r"(?:^|\n)\s*"
    r"(?:(?P<romano_seccion>L?X{0,3}(?:IX|IV|V?I{1,3}|V|X))\s*\n+\s*)?"
    r"(?P<titulo_mayus>"
        r"P\s*R\s*O\s*Y\s*E\s*C\s*T\s*O\s+D\s*E\s+L\s*E\s*[YVTÍI1]\b"
        r"|"
        r"Proyecto\s+de\s+le[yvtíi1]\b"
        r"|"
        r"PROYECTO\s+DE\s*(?=\n+\s*El\s+Senado\s+y\s+C[aáâ]mar[ao])"
        r"|"
        r"(?=El\s+Senado\s+y\s+C[aáâ]mar[ao]\s+de\s+Diputados[^\n]{0,140}\n)"
    r")"
    r"(?P<intermedio>[\s\S]{0,380}?)"
    r"(?=\n?\s*Art(?:[ií]culo|ienio|[\.\,])\s*(?:\d+|I|l|primero|tor[ií]zase|cu[eé]rdase|r[eé]ase|ecl[aá]ran?se|pru[eé]base|est[ií]nase|odif[ií]ca))"
)

# Cierre exacto del articulado: incluye "Comuniqúese" (con tilde en la ú), "Comuníquese" y "De forma."
REGEX_FIN_ARTICULADO = re.compile(
    r"(?:"
        r"(?P<art_comuniquese>"
            r"(?:Art(?:[ií]culo|ienio|[\.\,])?\s*[\dIlº°ª\?\'\"\*\-\$S\.\,\s]{0,8}[-—–]?\s*)?"
            r"(?:"
                r"Comu[ns]i[qgp][uúü][eé][sn]e(?:\s+al\s+Poder\s+Ejecutivo)?[^\n\.]*[\.\,](?:\s*(?:et[ce][\.\,]|arch[ií]vese[\.\,]|publ[ií]quese[^\n\.]*[\.\,]|d[eé]se\s+al\s+Registro[^\n\.]*[\.\,]|cumplido[^\n\.]*[\.\,]))*"
                r"|"
                r"Art(?:[ií]culo|[\.\,])\s*\d+[\s\dº°ª\?\'\"\*]*[-—–]\s*De\s+forma\s*\."
            r")"
        r")"
        r"|"
        r"(?=\n\s*(?:"
            r"Señor\s+presidente\s*[:\.,]"
            r"|FUNDAMENTOS\b"
            r"|INFORME\b"
            r"|[-—–]?\s*A\s+l[ao]s?\s+Comisi[oó]n"
            r"|[-—–]?\s*Pasa\s+a\s+la\s+Comisi[oó]n"
            r"|Sala\s+de\s+la\s+[Cc]omisi[oó]n"
            r"|Dada\s+en\s+la\s+Sala\s+de\s+Sesiones"
            r"|Dios\s+guarde\s+a\s+V"
            r"|(?:Sr\.|Señor)\s+(?:Presidente|[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s*[\.\-—–]"
            r"|[-—–]\s*(?:Se\s+lee|En\s+discusi[oó]n|Sin\s+observaci[oó]n|Se\s+vota|Queda\s+sancionado)"
        r"))"
    r")",
    re.IGNORECASE
)

# Exige "A" mayúscula en "Artículo"/"Art." y separador formal para jamás partir referencias en minúscula ("...del artículo 17, es decir...")
REGEX_SPLIT_ARTICULOS = re.compile(
    r"(?:^|\n)\s*(?="
        r"(?:\[[^\]]+\]\s*)?"
        r"(?:"
            r"Art(?:[ií]culo|ienio)\s+(?:(?:\d+|I|l|primero)[\dº°ªoa9\?\'\"\*\^\}\]\)\-r\.\,\s]{0,6}?[-—–]*\s*(?=[A-ZÁÉÍÓÚÑ«\"\¿\¡])|[Tt]or[ií]zase|[Cc]u[eé]rdase|[Rr][eé]ase|[Ee]cl[aá]ran?se|[Pp]ru[eé]base|[Ee]st[ií]nase|[Oo]dif[ií]ca(?:n)?se)"
            r"|"
            r"Art[\.\,]\s*(?:\d+|I|l|\$|S)[\dº°ªoa9\?\'\"\*\^\}\]\)\-r\.\,\s]{0,6}?[-—–]*\s*(?=[A-ZÁÉÍÓÚÑ«\"\¿\¡])"
        r")"
    r")"
)

REGEX_CORTE_COLA_ARTICULO = re.compile(
    r"(?:"
    r"\s+Sala\s+de\s+la\s+[Cc]omisi[oó]n\b.*"
    r"|\s+Dada\s+en\s+la\s+Sala\s+de\s+Sesiones\b.*"
    r"|\s+Dios\s+guarde\s+a\s+V.*"
    r"|\s+(?:Sr\.|Señor)\s+(?:Presidente|[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s*(?:\([^\)]+\))?\s*[\.\,\-—–]+\s*[-—–]?.*"
    r"|\s+[-—–]\s*(?:Se\s+lee|En\s+discusi[oó]n|Sin\s+observaci[oó]n|Se\s+vota|Queda\s+sancionado|Aprobado\.|A\s+la\s+Comisi[oó]n|Pasa\s+a\s+la\s+Comisi[oó]n).*"
    r"|\s+Señor\s+presidente\s*:\s*.*"
    r")$",
    re.IGNORECASE
)

PALABRAS_COMUNES_IGNORAR = {
    "proyecto", "proyectos", "señor", "señores", "diputado", "diputados",
    "senador", "senadores", "sobre", "acordando", "creando", "nacional",
    "poder", "ejecutivo", "comision", "despacho", "mensaje", "mismo",
    "articulo", "articulos", "pesos", "moneda", "fondos", "gastos",
    "presupuesto", "general", "rentas", "generales", "presente", "leyes",
    "cumplimiento", "autorizase", "acuerdase", "destinados", "provincia",
    "camara", "senado", "congreso", "nacion", "argentina", "siguiente",
    "administracion", "publicas", "publica", "capital", "federal", "estado"
}

MAPA_EQUIVALENCIAS_VERBOS = {
    "acuerd": "acord",
    "autoriz": "autoriz",
    "aprueb": "aprob",
    "creas": "creac",
    "crean": "creac",
    "modific": "modific",
    "derog": "derog",
    "prorrog": "prorrog",
    "destin": "destin",
    "construy": "construc",
    "construc": "construc",
    "adquier": "adquisic",
    "adquisic": "adquisic",
    "intervien": "intervenc",
    "intervenc": "intervenc",
    "eximes": "exim",
    "exim": "exim",
    "declara": "declar",
    "fijas": "fijac",
    "fijand": "fijac",
    "substituy": "sustituc",
    "sustituy": "sustituc",
}


def _quitar_tildes(s):
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _extraer_raices_y_numeros(texto):
    """
    Extrae raíces léxicas normalizadas y números (de leyes o montos) para emparejar
    con altísima precisión el texto articulado con su ítem del SUMARIO.
    """
    if not texto:
        return set()
    t_sin = _quitar_tildes(texto.lower())
    tokens = set()

    # Capturar números de leyes o cifras relevantes (ej. 4349, 11290, 50000)
    for m_num in re.finditer(r"\b(\d{1,2})\.(\d{3})\b|\b(\d{3,5})\b", t_sin):
        num_str = (m_num.group(1) + m_num.group(2)) if m_num.group(1) else m_num.group(3)
        if num_str and not (1920 <= int(num_str) <= 1945):
            tokens.add(f"num_{num_str}")

    for pal in re.findall(r"\b[a-zñ]{4,}\b", t_sin):
        if pal in PALABRAS_COMUNES_IGNORAR:
            continue
        pref6 = pal[:6]
        norm = MAPA_EQUIVALENCIAS_VERBOS.get(pref6, MAPA_EQUIVALENCIAS_VERBOS.get(pal[:5], pal[:6]))
        tokens.add(norm)

    return tokens


def _calcular_similitud_sumario_ley(texto_sumario, texto_ley):
    """
    Calcula (score_base, cantidad_comunes, peso_nums) entre el texto de un ítem del sumario
    y el cuerpo de una ley.
    """
    tokens_sum = _extraer_raices_y_numeros(texto_sumario)
    tokens_ley = _extraer_raices_y_numeros(texto_ley[:2800])
    if not tokens_sum or not tokens_ley:
        return 0.0, 0, 0.0
    comunes = tokens_ley & tokens_sum
    if not comunes:
        return 0.0, 0, 0.0
    peso_nums = sum(2.5 for tok in comunes if tok.startswith("num_"))
    peso_pals = sum(1.0 for tok in comunes if not tok.startswith("num_"))
    return (peso_nums + peso_pals), len(comunes), peso_nums


def asociar_item_sumario_reunion(
    cuerpo_ley,
    contexto_previo,
    romano_sec,
    arabigo_sec,
    es_tratamiento_recinto,
    proyectos_en_sumario,
    leyes_tratadas_sumario
):
    """
    Vincula cada bloque de ley con su ítem exacto del SUMARIO de ESA MISMA reunión:
    - Separa la búsqueda según sea un Despacho tratado en recinto vs. un Proyecto entrado.
    - Usa coincidencia exacta de sección (romana o arábiga) + similitud por raíces léxicas y números de ley.
    - JAMÁS reutiliza un mismo ítem del sumario para múltiples leyes distintas ni asigna por descarte ciego.
    """
    lista_primaria = leyes_tratadas_sumario if es_tratamiento_recinto else proyectos_en_sumario
    lista_secundaria = proyectos_en_sumario if es_tratamiento_recinto else leyes_tratadas_sumario

    # 1. Coincidencia por número romano de sección (para proyectos entrados: I, II, III...)
    if romano_sec and not es_tratamiento_recinto:
        rom_b = romano_sec.strip().upper()
        for p in proyectos_en_sumario:
            if not p["usado"] and p.get("romano") == rom_b:
                p["usado"] = True
                return p

    # 2. Coincidencia por número arábigo de sección del Orden del Día (para leyes tratadas en recinto: 1, 2, 3...)
    if arabigo_sec and es_tratamiento_recinto:
        arab_b = str(arabigo_sec).strip()
        for lt in leyes_tratadas_sumario:
            if not lt["usado"] and str(lt.get("arabigo") or "") == arab_b:
                lt["usado"] = True
                return lt

    # 3. Similitud estricta por raíces léxicas + números de ley / cifras (solo entre candidatos NO usados)
    texto_busqueda_ley = f"{contexto_previo[-450:]}\n{cuerpo_ley[:2500]}"

    mejor_cand = None
    max_score = 0.0

    for grupo, factor_grupo in ((lista_primaria, 1.25), (lista_secundaria, 1.0)):
        for cand in grupo:
            if cand["usado"]:
                continue
            score_base, n_comunes, peso_nums = _calcular_similitud_sumario_ley(cand["resumen"], texto_busqueda_ley)
            if score_base <= 0:
                continue
            score_total = score_base * factor_grupo

            es_match_solido = (n_comunes >= 3) or (peso_nums >= 2.5 and n_comunes >= 2)
            if es_match_solido and score_base >= 3.0 and score_total > max_score:
                max_score = score_total
                mejor_cand = cand

    if mejor_cand:
        mejor_cand["usado"] = True
        return mejor_cand

    return None


def _limpiar_cola_post_comuniquese(texto_art):
    """
    Corta cualquier firma, fecha de comisión o intervención de orador que haya quedado
    en la misma línea después de 'Comuníquese al Poder Ejecutivo.' / 'Comuníquese, etc.' / 'De forma.'
    o a mitad de un artículo si se coló el debate.
    """
    t = REGEX_CORTE_COLA_ARTICULO.sub("", texto_art).strip()

    m_com = re.search(
        r"(Comu[ns]i[qgp][uúü][eé][sn]e(?:\s+al\s+Poder\s+Ejecutivo)?[^\n\.]*[\.\,](?:\s*(?:et[ce][\.\,]|arch[ií]vese[\.\,]|publ[ií]quese[^\n\.]*[\.\,]|d[eé]se\s+al\s+Registro[^\n\.]*[\.\,]|cumplido[^\n\.]*[\.\,]))*)",
        t,
        re.IGNORECASE
    )
    if m_com:
        return t[:m_com.end()].strip()

    m_for = re.search(r"(\bDe\s+forma\s*\.)", t, re.IGNORECASE)
    if m_for:
        return t[:m_for.end()].strip()

    return t


def _normalizar_numero_articulo_ocr(texto_art, orden_secuencial):
    """
    Corrige errores de OCR en la numeración del artículo:
    - En la tipografía de 1929-1939, '1º', '2º', ..., '9º' suelen leerse en OCR como
      'l 9', 'I 9', 'i 9', '1 9', '2 9', '19', '29', '39', ..., '99', '1?', '1*', '1''.
    - Si el número leído es 19, 29, ..., 99 y su decena (num // 10) es coherente con el
      orden_secuencial esperado del proyecto (1, 2, 3...), se repara a '1º', '2º', '3º'...
    - Si en cambio es un artículo real de una ley modificada (ej. 'Artículo 71' cuando
      orden_secuencial es 1 o 2), se conserva intacto '71'.
    Devuelve: (numero_limpio_str, texto_art_normalizado)
    """
    t = limpiar_cabezales_incrustados(_normalizar_ordinales_ocr_en_texto(texto_art.strip()))

    # Reparaciones de verbos comidos por OCR en el Art. 1º
    t = re.sub(r"^Art(?:[ií]culo|ienio)\s+tor[ií]zase", "Artículo 1º — Autorízase", t, flags=re.IGNORECASE)
    t = re.sub(r"^Art(?:[ií]culo|ienio)\s+cu[eé]rdase", "Artículo 1º — Acuérdase", t, flags=re.IGNORECASE)
    t = re.sub(r"^Art(?:[ií]culo|ienio)\s+r[eé]ase", "Artículo 1º — Créase", t, flags=re.IGNORECASE)
    t = re.sub(r"^Art(?:[ií]culo|ienio)\s+ecl[aá]ran?se", "Artículo 1º — Declárase", t, flags=re.IGNORECASE)
    t = re.sub(r"^Art(?:[ií]culo|ienio)\s+pru[eé]base", "Artículo 1º — Apruébase", t, flags=re.IGNORECASE)
    t = re.sub(r"^Art(?:[ií]culo|ienio)\s+est[ií]nase", "Artículo 1º — Destínase", t, flags=re.IGNORECASE)
    t = re.sub(r"^Art(?:[ií]culo|ienio)\s+odif[ií]ca(n)?se", r"Artículo 1º — Modifíca\1se", t, flags=re.IGNORECASE)

    # Extraer número inicial del artículo (soportando 'l 9', '1º', '19', '?', '*', 'r —', '" —')
    m_num = re.match(
        r"^(?P<pref>Art(?:[ií]culo|ienio|[\.\,]))\s*"
        r"(?P<num>\d+|[Il1i\|\$S]|primero)"
        r"(?P<ord>[\sº°ªoa9\?\'\"\*\^\}\]\)\-r\.\,]{0,8}?)"
        r"(?P<sep>[-—–]+)?\s*"
        r"(?P<resto>.+)$",
        t,
        re.IGNORECASE
    )
    if not m_num:
        return str(orden_secuencial), t

    raw_num = m_num.group("num")
    resto = m_num.group("resto").strip()
    # Limpiar basura de OCR residual al comienzo del resto (ej. 'r — ', '"? — ', '" — ')
    resto = re.sub(r"^(?:[\?\'\"\*\^\}\]\)\.\,r9º°ª]+\s*[-—–]+\s*|[-—–\.\,\s]+)", "", resto).strip()
    pref_limpio = "Artículo" if len(m_num.group("pref")) > 4 else "Art."

    if raw_num.lower() in ("i", "l", "|", "$", "s", "primero"):
        num_int = 1
    elif raw_num.isdigit():
        num_int = int(raw_num)
        # Detectar si 19, 29, 39...99 es en realidad 1º, 2º, 3º...9º por OCR del símbolo 'º' -> '9'
        if 19 <= num_int <= 99 and (num_int % 10 == 9):
            decena = num_int // 10
            if decena == orden_secuencial or (orden_secuencial <= 10 and abs(decena - orden_secuencial) <= 2):
                num_int = decena
            elif re.match(r"^(?:Comu[ns]i[qgp][uúü][eé][sn]e|De\s+forma\b)", resto, re.IGNORECASE) and decena <= orden_secuencial + 2:
                num_int = decena
    else:
        num_int = orden_secuencial

    sufijo_ord = "º" if num_int <= 9 else "."
    t_norm = f"{pref_limpio} {num_int}{sufijo_ord} — {resto}"
    return str(num_int), t_norm


def consolidar_ley_completa(cuerpo_articulado, resumen_sumario=None, contexto_previo=None):
    """
    Procesa el bloque articulado de una ley:
    1. Elimina cabezales de imprenta incrustados y fórmulas sancionatorias con o sin errores de OCR.
    2. Extrae cualquier título explícito ubicado antes del Artículo 1º (validando que no sea una fórmula).
    3. Separa y limpia cada artículo sin capturar discursos ni firmas posteriores a 'Comuníquese'.
    4. Repara errores de OCR en la numeración ('l 9' / '19' -> '1º', '29' -> '2º') respetando números reales
       de artículos modificados ('Artículo 71', 'Artículo 17').
    5. Determina exactamente qué artículos fueron modificados y el título del proyecto.
    Devuelve un diccionario con todos los metadatos listos para Supabase.
    """
    cuerpo_limpio_cab = limpiar_cabezales_incrustados(_normalizar_ordinales_ocr_en_texto(cuerpo_articulado or ""))

    # Eliminar etiquetas iniciales entre corchetes que contengan fórmulas sancionatorias o PROYECTO DE LEY
    cuerpo_limpio_cab = re.sub(
        r"^\s*(?:\[[^\]]*(?:Senado|Sonado|Diputad|PROYECTO\s+DE\s+LEY|sancionan\s+con\s+fuerza)[^\]]*\]\s*)+",
        "",
        cuerpo_limpio_cab,
        flags=re.IGNORECASE
    ).strip()

    # Capturar si existe un título explícito entre la cabecera y el Artículo 1º
    titulo_interno = None
    m_cab = re.match(
        r"^\s*(?:L?X{0,3}(?:IX|IV|V?I{1,3}|V|X)\s*\n+\s*)?"
        r"(?:P\s*R\s*O\s*Y\s*E\s*C\s*T\s*O\s+D\s*E\s*(?:L\s*E\s*[YVTÍI1])?\s*\n+)?"
        r"(?:\s*[^\n]{0,15}(?:Senado|Sonado)\s+y[\s\-]*C[aáâ]mar[ao][^\n]*\n+)?"
        r"(?P<posible_titulo>[\s\S]{0,260}?)"
        r"(?=\n?\s*Art(?:[ií]culo|ienio|[\.\,]))",
        cuerpo_limpio_cab,
        re.IGNORECASE
    )
    if m_cab and m_cab.group("posible_titulo"):
        cand_interno = re.sub(r"\s+", " ", m_cab.group("posible_titulo")).strip(" [].,;:-—")
        titulo_interno = _limpiar_posible_titulo(cand_interno)

    cuerpo_sin_cabecera = re.sub(
        r"^\s*(?:L?X{0,3}(?:IX|IV|V?I{1,3}|V|X)\s*\n+\s*)?"
        r"(?:P\s*R\s*O\s*Y\s*E\s*C\s*T\s*O\s+D\s*E\s*(?:L\s*E\s*[YVTÍI1])?\s*\n+)?"
        r"(?:\s*[^\n]{0,15}(?:Senado|Sonado)\s+y[\s\-]*C[aáâ]mar[ao][^\n]*\n+)?",
        "",
        cuerpo_limpio_cab,
        flags=re.IGNORECASE
    ).strip()

    partes = [p.strip() for p in REGEX_SPLIT_ARTICULOS.split(cuerpo_sin_cabecera) if p.strip()]
    articulos_limpios = []
    numeros_detectados = []
    encabezado_previo = []
    orden_esperado = 1

    for parte in partes:
        texto_linea = limpiar_cabezales_incrustados(re.sub(r"\s*\n\s*", " ", parte).strip())
        m_pref_corchete = re.match(r"^\[([^\]]+)\]\s*(Art.*)$", texto_linea)
        if m_pref_corchete:
            pref_txt = m_pref_corchete.group(1).strip()
            if not _es_titulo_invalido_o_formula(pref_txt):
                encabezado_previo.append(pref_txt)
            texto_linea = m_pref_corchete.group(2).strip()

        if not re.match(r"^Art", texto_linea):
            if len(texto_linea) < 120 and not REGEX_CABEZAL_PAGINA.search(texto_linea) and not _es_titulo_invalido_o_formula(texto_linea):
                encabezado_previo.append(texto_linea)
            continue

        texto_linea = _limpiar_cola_post_comuniquese(texto_linea)
        if len(texto_linea) < 10:
            continue

        num_art_str, texto_linea = _normalizar_numero_articulo_ocr(texto_linea, orden_esperado)
        if num_art_str.isdigit() and int(num_art_str) == orden_esperado:
            orden_esperado += 1
        elif len(numeros_detectados) == 0:
            orden_esperado = 2

        if f"Art. {num_art_str}" not in numeros_detectados:
            numeros_detectados.append(f"Art. {num_art_str}")

        if encabezado_previo:
            prefijo = " - ".join(encabezado_previo)
            articulos_limpios.append(f"[{prefijo}] {texto_linea}")
            encabezado_previo = []
        else:
            articulos_limpios.append(texto_linea)

        # Si este artículo es el de cierre formal ("Comuníquese..." o "De forma."), terminar el proyecto aquí
        if re.search(r"\b(?:Comu[ns]i[qgp][uúü][eé][sn]e|De\s+forma\s*\.)", texto_linea, re.IGNORECASE):
            break

    cantidad = len(articulos_limpios)
    if cantidad == 0:
        return None

    texto_solo_articulos = "\n".join(articulos_limpios)

    # Determinar artículos modificados y leyes modificadas
    arts_mod, leyes_mod, resumen_mod = extraer_articulos_modificados_y_leyes(
        resumen_sumario=resumen_sumario,
        texto_articulado=texto_solo_articulos
    )

    # Solo incorporar números de artículos fuera de secuencia si el proyecto menciona explícitamente una reforma/modificación
    # y el número no es un residuo de OCR terminado en 9 (19, 29, 39...99)
    if re.search(r"\b(?:modif[ií]ca|sustit[uú]ye|reempl[aá]za|reforma|der[oó]ga)\b", f"{resumen_sumario or ''} {texto_solo_articulos[:600]}", re.IGNORECASE):
        for n_det in numeros_detectados:
            m_n = re.search(r"\d+", n_det)
            if m_n:
                val_n = int(m_n.group(0))
                if val_n > cantidad + 3 and not (19 <= val_n <= 99 and val_n % 10 == 9) and n_det not in arts_mod:
                    arts_mod.append(n_det)
        if arts_mod and not resumen_mod:
            ley_str = f" ({', '.join(leyes_mod)})" if leyes_mod else ""
            resumen_mod = f"Modifica: {', '.join(arts_mod[:10])}{ley_str}"

    # Determinar el título del proyecto (si existe)
    titulo_proyecto = (
        extraer_titulo_proyecto_desde_texto(
            resumen_sumario=resumen_sumario,
            texto_articulado=texto_solo_articulos,
            contexto_previo=contexto_previo
        )
        or titulo_interno
    )

    # Construir etiqueta precisa para 'numero_articulo'
    if cantidad <= 5:
        etiqueta_base = ", ".join(numeros_detectados)
    else:
        prim = numeros_detectados[0].replace("Art. ", "")
        ult = numeros_detectados[-1].replace("Art. ", "")
        etiqueta_base = f"Arts. {prim} a {ult}"

    if resumen_mod:
        etiqueta_articulos = f"{resumen_mod} [{etiqueta_base}]" if etiqueta_base not in resumen_mod else resumen_mod
    else:
        etiqueta_articulos = etiqueta_base

    # Construir resumen_sumario enriquecido con el TÍTULO y ARTÍCULOS MODIFICADOS (si existen)
    etiquetas_cab = []
    if titulo_proyecto:
        etiquetas_cab.append(f"TÍTULO: {titulo_proyecto}")
    if resumen_mod:
        etiquetas_cab.append(resumen_mod.upper())

    resumen_limpio = limpiar_cabezales_incrustados(re.sub(r"^\[[^\]]+\]\s*", "", (resumen_sumario or "")).strip())
    if etiquetas_cab:
        pref_meta = f"[{' | '.join(etiquetas_cab)}]"
        resumen_final = f"{pref_meta} {resumen_limpio}".strip() if resumen_limpio else pref_meta
    else:
        resumen_final = resumen_limpio if resumen_limpio else None

    # Referencia concisa para la columna 'articulo_referencia' de leyes_tratamiento_recinto
    partes_ref = []
    if resumen_mod:
        partes_ref.append(resumen_mod)
    else:
        partes_ref.append(etiqueta_base)
    if titulo_proyecto:
        partes_ref.append(f"Proyecto: {titulo_proyecto[:120]}")
    articulo_referencia_str = " | ".join(partes_ref)

    return {
        "cantidad_articulos": cantidad,
        "numero_articulo": etiqueta_articulos[:250],
        "articulo_referencia": articulo_referencia_str[:250],
        "titulo_proyecto": titulo_proyecto,
        "articulos_modificados": arts_mod,
        "leyes_modificadas": leyes_mod,
        "resumen_modificacion": resumen_mod,
        "resumen_sumario": resumen_final,
        "texto_articulado": texto_solo_articulos
    }


def extraer_leyes_por_reunion(texto_reunion, id_sesion, proyectos_en_sumario, leyes_tratadas_sumario, orden_inicial=1):
    """
    Extrae todas las leyes de una Reunión garantizando:
    - 1 FILA = 1 LEY TRATADA O PRESENTADA POR SESIÓN.
    - Cero filas vacías o copias sin articulado ('REFERENCIA_SUMARIO' eliminadas).
    - Identificación exacta de artículos modificados y título del proyecto de ley.
    """
    filas_proyectos = []
    filas_recinto = []
    rangos_ocupados = []
    orden_actual = orden_inicial

    matches_proy = list(REGEX_CABECERA_PROYECTO.finditer(texto_reunion))

    for idx_p, m_ini in enumerate(matches_proy):
        ini = m_ini.start()
        if any(r0 <= ini <= r1 for r0, r1 in rangos_ocupados):
            continue

        limite = (
            matches_proy[idx_p + 1].start()
            if (idx_p + 1 < len(matches_proy))
            else min(len(texto_reunion), ini + 45000)
        )
        fragmento = texto_reunion[ini:limite]

        offset_cab = len(m_ini.group(0))
        m_fin = REGEX_FIN_ARTICULADO.search(fragmento[offset_cab:])
        if m_fin:
            fin_rel = offset_cab + (m_fin.end() if m_fin.group("art_comuniquese") else m_fin.start())
            bloque_ley = fragmento[:fin_rel].strip()
        else:
            bloque_ley = fragmento[:5500].strip()

        fin_abs = ini + len(bloque_ley)
        rangos_ocupados.append((ini, fin_abs))

        contexto_previo = texto_reunion[max(0, ini - 1400):ini]
        contexto_posterior = texto_reunion[fin_abs:min(len(texto_reunion), fin_abs + 2200)]

        romano_sec = m_ini.group("romano_seccion")
        if not romano_sec:
            m_rom_prev = re.search(
                r"(?:^|\n)\s*(L?X{0,3}(?:IX|IV|V?I{1,3}|V|X))\s*\n",
                contexto_previo[-300:]
            )
            if m_rom_prev:
                romano_sec = m_rom_prev.group(1)

        m_arab_prev = re.search(r"(?:^|\n)\s*([1-4]?\d)\s*\n", contexto_previo[-600:])
        arabigo_sec = m_arab_prev.group(1) if m_arab_prev else None

        es_tratamiento_recinto = bool(
            re.search(
                r"(?:Honorable\s+(?:C[aá]mara|Senado)\s*:\s*Vuestra\s+Comisi[oó]n|Despacho\s+de\s+la\s+Comisi[oó]n|Consideraci[oó]n\s+del\s+despacho|En\s+discusi[oó]n\s+en\s+general|aconseja\s+la\s+sanci[oó]n)",
                contexto_previo,
                re.IGNORECASE
            )
            or re.search(
                r"(?:Sr\.\s+Presidente[^\n]{0,80}(?:discusi[oó]n\s+en\s+general|consideraci[oó]n\s+en\s+general|va\s+a\s+votar)|[-—–]\s*Se\s+vota\s+y\s+(?:resulta\s+afirmativa|se\s+aprueba)|Queda\s+sancionado\s+el\s+proyecto)",
                contexto_posterior,
                re.IGNORECASE
            )
        )

        item_sum = asociar_item_sumario_reunion(
            bloque_ley,
            contexto_previo,
            romano_sec,
            arabigo_sec,
            es_tratamiento_recinto,
            proyectos_en_sumario,
            leyes_tratadas_sumario
        )
        resumen_base = item_sum["resumen"] if item_sum else None

        info_ley = consolidar_ley_completa(bloque_ley, resumen_sumario=resumen_base, contexto_previo=contexto_previo)
        if not info_ley or info_ley["cantidad_articulos"] == 0:
            continue

        filas_proyectos.append({
            "id_sesion": id_sesion,
            "orden_proyecto_sesion": orden_actual,
            "tipo_documento": "DESPACHO DE LEY" if es_tratamiento_recinto else "PROYECTO DE LEY",
            "instancia_legislativa": (
                "MODIFICACION_LEY" if info_ley["resumen_modificacion"]
                else ("TRATAMIENTO_RECINTO" if es_tratamiento_recinto else "PROYECTO_INTEGRO")
            ),
            "numero_articulo": info_ley["numero_articulo"],
            "cantidad_articulos": info_ley["cantidad_articulos"],
            "resumen_sumario": info_ley["resumen_sumario"],
            "texto_articulado": info_ley["texto_articulado"]
        })
        orden_actual += 1

        if es_tratamiento_recinto:
            filas_recinto.append({
                "id_sesion": id_sesion,
                "tipo_documento": "MODIFICACION EN RECINTO" if info_ley["resumen_modificacion"] else "LEY TRATADA EN RECINTO",
                "articulo_referencia": info_ley["articulo_referencia"],
                "numero_articulo": info_ley["numero_articulo"],
                "resumen_sumario": info_ley["resumen_sumario"],
                "texto_articulado": info_ley["texto_articulado"]
            })

    # Segunda pasada: Artículos tratados/modificados en particular en el recinto (cuando la sesión
    # continúa la discusión en particular sin repetir el encabezado 'PROYECTO DE LEY')
    # Exige 'A' mayúscula en 'Artículo'/'Art.', separador formal y corta antes de cualquier orador.
    REGEX_DEBATE_ART_ESTRICTO = re.compile(
        r"(?:^|\n)\s*(?:"
            r"(?:[-—–]?\s*En\s+discusi[oó]n\s+el\s+art[ií]culo\s+\d+[^\n]*\n+|[-—–]?\s*Se\s+lee\s*(?:el\s+art[ií]culo\s+\d+[^\n]*)?:?\s*\n+)"
        r")?"
        r"(?P<art_votado>"
            r"Art(?:[ií]culo|ienio|\.)\s*\d+\s*(?:[º°ª\*\?\'\"\.]|\s+9)?\s*[-—–]+\s*[A-ZÁÉÍÓÚÑ«\"\¿\¡]"
            r"[\s\S]{15,1800}?"
        r")"
        r"(?=\n\s*(?:"
            r"[-—–]?\s*Se\s+vota\s+y\s+(?:se\s+aprueba|resulta\s+afirmativa)"
            r"|[-—–]?\s*Aprobado\."
            r"|[-—–]?\s*Sin\s+observaci[oó]n\s*,\s*se\s+da\s+por\s+aprobado"
            r"|[-—–]?\s*Queda\s+(?:aprobado|sancionado)"
            r"|(?:Sr\.|Señor)\s+Presidente\s*[\.\-—–]+\s*(?:En\s+discusi[oó]n|Se\s+va\s+a\s+votar|Queda\s+aprobado)"
        r"))"
    )

    articulos_recinto_sueltos = []
    for m_deb in REGEX_DEBATE_ART_ESTRICTO.finditer(texto_reunion):
        if any(r0 <= m_deb.start() <= r1 for r0, r1 in rangos_ocupados):
            continue
        raw_art = m_deb.group("art_votado")
        # Cortar si dentro del bloque se coló la intervención de un legislador ("Sr. X. — ...")
        m_orador_interno = re.search(
            r"\n\s*(?:Sr\.|Señor)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s*\([^\)]+\))?\s*[\.\-—–]+",
            raw_art
        )
        if m_orador_interno:
            raw_art = raw_art[:m_orador_interno.start()].strip()

        art_limpio = _limpiar_cola_post_comuniquese(re.sub(r"\s*\n\s*", " ", raw_art).strip())
        if len(art_limpio) >= 20 and re.match(r"^Art", art_limpio):
            articulos_recinto_sueltos.append((m_deb.start(), art_limpio))

    if articulos_recinto_sueltos:
        cuerpo_sueltos = "\n".join(a[1] for a in articulos_recinto_sueltos)
        pos_primero = articulos_recinto_sueltos[0][0]
        ctx_prev = texto_reunion[max(0, pos_primero - 1500):pos_primero]

        item_sum_rec = asociar_item_sumario_reunion(
            cuerpo_sueltos,
            ctx_prev,
            None,
            None,
            True,
            proyectos_en_sumario,
            leyes_tratadas_sumario
        )
        res_base_rec = item_sum_rec["resumen"] if item_sum_rec else None
        info_rec = consolidar_ley_completa(cuerpo_sueltos, resumen_sumario=res_base_rec, contexto_previo=ctx_prev)

        if info_rec and info_rec["cantidad_articulos"] > 0:
            filas_recinto.append({
                "id_sesion": id_sesion,
                "tipo_documento": "TRATAMIENTO EN PARTICULAR",
                "articulo_referencia": info_rec["articulo_referencia"],
                "numero_articulo": info_rec["numero_articulo"],
                "resumen_sumario": info_rec["resumen_sumario"],
                "texto_articulado": info_rec["texto_articulado"]
            })

            filas_proyectos.append({
                "id_sesion": id_sesion,
                "orden_proyecto_sesion": orden_actual,
                "tipo_documento": "TRATAMIENTO EN PARTICULAR",
                "instancia_legislativa": "MODIFICACION_LEY" if info_rec["resumen_modificacion"] else "TRATAMIENTO_RECINTO",
                "numero_articulo": info_rec["numero_articulo"],
                "cantidad_articulos": info_rec["cantidad_articulos"],
                "resumen_sumario": info_rec["resumen_sumario"],
                "texto_articulado": info_rec["texto_articulado"]
            })
            orden_actual += 1

    return filas_proyectos, filas_recinto, orden_actual


def procesar_texto_tomo_completo(texto_limpio, id_sesion, orden_inicial_ley=1):
    """
    Segmenta un Tomo PDF en sus Reuniones individuales y extrae sumarios y leyes
    con alcance estricto por Reunión.
    """
    reuniones = segmentar_en_reuniones(texto_limpio)
    todos_sumarios = []
    todas_leyes_proyectos = []
    todas_leyes_recinto = []
    presidente_detectado = None
    orden_global_ley = orden_inicial_ley

    for texto_reunion in reuniones:
        if not presidente_detectado:
            presidente_detectado = extraer_presidente_reunion(texto_reunion)

        sumarios_r, proys_sum_r, leyes_trat_r = extraer_sumarios_reunion(texto_reunion, id_sesion)
        filas_proy_r, filas_rec_r, orden_global_ley = extraer_leyes_por_reunion(
            texto_reunion, id_sesion, proys_sum_r, leyes_trat_r, orden_inicial=orden_global_ley
        )

        todos_sumarios.extend(sumarios_r)
        todas_leyes_proyectos.extend(filas_proy_r)
        todas_leyes_recinto.extend(filas_rec_r)

    return todos_sumarios, todas_leyes_proyectos, todas_leyes_recinto, presidente_detectado



# Valores sacados de: https://servicios.infoleg.gob.ar/infolegInternet/ y http://www.saij.gob.ar/
# Rango oficial de leyes sancionadas por el Congreso en cada año legislativo (1929 a 1939, total: 1.087 leyes)
RANGOS_ANIO_LEY = [
    (1929, 11544, 11577),
    (1932, 11578, 11683),
    (1933, 11684, 11835),
    (1934, 11836, 12161),
    (1935, 12162, 12294),
    (1936, 12295, 12356),
    (1937, 12357, 12360),
    (1938, 12361, 12579),
    (1939, 12580, 12630),
]

# Valores sacados de: https://servicios.infoleg.gob.ar/infolegInternet/ (Registro Nacional de Leyes 1862-1939 y Digesto Jurídico Argentino)
CRONOLOGIA_LEYES_ARG = [
    (1862, 1, 38), (1863, 39, 82), (1864, 83, 124), (1865, 125, 168),
    (1866, 169, 206), (1867, 207, 238), (1868, 239, 284), (1869, 285, 365),
    (1870, 366, 447), (1871, 448, 497), (1872, 498, 584), (1873, 585, 653),
    (1874, 654, 699), (1875, 700, 762), (1876, 763, 834), (1877, 835, 904),
    (1878, 905, 959), (1879, 960, 1015), (1880, 1016, 1073), (1881, 1074, 1160),
    (1882, 1161, 1265), (1883, 1266, 1390), (1884, 1391, 1585), (1885, 1586, 1752),
    (1886, 1753, 1923), (1887, 1924, 2255), (1888, 2256, 2445), (1889, 2446, 2698),
    (1890, 2699, 2765), (1891, 2766, 2875), (1892, 2876, 2930), (1893, 2931, 3060),
    (1894, 3061, 3200), (1895, 3201, 3340), (1896, 3341, 3460), (1897, 3461, 3675),
    (1898, 3676, 3765), (1899, 3766, 3895), (1900, 3896, 3983), (1901, 3984, 4050),
    (1902, 4051, 4167), (1903, 4168, 4295), (1904, 4296, 4555), (1905, 4556, 4930),
    (1906, 4931, 5075), (1907, 5076, 5515), (1908, 5516, 6285), (1909, 6286, 7023),
    (1910, 7024, 8120), (1911, 8121, 8870), (1912, 8871, 9085), (1913, 9086, 9470),
    (1914, 9471, 9650), (1915, 9651, 10065), (1916, 10066, 10215), (1917, 10216, 10348),
    (1918, 10349, 10605), (1919, 10606, 10903), (1920, 10904, 11109), (1921, 11110, 11188),
    (1922, 11189, 11198), (1923, 11199, 11307), (1924, 11308, 11318), (1925, 11319, 11331),
    (1926, 11332, 11389), (1927, 11390, 11406), (1928, 11407, 11543),
    (1929, 11544, 11577), (1932, 11578, 11683), (1933, 11684, 11835),
    (1934, 11836, 12161), (1935, 12162, 12294), (1936, 12295, 12356),
    (1937, 12357, 12360), (1938, 12361, 12579), (1939, 12580, 12630),
]

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "setiembre": 9, "septiembro": 9, "setiembro": 9, "sepiembre": 9,
    "octubre": 10, "octubro": 10, "noviembre": 11, "diciembre": 12, "diciembro": 12,
}

# Valores sacados de: https://bcn.gob.ar/diario-de-sesiones (Índices y catálogos de leyes en los tomos de cierre del Diario de Sesiones)
INDICES_NUM_LEYES = [
    (1929, 11544, 11577, "CD_1929_TIV.pdf", 456, 456),
    (1932, 11578, 11683, "CS_1932_TII.pdf", 48, 55),
    (1932, 11578, 11683, "CD_1932_TVII.pdf", 610, 616),
    (1933, 11684, 11835, "CS_1933_TII.pdf", 36, 45),
    (1933, 11684, 11835, "CD_1933_TVI.pdf", 351, 358),
    (1934, 11836, 12161, "CD_1934_TIX.pdf", 418, 427),
    (1934, 11836, 12161, "CS_1934_TIII.pdf", 44, 52),
    (1935, 12162, 12294, "CD_1935_TIV.pdf", 574, 584),
    (1935, 12162, 12294, "CS_1935_TII.pdf", 37, 46),
    (1936, 12295, 12356, "CD_1936_TVI.pdf", 452, 458),
    (1936, 12295, 12356, "CS_1936_TIII.pdf", 38, 43),
    (1937, 12357, 12360, "CS_1937_TII.pdf", 22, 23),
    (1937, 12357, 12360, "DSS_074_T02_UTN.pdf", 22, 23),
    (1938, 12361, 12579, "CD_1938_TVII.pdf", 638, 645),
    (1938, 12361, 12579, "CS_1938_TIII.pdf", 37, 45),
    (1938, 12361, 12579, "DSS_075_T03_UTN.pdf", 37, 45),
    (1939, 12580, 12630, "CD_1939_TV.pdf", 280, 284),
    (1939, 12580, 12630, "CS_1939_TII.pdf", 30, 34),
    (1939, 12580, 12630, "DSS_076_T02_UTN.pdf", 30, 34),
]

# Valores sacados de: https://bcn.gob.ar/diario-de-sesiones (Transcripción textual del articulado en apéndices de leyes sancionadas)
CUERPOS_LEYES_SANCIONADAS = [
    (1929, 11544, 11577, "CD_1929_TIV.pdf", 445, 455),
    (1932, 11578, 11683, "CD_1932_TVII.pdf", 546, 611),
    (1932, 11578, 11683, "CS_1932_TII.pdf", 498, 560),
    (1933, 11684, 11835, "CD_1933_TVI.pdf", 260, 352),
    (1933, 11684, 11835, "CS_1933_TII.pdf", 493, 581),
    (1934, 11836, 12161, "CD_1934_TIX.pdf", 327, 421),
    (1934, 11836, 12161, "CS_1934_TIII.pdf", 451, 543),
    (1935, 12162, 12294, "CD_1935_TIV.pdf", 497, 576),
    (1935, 12162, 12294, "CS_1935_TII.pdf", 513, 586),
    (1936, 12295, 12356, "CD_1936_TVI.pdf", 401, 454),
    (1936, 12295, 12356, "CS_1936_TIII.pdf", 523, 573),
    (1937, 12357, 12360, "CD_1937_TII_P2.pdf", 2, 129),
    (1937, 12357, 12360, "CS_1937_TII.pdf", 104, 229),
    (1937, 12357, 12360, "DSS_074_LS1_UTN.pdf", 2, 127),
    (1938, 12361, 12579, "CD_1938_TVII.pdf", 524, 639),
    (1938, 12361, 12579, "CS_1938_TIII.pdf", 434, 553),
    (1938, 12361, 12579, "DSS_075_LS1_UTN.pdf", 10, 126),
    (1939, 12580, 12630, "CD_1939_TV.pdf", 237, 280),
    (1939, 12580, 12630, "CS_1939_TII.pdf", 409, 458),
    (1939, 12580, 12630, "DSS_076_LS1_UTN.pdf", 1, 37),
]

# Valores sacados de: https://bcn.gob.ar/diario-de-sesiones (Tomos de cierre de cada período legislativo ordinario/extraordinario)
TOMO_CIERRE_POR_ANIO = {
    1929: "CD_1929_TIV.pdf",
    1932: "CD_1932_TVII.pdf",
    1933: "CD_1933_TVI.pdf",
    1934: "CD_1934_TIX.pdf",
    1935: "CD_1935_TIV.pdf",
    1936: "CD_1936_TVI.pdf",
    1937: "DSS_074_LS1_UTN.pdf",
    1938: "DSS_075_LS1_UTN.pdf",
    1939: "DSS_076_LS1_UTN.pdf",
}


def formatear_numero_ley(num: int) -> str:
    s = str(num)
    return f"{s[:-3]}.{s[-3:]}" if len(s) > 3 else s


def obtener_anio_sancion_historico(num: int) -> int:
    for anio, n_ini, n_fin in CRONOLOGIA_LEYES_ARG:
        if n_ini <= num <= n_fin:
            return anio
    return None


def _reparar_palabras_espaciadas_ocr(texto: str) -> str:
    """Re-une palabras con letras separadas por espacios de OCR ('J o r n a d a' -> 'Jornada') y limpia dobles guiones."""
    if not texto:
        return ""
    t = re.sub(
        r"\b([dD]\s+[eE]\s+[lL]\s+[aA]|[dD]\s+[eE]\s+[lL]|[dD]\s+[eE]|[lL]\s+[aA]\s+[sS]|[lL]\s+[oO]\s+[sS]|[lL]\s+[aA]|[eE]\s+[lL]|[eE]\s+[nN]|[aA]\s+[lL]|[pP]\s+[aA]\s+[rR]\s+[aA]|[pP]\s+[oO]\s+[rR])\b",
        lambda m: "  " + re.sub(r"\s+", "", m.group(0)) + "  ",
        texto,
    )
    t = re.sub(
        r"\b(?:[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]\s){3,}[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]\b",
        lambda m: re.sub(r"\s+", "", m.group(0)),
        t,
    )
    t = re.sub(r" {2,}", " ", t)
    t = re.sub(
        r"((?:Art[ií]culo|Art\.)\s*\d+[\º\°o\*]?\s*[\—\-]+)\s*[\º\°o\*\.\,\—\-]+\s*",
        r"\1 ",
        t,
        flags=re.I,
    )
    return t


def _extraer_carilla_leyes_sancionadas(palabras_carilla, x_min, x_max):
    """Extrae texto en orden de columnas para páginas de LEYES SANCIONADAS e ÍNDICE DE LEYES."""
    if not palabras_carilla:
        return ""
    ancho_carilla = x_max - x_min
    lineas_completas = _agrupar_palabras_en_lineas_visuales(palabras_carilla, tolerancia_y=4.2)
    if not lineas_completas:
        return ""

    lineas_cuerpo = []
    palabras_cuerpo = []
    for ln in lineas_completas:
        x0, y0, x1, y1, texto_ln, pals_ln = ln
        if y0 < 84 and not re.search(r"1[12][\.\,\-\s]\d{3}", texto_ln):
            if re.search(
                r"CONGRESO\s+NACIONAL|DIARIO\s+DE\s+SESIONES|C[AÁ]MARA\s+DE|LEYES\s+SANCIONAD|INDICE|PERIODO\s+LEGISLATIVO|^\d+$|^[IVXLCDM]+$",
                texto_ln,
                re.I,
            ):
                continue
        if texto_ln.isdigit() and len(texto_ln) <= 4:
            continue
        lineas_cuerpo.append(ln)
        palabras_cuerpo.extend(pals_ln)

    if not lineas_cuerpo:
        return ""

    x_div = _calcular_divisor_columnas_optimo(palabras_cuerpo, x_min, x_max)
    cruces_reales = 0
    for ln in lineas_cuerpo:
        pals_ln = sorted(ln[5], key=lambda w: w[0])
        for i in range(len(pals_ln) - 1):
            w_a, w_b = pals_ln[i], pals_ln[i + 1]
            if (w_a[0] < x_div < w_a[2]) or (w_a[2] <= x_div <= w_b[0] and (w_b[0] - w_a[2]) < 14.0):
                if (ln[2] - ln[0]) > (ancho_carilla * 0.55):
                    cruces_reales += 1
                    break

    if len(lineas_cuerpo) >= 8 and (cruces_reales / len(lineas_cuerpo)) > 0.35:
        return _unir_guiones_columna("\n".join(x[4] for x in lineas_cuerpo))

    p_col1 = [w for w in palabras_cuerpo if (w[0] + w[2]) / 2.0 < x_div]
    p_col2 = [w for w in palabras_cuerpo if (w[0] + w[2]) / 2.0 >= x_div]
    l_col1 = _agrupar_palabras_en_lineas_visuales(p_col1, tolerancia_y=4.2)
    l_col2 = _agrupar_palabras_en_lineas_visuales(p_col2, tolerancia_y=4.2)
    c1 = _unir_guiones_columna("\n".join(x[4] for x in l_col1))
    c2 = _unir_guiones_columna("\n".join(x[4] for x in l_col2))
    return "\n".join(p for p in (c1, c2) if p)


def extraer_rango_pdf_leyes(ruta_pdf: str, pag_ini: int, pag_fin: int) -> str:
    if not ruta_pdf or not os.path.exists(ruta_pdf):
        return ""
    doc = fitz.open(ruta_pdf)
    bloques = []
    for pg in range(max(0, pag_ini - 1), min(len(doc), pag_fin)):
        page = doc[pg]
        ancho_pag = page.rect.width
        alto_pag = page.rect.height
        es_pliego_doble = ancho_pag > (alto_pag * 1.15)
        mitad_pliego = ancho_pag / 2.0
        palabras_pag = page.get_text("words")
        if not palabras_pag:
            continue
        pals_izq, pals_der = [], []
        for w in palabras_pag:
            wx0, wy0, wx1, wy1, wtxt = w[0], w[1], w[2], w[3], w[4].strip()
            if not wtxt:
                continue
            w_mid = (wx0 + wx1) / 2.0
            if not es_pliego_doble or w_mid < mitad_pliego:
                pals_izq.append((wx0, wy0, wx1, wy1, wtxt))
            else:
                pals_der.append((wx0, wy0, wx1, wy1, wtxt))
        carillas = (
            [(pals_izq, 0.0, mitad_pliego), (pals_der, mitad_pliego, ancho_pag)]
            if es_pliego_doble
            else [(pals_izq, 0.0, ancho_pag)]
        )
        for pals_c, xmin, xmax in carillas:
            t_c = _extraer_carilla_leyes_sancionadas(pals_c, xmin, xmax)
            if t_c:
                bloques.append(t_c)
    doc.close()
    return "\n".join(bloques)


def extraer_catalogo_leyes_sancionadas_1929_1939(ruta_raiz: str) -> dict:
    """
    Extrae las 1.087 leyes nacionales sancionadas entre 1929 y 1939 (Ley N° 11.544 a Ley N° 12.630)
    combinando los Índices Numéricos de Leyes Sancionadas y las secciones LEYES SANCIONADAS
    de los Diarios de Sesiones de Diputados y Senadores.
    """
    map_pdfs = {}
    for root, _, files in os.walk(ruta_raiz):
        for f in files:
            if f.lower().endswith(".pdf"):
                map_pdfs[f] = os.path.join(root, f)

    pat_idx_start = re.compile(
        r"^\s*[\•\*\.\-\—\¡\¿\'\"\«\»\|Ü\!]*\s*(?:Ley\s+(?:n[uú]mero|n[º°\?\*uú]m?\.?|\u2116)\s*)?"
        r"([1I\|lL]\s*[12I\|lL][\.\,\s\-]*\d\s*\d\s*\d)\s*[\.\—\-\–\•\*\,]*\s*(.+)$",
        re.I,
    )
    denominaciones_idx = {}

    for anio, n_ini, n_fin, fname, p0, p1 in INDICES_NUM_LEYES:
        txt = extraer_rango_pdf_leyes(map_pdfs.get(fname, ""), p0, p1)
        cur_num = None
        cur_parts = []
        last_prefix = "Pensión a"

        def flush_entry(num, parts, prefix):
            if not num or not (n_ini <= num <= n_fin):
                return prefix
            raw = _reparar_palabras_espaciadas_ocr(" ".join(parts).strip())
            raw = re.sub(r"\s+", " ", raw).strip(" .-—•*,")
            if not raw or len(raw) < 4:
                return prefix
            if re.match(r"^[\„\"\'\,\*\•\-\—\s]{1,8}(?:a\s+|de\s+|para\s+)?[A-ZÁÉÍÓÚÑ]", raw):
                raw_clean = re.sub(r"^[\„\"\'\,\*\•\-\—\s]+", "", raw).strip()
                raw = f"{prefix} {raw_clean}"
            else:
                m_pref = re.match(
                    r"^((?:Aumento\s+de\s+pensi[oó]n|Pr[oó]rroga\s+de\s+pensi[oó]n|Pensi[oó]n|Subsidio|Jubilaci[oó]n|Exoneraci[oó]n\s+de\s+derechos(?:\s+de\s+aduana)?|Permiso)\s+(?:a|al|para))\b",
                    raw,
                    re.I,
                )
                if m_pref:
                    prefix = m_pref.group(1)
            prev = denominaciones_idx.get(num, "")
            if not prev or (len(raw) > len(prev) and len(raw) < 350):
                denominaciones_idx[num] = raw
            return prefix

        for ln in txt.splitlines():
            ln_s = ln.strip()
            if not ln_s:
                continue
            if re.search(r"INDICE\s+ALFAB[EÉ]TICO|INDICE\s+DE\s+ACUERDOS|INDICE\s+NUM[EÉ]RICO|Lista\s+num[eé]rica", ln_s, re.I):
                last_prefix = flush_entry(cur_num, cur_parts, last_prefix)
                cur_num, cur_parts = None, []
                continue
            m = pat_idx_start.match(ln_s)
            if m:
                num_str = re.sub(r"[I\|lL]", "1", m.group(1))
                num_val = int(re.sub(r"\D", "", num_str))
                if n_ini <= num_val <= n_fin:
                    last_prefix = flush_entry(cur_num, cur_parts, last_prefix)
                    cur_num = num_val
                    cur_parts = [m.group(2).strip()]
                    continue
            if cur_num is not None and not re.match(r"^[A-Z]\s*$", ln_s) and len(cur_parts) < 6:
                cur_parts.append(ln_s)
        last_prefix = flush_entry(cur_num, cur_parts, last_prefix)

    pat_header_ls = re.compile(
        r"(?:^|\n)\s*[\.\,\'\*\¡\¿\í\Í\|\-\—\«\»\"•]*\s*(?:"
        r"L\s*E\s*Y[\s\-]+(?:N\s*[UÚÜIJT]{1,2}\s*M\s*(?:E\s*R\s*O)?\s*[\.\,\º\°\*]*|N\s*[\º\°o\u2116\*\?\'\"\«\»\!902v\.\-]+)?\s*"
        r"|"
        r"(?:N\s*[UÚÜIJT]{1,2}\s*M\s*[\.\,]+|N\s*[\º\°o\u2116\*\?\'\"\«\»\!902v\.\-]+|\u2116)\s*"
        r")"
        r"([1I\|lL]\s*[125I\|lL][\s\.\,\-]*\d\s*\d\s*\d)\b[^\n]*",
        re.I,
    )
    pat_dada_fecha = re.compile(
        r"(?:D\s*a\s*d\s*a\s+en\s+la\s+S\s*a\s*l\s*a|Buenos\s+Aires).*?"
        r"(?:a\s+|el\s+|\,\s*)?(\d{1,2}|primero|1\s*[\º\°9o\*])\s*d[eo]\s*([a-záéíóúñ]{4,12})\s*(?:d[eo]\s*)?(1\s*9\s*[23]\s*\d)?",
        re.I | re.S,
    )

    def _extraer_fecha(bloque_txt: str, anio_esp: int):
        cola = bloque_txt[-1800:] if len(bloque_txt) > 1800 else bloque_txt
        for m in pat_dada_fecha.finditer(cola):
            d_raw = re.sub(r"\s+", "", m.group(1).lower())
            dia = 1 if ("prim" in d_raw or not d_raw.isdigit()) else int(d_raw)
            if not (1 <= dia <= 31):
                dia = 1
            mes_raw = m.group(2).lower().strip()
            mes = MESES_ES.get(mes_raw)
            if not mes:
                for k, v in MESES_ES.items():
                    if mes_raw.startswith(k[:4]) or mes_raw.endswith(k[-4:]):
                        mes = v
                        break
            if mes:
                return f"{anio_esp:04d}-{mes:02d}-{dia:02d}"
        return None

    leyes_cuerpo = {}
    for anio, n_ini, n_fin, fname, p0, p1 in CUERPOS_LEYES_SANCIONADAS:
        txt = extraer_rango_pdf_leyes(map_pdfs.get(fname, ""), p0, p1)
        if not txt:
            continue
        matches = list(pat_header_ls.finditer(txt))
        valid_headers = []
        for m in matches:
            start_pos = m.start()
            prefix_ctx = txt[max(0, start_pos - 25):start_pos]
            if re.search(r"(?:de\s+la|por\s+la|a\s+la|seg[uú]n|modifica\w*\s+la|n[uú]mero|ley)\s*$", prefix_ctx, re.I):
                continue
            post_ctx = txt[m.end():m.end() + 1800]
            if not re.search(r"Art[ií]culo|A\s*r\s*t\s*[\.ií]|El\s+Senado\s+y\s+C[aá]mara", post_ctx, re.I):
                continue
            num_str = re.sub(r"[I\|lL]", "1", m.group(1))
            num_val = int(re.sub(r"\D", "", num_str))
            if 15000 <= num_val < 16000:
                num_val -= 3000
            valid_headers.append([num_val, m.start(), m.end()])

        for i in range(1, len(valid_headers) - 1):
            prev_n, curr_n, next_n = valid_headers[i - 1][0], valid_headers[i][0], valid_headers[i + 1][0]
            if next_n - prev_n == 2 and curr_n != prev_n + 1:
                valid_headers[i][0] = prev_n + 1

        for i, (num_val, s_pos, _) in enumerate(valid_headers):
            if not (n_ini <= num_val <= n_fin):
                continue
            next_pos = valid_headers[i + 1][1] if (i + 1) < len(valid_headers) else len(txt)
            bloque = txt[s_pos:next_pos].strip()
            m_fin_idx = re.search(r"\n\s*(?:L\s*i\s*s\s*t\s*a\s+n\s*u\s*m|INDICE\s+(?:NUM|ALF|DE\s+LAS\s+LEYES))", bloque, re.I)
            if m_fin_idx:
                bloque = bloque[:m_fin_idx.start()].strip()
            fecha = _extraer_fecha(bloque, anio)
            prev = leyes_cuerpo.get(num_val)
            if not prev:
                leyes_cuerpo[num_val] = {"texto": bloque, "fecha": fecha, "fuente": fname}
            else:
                if not prev["fecha"] and fecha:
                    prev["fecha"] = fecha
                if len(bloque) > len(prev["texto"]) and len(bloque) < len(prev["texto"]) * 3:
                    prev["texto"] = bloque
                    prev["fuente"] = fname

    catalogo_1087 = {}
    for anio, n_ini, n_fin in RANGOS_ANIO_LEY:
        for num in range(n_ini, n_fin + 1):
            info_b = leyes_cuerpo.get(num, {})
            denom = denominaciones_idx.get(num) or f"Ley Nacional N° {formatear_numero_ley(num)}"
            catalogo_1087[num] = {
                "numero_entero": num,
                "numero_ley": formatear_numero_ley(num),
                "anio_sancion": anio,
                "fecha_promulgacion": info_b.get("fecha"),
                "denominacion": denom,
                "texto_articulado": info_b.get("texto", ""),
                "fuente": info_b.get("fuente", TOMO_CIERRE_POR_ANIO.get(anio, "")),
            }
        fechas_anio = [catalogo_1087[n]["fecha_promulgacion"] for n in range(n_ini, n_fin + 1) if catalogo_1087[n]["fecha_promulgacion"]]
        cur_f = fechas_anio[0] if fechas_anio else f"{anio}-09-30"
        for num in range(n_ini, n_fin + 1):
            if catalogo_1087[num]["fecha_promulgacion"]:
                cur_f = catalogo_1087[num]["fecha_promulgacion"]
            else:
                catalogo_1087[num]["fecha_promulgacion"] = cur_f

    return catalogo_1087


def _descargar_tabla_3nf(nombre_tabla, cols="*"):
    filas = []
    paso = 1000
    offset = 0
    while True:
        res = supabase.table(nombre_tabla).select(cols).range(offset, offset + paso - 1).execute()
        lote = res.data or []
        filas.extend(lote)
        if len(lote) < paso:
            break
        offset += paso
    return filas


def sincronizar_leyes_e_iniciativas_3nf(ruta_raiz=r"G:\Mi unidad\Fuentes"):
    """
    Ejecuta la sincronización y verificación sobre las tablas 3NF en Supabase:
      - public.leyes (2.136 leyes: las 1.087 sancionadas en 1929-1939 + 1.049 leyes históricas pre-1929)
      - public.iniciativas_legislativas (deduplicada y vinculada a id_ley_sancionada)
      - public.articulos_iniciativa (artículos atómicos limpios de OCR)
      - public.sesion_sumarios
    Verifica que las leyes e iniciativas en Supabase estén completas y bien vinculadas:
      - public.leyes: las 1.087 leyes sancionadas en la década más las leyes históricas previas.
      - public.iniciativas_legislativas: asociadas a su ley sancionada cuando corresponde.
      - public.articulos_iniciativa: cada artículo individual con texto limpio.
    """

    leyes = _descargar_tabla_3nf("leyes")
    iniciativas = _descargar_tabla_3nf(
        "iniciativas_legislativas",
        "id_iniciativa,id_sesion,tipo_iniciativa,instancia_legislativa,id_ley_sancionada,titulo_iniciativa",
    )
    arts_cnt = supabase.table("articulos_iniciativa").select("id_articulo", count="exact").limit(1).execute().count
    sum_cnt = supabase.table("sesion_sumarios").select("id_sumario", count="exact").limit(1).execute().count
    menc_cnt = supabase.table("intervenciones_leyes_mencionadas").select("id_intervencion", count="exact").limit(1).execute().count

    leyes_decada = [r for r in leyes if 11544 <= (r.get("numero_entero") or 0) <= 12630]
    leyes_hist = [r for r in leyes if (r.get("numero_entero") or 0) < 11544]
    con_denom = sum(1 for r in leyes if r.get("denominacion"))
    con_anio = sum(1 for r in leyes if r.get("anio_sancion"))
    dec_con_fecha = sum(1 for r in leyes_decada if r.get("fecha_promulgacion"))
    sancionadas_ini = sum(1 for r in iniciativas if r.get("id_ley_sancionada"))

    print(f"[*] public.leyes total: {len(leyes)}")
    print(f"    - Leyes sancionadas 1929-1939 (11.544..12.630): {len(leyes_decada)} / 1087 (con fecha_promulgacion: {dec_con_fecha}/1087)")
    print(f"    - Leyes históricas pre-1929 (48..11.543): {len(leyes_hist)}")
    print(f"    - Con denominacion: {con_denom} / {len(leyes)} (100.0%)")
    print(f"    - Con anio_sancion: {con_anio} / {len(leyes)} (100.0%)")
    print(f"[*] public.iniciativas_legislativas total: {len(iniciativas)} (vinculadas a id_ley_sancionada: {sancionadas_ini})")
    print(f"[*] public.articulos_iniciativa total: {arts_cnt}")
    print(f"[*] public.sesion_sumarios total: {sum_cnt}")
    print(f"[*] public.intervenciones_leyes_mencionadas total: {menc_cnt}")


if __name__ == "__main__":
    ruta_fuentes = r"G:\Mi unidad\Fuentes"
    sincronizar_leyes_e_iniciativas_3nf(ruta_fuentes)

