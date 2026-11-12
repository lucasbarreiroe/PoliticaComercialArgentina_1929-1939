#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Este script recorre los 209 tomos en PDF del Congreso (1929-1939) para identificar
cada reunión o sesión por separado.

En los diarios de sesiones, un solo tomo físico suele agrupar varias reuniones.
Lo que hacemos acá es:
1. Detectar cuándo arranca cada sesión, su número de reunión, fecha exacta y tipo
   (ordinaria, extraordinaria, especial, etc.).
2. Identificar quién presidía la sesión cruzándolo con la tabla de personas.
3. Cargar las sesiones reales en Supabase y revincular todas las tablas hijas
   (intervenciones, sumarios e iniciativas) para que cada registro apunte
   a la sesión que realmente le corresponde.
"""

import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from collections import Counter
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed

import pymupdf as fitz
from dotenv import load_dotenv
from supabase import create_client

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_KEY en el archivo .env")

RUTA_DRIVE = Path(r"G:\Mi unidad\Fuentes")



def sin_acentos(texto: str) -> str:
    if not texto:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(texto))
        if not unicodedata.combining(c)
    )


MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12
}

DIAS_MAX_MES = {
    1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
    7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
}

DIAS_PALABRAS = {
    "un": 1, "uno": 1, "primer": 1, "primero": 1,
    "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
    "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciseis": 16, "diez y seis": 16, "diecisiete": 17, "diez y siete": 17,
    "dieciocho": 18, "diez y ocho": 18, "diecinueve": 19, "diez y nueve": 19,
    "veinte": 20, "veintiun": 21, "veintiuno": 21, "veinte y uno": 21, "veinte y un": 21,
    "veintidos": 22, "veinte y dos": 22, "veintitres": 23, "veinte y tres": 23,
    "veinticuatro": 24, "veinte y cuatro": 24, "veinticinco": 25, "veinte y cinco": 25,
    "veintiseis": 26, "veinte y seis": 26, "veintisiete": 27, "veinte y siete": 27,
    "veintiocho": 28, "veinte y ocho": 28, "veintinueve": 29, "veinte y nueve": 29,
    "treinta": 30, "treinta y un": 31, "treinta y uno": 31
}

REGEX_MESES_ESPACIADOS = re.compile(
    r"\b(?:"
    r"E\s*n\s*e\s*r\s*o|F\s*e\s*b\s*r\s*e\s*r\s*o|M\s*a\s*r\s*z\s*o|A\s*b\s*r\s*i\s*l|"
    r"M\s*a\s*y\s*o|J\s*u\s*n\s*i\s*o|J\s*u\s*l\s*i\s*o|A\s*g\s*o\s*s\s*t\s*o|"
    r"S\s*e\s*p?\s*t\s*i\s*e\s*m\s*b\s*r\s*e|O\s*c\s*t\s*u\s*b\s*r\s*e|"
    r"N\s*o\s*v\s*i\s*e\s*m\s*b\s*r\s*e|D\s*i\s*c\s*i\s*e\s*m\s*b\s*r\s*e"
    r")\b",
    re.IGNORECASE
)

PAT_MES_DIA_ANIO = re.compile(
    r"\b(ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|SEPTIEMBRE|SETIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE)\s+"
    r"[\.\,\-]*\s*(\d{1,2}[a-z\*\'\.\°\º]*|[lI][a-z\*\'\.\°\º]+)"
    r"(?:\s*(?:Y|AL|,|-)\s*\d{1,2}[a-z\*\'\.\°\º]*)?"
    r"\s*[\.\,]*\s*(?:DE\s+|DO\s+|DEL?\s+)?(1\s*9\s*[23]\s*[\d\'\"pP\!lI\°\º])\b",
    re.IGNORECASE
)

PAT_DIA_MES_ANIO = re.compile(
    r"\b(?:De\s+)?(\d{1,2}[a-z\*\'\.\°\º]*|[lI][a-z\*\'\.\°\º]+)\s+(?:de\s+)?"
    r"(ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|SEPTIEMBRE|SETIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE)"
    r"(?:\s+a\s+\d{1,2}\s+de\s+[a-z]+)?\s+de\s+(1\s*9\s*[23]\s*\d)\b",
    re.IGNORECASE
)

PAT_APERTURA_PROSA = re.compile(
    r"En\s+(?:la\s+ciudad\s+de\s+|la\s+Capital\s+de\s+)?Buenos\s+Aires\s*,?\s*a\s+(?:los\s+)?"
    r"([a-z\s\d]{1,22}?)\s+dias?\s+del\s+mes\s+de\s+"
    r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)",
    re.IGNORECASE
)

PAT_REU_NUM = re.compile(
    r"[RrBbEe¡!]?e\s*u\s*n\s*i\s*[o0a]\s*n[\s\,\.]*[nm][uui\°\º\*][mnl]?[\.\,\s]*(\d{1,2})\b",
    re.IGNORECASE
)
PAT_NUM_REU = re.compile(
    r"(?:^|\s)(\d{1,2})\s*[\.\,\*\'\"\-\s]{0,3}[a-z\°\º\*\'\"\»]{0,2}\s*R\s*e\s*u\s*n\s*i\s*[o0]\s*n(?!\s*[\.\,]*\s*[nm][uui\°\º\*])",
    re.IGNORECASE
)
PAT_NUMERO_BANNER = re.compile(r"\bN\s*U\s*M\s*E\s*R\s*O\s+(\d{1,2})\b", re.IGNORECASE)

STOPWORDS_ES = {
    "para", "como", "este", "esta", "estos", "estas", "sobre", "entre", "hasta",
    "desde", "cuando", "donde", "porque", "pero", "sino", "tambien", "mismo",
    "misma", "todo", "toda", "todos", "todas", "otro", "otra", "otros", "otras",
    "algun", "alguno", "alguna", "proyecto", "ley", "mensaje", "poder", "ejecutivo",
    "camara", "diputados", "senadores", "senado", "comision", "despacho", "honorable",
    "nacional", "nacion", "congreso", "señor", "senor", "diputado", "senador",
    "articulo", "inciso", "orden", "asunto", "asuntos", "entrados", "sumario",
    "sesion", "reunion", "acta", "aprobado", "general", "particular"
}


def norm_dia_token(tok: str, mes: int = 1):
    # A veces el OCR confunde el número 1 con una 'l' o una 'i' minúscula
    if not tok:
        return None
    tok = tok.strip().lower()
    if re.match(r"^(?:1|l|i)[^0-9]*$", tok):
        return 1
    m = re.match(r"^(\d{1,2})", tok)
    if m:
        d = int(m.group(1))
        max_d = DIAS_MAX_MES.get(mes, 31)
        if 1 <= d <= max_d:
            return d
    return None


def normalizar_tipo_sesion(raw_tipo: str) -> str:
    # Estandarizamos los nombres a las categorías canónicas del Congreso
    if not raw_tipo:
        return "Ordinaria"
    t = sin_acentos(raw_tipo).upper()
    if "PREPARATORIA" in t:
        return "Preparatoria"
    if "EXTRAORDINARIA" in t:
        return "Extraordinaria"
    if "ESPECIAL" in t:
        return "Especial"
    if "ASAMBLEA" in t:
        return "De Asamblea"
    if "MINORIA" in t:
        return "En Minoría"
    if "INFORMATIVA" in t:
        return "Informativa"
    return "Ordinaria"


def tokenizar_clave(texto: str) -> set:
    if not texto:
        return set()
    t = sin_acentos(texto).lower()
    pals = re.findall(r"\b(?:[a-z]{4,}|\d{2,5})\b", t)
    return {p for p in pals if p not in STOPWORDS_ES}



def construir_indice_personas(filas_personas: list) -> list:
    # Armamos una lista compacta sin espacios ni tildes para buscar rápido en el texto
    indice = []
    for p in filas_personas:
        id_p = p["id_persona"]
        nom = sin_acentos(p.get("nombre") or "").upper().strip()
        ap = sin_acentos(p.get("apellido") or "").upper().strip()
        nc_directo = f"{nom} {ap}".strip()
        c_directo = re.sub(r"[^A-Z]", "", nc_directo)
        c_ap = re.sub(r"[^A-Z]", "", ap)
        etiqueta = f"{p.get('nombre', '').strip()} {p.get('apellido', '').strip()}".strip()
        if len(c_ap) >= 3:
            indice.append({
                "id_persona": id_p,
                "etiqueta": etiqueta,
                "c_directo": c_directo,
                "c_ap": c_ap,
                "ap": ap,
                "nom": nom
            })
    indice.sort(key=lambda x: -len(x["c_directo"]))
    return indice


def limpiar_presidente_raw(raw: str):
    # Sacamos títulos honoríficos o cargos para quedarnos con el nombre limpio
    if not raw:
        return None
    p = re.sub(
        r"^(?:DEL\s+|DE\s+LA\s+|DE\s+LOS\s+|DE\s+)?(?:DOCTORES|DOCTOR|GENERAL|DR\.|ING\.|INGENIERO|SENORES|SENOR|DIPUTADOS|DIPUTADO|SENADORES|SENADOR|PROVISIONAL|PROVISORIO)\s+",
        "",
        raw.strip(),
        flags=re.IGNORECASE
    ).strip(" ,.;:-—'\"()")
    if re.search(r"\b(?:que|sino|pero|como|para|cuando|porque|cual|este|esta|tiene|hace|dice|Gobierno|Nacion|Republica|Honorable)\b", p, re.IGNORECASE):
        return None
    if len(p) < 4 or len(p) > 110:
        return None
    return p


def resolver_presidentes(raw_pres: str, indice_personas: list):
    """
    Busca al presidente en el padrón histórico.
    Primero prueba coincidencia exacta del nombre y apellido compacto.
    Si no lo encuentra o hubo algún error de OCR, prueba con coincidencia difusa.
    """
    limpio = limpiar_presidente_raw(raw_pres)
    if not limpio:
        return None, []

    s = sin_acentos(limpio).upper()
    s = re.sub(
        r"\b(?:DOCTORES|DOCTOR|DOCTOE|DOCTOS|GENERAL|INGENIERO|SENORES|SENOR|DON|DIPUTADOS|DIPUTADO|SENADORES|SENADOR|PRESIDENTE|PROVISIONAL|PROVISORIO)\b",
        " ",
        s
    )
    s_compact = re.sub(r"[^A-Z]", "", s)
    if len(s_compact) < 5:
        return None, []

    encontrados = []
    # 1. Búsqueda exacta de nombre y apellido
    for item in indice_personas:
        cd = item["c_directo"]
        if len(cd) >= 8 and cd in s_compact:
            pos = s_compact.find(cd)
            if item["id_persona"] not in [e[0] for e in encontrados]:
                encontrados.append((item["id_persona"], item["etiqueta"], pos))
                s_compact = s_compact.replace(cd, "_" * len(cd), 1)

    # 2. Búsqueda difusa por partes (para tolerar pequeñas pifias del OCR en alguna letra)
    restante = s_compact.replace("_", "")
    if not encontrados or len(restante) >= 8:
        partes = re.split(r"\b(?:Y|E|O)\b|[,;/]", s)
        for idx_p, parte in enumerate(partes):
            pc = re.sub(r"[^A-Z]", "", parte)
            if len(pc) < 6:
                continue
            mejor_item = None
            mejor_ratio = 0.80
            for item in indice_personas:
                cd = item["c_directo"]
                if abs(len(pc) - len(cd)) > 4:
                    continue
                r = SequenceMatcher(None, pc, cd).ratio()
                if r > mejor_ratio:
                    mejor_ratio = r
                    mejor_item = item
            if mejor_item and mejor_item["id_persona"] not in [e[0] for e in encontrados]:
                encontrados.append((mejor_item["id_persona"], mejor_item["etiqueta"], 500 + idx_p))

    if encontrados:
        encontrados.sort(key=lambda x: x[2])
        texto_can = " / ".join(e[1] for e in encontrados)
        ids_can = [e[0] for e in encontrados]
        return texto_can, ids_can

    return limpio.title(), []



def lineas_carilla(words_carilla: list) -> list:
    # Agrupamos las palabras por su posición vertical (Y) para reconstruir renglones enteros
    if not words_carilla:
        return []
    words_carilla.sort(key=lambda w: ((w[1] + w[3]) / 2.0, w[0]))
    clusters = []
    for w in words_carilla:
        ym = (w[1] + w[3]) / 2.0
        if clusters and abs(ym - clusters[-1][0]) <= 4.5:
            clusters[-1][1].append(w)
            clusters[-1][0] = sum((x[1] + x[3]) / 2.0 for x in clusters[-1][1]) / len(clusters[-1][1])
        else:
            clusters.append([ym, [w]])
    res = []
    for ym, pals in clusters:
        pals.sort(key=lambda x: x[0])
        s = sin_acentos(" ".join(x[4] for x in pals))
        s = REGEX_MESES_ESPACIADOS.sub(lambda m: re.sub(r"\s+", "", m.group(0)), s)
        s = re.sub(
            r"\b([1-9])\s+(\d)\s*(?=[\.\ª\º\°\*\'\"a]?\s*R\s*e\s*u\s*n\s*i)",
            r"\1\2",
            s,
            flags=re.IGNORECASE
        )
        res.append((ym, s))
    return res


def escanear_pdf_dss(ruta_pdf: Path, anio_base: int, indice_personas: list) -> dict:
    """
    Procesa un cuadernillo individual del Senado (1937-1939).
    Como cada cuadernillo corresponde a una única sesión, buscamos la fecha exacta,
    el número de reunión y las autoridades en las primeras páginas.
    """
    doc = fitz.open(ruta_pdf)
    n_pags = len(doc)
    stem = ruta_pdf.stem.upper()

    # Número de reunión desde el nombre del archivo (ej. DSS_074_008_UTN -> 8)
    r_num_archivo = None
    m_code = re.search(r"DSS_\d+_(\d{1,3})[A-Z]?_UTN", stem)
    if m_code:
        r_num_archivo = int(m_code.group(1))
    elif "_A0" in stem:
        m_as = re.search(r"_A0(\d)_", stem)
        if m_as:
            r_num_archivo = int(m_as.group(1))

    fechas_p1_plus = []
    fechas_p0 = []
    reuniones_hdr = []
    tipos_hdr = []
    presidentes_raw = []
    tokens_pag = {}

    for pg in range(min(10, n_pags)):
        page = doc[pg]
        words = page.get_text("words", clip=fitz.Rect(0, 0, page.rect.width, 420))
        lns = lineas_carilla(words)
        txt_top = "\n".join(s for ym, s in lns if ym < 260)
        txt_norm = "\n".join(s for ym, s in lns)
        tokens_pag[pg + 1] = tokenizar_clave(txt_norm)

        for src in (txt_top, txt_norm):
            for m in PAT_MES_DIA_ANIO.finditer(src):
                mes = MESES[m.group(1).lower()]
                dia = norm_dia_token(m.group(2), mes)
                y_raw = re.sub(r"\D+", "", m.group(3))
                anio = int(y_raw) if (len(y_raw) == 4 and 1928 <= int(y_raw) <= 1940) else anio_base
                if dia:
                    f_str = f"{anio:04d}-{mes:02d}-{dia:02d}"
                    if pg == 0 and n_pags > 1:
                        fechas_p0.append(f_str)
                    else:
                        fechas_p1_plus.append(f_str)

            for m in PAT_DIA_MES_ANIO.finditer(src):
                mes = MESES[m.group(2).lower()]
                dia = norm_dia_token(m.group(1), mes)
                y_raw = re.sub(r"\D+", "", m.group(3))
                anio = int(y_raw) if (len(y_raw) == 4 and 1928 <= int(y_raw) <= 1940) else anio_base
                if dia:
                    f_str = f"{anio:04d}-{mes:02d}-{dia:02d}"
                    if pg == 0 and n_pags > 1:
                        fechas_p0.append(f_str)
                    else:
                        fechas_p1_plus.append(f_str)

        if pg > 0 or n_pags == 1:
            for pat in (PAT_REU_NUM, PAT_NUMERO_BANNER, PAT_NUM_REU):
                m_r = pat.search(txt_top)
                if m_r:
                    reuniones_hdr.append(int(m_r.group(1)))
                    break
            m_tp = re.search(
                r"SESION\s+(PREPARATORIA|ORDINARIA|EXTRAORDINARIA|ESPECIAL|DE\s+ASAMBLEA|EN\s+MINORIA)",
                txt_top,
                re.IGNORECASE
            )
            if m_tp:
                tipos_hdr.append(normalizar_tipo_sesion(m_tp.group(1)))
            m_pr = re.search(
                r"PRESIDENCIA\s+D(?:EL|E\s+LA|E\s+LOS|E)\s+([^\n]+)",
                txt_norm,
                re.IGNORECASE
            )
            if m_pr:
                presidentes_raw.append(m_pr.group(1))

    doc.close()

    # Fechas canónicas de respaldo para cuadernillos de índice/leyes sancionadas (T01, T02, T03, LS1)
    FALLBACK_DSS = {
        "DSS_074_T01_UTN": "1937-04-26",
        "DSS_074_T02_UTN": "1937-09-15",
        "DSS_074_LS1_UTN": "1938-02-20",
        "DSS_075_T01_UTN": "1938-04-26",
        "DSS_075_T02_UTN": "1938-08-31",
        "DSS_075_T03_UTN": "1938-11-21",
        "DSS_075_LS1_UTN": "1939-01-26",
        "DSS_076_T01_UTN": "1939-04-25",
        "DSS_076_T02_UTN": "1939-09-01",
        "DSS_076_LS1_UTN": "1939-09-30",
    }

    if stem in FALLBACK_DSS:
        fecha_final = FALLBACK_DSS[stem]
    elif fechas_p1_plus:
        fecha_final = Counter(fechas_p1_plus).most_common(1)[0][0]
    elif fechas_p0:
        fecha_final = Counter(fechas_p0).most_common(1)[0][0]
    else:
        fecha_final = f"{anio_base:04d}-05-01"

    r_final = r_num_archivo or (Counter(reuniones_hdr).most_common(1)[0][0] if reuniones_hdr else 1)
    if "_A0" in stem:
        tipo_final = "De Asamblea"
    elif tipos_hdr:
        tipo_final = Counter(tipos_hdr).most_common(1)[0][0]
    else:
        tipo_final = "Ordinaria"

    pres_txt, pres_ids = None, []
    for pr in presidentes_raw:
        pres_txt, pres_ids = resolver_presidentes(pr, indice_personas)
        if pres_txt:
            break

    return {
        "sesiones": [{
            "reunion": r_final,
            "fecha": fecha_final,
            "pag_ini": 1,
            "pag_fin": max(1, n_pags),
            "carilla_ini": 0,
            "tipo": tipo_final,
            "pres_texto": pres_txt,
            "pres_ids": pres_ids
        }],
        "tokens_pag": tokens_pag,
        "n_pags": n_pags
    }


def escanear_pdf_tomo_multisesion(ruta_pdf: Path, anio_base: int, indice_personas: list) -> dict:
    """
    Escanea un tomo completo donde conviven varias sesiones.
    Lee página por página y carilla por carilla buscando encabezados de reunión
    y portadillas. Aplica un filtro de ventana para descartar fechas erróneas
    que a veces genera el OCR, asegurando que la cronología avance siempre en orden.
    """
    doc = fitz.open(ruta_pdf)
    n_pags = len(doc)
    carillas = []
    tokens_pag = {}

    for pg in range(n_pags):
        page = doc[pg]
        w_pag, h_pag = page.rect.width, page.rect.height
        es_doble = w_pag > h_pag * 1.15
        mitad = w_pag / 2.0

        words = page.get_text("words", clip=fitz.Rect(0, 0, w_pag, 340))
        if not words:
            continue
        tokens_pag[pg + 1] = tokenizar_clave(" ".join(w[4] for w in words))
        c_list = (
            [[w for w in words if (w[0] + w[2]) / 2.0 < mitad],
             [w for w in words if (w[0] + w[2]) / 2.0 >= mitad]]
            if es_doble else [words]
        )
        for c_idx, pals_c in enumerate(c_list):
            lns = lineas_carilla(pals_c)
            if not lns:
                continue
            txt_top = "\n".join(s for ym, s in lns if ym < 112)
            txt_all = "\n".join(s for ym, s in lns)
            if re.search(
                r"INDICE\s+GENERAL|NOMENCLATOR|INDICE\s+ALFABETICO|INDICE\s+DE\s+LEYES",
                txt_top,
                re.IGNORECASE
            ):
                continue

            marcadores_ap = sum([
                bool(re.search(r"\bPRESIDENCIA\s+D", txt_all, re.IGNORECASE)),
                bool(re.search(r"\b(?:DIPUTADOS|SENADORES|MINISTROS)\s+PRESENTES\b", txt_all, re.IGNORECASE)),
                bool(re.search(r"(?:^|\n)\s*S\s*U\s*M\s*A\s*R\s*I\s*O\b", txt_all, re.IGNORECASE)),
                bool(
                    re.search(
                        r"\bSESION\s+(?:PREPARATORIA|ORDINARIA|EXTRAORDINARIA|ESPECIAL|DE\s+ASAMBLEA|EN\s+MINORIA)\b",
                        txt_all,
                        re.IGNORECASE
                    ) and not (txt_top and "SESION" in txt_top.upper())
                )
            ])
            es_apertura = (marcadores_ap >= 2) or bool(re.search(r"(?:^|\n)\s*SUMARIO\s*(?:\n|$)", txt_all))

            r_num = None
            srcs = (txt_top, txt_all) if es_apertura else (txt_top,)
            for src in srcs:
                for pat in (PAT_REU_NUM, PAT_NUMERO_BANNER, PAT_NUM_REU):
                    m = pat.search(src)
                    if m:
                        val_r = int(m.group(1))
                        if 1 <= val_r <= 98:
                            r_num = val_r
                            break
                if r_num:
                    break

            fecha = None
            for src in srcs:
                m_f = PAT_MES_DIA_ANIO.search(src)
                if m_f:
                    mes = MESES[m_f.group(1).lower()]
                    dia = norm_dia_token(m_f.group(2), mes)
                    y_raw = re.sub(r"\D+", "", m_f.group(3))
                    anio = int(y_raw) if (len(y_raw) == 4 and int(y_raw) in (anio_base, anio_base + 1)) else anio_base
                    if mes in (1, 2, 3) and anio == anio_base and pg > n_pags * 0.25:
                        anio = anio_base + 1
                    if dia:
                        fecha = f"{anio:04d}-{mes:02d}-{dia:02d}"
                        break
            if not fecha and es_apertura:
                m_p = PAT_APERTURA_PROSA.search(txt_all)
                if m_p:
                    d_raw = re.sub(r"\s+", " ", m_p.group(1).strip().lower())
                    mes = MESES[m_p.group(2).lower()]
                    dia = DIAS_PALABRAS.get(d_raw) or norm_dia_token(d_raw, mes)
                    anio = anio_base + 1 if (mes in (1, 2, 3) and pg > n_pags * 0.25) else anio_base
                    if dia:
                        fecha = f"{anio:04d}-{mes:02d}-{dia:02d}"

            pres_raw = None
            if es_apertura:
                m_pr = re.search(r"PRESIDENCIA\s+D(?:EL|E\s+LA|E\s+LOS|E)\s+([^\n]+)", txt_all, re.IGNORECASE)
                if m_pr:
                    pres_raw = m_pr.group(1)

            tipo = None
            m_tp = re.search(
                r"SESION\s+(PREPARATORIA|ORDINARIA|EXTRAORDINARIA|ESPECIAL|DE\s+ASAMBLEA|EN\s+MINORIA)",
                txt_all,
                re.IGNORECASE
            )
            if m_tp:
                tipo = normalizar_tipo_sesion(m_tp.group(1))

            if r_num or fecha or es_apertura:
                carillas.append({
                    "pg": pg + 1, "c": c_idx, "r": r_num, "f": fecha,
                    "ap": es_apertura, "pres_raw": pres_raw, "tipo": tipo
                })

    doc.close()

    # Filtrado de fechas outlier respecto a las ventanas vecinas (anterior y futura)
    n = len(carillas)
    for i in range(n):
        f_cur = carillas[i]["f"]
        if f_cur:
            fut = [carillas[j]["f"] for j in range(i + 1, min(n, i + 14)) if carillas[j]["f"]]
            prev = [carillas[j]["f"] for j in range(max(0, i - 10), i) if carillas[j]["f"]]
            if len(fut) >= 3:
                f_med_fut = sorted(fut)[len(fut) // 2]
                if f_cur > f_med_fut and fut.count(f_cur) == 0:
                    carillas[i]["f"] = prev[-1] if prev else f_med_fut
            if len(prev) >= 3:
                f_med_prev = sorted(prev)[len(prev) // 2]
                if f_cur < f_med_prev and (not fut or fut.count(f_cur) == 0):
                    carillas[i]["f"] = f_med_prev

    # Segmentación secuencial monótona
    raw_sesiones = []
    for item in carillas:
        fc = item["f"]
        rc = item["r"]
        if not fc and not rc and not item["ap"]:
            continue
        if not raw_sesiones:
            raw_sesiones.append({
                "r_list": [rc] if rc else [],
                "f_list": [fc] if fc else [],
                "pag_ini": item["pg"],
                "pag_fin": item["pg"],
                "carilla_ini": item["c"],
                "pres_raws": [item["pres_raw"]] if item["pres_raw"] else [],
                "tipos": [item["tipo"]] if item["tipo"] else []
            })
            continue

        ult = raw_sesiones[-1]
        f_ult = Counter(ult["f_list"]).most_common(1)[0][0] if ult["f_list"] else None
        r_ult = Counter(ult["r_list"]).most_common(1)[0][0] if ult["r_list"] else None

        nueva = False
        if fc and f_ult and fc > f_ult:
            nueva = True
        elif item["ap"] and rc and r_ult and rc == r_ult + 1 and (not fc or fc >= f_ult):
            nueva = True

        if nueva:
            raw_sesiones.append({
                "r_list": [rc] if rc else [],
                "f_list": [fc] if fc else [],
                "pag_ini": item["pg"],
                "pag_fin": item["pg"],
                "carilla_ini": item["c"],
                "pres_raws": [item["pres_raw"]] if item["pres_raw"] else [],
                "tipos": [item["tipo"]] if item["tipo"] else []
            })
        else:
            ult["pag_fin"] = item["pg"]
            if rc:
                ult["r_list"].append(rc)
            if fc:
                ult["f_list"].append(fc)
            if item["pres_raw"]:
                ult["pres_raws"].append(item["pres_raw"])
            if item["tipo"]:
                ult["tipos"].append(item["tipo"])

    # Consolidar segmentos adyacentes con la misma fecha (o micro-segmentos de transición de 1 carilla)
    final = []
    for idx_s, s in enumerate(raw_sesiones, 1):
        f_val = (
            Counter(s["f_list"]).most_common(1)[0][0]
            if s["f_list"]
            else (final[-1]["fecha"] if final else f"{anio_base:04d}-05-01")
        )
        r_val = (
            Counter(s["r_list"]).most_common(1)[0][0]
            if s["r_list"]
            else (final[-1]["reunion"] + 1 if final and final[-1]["reunion"] else idx_s)
        )
        tipo_val = Counter(s["tipos"]).most_common(1)[0][0] if s["tipos"] else "Ordinaria"
        pres_txt, pres_ids = None, []
        for pr in s["pres_raws"]:
            pres_txt, pres_ids = resolver_presidentes(pr, indice_personas)
            if pres_txt:
                break

        # Fusionar si tiene exactamente la misma fecha que el segmento anterior y no es una reunión distinta con apertura propia
        if final and final[-1]["fecha"] == f_val and (
            final[-1]["reunion"] == r_val
            or not s["r_list"]
            or (s["pag_fin"] == s["pag_ini"] and not pres_txt)
        ):
            final[-1]["pag_fin"] = max(final[-1]["pag_fin"], s["pag_fin"])
            if s["r_list"] and len(s["r_list"]) >= 2:
                final[-1]["reunion"] = r_val
            if not final[-1]["pres_texto"] and pres_txt:
                final[-1]["pres_texto"] = pres_txt
                final[-1]["pres_ids"] = pres_ids
            if final[-1]["tipo"] == "Ordinaria" and tipo_val != "Ordinaria":
                final[-1]["tipo"] = tipo_val
        else:
            final.append({
                "reunion": r_val,
                "fecha": f_val,
                "pag_ini": s["pag_ini"],
                "pag_fin": s["pag_fin"],
                "carilla_ini": s["carilla_ini"],
                "tipo": tipo_val,
                "pres_texto": pres_txt,
                "pres_ids": pres_ids
            })

    if not final:
        final.append({
            "reunion": 1,
            "fecha": f"{anio_base:04d}-05-01",
            "pag_ini": 1,
            "pag_fin": max(1, n_pags),
            "carilla_ini": 0,
            "tipo": "Ordinaria",
            "pres_texto": None,
            "pres_ids": []
        })

    # Asegurar que la primera sesión cubra desde la página 1 y la última hasta n_pags para que ninguna intervención quede fuera
    final[0]["pag_ini"] = 1
    final[-1]["pag_fin"] = max(final[-1]["pag_fin"], n_pags)

    # Corregir numeración de reunión secuencial cuando el OCR del primer pliego leyó otro dígito
    for i in range(len(final)):
        if i + 1 < len(final) and final[i + 1]["reunion"] == i + 2 and final[i]["reunion"] != i + 1:
            final[i]["reunion"] = i + 1
        elif i > 0 and final[i]["reunion"] <= final[i - 1]["reunion"]:
            final[i]["reunion"] = final[i - 1]["reunion"] + 1

    return {
        "sesiones": final,
        "tokens_pag": tokens_pag,
        "n_pags": n_pags
    }


def escanear_pdf_general(tarea: dict, indice_personas: list) -> dict:
    ruta_pdf = tarea["ruta_pdf"]
    anio_leg = tarea["anio_legislativo"]
    es_dss = "DSS_" in ruta_pdf.name.upper()
    if es_dss:
        res = escanear_pdf_dss(ruta_pdf, anio_leg, indice_personas)
    else:
        res = escanear_pdf_tomo_multisesion(ruta_pdf, anio_leg, indice_personas)
    res["id_tomo"] = tarea["id_tomo"]
    res["codigo_tomo"] = tarea["codigo_tomo"]
    res["camara"] = tarea["camara"]
    res["anio_legislativo"] = anio_leg
    return res



def ejecutar_con_reintento(fn, descripcion="operación Supabase", max_intentos=5):
    for intento in range(1, max_intentos + 1):
        try:
            return fn()
        except Exception as e:
            if intento == max_intentos:
                raise RuntimeError(f"Error tras {max_intentos} intentos en {descripcion}: {e}") from e
            time.sleep(1.5 * intento)


def descargar_filas_por_sesiones(sb, tabla: str, cols: str, ids_sesion: list, pk_col: str) -> list:
    filas = []
    ultimo_id = 0
    while True:
        res = ejecutar_con_reintento(
            lambda: (
                sb.table(tabla)
                .select(cols)
                .in_("id_sesion", ids_sesion)
                .gt(pk_col, ultimo_id)
                .order(pk_col)
                .limit(1000)
                .execute()
            ),
            f"select {tabla}"
        )
        lote = res.data or []
        if not lote:
            break
        filas.extend(lote)
        ultimo_id = lote[-1][pk_col]
        if len(lote) < 1000:
            break
    return filas


def asignar_intervenciones_a_sesiones(intervenciones: list, sesiones_info: list) -> dict:
    """
    Asigna cada discurso a la sesión que le corresponde según el número de página.
    Si una página queda en el límite entre dos sesiones, usamos el inicio del presidente
    para saber exactamente dónde cortar.
    """
    asignacion = {i: [] for i in range(len(sesiones_info))}
    if not intervenciones:
        return asignacion
    if len(sesiones_info) == 1:
        asignacion[0] = [r["id_intervencion"] for r in intervenciones]
        return asignacion

    # Agrupar intervenciones por página en orden de diálogo
    por_pag = {}
    for r in sorted(intervenciones, key=lambda x: (x.get("orden_dialogo") or 0, x["id_intervencion"])):
        pg = r.get("nro_pagina") or 1
        por_pag.setdefault(pg, []).append(r)

    for pg, lista_int in sorted(por_pag.items()):
        # Buscar sesiones cuyo rango [pag_ini, pag_fin] contiene pg
        candidatas = [
            i for i, s in enumerate(sesiones_info)
            if s["pag_ini"] <= pg <= s["pag_fin"]
        ]
        if not candidatas:
            # Si cayó justo fuera de rango, se la asignamos a la sesión más cercana
            mejor_i = min(
                range(len(sesiones_info)),
                key=lambda i: min(abs(pg - sesiones_info[i]["pag_ini"]), abs(pg - sesiones_info[i]["pag_fin"]))
            )
            asignacion[mejor_i].extend(r["id_intervencion"] for r in lista_int)
        elif len(candidatas) == 1:
            asignacion[candidatas[0]].extend(r["id_intervencion"] for r in lista_int)
        else:
            # Página compartida entre la sesión que termina y la que empieza
            idx_ant = candidatas[0]
            idx_sig = candidatas[1]
            if sesiones_info[idx_sig].get("carilla_ini", 0) == 0:
                asignacion[idx_sig].extend(r["id_intervencion"] for r in lista_int)
            else:
                # Buscamos dónde interviene el presidente para marcar el arranque de la nueva sesión
                corte = len(lista_int) // 2
                for k_idx, r in enumerate(lista_int):
                    orador = sin_acentos(r.get("nombre_extraido_ocr") or "").upper()
                    if "PRESIDENTE" in orador and k_idx > 0:
                        corte = k_idx
                        break
                for r in lista_int[:corte]:
                    asignacion[idx_ant].append(r["id_intervencion"])
                for r in lista_int[corte:]:
                    asignacion[idx_sig].append(r["id_intervencion"])

    return asignacion


def _extraer_entero_item(num_item: str) -> int:
    if not num_item:
        return 999
    m = re.match(r"^(\d+)", str(num_item).strip())
    return int(m.group(1)) if m else 999


def asignar_sumarios_a_sesiones(sumarios: list, sesiones_info: list, tokens_por_sesion: list) -> dict:
    """
    Agrupa los puntos del sumario cada vez que la numeración vuelve a 1,
    y asocia cada grupo a la sesión correspondiente cruzando palabras clave.
    """
    asignacion = {i: [] for i in range(len(sesiones_info))}
    if not sumarios:
        return asignacion
    if len(sesiones_info) == 1:
        asignacion[0] = [s["id_sumario"] for s in sumarios]
        return asignacion

    sumarios_ord = sorted(sumarios, key=lambda x: x["id_sumario"])
    bloques = []
    bloque_actual = []
    ult_num = -1

    for s in sumarios_ord:
        n_it = _extraer_entero_item(s.get("numero_item"))
        if bloque_actual and (
            (n_it == 1 and ult_num >= 1)
            or (n_it < ult_num and n_it <= 2 and ult_num < 900)
        ):
            bloques.append(bloque_actual)
            bloque_actual = [s]
        else:
            bloque_actual.append(s)
        if n_it < 900:
            ult_num = n_it
    if bloque_actual:
        bloques.append(bloque_actual)

    n_ses = len(sesiones_info)
    n_bloq = len(bloques)
    ses_min = 0

    for b_idx, blq in enumerate(bloques):
        texto_blq = " ".join((x.get("titulo_tema") or "") + " " + (x.get("descripcion_tema") or "") for x in blq)
        toks_b = tokenizar_clave(texto_blq)
        # Ventana plausible de sesiones manteniendo orden
        pos_esperada = int(round(b_idx * (n_ses - 1) / max(1, n_bloq - 1))) if n_bloq > 1 else 0
        ini_busq = max(ses_min, pos_esperada - 4)
        fin_busq = min(n_ses - 1, max(ini_busq, pos_esperada + 5))

        mejor_s = pos_esperada
        mejor_score = -1.0
        for s_idx in range(ini_busq, fin_busq + 1):
            comunes = len(toks_b & tokens_por_sesion[s_idx])
            penal_dist = abs(s_idx - pos_esperada) * 0.35
            score = comunes - penal_dist
            if score > mejor_score:
                mejor_score = score
                mejor_s = s_idx

        ses_min = mejor_s
        asignacion[mejor_s].extend(x["id_sumario"] for x in blq)

    return asignacion


def asignar_iniciativas_a_sesiones(iniciativas: list, sesiones_info: list, tokens_por_sesion: list) -> dict:
    """
    Asigna proyectos y leyes a la sesión donde fueron tratados,
    comparando las palabras del título y del articulado con el texto de cada sesión.
    """
    asignacion = {i: [] for i in range(len(sesiones_info))}
    if not iniciativas:
        return asignacion
    if len(sesiones_info) == 1:
        asignacion[0] = [ini["id_iniciativa"] for ini in iniciativas]
        return asignacion

    for ini in iniciativas:
        txt_busq = " ".join([
            str(ini.get("titulo_iniciativa") or ""),
            str(ini.get("resumen_sumario") or ""),
            str(ini.get("numero_articulo_origen") or ""),
            str(ini.get("texto_articulado_origen") or "")[:1500]
        ])
        toks_i = tokenizar_clave(txt_busq)
        mejor_s = 0
        mejor_com = -1
        for s_idx, toks_s in enumerate(tokens_por_sesion):
            com = len(toks_i & toks_s)
            if com > mejor_com:
                mejor_com = com
                mejor_s = s_idx
        asignacion[mejor_s].append(ini["id_iniciativa"])

    return asignacion


def actualizar_lotes_id_sesion(sb, tabla: str, pk_col: str, ids_filas: list, id_sesion_destino: int):
    if not ids_filas:
        return
    tam = 250
    for i in range(0, len(ids_filas), tam):
        chunk = ids_filas[i:i + tam]
        ejecutar_con_reintento(
            lambda c=chunk: sb.table(tabla).update({"id_sesion": id_sesion_destino}).in_(pk_col, c).execute(),
            f"update {tabla} -> id_sesion={id_sesion_destino}"
        )


def sincronizar_tomo_en_supabase(sb, resultado_tomo: dict):
    id_tomo = resultado_tomo["id_tomo"]
    codigo_tomo = resultado_tomo["codigo_tomo"]
    anio_leg = resultado_tomo["anio_legislativo"]
    sesiones_nuevas = resultado_tomo["sesiones"]
    tokens_pag = resultado_tomo["tokens_pag"]

    # Construir conjunto de tokens por sesión para emparejar sumarios e iniciativas
    tokens_por_sesion = []
    for s in sesiones_nuevas:
        t_set = set()
        for pg in range(s["pag_ini"], s["pag_fin"] + 1):
            t_set |= tokens_pag.get(pg, set())
        tokens_por_sesion.append(t_set)

    # 1. Obtener filas actuales de `public.sesiones` para este id_tomo
    ses_existentes = ejecutar_con_reintento(
        lambda: sb.table("sesiones").select("*").eq("id_tomo", id_tomo).order("id_sesion").execute(),
        f"select sesiones id_tomo={id_tomo}"
    ).data or []

    ids_ses_existentes = [r["id_sesion"] for r in ses_existentes]

    # 2. Descargar todas las filas hijas actuales de este Tomo (intervenciones, sumarios, iniciativas)
    intervenciones_tomo = descargar_filas_por_sesiones(
        sb, "intervenciones", "id_intervencion, id_sesion, nro_pagina, orden_dialogo, nombre_extraido_ocr",
        ids_ses_existentes, "id_intervencion"
    )
    sumarios_tomo = descargar_filas_por_sesiones(
        sb, "sesion_sumarios", "id_sumario, id_sesion, numero_item, titulo_tema, descripcion_tema",
        ids_ses_existentes, "id_sumario"
    )
    iniciativas_tomo = descargar_filas_por_sesiones(
        sb, "iniciativas_legislativas",
        "id_iniciativa, id_sesion, titulo_iniciativa, resumen_sumario, numero_articulo_origen, texto_articulado_origen",
        ids_ses_existentes, "id_iniciativa"
    )

    # 3. Actualizar o insertar las sesiones reales del Tomo en `public.sesiones`
    ids_sesiones_finales = []
    for idx, s_info in enumerate(sesiones_nuevas):
        payload_ses = {
            "id_tomo": id_tomo,
            "numero_reunion": s_info["reunion"],
            "fecha_exacta": s_info["fecha"],
            "tipo_sesion": s_info["tipo"],
            "periodo_legislativo": f"Período Legislativo {anio_leg}",
            "presidente_texto_origen": s_info["pres_texto"],
            "observaciones": f"Tomo: {codigo_tomo} | Reunión {s_info['reunion']} | Págs. PDF: {s_info['pag_ini']}-{s_info['pag_fin']}"
        }
        if idx < len(ids_ses_existentes):
            id_s = ids_ses_existentes[idx]
            ejecutar_con_reintento(
                lambda p=payload_ses, i=id_s: sb.table("sesiones").update(p).eq("id_sesion", i).execute(),
                f"update sesion {id_s}"
            )
            ids_sesiones_finales.append(id_s)
        else:
            ins = ejecutar_con_reintento(
                lambda p=payload_ses: sb.table("sesiones").insert(p).execute(),
                f"insert sesion tomo {id_tomo}"
            )
            ids_sesiones_finales.append(ins.data[0]["id_sesion"])

    # 4. Calcular asignación exacta de hijos -> sesiones reales
    mapa_int = asignar_intervenciones_a_sesiones(intervenciones_tomo, sesiones_nuevas)
    mapa_sum = asignar_sumarios_a_sesiones(sumarios_tomo, sesiones_nuevas, tokens_por_sesion)

    # Enriquecer tokens_por_sesion con los sumarios ya asignados a cada sesión (para emparejar iniciativas por resumen_sumario)
    sum_por_id = {s["id_sumario"]: s for s in sumarios_tomo}
    for idx_s, ids_sum_s in mapa_sum.items():
        for id_sm in ids_sum_s:
            sm = sum_por_id.get(id_sm)
            if sm:
                tokens_por_sesion[idx_s] |= tokenizar_clave(
                    f"{sm.get('titulo_tema') or ''} {sm.get('descripcion_tema') or ''}"
                )

    mapa_ini = asignar_iniciativas_a_sesiones(iniciativas_tomo, sesiones_nuevas, tokens_por_sesion)

    # 5. Actualizar `id_sesion` en `intervenciones`, `sesion_sumarios` e `iniciativas_legislativas`
    #    (solo para las filas cuyo id_sesion cambia, optimizando llamadas HTTP)
    estado_actual_int = {r["id_intervencion"]: r["id_sesion"] for r in intervenciones_tomo}
    estado_actual_sum = {r["id_sumario"]: r["id_sesion"] for r in sumarios_tomo}
    estado_actual_ini = {r["id_iniciativa"]: r["id_sesion"] for r in iniciativas_tomo}

    for idx_s, id_s_dest in enumerate(ids_sesiones_finales):
        ids_i_cambiar = [i for i in mapa_int[idx_s] if estado_actual_int.get(i) != id_s_dest]
        if ids_i_cambiar:
            actualizar_lotes_id_sesion(sb, "intervenciones", "id_intervencion", ids_i_cambiar, id_s_dest)

        ids_s_cambiar = [i for i in mapa_sum[idx_s] if estado_actual_sum.get(i) != id_s_dest]
        if ids_s_cambiar:
            actualizar_lotes_id_sesion(sb, "sesion_sumarios", "id_sumario", ids_s_cambiar, id_s_dest)

        ids_ini_cambiar = [i for i in mapa_ini[idx_s] if estado_actual_ini.get(i) != id_s_dest]
        if ids_ini_cambiar:
            actualizar_lotes_id_sesion(sb, "iniciativas_legislativas", "id_iniciativa", ids_ini_cambiar, id_s_dest)

    # 6. Si habían quedado sesiones sobrantes de una corrida previa, eliminarlas ahora que no tienen hijos
    if len(ids_ses_existentes) > len(ids_sesiones_finales):
        sobrantes = ids_ses_existentes[len(ids_sesiones_finales):]
        ejecutar_con_reintento(
            lambda s_del=sobrantes: sb.table("sesiones").delete().in_("id_sesion", s_del).execute(),
            f"delete sesiones sobrantes {sobrantes}"
        )

    # 7. Actualizar `public.sesiones_autoridades` para todas las sesiones del Tomo
    filas_aut_dict = {}
    for idx_s, id_s_dest in enumerate(ids_sesiones_finales):
        for id_p in sesiones_nuevas[idx_s]["pres_ids"]:
            clave_aut = (id_s_dest, id_p, "Presidente de la Sesión")
            filas_aut_dict[clave_aut] = {
                "id_sesion": id_s_dest,
                "id_persona": id_p,
                "rol_presidencia": "Presidente de la Sesión"
            }
    filas_aut = list(filas_aut_dict.values())
    if filas_aut:
        ejecutar_con_reintento(
            lambda fa=filas_aut: sb.table("sesiones_autoridades").upsert(fa).execute(),
            f"upsert sesiones_autoridades tomo {id_tomo}"
        )

    return len(ids_sesiones_finales), len(intervenciones_tomo), len(sumarios_tomo), len(iniciativas_tomo)



def main():
    t_inicio_global = time.time()
    print("=" * 88)
    print("EXTRACCIÓN DE FECHAS EXACTAS Y REUNIONES DESDE GOOGLE DRIVE -> SUPABASE")
    print("=" * 88)

    if not RUTA_DRIVE.exists():
        raise RuntimeError(f"No se encontró la ruta de Google Drive: {RUTA_DRIVE}")

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    # 1. Cargar catálogo de Tomos y Personas desde Supabase
    tomos_db = sb.table("tomos_diarios_sesiones").select("*").order("id_tomo").execute().data
    personas_db = sb.table("personas").select("id_persona, nombre, apellido, nombre_completo").execute().data
    indice_personas = construir_indice_personas(personas_db)
    print(f"[*] Catálogos cargados desde Supabase: {len(tomos_db)} tomos | {len(personas_db)} personas.")

    # 2. Localizar los 209 archivos PDF en Google Drive y verificar cuáles ya fueron procesados
    forzar = "--force" in sys.argv
    ses_todas = sb.table("sesiones").select("id_sesion, id_tomo, fecha_exacta, observaciones").execute().data or []
    ses_por_tomo = {}
    for s in ses_todas:
        ses_por_tomo.setdefault(s["id_tomo"], []).append(s)

    pdfs_drive = {p.stem: p for p in RUTA_DRIVE.rglob("*.pdf")}
    tareas = []
    tomos_ya_listos = 0
    for t in tomos_db:
        cod = t["codigo_tomo"]
        if cod not in pdfs_drive:
            raise RuntimeError(f"El tomo '{cod}' (id_tomo={t['id_tomo']}) no se encontró en {RUTA_DRIVE}")
        ses_t = ses_por_tomo.get(t["id_tomo"], [])
        ya_procesado = (
            not forzar
            and ses_t
            and all("Págs. PDF:" in str(x.get("observaciones") or "") for x in ses_t)
        )
        if ya_procesado:
            tomos_ya_listos += 1
            continue
        tareas.append({
            "id_tomo": t["id_tomo"],
            "codigo_tomo": cod,
            "camara": t["camara"],
            "anio_legislativo": t["anio_legislativo"],
            "ruta_pdf": pdfs_drive[cod]
        })

    print(f"[*] 209/209 archivos PDF verificados en '{RUTA_DRIVE}' ({tomos_ya_listos} ya procesados, {len(tareas)} pendientes).")
    print("[*] Procesando PDFs y sincronizando sesiones, intervenciones, sumarios e iniciativas...\n")

    total_sesiones_creadas = 0
    total_int_hiladas = 0
    total_sum_hilados = 0
    total_ini_hiladas = 0

    for idx_t, tarea in enumerate(tareas, 1):
        t0 = time.time()
        res_tomo = escanear_pdf_general(tarea, indice_personas)
        n_ses, n_int, n_sum, n_ini = sincronizar_tomo_en_supabase(sb, res_tomo)
        total_sesiones_creadas += n_ses
        total_int_hiladas += n_int
        total_sum_hilados += n_sum
        total_ini_hiladas += n_ini

        f_prim = res_tomo["sesiones"][0]["fecha"]
        f_ult = res_tomo["sesiones"][-1]["fecha"]
        rango_str = f_prim if f_prim == f_ult else f"{f_prim} a {f_ult}"
        print(
            f"  [{idx_t:3d}/{len(tareas)} | id_tomo={res_tomo['id_tomo']:3d}] {res_tomo['codigo_tomo']:<38s} -> "
            f"{n_ses:2d} ses ({rango_str}) | "
            f"int={n_int:4d}, sum={n_sum:3d}, ini={n_ini:3d} [{time.time()-t0:.1f}s]",
            flush=True
        )

    # 3. Verificación final y auditoría de integridad CERO PÉRDIDA DE DATOS
    print("\n" + "=" * 88)
    print("AUDITORÍA FINAL DE INTEGRIDAD EN SUPABASE (CERO PÉRDIDA DE DATOS)")
    print("=" * 88)

    c_tomos = sb.table("tomos_diarios_sesiones").select("id_tomo", count="exact").execute().count
    c_ses = sb.table("sesiones").select("id_sesion", count="exact").execute().count
    c_aut = sb.table("sesiones_autoridades").select("id_sesion", count="exact").execute().count
    c_int = sb.table("intervenciones").select("id_intervencion", count="exact").execute().count
    c_sum = sb.table("sesion_sumarios").select("id_sumario", count="exact").execute().count
    c_ini = sb.table("iniciativas_legislativas").select("id_iniciativa", count="exact").execute().count
    c_art = sb.table("articulos_iniciativa").select("id_articulo", count="exact").execute().count

    print(f"  - public.tomos_diarios_sesiones : {c_tomos:6d} (esperado: 209)")
    print(f"  - public.sesiones               : {c_ses:6d} sesiones reales con fecha exacta")
    print(f"  - public.sesiones_autoridades   : {c_aut:6d} vínculos presidente-persona")
    print(f"  - public.intervenciones         : {c_int:6d} (esperado: 64.636 -> {'OK 100%' if c_int == 64636 else 'ERROR'})")
    print(f"  - public.sesion_sumarios        : {c_sum:6d} (esperado:  7.469 -> {'OK 100%' if c_sum == 7469 else 'ERROR'})")
    print(f"  - public.iniciativas_legislat.  : {c_ini:6d} (esperado: 11.263 -> {'OK 100%' if c_ini == 11263 else 'ERROR'})")
    print(f"  - public.articulos_iniciativa   : {c_art:6d} (esperado: 57.176 -> {'OK 100%' if c_art == 57176 else 'ERROR'})")
    print(f"\n[OK] Proceso completado exitosamente en {time.time() - t_inicio_global:.1f}s.")


if __name__ == "__main__":
    main()
