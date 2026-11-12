#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Este script es el motor de reconocimiento de entidades (NER) y análisis de postura (ABSA)
para los debates sobre política comercial entre 1929 y 1939.

Lo que hace es:
1. Detectar menciones de actores clave, tratados (como el Roca-Runciman), organismos
   (Junta Nacional de Carnes, Banco Central) y leyes económicas en los discursos.
2. Evaluar la postura del orador (a favor, en contra o neutral) usando un léxico histórico
   adaptado al vocabulario parlamentario de la década del 30.
3. Guardar las menciones y co-ocurrencias en Supabase para alimentar los dashboards y gráficos.
"""

import os
import sys
from pathlib import Path
import re
import csv
import json
import time
import argparse
import unicodedata

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
DIR_DB = ROOT_DIR / "base_de_datos"
if str(DIR_DB) not in sys.path:
    sys.path.insert(0, str(DIR_DB))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from itertools import cycle, combinations
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Optional, Set, Any
import pandas as pd
from openai import OpenAI
from database_connection import supabase

# Lectores opcionales para PDF y DOCX
try:
    import pymupdf as fitz
except ImportError:
    fitz = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    import docx
except ImportError:
    docx = None

try:
    import spacy
    SPACY_DISPONIBLE = True
except ImportError:
    spacy = None
    SPACY_DISPONIBLE = False



USAR_QWEN_DESAMBIGUACION = False
EVALUAR_POSTURA_ABSA_CON_QWEN = False

QWEN_API_KEYS = [
    os.getenv("QWEN_API_KEY_1", "TU_API_KEY_1"),
    os.getenv("QWEN_API_KEY_2", "TU_API_KEY_2"),
    os.getenv("QWEN_API_KEY_3", "TU_API_KEY_3"),
]
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")


class QwenClientPool:
    """Gestiona múltiples API keys en Round-Robin con reintentos automáticos ante Rate Limits."""
    def __init__(self, api_keys: List[str], base_url: str, model: str):
        keys_validas = [k for k in api_keys if k and not k.startswith("TU_API_KEY")]
        self.clientes = [OpenAI(api_key=k, base_url=base_url) for k in keys_validas]
        self.ciclo_clientes = cycle(self.clientes) if self.clientes else None
        self.model = model

    def analizar_mencion(self, nombre_entidad: str, contexto: str, evaluar_absa: bool = False) -> Dict:
        score_lex, postura_lex = evaluar_polaridad_y_postura_1930(contexto, aspecto=nombre_entidad)
        if not self.ciclo_clientes:
            return {"es_valida": True, "postura": postura_lex, "score_polaridad": score_lex, "justificacion": None}

        prompt_sistema = (
            "Eres un historiador económico especializado en la política comercial argentina entre 1929 y 1939 "
            "(proyecto UNSAM/CONICET). Analizas fragmentos de los Diarios de Sesiones del Congreso Nacional. "
            "Responde ÚNICAMENTE con un objeto JSON válido."
        )
        prompt_usuario = (
            f"Entidad o aspecto evaluado: '{nombre_entidad}'\n"
            f"Fragmento de la intervención parlamentaria:\n\"\"\"{contexto}\"\"\"\n\n"
            "Instrucciones:\n"
            "1. Determina si la mención se refiere efectivamente a la entidad histórica/económica/política indicada ('es_valida': true/false).\n"
            "2. Clasifica la postura ideológica o valorativa del orador hacia dicha entidad/tema en el fragmento "
            "('postura': 'A_FAVOR', 'EN_CONTRA' o 'NEUTRAL').\n"
            "3. Breve justificación de 1 oración ('justificacion').\n"
            "Formato JSON: {\"es_valida\": true, \"postura\": \"NEUTRAL\", \"justificacion\": \"...\"}"
        )

        for _ in range(len(self.clientes) * 2):
            cliente = next(self.ciclo_clientes)
            try:
                resp = cliente.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": prompt_sistema},
                        {"role": "user", "content": prompt_usuario}
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
                datos = json.loads(resp.choices[0].message.content)
                postura_final = datos.get("postura", postura_lex) if evaluar_absa else postura_lex
                return {
                    "es_valida": bool(datos.get("es_valida", True)),
                    "postura": postura_final,
                    "score_polaridad": score_lex,
                    "justificacion": datos.get("justificacion")
                }
            except Exception:
                time.sleep(1.5)
        return {"es_valida": True, "postura": postura_lex, "score_polaridad": score_lex, "justificacion": "Fallback léxico"}



PALABRAS_APOYO_EPOCA = {
    "favorable", "beneficio", "beneficios", "beneficioso", "progreso", "defensa",
    "proteger", "protección", "fomento", "fomentar", "necesario", "indispensable",
    "prestigio", "meritorio", "eficaz", "eficiencia", "acierto", "acertada",
    "justicia", "equidad", "salvación", "patriótico", "positiva", "positivo",
    "apoyar", "apoyo", "felicitar", "elogio", "importante", "garantía", "estabilidad",
    "reciprocidad", "cooperación", "estímulo", "alivio", "resguardo", "amparo",
    "conveniente", "conveniencia", "salvaguarda", "equilibrio", "solvencia",
    "prudente", "prudencia", "vital", "legítimo", "legítima", "prosperidad"
}

PALABRAS_CRITICA_EPOCA = {
    "monopolio", "monopolios", "trust", "trusts", "perjuicio", "perjudicial",
    "ruina", "especulación", "especuladores", "privilegio", "privilegios",
    "inconstitucional", "ilegal", "abuso", "abusos", "explotación", "entrega",
    "sumisión", "desastre", "fracaso", "inocuo", "burocracia", "voracidad",
    "contra", "combatir", "rechazar", "oposición", "nocivo", "expoliación",
    "usura", "arbitrario", "arbitrariedad", "gravoso", "agravio", "colonial",
    "coloniaje", "vasallaje", "opresión", "expoliador", "latifundio", "oligarquía",
    "extorsión", "claudicación", "humillante", "ruinoso", "leonino", "carestía",
    "encarecimiento", "asfixia", "despojo", "favoritismo", "injusticia"
}

FRASES_APOYO_EPOCA = [
    r"\ben\s+defensa\s+de\b",
    r"\ba\s+favor\s+de\b",
    r"\bmedida\s+salvadora\b",
    r"\bprotecci[oó]n\s+leg[ií]tima\b",
    r"\bintereses\s+generales\s+del\s+pa[ií]s\b",
    r"\bsalvar\s+la\s+producci[oó]n\b",
]

FRASES_CRITICA_EPOCA = [
    r"\ben\s+perjuicio\s+de\b",
    r"\ben\s+contra\s+de\b",
    r"\bmonopolio\s+frigor[ií]fico\b",
    r"\btrust\s+de\s+la\s+carne\b",
    r"\bpacto\s+leonino\b",
    r"\bimpuesto\s+al\s+consumo\b",
    r"\bprivilegio\s+irritante\b",
]


def evaluar_polaridad_y_postura_1930(contexto: str, aspecto: Optional[str] = None) -> Tuple[float, str]:
    """
    Evalúa la actitud del orador hacia una entidad, socio comercial o concepto de política comercial
    dentro de su ventana de contexto parlamentario (ABSA léxico calibrado para 1929-1939).
    Devuelve: (score_polaridad en [-1.0, +1.0], etiqueta en {'A_FAVOR', 'EN_CONTRA', 'NEUTRAL'})
    """
    if not contexto:
        return 0.0, "NEUTRAL"

    ctx_low = contexto.lower()
    palabras = re.findall(r"\b[a-záéíóúñü]{4,}\b", ctx_low)
    if not palabras:
        return 0.0, "NEUTRAL"

    pts_favor = sum(1.0 for p in palabras if p in PALABRAS_APOYO_EPOCA)
    pts_contra = sum(1.0 for p in palabras if p in PALABRAS_CRITICA_EPOCA)

    for rx_f in FRASES_APOYO_EPOCA:
        if re.search(rx_f, ctx_low):
            pts_favor += 1.5
    for rx_c in FRASES_CRITICA_EPOCA:
        if re.search(rx_c, ctx_low):
            pts_contra += 1.5

    total_pts = pts_favor + pts_contra
    if total_pts == 0:
        return 0.0, "NEUTRAL"

    score = round((pts_favor - pts_contra) / max(total_pts, 2.0), 4)
    if pts_favor >= pts_contra + 1.5:
        return score, "A_FAVOR"
    if pts_contra >= pts_favor + 1.5:
        return score, "EN_CONTRA"
    return score, "NEUTRAL"


def clasificar_postura_lexica_1930(contexto: str) -> str:
    """Compatibilidad directa: devuelve 'A_FAVOR', 'EN_CONTRA' o 'NEUTRAL'."""
    _, postura = evaluar_polaridad_y_postura_1930(contexto)
    return postura


# Las 42 entradas exactas registradas en 'Lista Entidades - OCT26.pdf' 
ENTIDADES_OFICIALES_PDF_OCT26 = [
    ("Banco Central", "Instituciones económicas oficiales/privadas"),
    ("Banco de Inglaterra", "Instituciones económicas oficiales/privadas"),
    ("Bolsa de Cereales", "Instituciones económicas oficiales/privadas"),
    ("Bolsa de Comercio", "Instituciones económicas oficiales/privadas"),
    ("CAC", "Instituciones económicas oficiales/privadas"),
    ("CACIP", "Instituciones económicas oficiales/privadas"),
    ("Caja de Conversión", "Instituciones económicas oficiales/privadas"),
    ("Cámara Argentina de Comercio", "Instituciones económicas oficiales/privadas"),
    ("Cámara de Importadores", "Instituciones económicas oficiales/privadas"),
    ("CARBAP", "Instituciones económicas oficiales/privadas"),
    ("CARCLO", "Instituciones económicas oficiales/privadas"),
    ("Comisión de Control de Cambios", "Instituciones económicas oficiales/privadas"),
    ("Comisión Reguladora de la Producción y el Comercio de la Yerba Mate", "Instituciones económicas oficiales/privadas"),
    ("Confederación Argentina del Comercio, la Industria y la Producción", "Instituciones económicas oficiales/privadas"),
    ("Confederación de Asociaciones Rurales de Buenos Aires y La Pampa", "Instituciones económicas oficiales/privadas"),
    ("Confederación de Asociaciones Rurales del Centro y Litoral Oeste", "Instituciones económicas oficiales/privadas"),
    ("Federación Agraria Argentina", "Instituciones económicas oficiales/privadas"),
    ("Junta Nacional de Algodón", "Instituciones económicas oficiales/privadas"),
    ("Junta Nacional de Carnes", "Instituciones económicas oficiales/privadas"),
    ("Junta Reguladora de Granos", "Instituciones económicas oficiales/privadas"),
    ("Junta Reguladora de la Industria de la Industria Lechera", "Instituciones económicas oficiales/privadas"),
    ("Junta Reguladora de Vinos", "Instituciones económicas oficiales/privadas"),
    ("Liga de Naciones", "Instituciones económicas oficiales/privadas"),
    ("Sociedad de Naciones", "Instituciones económicas oficiales/privadas"),
    ("Sociedad Rural Argentina", "Instituciones económicas oficiales/privadas"),
    ("UIA", "Instituciones económicas oficiales/privadas"),
    ("Unión Industrial Argentina", "Instituciones económicas oficiales/privadas"),
    ("Yacimientos Petrolíferos Fiscales", "Instituciones económicas oficiales/privadas"),
    ("YPF", "Instituciones económicas oficiales/privadas"),

    ("Alemania", "Unidades políticas extranjeras"),
    ("Commonwealth", "Unidades políticas extranjeras"),
    ("Estados Unidos", "Unidades políticas extranjeras"),
    ("Estados Unidos de Norteamérica", "Unidades políticas extranjeras"),
    ("Gran Bretaña", "Unidades políticas extranjeras"),
    ("Inglaterra", "Unidades políticas extranjeras"),
    ("Reino Unido", "Unidades políticas extranjeras"),

    # 3. Fenómenos/procesos/hechos (4 entradas en el PDF)
    ("Cobden-Chevalier", "Fenómenos/procesos/hechos"),
    ("Gran Depresión", "Fenómenos/procesos/hechos"),
    ("Roca-Runciman", "Fenómenos/procesos/hechos"),
    ("Wall Street", "Fenómenos/procesos/hechos"),

    # 4. Personalidades (2 entradas en el PDF)
    ("Hoover", "Personalidades"),
    ("Roosevelt", "Personalidades"),
]

NOMBRES_EXACTOS_PDF_OCT26 = {nombre.lower(): (nombre, cat) for nombre, cat in ENTIDADES_OFICIALES_PDF_OCT26}

# Entidades complementarias para cubrir actores políticos y organismos de los años 30 mencionados en el Plan de Trabajo
ENTIDADES_COMPLEMENTARIAS_PLAN = [
    ("Banco de la Nación Argentina", "Instituciones económicas oficiales/privadas"),
    ("Banco Hipotecario Nacional", "Instituciones económicas oficiales/privadas"),
    ("Corporación Argentina de Productores de Carnes", "Instituciones económicas oficiales/privadas"),
    ("Instituto Movilizador de Inversiones Bancarias", "Instituciones económicas oficiales/privadas"),
    ("Dirección Nacional de Vialidad", "Instituciones económicas oficiales/privadas"),
    ("Conferencia de Ottawa", "Fenómenos/procesos/hechos"),
    ("Unión Cívica Radical", "Actores políticos y partidarios"),
    ("Partido Socialista", "Actores políticos y partidarios"),
    ("Partido Demócrata Nacional", "Actores políticos y partidarios"),
    ("Partido Demócrata Progresista", "Actores políticos y partidarios"),
    ("Concordancia", "Actores políticos y partidarios"),
]

MAPA_CANONICO = {
    # Actores Privados y Corporativos (Lista Entidades - OCT26.pdf)
    "UIA": "Unión Industrial Argentina",
    "Unión Industrial Argentina": "Unión Industrial Argentina",
    "Unión Industrial": "Unión Industrial Argentina",
    "SRA": "Sociedad Rural Argentina",
    "Sociedad Rural Argentina": "Sociedad Rural Argentina",
    "Sociedad Rural": "Sociedad Rural Argentina",
    "CAC": "Cámara Argentina de Comercio",
    "Cámara Argentina de Comercio": "Cámara Argentina de Comercio",
    "CACIP": "Confederación Argentina del Comercio, la Industria y la Producción",
    "Confederación Argentina del Comercio, la Industria y la Producción": "Confederación Argentina del Comercio, la Industria y la Producción",
    "CARBAP": "Confederación de Asociaciones Rurales de Buenos Aires y La Pampa",
    "Confederación de Asociaciones Rurales de Buenos Aires y La Pampa": "Confederación de Asociaciones Rurales de Buenos Aires y La Pampa",
    "CARCLO": "Confederación de Asociaciones Rurales del Centro y Litoral Oeste",
    "Confederación de Asociaciones Rurales del Centro y Litoral Oeste": "Confederación de Asociaciones Rurales del Centro y Litoral Oeste",
    "FAA": "Federación Agraria Argentina",
    "Federación Agraria Argentina": "Federación Agraria Argentina",
    "Federación Agraria": "Federación Agraria Argentina",
    "CAP": "Corporación Argentina de Productores de Carnes",
    "Corporación Argentina de Productores de Carnes": "Corporación Argentina de Productores de Carnes",
    "Bolsa de Comercio": "Bolsa de Comercio",
    "Bolsa de Cereales": "Bolsa de Cereales",
    "Cámara de Importadores": "Cámara de Importadores",

    # Instituciones Económicas Oficiales / Reguladoras (Lista Entidades - OCT26.pdf)
    "YPF": "Yacimientos Petrolíferos Fiscales",
    "Yacimientos Petrolíferos Fiscales": "Yacimientos Petrolíferos Fiscales",
    "BCRA": "Banco Central",
    "Banco Central": "Banco Central",
    "Banco Central de la República Argentina": "Banco Central",
    "Banco de la Nación Argentina": "Banco de la Nación Argentina",
    "Banco de la Nación": "Banco de la Nación Argentina",
    "Banco Hipotecario Nacional": "Banco Hipotecario Nacional",
    "Caja de Conversión": "Caja de Conversión",
    "Comisión de Control de Cambios": "Comisión de Control de Cambios",
    "Control de Cambios": "Comisión de Control de Cambios",
    "Junta Nacional de Carnes": "Junta Nacional de Carnes",
    "Junta Reguladora de Granos": "Junta Reguladora de Granos",
    "Comisión Nacional de Granos y Elevadores": "Junta Reguladora de Granos",
    "Junta Nacional de Algodón": "Junta Nacional de Algodón",
    "Junta Nacional del Algodón": "Junta Nacional de Algodón",
    # Nota: en Lista Entidades - OCT26.pdf figura con doble "de la Industria"; se unifica y mapea
    "Junta Reguladora de la Industria de la Industria Lechera": "Junta Reguladora de la Industria Lechera",
    "Junta Reguladora de la Industria Lechera": "Junta Reguladora de la Industria Lechera",
    "Junta Reguladora de Vinos": "Junta Reguladora de Vinos",
    "Comisión Reguladora de la Producción y el Comercio de la Yerba Mate": "Comisión Reguladora de la Producción y el Comercio de la Yerba Mate",
    "CRYM": "Comisión Reguladora de la Producción y el Comercio de la Yerba Mate",
    "Instituto Movilizador de Inversiones Bancarias": "Instituto Movilizador de Inversiones Bancarias",
    "Dirección Nacional de Vialidad": "Dirección Nacional de Vialidad",

    # Unidades Políticas Extranjeras y Organismos Internacionales (Lista Entidades - OCT26.pdf)
    "Liga de Naciones": "Sociedad de las Naciones / Liga de las Naciones",
    "Sociedad de Naciones": "Sociedad de las Naciones / Liga de las Naciones",
    "Banco de Inglaterra": "Banco de Inglaterra",
    "Estados Unidos": "Estados Unidos",
    "Estados Unidos de Norteamérica": "Estados Unidos",
    "Gran Bretaña": "Reino Unido / Gran Bretaña",
    "Inglaterra": "Reino Unido / Gran Bretaña",
    "Reino Unido": "Reino Unido / Gran Bretaña",
    "Commonwealth": "Commonwealth",
    "Alemania": "Alemania",

    # Fenómenos / Procesos / Hechos (Lista Entidades - OCT26.pdf)
    "Roca-Runciman": "Pacto Roca-Runciman",
    "Tratado de Londres": "Pacto Roca-Runciman",
    "Cobden-Chevalier": "Tratado Cobden-Chevalier",
    "Conferencia de Ottawa": "Conferencia de Ottawa",
    "Gran Depresión": "Gran Depresión",
    "Wall Street": "Wall Street",

    # Personalidades (Lista Entidades - OCT26.pdf)
    "Hoover": "Hoover",
    "Roosevelt": "Roosevelt",

    # Actores Políticos y Partidarios (Plan de Trabajo)
    "Unión Cívica Radical": "Unión Cívica Radical",
    "Partido Socialista": "Partido Socialista",
    "Partido Demócrata Nacional": "Partido Demócrata Nacional",
    "Partido Demócrata Progresista": "Partido Demócrata Progresista",
    "Concordancia": "Concordancia",
}

# Clasificación analítica alineada con los objetivos del Plan de Trabajo (Intereses privados vs. Oficiales vs. Socios comerciales)
MAPA_TIPO_ACTOR = {
    # Intereses privados / corporativos (Objetivo específico 3 y Resultado esperado 2)
    "Sociedad Rural Argentina": "INTERES_PRIVADO_CORPORATIVO",
    "Unión Industrial Argentina": "INTERES_PRIVADO_CORPORATIVO",
    "Cámara Argentina de Comercio": "INTERES_PRIVADO_CORPORATIVO",
    "Confederación Argentina del Comercio, la Industria y la Producción": "INTERES_PRIVADO_CORPORATIVO",
    "Confederación de Asociaciones Rurales de Buenos Aires y La Pampa": "INTERES_PRIVADO_CORPORATIVO",
    "Confederación de Asociaciones Rurales del Centro y Litoral Oeste": "INTERES_PRIVADO_CORPORATIVO",
    "Federación Agraria Argentina": "INTERES_PRIVADO_CORPORATIVO",
    "Corporación Argentina de Productores de Carnes": "INTERES_PRIVADO_CORPORATIVO",
    "Bolsa de Comercio": "INTERES_PRIVADO_CORPORATIVO",
    "Bolsa de Cereales": "INTERES_PRIVADO_CORPORATIVO",
    "Cámara de Importadores": "INTERES_PRIVADO_CORPORATIVO",

    # Instituciones económicas oficiales y juntas reguladoras estatales
    "Banco Central": "INSTITUCION_ECONOMICA_OFICIAL",
    "Banco de la Nación Argentina": "INSTITUCION_ECONOMICA_OFICIAL",
    "Banco Hipotecario Nacional": "INSTITUCION_ECONOMICA_OFICIAL",
    "Caja de Conversión": "INSTITUCION_ECONOMICA_OFICIAL",
    "Comisión de Control de Cambios": "INSTITUCION_ECONOMICA_OFICIAL",
    "Yacimientos Petrolíferos Fiscales": "INSTITUCION_ECONOMICA_OFICIAL",
    "Junta Nacional de Carnes": "INSTITUCION_ECONOMICA_OFICIAL",
    "Junta Reguladora de Granos": "INSTITUCION_ECONOMICA_OFICIAL",
    "Junta Nacional de Algodón": "INSTITUCION_ECONOMICA_OFICIAL",
    "Junta Reguladora de la Industria Lechera": "INSTITUCION_ECONOMICA_OFICIAL",
    "Junta Reguladora de Vinos": "INSTITUCION_ECONOMICA_OFICIAL",
    "Comisión Reguladora de la Producción y el Comercio de la Yerba Mate": "INSTITUCION_ECONOMICA_OFICIAL",
    "Instituto Movilizador de Inversiones Bancarias": "INSTITUCION_ECONOMICA_OFICIAL",
    "Dirección Nacional de Vialidad": "INSTITUCION_ECONOMICA_OFICIAL",

    # Organismos e instituciones internacionales
    "Banco de Inglaterra": "ORGANISMO_INTERNACIONAL_EXTRANJERO",
    "Sociedad de las Naciones / Liga de las Naciones": "ORGANISMO_INTERNACIONAL_EXTRANJERO",

    # Socios comerciales / Unidades políticas extranjeras (Objetivo específico 5)
    "Reino Unido / Gran Bretaña": "SOCIO_COMERCIAL_EXTRANJERO",
    "Estados Unidos": "SOCIO_COMERCIAL_EXTRANJERO",
    "Alemania": "SOCIO_COMERCIAL_EXTRANJERO",
    "Commonwealth": "SOCIO_COMERCIAL_EXTRANJERO",

    # Tratados, fenómenos y procesos macroeconómicos (Objetivo específico 4)
    "Pacto Roca-Runciman": "FENOMENO_PROCESO_HECHO",
    "Tratado Cobden-Chevalier": "FENOMENO_PROCESO_HECHO",
    "Conferencia de Ottawa": "FENOMENO_PROCESO_HECHO",
    "Gran Depresión": "FENOMENO_PROCESO_HECHO",
    "Wall Street": "FENOMENO_PROCESO_HECHO",

    # Personalidades históricas internacionales
    "Hoover": "PERSONALIDAD_HISTORICA",
    "Roosevelt": "PERSONALIDAD_HISTORICA",

    # Actores políticos y partidarios (Objetivo específico 3)
    "Unión Cívica Radical": "ACTOR_POLITICO_PARTIDARIO",
    "Partido Socialista": "ACTOR_POLITICO_PARTIDARIO",
    "Partido Demócrata Nacional": "ACTOR_POLITICO_PARTIDARIO",
    "Partido Demócrata Progresista": "ACTOR_POLITICO_PARTIDARIO",
    "Concordancia": "ACTOR_POLITICO_PARTIDARIO",
}

# Expresiones regulares calibradas para la lengua parlamentaria y el OCR de 1929-1939
PATRONES_ESPECIALES_EPOCA = {
    "Banco Central": r"\bBan[ce]o\s+Central(?:\s+de\s+la\s+Rep[uú]blica(?:\s+Argentina)?)?\b",
    "Banco de Inglaterra": r"\bBan[ce]o\s+de\s+Inglaterra\b",
    "Banco de la Nación Argentina": r"\bBan[ce]o\s+de\s+la\s+Naci[oó]n(?:\s+Argentina)?\b",
    "Banco Hipotecario Nacional": r"\bBan[ce]o\s+Hipotecario(?:\s+Nacional)?\b",
    "Bolsa de Cereales": r"\bBolsa\s+de\s+Cereales\b",
    "Bolsa de Comercio": r"\bBolsa\s+de\s+Comercio\b",
    "Caja de Conversión": r"\bCaja\s+de\s+Conversi[oó]n\b",
    "Cámara Argentina de Comercio": r"\bC[aá]mara\s+Argentina\s+de\s+Comercio\b",
    "Cámara de Importadores": r"\bC[aá]mara\s+(?:Argentina\s+)?de\s+Importadores\b",
    "Sociedad Rural Argentina": r"\bSociedad\s+Rural\s+Argentina\b|\bSociedad\s+Rural\b(?!\s+de\s+[A-ZÁÉÍÓÚÑ])",
    "Unión Industrial Argentina": r"\bUni[oó]n\s+Industrial(?:\s+Argentina)?\b",
    "Federación Agraria Argentina": r"\bFederaci[oó]n\s+Agraria(?:\s+Argentina)?\b",
    "Corporación Argentina de Productores de Carnes": r"\bCorporaci[oó]n\s+(?:Argentina\s+)?de\s+Productores\s+de\s+Carnes\b",
    "CAC": r"\bC\.\s*A\.\s*C\.|\bCAC\b",
    "CACIP": r"\bC\.?\s*A\.?\s*C\.?\s*I\.?\s*P\.?\b",
    "CARBAP": r"\bC\.?\s*A\.?\s*R\.?\s*B\.?\s*A\.?\s*P\.?\b",
    "CARCLO": r"\bC\.?\s*A\.?\s*R\.?\s*C\.?\s*L\.?\s*O\.?\b",
    "UIA": r"\bU\.\s*I\.\s*A\.|\bUIA\b",
    "YPF": r"\bY\.?\s*P\.?\s*F\.?\b",
    "Yacimientos Petrolíferos Fiscales": r"\bYacimientos\s+Petrol[ií]feros\s+Fiscales\b",
    "Confederación Argentina del Comercio, la Industria y la Producción": (
        r"\bConfederaci[oó]n\s+(?:Argentina\s+)?del\s+Comercio[\,\s]+(?:de\s+)?la\s+Industria\s+y\s+(?:de\s+)?la\s+Producci[oó]n\b"
    ),
    "Confederación de Asociaciones Rurales de Buenos Aires y La Pampa": (
        r"\bConfederaci[oó]n\s+de\s+(?:Asociaciones|Sociedades)\s+Rurales\s+de\s+Buenos\s+Aires\s+y\s+(?:La\s+)?Pampa\b"
    ),
    "Confederación de Asociaciones Rurales del Centro y Litoral Oeste": (
        r"\bConfederaci[oó]n\s+de\s+(?:Asociaciones|Sociedades)\s+Rurales\s+del\s+Centro\s+y\s+Litoral\s+Oeste\b"
    ),
    "Comisión Reguladora de la Producción y el Comercio de la Yerba Mate": (
        r"\b(?:Comisi[oó]n|Junta)\s+Reguladora\s+de\s+la\s+(?:Producci[oó]n\s+y\s+(?:el\s+)?Comercio\s+de\s+la\s+)?Yerba\s+Mate\b|\bC\.\s*R\.\s*Y\.\s*M\."
    ),
    "Comisión de Control de Cambios": r"\b(?:Comisi[oó]n|Oficina)\s+de\s+Control\s+de\s+Cambios\b",
    "Junta Nacional de Algodón": r"\bJunta\s+Nacional\s+del?\s+Algod[oó]n\b",
    "Junta Nacional de Carnes": r"\bJunta\s+Nacional\s+de\s+Carnes\b",
    "Junta Reguladora de Granos": r"\b(?:Junta\s+Reguladora\s+de\s+Granos|Comisi[oó]n\s+Nacional\s+de\s+Granos\s+y\s+Elevadores)\b",
    "Junta Reguladora de la Industria de la Industria Lechera": (
        r"\b(?:Junta\s+Reguladora\s+de\s+la\s+(?:Industria\s+de\s+la\s+)?Industria\s+Lechera|Junta\s+Reguladora\s+de\s+la\s+Leche|Comisi[oó]n\s+Aut[oó]noma\s+de\s+la\s+Industria\s+Lechera)\b"
    ),
    "Junta Reguladora de la Industria Lechera": (
        r"\b(?:Junta\s+Reguladora\s+de\s+la\s+(?:Industria\s+de\s+la\s+)?Industria\s+Lechera|Junta\s+Reguladora\s+de\s+la\s+Leche|Comisi[oó]n\s+Aut[oó]noma\s+de\s+la\s+Industria\s+Lechera)\b"
    ),
    "Junta Reguladora de Vinos": r"\bJunta\s+Reguladora\s+de\s+Vinos\b",
    "Instituto Movilizador de Inversiones Bancarias": r"\bInstituto\s+Movilizador(?:\s+de\s+Inversiones\s+Bancarias)?\b",
    "Dirección Nacional de Vialidad": r"\bDirecci[oó]n\s+Nacional\s+de\s+Vialidad\b",
    "Liga de Naciones": r"\bLiga\s+de\s+(?:las\s+)?Naciones\b",
    "Sociedad de Naciones": r"\bSociedad\s+de\s+(?:las\s+)?Naciones\b",
    "Estados Unidos": r"\bEstados\s+Unidos\b(?!\s+de\s+(?:Norte\s*)?Am[eé]rica\b|\s+del\s+Brasil\b)|\bEE\.\s*UU\.",
    "Estados Unidos de Norteamérica": r"\bEstados\s+Unidos\s+de\s+(?:Norte\s*)?Am[eé]rica\b",
    "Gran Bretaña": r"\bGran\s+Breta[ñn]a\b",
    "Inglaterra": r"(?<!Banco\sde\s)\bInglaterra\b(?!\s*(?:es\s+el\s+Banco))",
    "Reino Unido": r"\bReino\s+Unido\b",
    "Commonwealth": r"\bCommonwealth\b|\bComunidad\s+Brit[aá]nica\s+de\s+Naciones\b",
    "Alemania": r"\bAlemania\b",
    "Roca-Runciman": (
        r"\b(?:(?:Pacto|Convenio|Tratado|Acuerdo)\s+)?Roca\s*[-\–\s]\s*Runciman\b"
        r"|\b(?:Convenio|Tratado|Pacto)\s+de\s+Londres\b"
        r"|\b(?:convenio|tratado)\s+anglo\s*[-\–]?\s*argentino\b"
    ),
    "Cobden-Chevalier": r"\b(?:(?:Tratado|Pacto)\s+)?Cobden\s*[-\–\s]\s*Chevalier\b",
    "Conferencia de Ottawa": r"\b(?:Conferencia|Pactos?|Acuerdos?)\s+(?:Imperial\s+)?de\s+Ottawa\b",
    "Gran Depresión": r"\bGran\s+Depresi[oó]n\b|\bdepresi[oó]n\s+econ[oó]mica\s+mundial\b",
    "Wall Street": r"\bWall\s+Street\b",
    "Hoover": r"\bHoover\b",
    "Roosevelt": r"\bRoosevelt\b",
    "Unión Cívica Radical": r"\bUni[oó]n\s+C[ií]vica\s+Radical\b|\bU\.\s*C\.\s*R\.",
    "Partido Socialista": r"\bPartido\s+Socialista\b",
    "Partido Demócrata Nacional": r"\bPartido\s+Dem[oó]crata\s+Nacional\b|\bDem[oó]crata\s+Nacional\b",
    "Partido Demócrata Progresista": r"\bPartido\s+Dem[oó]crata\s+Progresista\b|\bDem[oó]crata\s+Progresista\b",
    "Concordancia": r"\bConcordancia\b",
}



EJES_TEMATICOS_POLITICA_COMERCIAL = {
    "ARANCELES_Y_PROTECCIONISMO": {
        "nombre_eje": "Aranceles, Tarifas Aduaneras y Proteccionismo Industrial",
        "patron": re.compile(
            r"\b(?:"
            r"arancel(?:es|ario|aria)?|tarifa(?:s)?\s+de\s+aval[uú]os|derechos?\s+aduaneros?|derechos?\s+de\s+importaci[oó]n|"
            r"aforo(?:s)?\s+aduaneros?|adicional\s+del\s+10\s*%|proteccionismo|protecci[oó]n\s+aduanera|"
            r"protecci[oó]n\s+a\s+la\s+industria|librecambio|libre\s+cambio|dumping|contingentes?\s+de\s+importaci[oó]n|"
            r"cuotas?\s+de\s+importaci[oó]n|barreras?\s+aduaneras?|medidas?\s+para[-\s]?arancelarias?"
            r")\b",
            re.IGNORECASE
        )
    },
    "CONTROL_DE_CAMBIOS_Y_POLITICA_MONETARIA": {
        "nombre_eje": "Control de Cambios, Divisas y Régimen Monetario",
        "patron": re.compile(
            r"\b(?:"
            r"control\s+de\s+cambios|tipo(?:s)?\s+de\s+cambio|mercado\s+libre\s+de\s+cambios|cambio\s+oficial|"
            r"permisos?\s+previos?\s+de\s+cambio|divisas?\s+extranjeras?|bloqueo\s+de\s+fondos|"
            r"desvalorizaci[oó]n\s+monetaria|depreciaci[oó]n\s+del\s+peso|conversi[oó]n\s+del\s+peso|"
            r"patr[oó]n\s+oro|redescuento|emisi[oó]n\s+monetaria|margen\s+de\s+cambios"
            r")\b",
            re.IGNORECASE
        )
    },
    "PACTO_ROCA_RUNCIMAN_Y_BILATERALISMO": {
        "nombre_eje": "Pacto Roca-Runciman, Cuota de Carnes y Bilateralismo",
        "patron": re.compile(
            r"\b(?:"
            r"roca\s*[-\–\s]\s*runciman|convenio\s+de\s+londres|tratado\s+de\s+londres|conferencia\s+de\s+ottawa|"
            r"acuerdos?\s+de\s+ottawa|cuota\s+de\s+carnes|chilled\s+beef|carne\s+enfriada|carne\s+congelada|"
            r"pool\s+frigor[ií]fico|monopolio\s+frigor[ií]fico|cl[aá]usula\s+de\s+la\s+naci[oó]n\s+m[aá]s\s+favorecida|"
            r"comprar\s+a\s+quien\s+nos\s+compra|comercio\s+bilateral|tratados?\s+de\s+comercio|reciprocidad\s+comercial"
            r")\b",
            re.IGNORECASE
        )
    },
    "JUNTAS_REGULADORAS_E_INTERVENCION_ESTATAL": {
        "nombre_eje": "Juntas Reguladoras de la Producción e Intervención Estatal",
        "patron": re.compile(
            r"\b(?:"
            r"juntas?\s+reguladoras?|junta\s+nacional\s+de\s+carnes|junta\s+reguladora\s+de\s+granos|"
            r"junta\s+reguladora\s+de\s+vinos|junta\s+nacional\s+del?\s+algod[oó]n|industria\s+lechera|"
            r"comisi[oó]n\s+reguladora\s+de\s+la\s+yerba\s+mate|corporaci[oó]n\s+argentina\s+de\s+productores|"
            r"precios?\s+b[aá]sicos?|precios?\s+m[ií]nimos?|red\s+de\s+elevadores\s+de\s+granos|econom[ií]a\s+dirigida"
            r")\b",
            re.IGNORECASE
        )
    },
    "ESPECIALIZACION_PRODUCTIVA_AGRO_E_INDUSTRIA": {
        "nombre_eje": "Especialización Productiva: Agroexportación, Industria y Economías Regionales",
        "patron": re.compile(
            r"\b(?:"
            r"exportaci[oó]n\s+de\s+(?:carnes|cereales|granos|trigo|ma[ií]z|lino|lanas|cueros)|"
            r"producci[oó]n\s+agropecuaria|ganader[ií]a\s+argentina|agricultura\s+nacional|"
            r"mercado\s+interno|sustituci[oó]n\s+de\s+importaciones|industria\s+nacional|industria\s+manufacturera|"
            r"industria\s+textil|industria\s+azucarera|industria\s+vitivin[ií]cola|yerba\s+mate|"
            r"productores\s+rurales|arrendamientos?\s+rurales|costo\s+de\s+vida|abastecimiento"
            r")\b",
            re.IGNORECASE
        )
    },
    "SOCIOS_COMERCIALES_Y_COMERCIO_EXTERIOR": {
        "nombre_eje": "Vínculos con Socios Comerciales e Intercambio Exterior",
        "patron": re.compile(
            r"\b(?:"
            r"balanza\s+comercial|balanza\s+de\s+pagos|intercambio\s+comercial|comercio\s+exterior|"
            r"comercio\s+internacional|mercado\s+brit[aá]nico|mercado\s+ingl[eé]s|mercado\s+norteamericano|"
            r"importaciones\s+brit[aá]nicas|importaciones\s+norteamericanas|carb[oó]n\s+ingl[eé]s|"
            r"ferrocarriles\s+brit[aá]nicos|capitales\s+extranjeros|socios\s+comerciales"
            r")\b",
            re.IGNORECASE
        )
    }
}



# Valores sacados de: https://servicios.infoleg.gob.ar/infolegInternet/ (Leyes económicas y comerciales históricas 1929-1939)
CATALOGO_LEYES_HISTORICAS = {
    "11281": "Ley 11.281 (Ley de Aduanas)",
    "11290": "Ley 11.290 (Impuesto de Sellos)",
    "11388": "Ley 11.388 (Régimen de Sociedades Cooperativas)",
    "11584": "Ley 11.584 (Presupuesto General y Emergencia Económica 1932)",
    "11627": "Ley 11.627 (Arrendamientos Rurales)",
    "11658": "Ley 11.658 (Creación de la Dirección Nacional de Vialidad)",
    "11682": "Ley 11.682 (Impuesto a los Réditos)",
    "11683": "Ley 11.683 (Procedimiento del Impuesto a los Réditos)",
    "11693": "Ley 11.693 (Aprobación del Convenio Roca-Runciman / Tratado de Londres)",
    "11729": "Ley 11.729 (Reforma del Código de Comercio - Empleados de Comercio)",
    "11742": "Ley 11.742 (Red Nacional de Elevadores de Granos)",
    "11747": "Ley 11.747 (Ley Nacional de Carnes - Creación de la Junta Nacional de Carnes y CAP)",
    "12137": "Ley 12.137 (Creación de la Junta Reguladora de Vinos)",
    "12139": "Ley 12.139 (Unificación de Impuestos Internos)",
    "12143": "Ley 12.143 (Impuesto a las Ventas)",
    "12155": "Ley 12.155 (Creación del Banco Central de la República Argentina)",
    "12156": "Ley 12.156 (Ley de Bancos)",
    "12157": "Ley 12.157 (Creación del Instituto Movilizador de Inversiones Bancarias)",
    "12158": "Ley 12.158 (Reforma de la Carta Orgánica del Banco de la Nación)",
    "12159": "Ley 12.159 (Reforma de la Carta Orgánica del Banco Hipotecario Nacional)",
    "12160": "Ley 12.160 (Organización del Sistema Monetario y Bancario)",
    "12236": "Ley 12.236 (Comisión Reguladora de la Producción y Comercio de la Yerba Mate)",
    "12253": "Ley 12.253 (Comisión Nacional de Granos y Elevadores)",
    "12355": "Ley 12.355 (Reforma de la Junta Reguladora de Vinos)",
    "12591": "Ley 12.591 (Control de Precios Máximos y Abastecimiento - 1939)",
}

PROVINCIAS_Y_TERRITORIOS_1930 = {
    "Buenos Aires": r"\bProvincia\s+de\s+Buenos\s+Aires\b|\bBuenos\s+Aires\b",
    "Capital Federal": r"\bCapital\s+Federal\b|\bCiudad\s+de\s+Buenos\s+Aires\b",
    "Santa Fe": r"\bSanta\s+Fe\b",
    "Córdoba": r"\bC[oó]rdoba\b",
    "Entre Ríos": r"\bEntre\s+R[ií]os\b",
    "Corrientes": r"\bCorrientes\b",
    "Mendoza": r"\bMendoza\b",
    "San Juan": r"\bSan\s+Juan\b",
    "San Luis": r"\bSan\s+Luis\b",
    "Tucumán": r"\bTucum[aá]n\b",
    "Salta": r"\bSalta\b",
    "Jujuy": r"\bJujuy\b",
    "Santiago del Estero": r"\bSantiago\s+del\s+Estero\b",
    "Catamarca": r"\bCatamarca\b",
    "La Rioja": r"\bLa\s+Rioja\b",
    "La Pampa": r"\bLa\s+Pampa\b|\bPampa\s+Central\b",
    "Chaco": r"\b(?:Territorio\s+del\s+)?Chaco\b",
    "Misiones": r"\b(?:Territorio\s+de\s+)?Misiones\b",
    "Río Negro": r"\bR[ií]o\s+Negro\b",
    "Neuquén": r"\bNeuqu[eé]n\b",
    "Chubut": r"\bChubut\b",
    "Santa Cruz": r"\bSanta\s+Cruz\b",
    "Formosa": r"\bFormosa\b",
    "Tierra del Fuego": r"\bTierra\s+del\s+Fuego\b",
}

# Apellidos y cargos de Ministros del Poder Ejecutivo Nacional que intervinieron en el Congreso (1929-1939)
MINISTROS_PE_1929_1939 = {
    "pinedo", "duhau", "hueyo", "saavedra lamas", "de tomaso", "alvarado",
    "uriburu", "cárcano", "carcano", "groppo", "padilla", "ortiz", "melo",
    "rodríguez jáuregui", "castillo", "bullrich", "videla", "cantilo",
    "abacá", "fleitas", "zuberbühler", "pérez", "iriondo"
}



REGEX_FORMULA_PROCEDIMENTAL = re.compile(
    r"^(?:"
    r"Queda\s+(?:abierta|levantada)\s+la\s+sesi[oó]n|"
    r"Se\s+va\s+a\s+(?:votar|dar\s+lectura|pasar\s+al\s+orden\s+del\s+d[ií]a)|"
    r"Tiene\s+la\s+palabra\s+el\s+se[ñn]or\s+(?:diputado|senador|ministro)|"
    r"Si\s+no\s+se\s+hace\s+uso\s+de\s+la\s+palabra|"
    r"Est[aá]\s+en\s+consideraci[oó]n|"
    r"Pido\s+la\s+palabra\.?$"
    r")",
    re.IGNORECASE
)


def clasificar_calidad_intervencion(texto: str, info_parl: Dict) -> Tuple[str, int, bool]:
    """
    Clasifica cada fila de 'intervenciones' de forma realista para no distorsionar la participación:
    - 'PROCEDIMENTAL_PRESIDENCIA': conducción formal de la sesión o lectura de secretaría.
    - 'ACOTACION_O_INTERRUPCION': intervención menor a 15 palabras (interjecciones, pedidos de palabra).
    - 'INTERVENCION_BREVE': entre 15 y 79 palabras (preguntas puntuales, aclaraciones, mociones).
    - 'DISCURSO_SUSTANTIVO': 80 o más palabras de exposición parlamentaria de fondo.

    Devuelve: (tipo_intervencion, cantidad_palabras, es_participacion_sustantiva)
    """
    if not texto:
        return "VACIA", 0, False

    palabras = re.findall(r"\b\w+\b", texto)
    n_palabras = len(palabras)

    if n_palabras < 15:
        return "ACOTACION_O_INTERRUPCION", n_palabras, False

    if n_palabras < 45 and REGEX_FORMULA_PROCEDIMENTAL.search(texto.strip()):
        return "PROCEDIMENTAL_PRESIDENCIA", n_palabras, False

    if n_palabras < 80:
        return "INTERVENCION_BREVE", n_palabras, True

    return "DISCURSO_SUSTANTIVO", n_palabras, True


def determinar_rol_institucional_orador(fila_interv: Dict, info_parl: Dict, info_ses: Dict, texto: str) -> str:
    """
    Distingue si quien habla representa la POSTURA OFICIAL DEL PODER EJECUTIVO (Ministros)
    o a los MIEMBROS DE LAS CÁMARAS (Diputados / Senadores), tal como pide el Plan de Trabajo:
    - 'PODER_EJECUTIVO_MINISTRO'
    - 'CAMARA_DIPUTADOS'
    - 'CAMARA_SENADORES'
    - 'NO_IDENTIFICADO_O_PRESIDENCIA'
    """
    rol_db = str(info_parl.get("rol") or "").strip().lower()
    nombre_db = str(info_parl.get("nombre_apellido") or "").strip().lower()
    orador_ocr = str(fila_interv.get("nombre_extraido_ocr") or "").strip().lower()
    inicio_txt = texto[:180].lower() if texto else ""

    if "ministro" in rol_db or "ministro" in nombre_db or "ministro" in orador_ocr:
        return "PODER_EJECUTIVO_MINISTRO"

    if re.search(r"\b(?:sr\.|se[ñn]or)\s+ministro\s+de\s+(?:hacienda|agricultura|relaciones\s+exteriores|obras\s+p[uú]blicas|interior|guerra|marina|justicia)", inicio_txt):
        return "PODER_EJECUTIVO_MINISTRO"

    if rol_db == "externo" and any(ap in nombre_db or ap in orador_ocr for ap in MINISTROS_PE_1929_1939):
        return "PODER_EJECUTIVO_MINISTRO"

    if "senador" in rol_db:
        return "CAMARA_SENADORES"
    if "diputado" in rol_db:
        return "CAMARA_DIPUTADOS"

    if "no identificado" in nombre_db or rol_db == "externo":
        return "NO_IDENTIFICADO_O_PRESIDENCIA"

    camara_ses = str(info_ses.get("camara") or "").lower()
    if "senad" in camara_ses:
        return "CAMARA_SENADORES"
    if "diput" in camara_ses:
        return "CAMARA_DIPUTADOS"

    return "MIEMBRO_CAMARA"


def generar_regex_tolerante_ocr(nombre_entidad: str) -> Tuple[str, bool]:
    """
    Convierte el nombre de una entidad en una expresión regular tolerante a falta de tildes
    y guiones de corte en el OCR de los años 30, distinguiendo siglas sensibles a mayúsculas.
    """
    if nombre_entidad in PATRONES_ESPECIALES_EPOCA:
        es_sigla = nombre_entidad.isupper() and len(nombre_entidad) <= 6
        return PATRONES_ESPECIALES_EPOCA[nombre_entidad], es_sigla

    if nombre_entidad.isupper() and len(nombre_entidad) <= 6:
        letras = [re.escape(c) for c in nombre_entidad]
        return r"\b" + r"\.?\s*".join(letras) + r"\.?\b", True

    mapa_vocales = {
        "a": "[aáâ]", "á": "[aáâ]",
        "e": "[eéê]", "é": "[eéê]",
        "i": "[iíî]", "í": "[iíî]",
        "o": "[oóô]", "ó": "[oóô]",
        "u": "[uúü]", "ú": "[uúü]",
    }
    palabras = nombre_entidad.split()
    palabras_regex = []
    for pal in palabras:
        pal_re = ""
        for ch in pal:
            low = ch.lower()
            if low in mapa_vocales:
                pal_re += mapa_vocales[low]
            else:
                pal_re += re.escape(ch)
        palabras_regex.append(pal_re)

    patron = r"\b" + r"[\s\xad]+".join(palabras_regex) + r"\b"
    return patron, False


def validar_mencion_en_contexto(nombre_lista: str, termino_exacto: str, snippet_contexto: str) -> bool:
    """
    Desambiguación heurística local para evitar falsos positivos en siglas cortas,
    fórmulas de apertura de sesión ('En Buenos Aires, a los...') o nombres de calles.
    """
    if nombre_lista in ("CAC", "UIA"):
        if "." in termino_exacto:
            return True
        ctx_low = snippet_contexto.lower()
        return any(
            kw in ctx_low
            for kw in (
                "cámara", "comercio", "industrial", "unión", "asociación",
                "entidad", "nota", "solicita", "memorial", "industria", "productores", "gremial"
            )
        )

    if nombre_lista in ("Hoover", "Roosevelt"):
        if re.search(r"\b(?:calle|avenida|hospital|escuela)\s+" + re.escape(nombre_lista), snippet_contexto, re.IGNORECASE):
            return False

    if nombre_lista == "Buenos Aires":
        if re.search(r"[-—–]?\s*En\s+(?:la\s+ciudad\s+de\s+)?Buenos\s+Aires[\,\s]+a\s+los", snippet_contexto, re.IGNORECASE):
            return False

    return True


def _extraer_lineas_desde_pdf_entidades(ruta_pdf: str) -> List[str]:
    """
    Extrae las líneas de 'Lista Entidades - OCT26.pdf' uniendo renglones partidos
    dentro de un mismo ítem con viñeta ('●', '•', '-') y respetando los encabezados de categoría.
    """
    texto_completo = ""
    if fitz is not None:
        doc = fitz.open(ruta_pdf)
        texto_completo = "\n".join(page.get_text("text") for page in doc)
        doc.close()
    elif pdfplumber is not None:
        with pdfplumber.open(ruta_pdf) as pdf:
            texto_completo = "\n".join((p.extract_text() or "") for p in pdf.pages)
    elif PdfReader is not None:
        reader = PdfReader(ruta_pdf)
        texto_completo = "\n".join((p.extract_text() or "") for p in reader.pages)

    lineas_brutas = [ln.strip() for ln in texto_completo.splitlines() if ln.strip()]
    encabezados_cat = {
        "instituciones económicas oficiales/privadas",
        "unidades políticas extranjeras",
        "fenómenos/procesos/hechos",
        "personalidades",
        "actores políticos",
        "provincias y territorios",
    }

    lineas_reconstruidas = []
    for ln in lineas_brutas:
        ln_sin_dos_puntos = ln.rstrip(":").strip()
        if ln_sin_dos_puntos.lower().startswith("lista entidades"):
            continue
        if ln_sin_dos_puntos.lower() in encabezados_cat:
            lineas_reconstruidas.append(ln_sin_dos_puntos)
            continue
        if re.match(r"^[\●\•\-\*\▪\uf0b7]\s*", ln):
            limpia_b = re.sub(r"^[\●\•\-\*\▪\uf0b7\s]+", "", ln).strip()
            if limpia_b:
                lineas_reconstruidas.append(limpia_b)
        elif lineas_reconstruidas and lineas_reconstruidas[-1].lower() not in encabezados_cat:
            # Continuación de renglón partido de la viñeta anterior
            lineas_reconstruidas[-1] = f"{lineas_reconstruidas[-1]} {ln}".strip()
        else:
            lineas_reconstruidas.append(ln)

    return lineas_reconstruidas


def descubrir_archivo_entidades(ruta_sugerida: Optional[str] = None) -> Optional[str]:
    """
    Busca automáticamente 'Lista Entidades - OCT26.pdf' (o .docx / .xlsx / .csv / .txt)
    en el directorio de trabajo.
    """
    if ruta_sugerida and os.path.exists(ruta_sugerida):
        return ruta_sugerida

    # Prioridad 1: 'Lista Entidades - OCT26.pdf'
    candidatos_prioritarios = [
        "Lista Entidades - OCT26.pdf",
        "Lista Entidades - OCT26.docx",
    ]
    for cand in candidatos_prioritarios:
        if os.path.exists(cand):
            return cand

    for archivo in sorted(os.listdir(".")):
        low = archivo.lower()
        if any(k in low for k in ("lista entidades", "entidades", "actores")) and low.endswith((".pdf", ".docx", ".xlsx", ".csv", ".txt")):
            if not low.startswith("ner_") and "plan de trabajo" not in low:
                return archivo
    return None


def cargar_entidades_desde_archivo(
    ruta_archivo: Optional[str] = "Lista Entidades - OCT26.pdf",
    incluir_complementarias_plan: bool = True
) -> List[Dict]:
    """
    Lee las entidades registradas en 'Lista Entidades - OCT26.pdf' (o formato alternativo),
    etiqueta cuáles pertenecen exactamente al listado oficial del PDF ('es_lista_oficial_pdf': True)
    y suma opcionalmente las entidades políticas/institucionales del Plan de Trabajo.
    """
    categorias_conocidas = {
        "instituciones económicas oficiales/privadas": "Instituciones económicas oficiales/privadas",
        "unidades políticas extranjeras": "Unidades políticas extranjeras",
        "fenómenos/procesos/hechos": "Fenómenos/procesos/hechos",
        "personalidades": "Personalidades",
        "actores políticos": "Actores políticos y partidarios",
        "actores políticos y partidarios": "Actores políticos y partidarios",
        "provincias y territorios": "Actores provinciales y regionales",
    }

    ruta_real = descubrir_archivo_entidades(ruta_archivo)
    lineas_crudas = []

    if ruta_real and os.path.exists(ruta_real):
        ext = os.path.splitext(ruta_real)[1].lower()
        try:
            if ext == ".pdf":
                lineas_crudas = _extraer_lineas_desde_pdf_entidades(ruta_real)
            elif ext == ".docx" and docx is not None:
                doc = docx.Document(ruta_real)
                lineas_crudas = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            elif ext == ".xlsx":
                df_e = pd.read_excel(ruta_real)
                for col in df_e.columns:
                    lineas_crudas.extend(str(v).strip() for v in df_e[col].dropna().tolist() if str(v).strip())
            elif ext in (".csv", ".txt"):
                with open(ruta_real, "r", encoding="utf-8", errors="replace") as f:
                    lineas_crudas = [ln.strip() for ln in f if ln.strip()]
            print(f"[*] Archivo de entidades leído exitosamente: '{ruta_real}' ({len(lineas_crudas)} líneas procesadas)")
        except Exception as e:
            print(f"[!] Aviso leyendo '{ruta_real}': {e}. Utilizando catálogo exacto embebido de 'Lista Entidades - OCT26.pdf'.")

    pares_entrada = []
    categoria_actual = "Instituciones económicas oficiales/privadas"

    for linea in lineas_crudas:
        limpia = re.sub(r"^[\●\•\-\*\▪\uf0b7\s]+", "", str(linea)).rstrip(":").strip()
        if not limpia or limpia.lower().startswith("lista entidades"):
            continue
        if limpia.lower() in categorias_conocidas:
            categoria_actual = categorias_conocidas[limpia.lower()]
            continue
        pares_entrada.append((limpia, categoria_actual, True))

    # Garantizar que las 42 entidades de 'Lista Entidades - OCT26.pdf' estén siempre presentes
    for nom_pdf, cat_pdf in ENTIDADES_OFICIALES_PDF_OCT26:
        pares_entrada.append((nom_pdf, cat_pdf, True))

    if incluir_complementarias_plan:
        for nom_comp, cat_comp in ENTIDADES_COMPLEMENTARIAS_PLAN:
            pares_entrada.append((nom_comp, cat_comp, False))

    catalogo = []
    vistos = set()

    for nombre_item, categoria_item, es_oficial_pdf in pares_entrada:
        clave_low = nombre_item.lower()
        if clave_low in vistos:
            continue
        vistos.add(clave_low)

        es_del_pdf = clave_low in NOMBRES_EXACTOS_PDF_OCT26 or es_oficial_pdf
        if clave_low in NOMBRES_EXACTOS_PDF_OCT26:
            nombre_item, categoria_item = NOMBRES_EXACTOS_PDF_OCT26[clave_low]

        nombre_canonico = MAPA_CANONICO.get(nombre_item, nombre_item)
        tipo_actor = MAPA_TIPO_ACTOR.get(nombre_canonico, "ACTOR_ECONOMICO_INSTITUCIONAL")
        patron_re, es_case_sensitive = generar_regex_tolerante_ocr(nombre_item)
        requiere_llm = es_case_sensitive or (categoria_item == "Personalidades")

        catalogo.append({
            "nombre_lista": nombre_item,
            "nombre_canonico": nombre_canonico,
            "categoria": categoria_item,
            "tipo_actor": tipo_actor,
            "es_lista_oficial_pdf": es_del_pdf,
            "origen_catalogo": "LISTA_ENTIDADES_PDF" if es_del_pdf else "COMPLEMENTARIO_PLAN_TRABAJO",
            "patron_regex": patron_re,
            "es_case_sensitive": es_case_sensitive,
            "requiere_desambiguacion_llm": requiere_llm
        })

    return catalogo


# Alias de compatibilidad
cargar_entidades_desde_docx = cargar_entidades_desde_archivo


REGEX_MENCION_LEY = re.compile(
    r"\b(?:ley(?:es)?)\s*(?:n[uú]m(?:ero|\.)?\s*|n[º°o\.]\s*)?(\d{1,2}[\.\s]?\d{3}|\d{3,5})\b",
    re.IGNORECASE
)

REGEX_PROVINCIAS_COMPILADAS = {
    prov: re.compile(pat, re.IGNORECASE)
    for prov, pat in PROVINCIAS_Y_TERRITORIOS_1930.items()
}

REGEX_ACTOR_EMERGENTE_NLP = re.compile(
    r"\b("
    r"(?:Sociedad\s+Rural|C[aá]mara\s+(?:de\s+Comercio|Sindical|Gremial|Industrial|Agr[ií]cola)|"
    r"Centro\s+(?:de\s+Bodegueros|Vitivin[ií]cola|Azucarero|de\s+Importadores|de\s+Exportadores|de\s+Navegaci[oó]n|Cerealista)|"
    r"Federaci[oó]n\s+(?:Obrera|Gremial|Rural|Econ[oó]mica)|"
    r"Asociaci[oó]n\s+(?:de\s+Cooperativas|de\s+Bancos|de\s+Productores|Rural)|"
    r"Frigor[ií]fico|Ferrocarril)"
    r"\s+(?:de\s+|del\s+|la\s+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}"
    r"(?:\s+(?:de|del|la|las|los|y)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}|\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}){0,3}"
    r")"
)

# Vocabulario económico-comercial clave para el Análisis Exploratorio del Corpus (Objetivo específico 2)
VOCABULARIO_COMERCIAL_CLAVE_1930 = [
    "arancel", "aranceles", "aduana", "aduanas", "aforo", "aforos", "tarifa", "tarifas",
    "importación", "importaciones", "exportación", "exportaciones", "divisas", "cambio",
    "cambios", "proteccionismo", "librecambio", "contingentes", "cuota", "cuotas",
    "tratado", "convenio", "bilateral", "reciprocidad", "frigorífico", "frigoríficos",
    "carnes", "chilled", "granos", "trigo", "maíz", "lino", "cereales", "algodón",
    "vino", "vinos", "azúcar", "yerba", "leche", "industria", "industrial",
    "agropecuaria", "ganadería", "agricultura", "productores", "precios", "monopolio",
    "trust", "empréstito", "deuda", "oro", "conversión", "redescuento", "presupuesto",
    "impuesto", "réditos", "crisis", "depresión", "desocupación", "salarios", "consumo"
]
SET_VOCABULARIO_CLAVE = set(VOCABULARIO_COMERCIAL_CLAVE_1930)


def extraer_leyes_estructuradas(texto: str) -> List[Dict]:
    """
    Detecta todas las leyes mencionadas en un texto parlamentario o proyecto de ley,
    normaliza su numeración (ej. 'Ley 11.747') e identifica si es una ley económica clave.
    """
    if not texto:
        return []
    encontradas = {}
    for m in REGEX_MENCION_LEY.finditer(texto):
        num_crudo = re.sub(r"[\.\s]", "", m.group(1))
        if not num_crudo.isdigit():
            continue
        num_int = int(num_crudo)
        if 1920 <= num_int <= 1945:
            continue
        if num_int < 50 or num_int > 15000:
            continue

        if len(num_crudo) >= 4:
            num_fmt = f"{num_crudo[:-3]}.{num_crudo[-3:]}"
        else:
            num_fmt = num_crudo

        etiqueta = CATALOGO_LEYES_HISTORICAS.get(num_crudo, f"Ley {num_fmt}")
        if num_crudo not in encontradas:
            encontradas[num_crudo] = {
                "numero_limpio": num_crudo,
                "codigo_ley": f"Ley {num_fmt}",
                "descripcion": etiqueta,
                "frecuencia": 0
            }
        encontradas[num_crudo]["frecuencia"] += 1

    return list(encontradas.values())


def detectar_provincias_en_texto(texto: str) -> Dict[str, int]:
    """Cuenta menciones a provincias y territorios nacionales dentro del texto."""
    if not texto:
        return {}
    conteo = {}
    for prov, rx in REGEX_PROVINCIAS_COMPILADAS.items():
        matches = list(rx.finditer(texto))
        if matches:
            validos = [
                m for m in matches
                if validar_mencion_en_texto_provincia(prov, texto, m.start(), m.end())
            ]
            if validos:
                conteo[prov] = len(validos)
    return conteo


def validar_mencion_en_texto_provincia(prov: str, texto: str, ini: int, fin: int) -> bool:
    if prov != "Buenos Aires":
        return True
    ventana = texto[max(0, ini - 35): min(len(texto), fin + 35)]
    if re.search(r"En\s+(?:la\s+ciudad\s+de\s+)?Buenos\s+Aires[\,\s]+a\s+los", ventana, re.IGNORECASE):
        return False
    return True


def detectar_ejes_tematicos_y_postura(texto: str, ventana_ctx: int = 280) -> List[Dict]:
    """
    Detecta qué ejes temáticos de política comercial y especialización productiva
    se discuten en la intervención y evalúa la postura ABSA del orador hacia cada eje.
    """
    if not texto or len(texto) < 15:
        return []

    resultados_ejes = []
    for codigo_eje, cfg in EJES_TEMATICOS_POLITICA_COMERCIAL.items():
        matches = list(cfg["patron"].finditer(texto))
        if not matches:
            continue

        # Evaluar polaridad/postura en torno a las apariciones del eje dentro del discurso
        snippets = []
        terminos_vistos = Counter()
        for m in matches[:8]:
            terminos_vistos[m.group(0).lower()] += 1
            ini_c = max(0, m.start() - ventana_ctx)
            fin_c = min(len(texto), m.end() + ventana_ctx)
            snippets.append(texto[ini_c:fin_c])

        contexto_unido = " ... ".join(snippets)
        score_pol, postura = evaluar_polaridad_y_postura_1930(contexto_unido, aspecto=cfg["nombre_eje"])

        resultados_ejes.append({
            "codigo_eje": codigo_eje,
            "nombre_eje": cfg["nombre_eje"],
            "frecuencia_terminos": len(matches),
            "terminos_principales": ", ".join(k for k, _ in terminos_vistos.most_common(4)),
            "postura_absa": postura,
            "score_polaridad": score_pol
        })

    return resultados_ejes


def extraer_frecuencias_vocabulario_comercial(texto: str) -> Counter:
    """Extrae frecuencias de términos económicos/comerciales clave para el EDA por año y cámara."""
    if not texto:
        return Counter()
    palabras = re.findall(r"\b[a-záéíóúñü]{3,}\b", texto.lower())
    return Counter(p for p in palabras if p in SET_VOCABULARIO_CLAVE)


def detectar_actores_emergentes_nlp(texto: str, nombres_canonicos_conocidos: Set[str]) -> List[str]:
    """
    Utiliza patrones morfosintácticos de NLP para descubrir organizaciones corporativas,
    cámaras regionales, frigoríficos y ferrocarriles mencionados en los debates.
    """
    if not texto:
        return []
    hallados = []
    for m in REGEX_ACTOR_EMERGENTE_NLP.finditer(texto):
        ent = re.sub(r"\s+", " ", m.group(1)).strip(" ,.;:-—")
        if len(ent) > 8 and ent.lower() not in nombres_canonicos_conocidos:
            hallados.append(ent)
    return hallados



def sincronizar_catalogo_supabase(catalogo: List[Dict]) -> Dict[str, int]:
    """
    Sincroniza el catálogo de entidades con Supabase. Si la tabla 'catalogo_entidades'
    no existe o tiene restricciones, devuelve un mapa de IDs determinístico en memoria.
    """
    datos_upsert = [
        {
            "nombre_lista": c["nombre_lista"],
            "nombre_canonico": c["nombre_canonico"],
            "categoria": c["categoria"],
            "patron_regex": c["patron_regex"],
            "requiere_desambiguacion_llm": c["requiere_desambiguacion_llm"]
        }
        for c in catalogo
    ]
    try:
        supabase.table("catalogo_entidades").upsert(datos_upsert, on_conflict="nombre_lista").execute()
        res = supabase.table("catalogo_entidades").select("id_entidad, nombre_lista").execute()
        if res.data:
            return {fila["nombre_lista"]: fila["id_entidad"] for fila in res.data}
    except Exception as e:
        print(f"   [!] Aviso en tabla 'catalogo_entidades' ({e}). Usando IDs locales en memoria.")

    return {c["nombre_lista"]: idx + 1 for idx, c in enumerate(catalogo)}


def compilar_buscadores(catalogo: List[Dict], mapa_ids: Dict[str, int]) -> List[Dict]:
    """
    Compila las expresiones regulares ordenándolas de MAYOR a MENOR longitud de nombre_lista
    para evitar solapamientos (ej. 'Estados Unidos de Norteamérica' antes que 'Estados Unidos',
    y 'Banco de Inglaterra' antes que 'Inglaterra').
    """
    buscadores = []
    for item in sorted(catalogo, key=lambda x: len(x["nombre_lista"]), reverse=True):
        flags = 0 if item["es_case_sensitive"] else re.IGNORECASE
        buscadores.append({
            **item,
            "id_entidad": mapa_ids.get(item["nombre_lista"], 0),
            "regex_compilado": re.compile(item["patron_regex"], flags)
        })
    return buscadores


def analizar_intervencion(
    id_intervencion: int,
    texto_intervencion: str,
    buscadores: List[Dict],
    qwen_pool: Optional[QwenClientPool] = None,
    ventana_contexto: int = 300
) -> Tuple[List[Dict], List[Dict]]:
    """
    Escanea el texto de una intervención parlamentaria (o de una ley), detecta todas las
    entidades sin solapamientos, evalúa su validez y postura (ABSA) y agrega las frecuencias.
    """
    if not texto_intervencion or len(texto_intervencion) < 5:
        return [], []

    # Normalizar guiones blandos de OCR (\xad) para que no corten nombres de entidades
    texto_norm = texto_intervencion.replace("\xad", "")

    rangos_usados = []
    menciones_detalle = []
    conteo_por_entidad = {}

    for buscador in buscadores:
        id_ent = buscador["id_entidad"]
        for match in buscador["regex_compilado"].finditer(texto_norm):
            ini, fin = match.span()
            if any(not (fin <= r_ini or ini >= r_fin) for r_ini, r_fin in rangos_usados):
                continue

            termino_exacto = match.group(0).strip()
            ctx_ini = max(0, ini - ventana_contexto)
            ctx_fin = min(len(texto_norm), fin + ventana_contexto)
            snippet_contexto = re.sub(r"\s+", " ", texto_norm[ctx_ini:ctx_fin]).strip()

            if not validar_mencion_en_contexto(buscador["nombre_lista"], termino_exacto, snippet_contexto):
                continue

            es_valida = True
            score_pol, postura = evaluar_polaridad_y_postura_1930(snippet_contexto, aspecto=buscador["nombre_canonico"])
            justificacion = None

            if qwen_pool and (
                (USAR_QWEN_DESAMBIGUACION and buscador["requiere_desambiguacion_llm"])
                or EVALUAR_POSTURA_ABSA_CON_QWEN
            ):
                eval_llm = qwen_pool.analizar_mencion(
                    buscador["nombre_canonico"],
                    snippet_contexto,
                    evaluar_absa=EVALUAR_POSTURA_ABSA_CON_QWEN
                )
                es_valida = eval_llm["es_valida"]
                postura = eval_llm["postura"]
                score_pol = eval_llm.get("score_polaridad", score_pol)
                justificacion = eval_llm["justificacion"]

            if not es_valida:
                continue

            rangos_usados.append((ini, fin))

            menciones_detalle.append({
                "id_intervencion": id_intervencion,
                "id_entidad": id_ent,
                "nombre_lista": buscador["nombre_lista"],
                "nombre_canonico": buscador["nombre_canonico"],
                "categoria": buscador["categoria"],
                "tipo_actor": buscador["tipo_actor"],
                "es_lista_oficial_pdf": buscador.get("es_lista_oficial_pdf", True),
                "origen_catalogo": buscador.get("origen_catalogo", "LISTA_ENTIDADES_PDF"),
                "termino_detectado": termino_exacto,
                "posicion_caracter": ini,
                "contexto_mencion": snippet_contexto,
                "validado_llm": bool(USAR_QWEN_DESAMBIGUACION or EVALUAR_POSTURA_ABSA_CON_QWEN),
                "postura_absa": postura,
                "score_polaridad": score_pol,
                "justificacion_llm": justificacion
            })

            if id_ent not in conteo_por_entidad:
                conteo_por_entidad[id_ent] = {
                    "frecuencia": 0,
                    "variantes": set(),
                    "nombre_lista": buscador["nombre_lista"],
                    "nombre_canonico": buscador["nombre_canonico"],
                    "categoria": buscador["categoria"],
                    "tipo_actor": buscador["tipo_actor"]
                }
            conteo_por_entidad[id_ent]["frecuencia"] += 1
            conteo_por_entidad[id_ent]["variantes"].add(termino_exacto)

    resumen_intervencion = [
        {
            "id_intervencion": id_intervencion,
            "id_entidad": id_ent,
            "frecuencia": datos["frecuencia"],
            "variantes_encontradas": sorted(list(datos["variantes"]))
        }
        for id_ent, datos in conteo_por_entidad.items()
    ]

    return resumen_intervencion, menciones_detalle



def _esquema_3nf_activo() -> bool:
    """Detecta si la base de datos en Supabase ya se encuentra migrada a Tercera Forma Normal (3NF)."""
    try:
        supabase.table("tomos_diarios_sesiones").select("id_tomo").limit(1).execute()
        return True
    except Exception:
        return False


def verificar_y_analizar_leyes_supabase(
    buscadores: List[Dict],
    mapa_sesiones: Dict[int, Dict],
    ruta_csv_salida: str = "ner_entidades_en_leyes_y_sumarios.csv"
) -> Tuple[Dict, Dict[int, List[str]]]:
    """
    1. Verifica en vivo el estado de las iniciativas legislativas y sumarios en Supabase
       (compatible nativamente con 3NF 'iniciativas_legislativas'/'articulos_iniciativa' y con el esquema legado).
    2. Comprueba cuántas sesiones tienen título de proyecto y artículos modificados identificados.
    3. Ejecuta el motor NER + detector de leyes sobre cada iniciativa tratada.
    4. Devuelve (estadisticas, mapa_leyes_por_sesion) para cruzar leyes con las intervenciones de cada sesión.
    """
    print("\n------------------------------------------------------------------")
    print("VERIFICACIÓN DE TABLAS DE LEYES Y NER SOBRE PROYECTOS / SUMARIOS")
    print("------------------------------------------------------------------")

    es_3nf = _esquema_3nf_activo()
    try:
        cnt_sum = supabase.table("sesion_sumarios").select("id_sumario", count="exact").limit(1).execute().count
        if es_3nf:
            cnt_ini = supabase.table("iniciativas_legislativas").select("id_iniciativa", count="exact").limit(1).execute().count
            cnt_art = supabase.table("articulos_iniciativa").select("id_articulo", count="exact").limit(1).execute().count
            cnt_ley = supabase.table("leyes").select("id_ley", count="exact").limit(1).execute().count
            print(
                f"   [*] Estado 3NF en Supabase -> sesion_sumarios: {cnt_sum} | "
                f"iniciativas_legislativas: {cnt_ini} | articulos_iniciativa: {cnt_art} | catalogo leyes: {cnt_ley}"
            )
        else:
            cnt_proy = supabase.table("proyectos_leyes").select("id_proyecto", count="exact").limit(1).execute().count
            cnt_rec = supabase.table("leyes_tratamiento_recinto").select("id_tratamiento", count="exact").limit(1).execute().count
            print(f"   [*] Estado legado en Supabase -> sesion_sumarios: {cnt_sum} | proyectos_leyes: {cnt_proy} | leyes_tratamiento_recinto: {cnt_rec}")
    except Exception as e:
        print(f"   [!] Aviso consultando conteos de tablas de leyes: {e}")

    filas_exportar = []
    mapa_leyes_por_sesion = defaultdict(list)
    sesiones_formato_nuevo = set()
    sesiones_formato_antiguo = set()

    estadisticas = {
        "total_proyectos_leyes": 0,
        "total_leyes_recinto": 0,
        "leyes_con_resumen_sumario": 0,
        "leyes_con_titulo_proyecto": 0,
        "leyes_con_articulos_modificados": 0,
        "leyes_con_entidades": 0,
        "menciones_en_leyes": 0,
        "conteo_entidades_leyes": Counter()
    }

    fuentes_consulta = (
        [("iniciativas_legislativas", "id_iniciativa")]
        if es_3nf
        else [("proyectos_leyes", "id_proyecto"), ("leyes_tratamiento_recinto", "id_tratamiento")]
    )

    for nombre_tabla, col_pk in fuentes_consulta:
        ultimo_id = 0
        lote_tam = 500
        while True:
            try:
                res = (
                    supabase.table(nombre_tabla)
                    .select("*")
                    .gt(col_pk, ultimo_id)
                    .order(col_pk)
                    .limit(lote_tam)
                    .execute()
                )
            except Exception as e:
                print(f"   [!] Error consultando '{nombre_tabla}': {e}")
                break

            datos = res.data
            if not datos:
                break

            for fila in datos:
                id_reg = fila[col_pk]
                ultimo_id = max(ultimo_id, id_reg)
                id_ses = fila.get("id_sesion")
                info_ses = mapa_sesiones.get(id_ses, {})

                if es_3nf:
                    origen_tabla = str(fila.get("tabla_origen_legacy") or fila.get("tipo_iniciativa") or "iniciativas_legislativas")
                    num_art_str = str(fila.get("numero_articulo_origen") or "")
                    art_ref_str = str(fila.get("articulo_referencia_origen") or "")
                    resumen_sum = str(fila.get("resumen_sumario") or "").strip()
                    texto_art = str(fila.get("texto_articulado_origen") or "").strip()
                    titulo_3nf = str(fila.get("titulo_iniciativa") or "").strip()
                    tipo_doc = str(fila.get("tipo_documento_origen") or fila.get("tipo_iniciativa") or "")
                    cant_arts = fila.get("cantidad_articulos_origen") or 1
                else:
                    origen_tabla = nombre_tabla
                    num_art_str = str(fila.get("numero_articulo") or "")
                    art_ref_str = str(fila.get("articulo_referencia") or "")
                    resumen_sum = str(fila.get("resumen_sumario") or "").strip()
                    texto_art = str(fila.get("texto_articulado") or "").strip()
                    titulo_3nf = ""
                    tipo_doc = str(fila.get("tipo_documento") or "")
                    cant_arts = fila.get("cantidad_articulos", 1)

                m_tit = re.search(r"T[IÍ]TULO:\s*([^\]\|]+)", resumen_sum, re.IGNORECASE)
                titulo_proy = m_tit.group(1).strip() if m_tit else titulo_3nf

                articulos_mod = ""
                if num_art_str.lower().startswith("modifica:"):
                    articulos_mod = num_art_str
                elif art_ref_str.lower().startswith("modifica:"):
                    articulos_mod = art_ref_str.split("|")[0].strip()
                else:
                    m_mod = re.search(r"MODIFICA:\s*([^\]\|]+)", resumen_sum, re.IGNORECASE)
                    if m_mod:
                        articulos_mod = f"Modifica: {m_mod.group(1).strip()}"

                if titulo_proy:
                    estadisticas["leyes_con_titulo_proyecto"] += 1
                if articulos_mod:
                    estadisticas["leyes_con_articulos_modificados"] += 1

                es_proyecto = origen_tabla in ("proyectos_leyes", "PROYECTO_DE_LEY", "RESOLUCION", "DECLARACION")
                if es_proyecto:
                    estadisticas["total_proyectos_leyes"] += 1
                    if "Arts. 1 a" in num_art_str or "Modifica:" in num_art_str or fila.get("instancia_legislativa") in ("PROYECTO_INTEGRO", "TRATAMIENTO_RECINTO", "MODIFICACION_LEY"):
                        sesiones_formato_nuevo.add(id_ses)
                    elif re.match(r"^Art\.\s*[2-9]", num_art_str) and "\n" not in texto_art:
                        sesiones_formato_antiguo.add(id_ses)
                    else:
                        sesiones_formato_nuevo.add(id_ses)
                else:
                    estadisticas["total_leyes_recinto"] += 1

                if resumen_sum or titulo_proy:
                    if resumen_sum:
                        estadisticas["leyes_con_resumen_sumario"] += 1
                    etiqueta_ley_ses = titulo_proy if titulo_proy else resumen_sum[:140]
                    if etiqueta_ley_ses and len(mapa_leyes_por_sesion[id_ses]) < 15 and etiqueta_ley_ses not in mapa_leyes_por_sesion[id_ses]:
                        mapa_leyes_por_sesion[id_ses].append(etiqueta_ley_ses)

                texto_combinado = f"{titulo_proy}\n{resumen_sum}\n{texto_art}".strip()
                _, menciones = analizar_intervencion(id_reg, texto_combinado, buscadores)
                leyes_citadas = extraer_leyes_estructuradas(texto_combinado)
                provincias_citadas = detectar_provincias_en_texto(texto_combinado)

                if menciones or leyes_citadas or provincias_citadas:
                    estadisticas["leyes_con_entidades"] += 1
                    estadisticas["menciones_en_leyes"] += len(menciones)

                    entidades_unicas = Counter(m["nombre_canonico"] for m in menciones)
                    for ent_nom, cnt in entidades_unicas.items():
                        estadisticas["conteo_entidades_leyes"][ent_nom] += cnt

                    filas_exportar.append({
                        "tabla_origen": origen_tabla,
                        "id_registro": id_reg,
                        "id_sesion": id_ses,
                        "numero_reunion": info_ses.get("numero_reunion", ""),
                        "anio": info_ses.get("anio", ""),
                        "camara": info_ses.get("camara", ""),
                        "tipo_documento": tipo_doc,
                        "instancia_legislativa": fila.get("instancia_legislativa", ""),
                        "titulo_proyecto": titulo_proy,
                        "articulos_modificados": articulos_mod,
                        "numero_articulo": num_art_str,
                        "cantidad_articulos": cant_arts,
                        "entidades_detectadas": "; ".join(f"{k} ({v})" for k, v in entidades_unicas.items()),
                        "provincias_afectadas": "; ".join(f"{k} ({v})" for k, v in provincias_citadas.items()),
                        "leyes_referenciadas": "; ".join(l["descripcion"] for l in leyes_citadas),
                        "resumen_sumario": resumen_sum[:300]
                    })

    if filas_exportar:
        with open(ruta_csv_salida, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(filas_exportar[0].keys()))
            writer.writeheader()
            writer.writerows(filas_exportar)
        print(f"   [OK] Reporte de NER en leyes exportado en '{ruta_csv_salida}' ({len(filas_exportar)} leyes con entidades/provincias).")

    print(
        f"   -> Auditoría formato '1 fila = 1 ley': {len(sesiones_formato_nuevo - sesiones_formato_antiguo)} sesiones ya consolidadas | "
        f"{len(sesiones_formato_antiguo)} sesiones pendientes de actualización."
    )
    print(
        f"   -> Leyes con resumen de sumario: {estadisticas['leyes_con_resumen_sumario']} | "
        f"Con título de proyecto: {estadisticas['leyes_con_titulo_proyecto']} | "
        f"Con artículos modificados: {estadisticas['leyes_con_articulos_modificados']} | "
        f"Top entidades: {estadisticas['conteo_entidades_leyes'].most_common(5)}"
    )
    return estadisticas, mapa_leyes_por_sesion



def cargar_contexto_maestro_supabase() -> Tuple[Dict[int, Dict], Dict[Any, Dict]]:
    """
    Carga en memoria el contexto institucional y biográfico desde Supabase.
    Soporta nativamente la arquitectura en Tercera Forma Normal (3NF: tomos_diarios_sesiones,
    sesiones, personas, mandatos_legislativos, partidos_politicos, provincias) con fallback
    automático al esquema legado si aún no se ejecutó la migración SQL.
    """
    mapa_sesiones = {}
    mapa_parlamentarios = {}
    es_3nf = _esquema_3nf_activo()

    if es_3nf:
        try:
            tomos = {
                t["id_tomo"]: t
                for t in (supabase.table("tomos_diarios_sesiones").select("*").execute().data or [])
            }
            sesiones_data = []
            off_s = 0
            while True:
                batch_s = (
                    supabase.table("sesiones")
                    .select("*")
                    .order("id_sesion")
                    .range(off_s, off_s + 999)
                    .execute()
                    .data
                    or []
                )
                if not batch_s:
                    break
                sesiones_data.extend(batch_s)
                if len(batch_s) < 1000:
                    break
                off_s += 1000
            for r in sesiones_data:
                tomo = tomos.get(r.get("id_tomo"), {})
                fecha_str = str(r.get("fecha_exacta") or "")
                anio = str(tomo.get("anio_legislativo") or fecha_str[:4] or "S/D")
                mapa_sesiones[r["id_sesion"]] = {
                    "fecha": fecha_str,
                    "anio": anio,
                    "camara": tomo.get("camara") or "S/D",
                    "numero_reunion": tomo.get("codigo_tomo") or str(r.get("numero_reunion") or ""),
                    "presidente": r.get("presidente_texto_origen") or ""
                }
        except Exception as e:
            print(f"[!] Aviso cargando 'sesiones/tomos' en 3NF: {e}")

        try:
            personas_map = {
                p["id_persona"]: p
                for p in (supabase.table("personas").select("*").execute().data or [])
            }
            partidos_map = {
                pt["id_partido"]: pt
                for pt in (supabase.table("partidos_politicos").select("*").execute().data or [])
            }
            provincias_map = {
                pr["id_provincia"]: pr
                for pr in (supabase.table("provincias").select("*").execute().data or [])
            }
            res_m = supabase.table("mandatos_legislativos").select("*").execute()
            for r in (res_m.data or []):
                per = personas_map.get(r.get("id_persona"), {})
                pt = partidos_map.get(r.get("id_partido"), {})
                pr = provincias_map.get(r.get("id_provincia"), {})
                mapa_parlamentarios[r["id_mandato"]] = {
                    "id_persona": r.get("id_persona"),
                    "nombre_apellido": per.get("nombre_completo") or "NO IDENTIFICADO",
                    "rol": r.get("cargo_especifico") or "Sin Especificar",
                    "partido_politico": pt.get("nombre_oficial") or "Sin Especificar",
                    "coalicion_general": pt.get("coalicion_general") or "Sin Especificar",
                    "distrito_provincia": pr.get("nombre") or "Sin Especificar"
                }
            for id_p, p in personas_map.items():
                mapa_parlamentarios[("persona", id_p)] = {
                    "id_persona": id_p,
                    "nombre_apellido": p.get("nombre_completo") or "NO IDENTIFICADO",
                    "rol": "Externo" if "NO IDENTIFICADO" in str(p.get("nombre_completo") or "").upper() else "Sin Especificar",
                    "partido_politico": "Sin Especificar",
                    "coalicion_general": "Sin Especificar",
                    "distrito_provincia": "Sin Especificar"
                }
        except Exception as e:
            print(f"[!] Aviso cargando 'mandatos_legislativos/personas/partidos/provincias' en 3NF: {e}")

        n_mandatos = sum(1 for k in mapa_parlamentarios if isinstance(k, int))
        n_personas = sum(1 for k in mapa_parlamentarios if isinstance(k, tuple))
        print(f"[*] Contexto 3NF cargado: {len(mapa_sesiones)} sesiones/tomos | {n_mandatos} mandatos | {n_personas} personas únicas.")
        return mapa_sesiones, mapa_parlamentarios

    # Fallback automático al esquema legado previo a la migración 3NF
    try:
        res_s = supabase.table("sesiones").select("*").execute()
        for r in res_s.data:
            fecha_str = str(r.get("fecha") or "")
            m_anio = re.search(r"(19[23]\d)", fecha_str) or re.search(r"(19[23]\d)", str(r.get("numero_reunion") or ""))
            anio = m_anio.group(1) if m_anio else str(r.get("tipo_sesion") or "S/D")
            mapa_sesiones[r["id_sesion"]] = {
                "fecha": fecha_str,
                "anio": anio,
                "camara": r.get("camara") or "S/D",
                "numero_reunion": r.get("numero_reunion") or "",
                "presidente": r.get("presidente") or ""
            }
    except Exception as e:
        print(f"[!] Aviso cargando 'sesiones': {e}")

    try:
        res_p = supabase.table("parlamentarios").select("*").execute()
        for r in res_p.data:
            mapa_parlamentarios[r["id_parlamentario"]] = {
                "nombre_apellido": r.get("nombre_apellido") or "NO IDENTIFICADO",
                "rol": r.get("rol") or "Sin Especificar",
                "partido_politico": r.get("partido_politico") or "Sin Especificar",
                "distrito_provincia": r.get("distrito_provincia") or "Sin Especificar"
            }
    except Exception as e:
        print(f"[!] Aviso cargando 'parlamentarios': {e}")

    print(f"[*] Contexto legado cargado: {len(mapa_sesiones)} sesiones | {len(mapa_parlamentarios)} parlamentarios.")
    return mapa_sesiones, mapa_parlamentarios


def ejecutar_pruebas_y_diagnostico_tablas(buscadores: List[Dict]):
    """
    Ejecuta pruebas automáticas sobre las tablas de Supabase (esquema 3NF o legado)
    y verifica el motor NER + ABSA + Ejes Temáticos sobre muestras reales.
    """
    print("\n------------------------------------------------------------------")
    print("AUTO-TEST DE TABLAS EN SUPABASE Y VERIFICACIÓN DEL MOTOR NER")
    print("------------------------------------------------------------------")

    if _esquema_3nf_activo():
        tablas_a_verificar = [
            ("provincias", "id_provincia"),
            ("partidos_politicos", "id_partido"),
            ("personas", "id_persona"),
            ("mandatos_legislativos", "id_mandato"),
            ("tomos_diarios_sesiones", "id_tomo"),
            ("sesiones", "id_sesion"),
            ("sesiones_autoridades", "id_sesion"),
            ("sesion_sumarios", "id_sumario"),
            ("leyes", "id_ley"),
            ("iniciativas_legislativas", "id_iniciativa"),
            ("articulos_iniciativa", "id_articulo"),
            ("intervenciones", "id_intervencion"),
            ("intervenciones_leyes_mencionadas", "id_intervencion"),
            ("intervenciones_versiones_texto", "id_version"),
        ]
    else:
        tablas_a_verificar = [
            ("sesiones", "id_sesion"),
            ("parlamentarios", "id_parlamentario"),
            ("intervenciones", "id_intervencion"),
            ("sesion_sumarios", "id_sumario"),
            ("proyectos_leyes", "id_proyecto"),
            ("leyes_tratamiento_recinto", "id_tratamiento"),
        ]

    for nombre_t, pk_col in tablas_a_verificar:
        try:
            r = supabase.table(nombre_t).select("*", count="exact").order(pk_col, desc=True).limit(1).execute()
            cols = list(r.data[0].keys()) if r.data else []
            print(f"   [OK] '{nombre_t}': {r.count} registros | Columnas: {cols}")
        except Exception as e:
            print(f"   [!] Error verificando '{nombre_t}': {e}")

    texto_prueba = (
        "Sr. Ministro de Hacienda (Dr. Pinedo). — El Poder Ejecutivo sostiene que el Banco Central, "
        "la Comisión de Control de Cambios y la Junta Reguladora de Granos han defendido la producción nacional "
        "frente a la Gran Depresión y Wall Street. En cambio, la Sociedad Rural Argentina, CARBAP y la UIA "
        "presentaron memoriales sobre el Convenio Roca-Runciman con Gran Bretaña y el comercio con Estados Unidos "
        "en relación con la ley 11.747 y los productores de Córdoba y Mendoza."
    )
    _, menc_p = analizar_intervencion(0, texto_prueba, buscadores)
    leyes_p = extraer_leyes_estructuradas(texto_prueba)
    provs_p = detectar_provincias_en_texto(texto_prueba)
    ejes_p = detectar_ejes_tematicos_y_postura(texto_prueba)
    print(
        f"   [OK] Auto-test motor NLP -> Entidades PDF detectadas: {[m['nombre_lista'] for m in menc_p]} | "
        f"Ejes temáticos: {[e['codigo_eje'] for e in ejes_p]} | "
        f"Leyes: {[l['descripcion'] for l in leyes_p]} | Provincias: {list(provs_p.keys())}"
    )


def obtener_mejor_texto_intervencion(fila: Dict) -> str:
    """
    Selecciona automáticamente la versión canónica o más limpia disponible del texto en 'intervenciones':
    1. 'texto_canonico' (esquema 3NF)
    2. 'texto_gemini' (esquema legado, si existe y no es 'OMITIDO_POR_LARGO')
    3. 'texto_corregido'
    4. 'texto_limpio'
    5. 'texto_intervencion' (fallback)
    """
    t_can = fila.get("texto_canonico")
    if t_can and isinstance(t_can, str) and len(t_can.strip()) > 10:
        return t_can.strip()

    t_gem = fila.get("texto_gemini")
    if t_gem and isinstance(t_gem, str) and t_gem != "OMITIDO_POR_LARGO" and len(t_gem.strip()) > 10:
        return t_gem.strip()

    for col in ("texto_corregido", "texto_limpio", "texto_intervencion"):
        val = fila.get(col)
        if val and isinstance(val, str) and len(val.strip()) > 10:
            return val.strip()

    return ""


def ejecutar_ner_sobre_intervenciones(
    ruta_archivo_entidades: Optional[str] = "Lista Entidades - OCT26.pdf",
    tamano_pagina: int = 500
):

    catalogo = cargar_entidades_desde_archivo(ruta_archivo_entidades, incluir_complementarias_plan=True)
    total_oficiales_pdf = sum(1 for c in catalogo if c.get("es_lista_oficial_pdf"))
    nombres_conocidos_low = {c["nombre_canonico"].lower() for c in catalogo} | {c["nombre_lista"].lower() for c in catalogo}
    print(
        f"[*] Catálogo activo: {len(catalogo)} entradas totales "
        f"({total_oficiales_pdf} entradas exactas de 'Lista Entidades - OCT26.pdf')"
    )

    mapa_ids = sincronizar_catalogo_supabase(catalogo)
    buscadores = compilar_buscadores(catalogo, mapa_ids)
    qwen_pool = QwenClientPool(QWEN_API_KEYS, QWEN_BASE_URL, QWEN_MODEL)

    mapa_sesiones, mapa_parlamentarios = cargar_contexto_maestro_supabase()

    # 0. Ejecutar pruebas de diagnóstico sobre todas las tablas y el motor NER
    ejecutar_pruebas_y_diagnostico_tablas(buscadores)

    # 1. Ejecutar auditoría y NER sobre las tablas de leyes y sumarios
    _, mapa_leyes_por_sesion = verificar_y_analizar_leyes_supabase(buscadores, mapa_sesiones)

    # 2. Recorrer la tabla 'intervenciones' mediante paginación indexada por id_intervencion
    print("\n------------------------------------------------------------------")
    print("PROCESANDO INTERVENCIONES PARLAMENTARIAS DESDE SUPABASE")
    print("------------------------------------------------------------------")

    ultimo_id = 0
    total_intervenciones_analizadas = 0
    total_discursos_sustantivos = 0
    total_menciones_halladas = 0
    tablas_ner_supabase_activas = True

    # Acumuladores cuantitativos multi-dimensionales alineados con el Plan de Trabajo
    # A. Resultados exclusivos de las 42 entidades de 'Lista Entidades - OCT26.pdf'
    resumen_lista_oct26 = defaultdict(lambda: {
        "frecuencia": 0,
        "intervenciones": 0,
        "discursos_sustantivos": 0,
        "palabras_contexto_discursos": 0,
        "menciones_ministros_pe": 0,
        "menciones_diputados": 0,
        "menciones_senadores": 0,
        "a_favor": 0,
        "en_contra": 0,
        "neutral": 0,
        "suma_polaridad": 0.0,
        "variantes_pdf": set()
    })

    # B. Resumen general por Año, Cámara y Entidad
    resumen_anio_camara = defaultdict(lambda: {
        "frecuencia": 0,
        "intervenciones": 0,
        "discursos_sustantivos": 0,
        "a_favor": 0,
        "en_contra": 0,
        "neutral": 0
    })

    # C. Participación cruzada por Provincia del Legislador, Partido Político, Rol y Entidad
    resumen_actor_provincia = defaultdict(lambda: {
        "frecuencia": 0,
        "intervenciones": 0,
        "discursos_sustantivos": 0,
        "a_favor": 0,
        "en_contra": 0,
        "neutral": 0
    })

    # D. Participación realista en los debates (Volumen de palabras vs. tipos de intervención)
    participacion_realista = defaultdict(lambda: {
        "intervenciones_totales": 0,
        "discursos_sustantivos": 0,
        "intervenciones_breves": 0,
        "acotaciones_interrupciones": 0,
        "procedimentales": 0,
        "palabras_totales": 0,
        "palabras_sustantivas": 0,
        "intervenciones_con_entidades_pdf": 0,
        "intervenciones_con_temas_comerciales": 0,
        "sesiones_distintas": set(),
        "oradores_distintos": set()
    })
    palabras_totales_por_anio_camara = Counter()

    # E. Contraste Postura Oficial (Ministros PE) vs. Miembros de las Cámaras (Diputados/Senadores)
    contraste_oficial_vs_camaras = defaultdict(lambda: {
        "frecuencia_menciones": 0,
        "intervenciones": 0,
        "discursos_sustantivos": 0,
        "palabras_totales": 0,
        "a_favor": 0,
        "en_contra": 0,
        "neutral": 0,
        "suma_polaridad": 0.0
    })

    # F. Sentimiento basado en aspectos (ABSA) sobre Especialización Productiva y Socios Comerciales
    absa_socios_y_especializacion = defaultdict(lambda: {
        "frecuencia": 0,
        "intervenciones": 0,
        "discursos_sustantivos": 0,
        "a_favor": 0,
        "en_contra": 0,
        "neutral": 0,
        "suma_polaridad": 0.0
    })

    # G. Co-ocurrencias de entidades en una misma intervención sustantiva + Leyes + Vocabulario EDA
    coocurrencias_entidades = Counter()
    resumen_leyes_debates = defaultdict(lambda: {"frecuencia": 0, "intervenciones": 0, "descripcion": "", "leyes_sesion": set()})
    vocabulario_por_anio_camara = defaultdict(Counter)
    conteo_actores_emergentes = Counter()

    while True:
        try:
            respuesta = (
                supabase.table("intervenciones")
                .select("*")
                .gt("id_intervencion", ultimo_id)
                .order("id_intervencion")
                .limit(tamano_pagina)
                .execute()
            )
        except Exception as e:
            print(f"   [!] Error de red consultando 'intervenciones' desde ID {ultimo_id}: {e}. Reintentando en 3s...")
            time.sleep(3)
            continue

        filas = respuesta.data
        if not filas:
            break

        lote_resumen_db = []
        lote_menciones_db = []

        for fila in filas:
            id_interv = fila["id_intervencion"]
            ultimo_id = max(ultimo_id, id_interv)
            texto = obtener_mejor_texto_intervencion(fila)
            if not texto:
                continue

            total_intervenciones_analizadas += 1
            id_ses = fila.get("id_sesion")
            id_mandato = fila.get("id_mandato")
            id_persona = fila.get("id_persona")
            id_parl_leg = fila.get("id_parlamentario")

            clave_parl = (
                id_mandato
                if id_mandato is not None
                else (id_parl_leg if id_parl_leg is not None else (("persona", id_persona) if id_persona is not None else None))
            )

            info_ses = mapa_sesiones.get(id_ses, {"anio": "S/D", "camara": "S/D", "numero_reunion": ""})
            info_parl = mapa_parlamentarios.get(clave_parl, {
                "nombre_apellido": "NO IDENTIFICADO",
                "rol": "Sin Especificar",
                "partido_politico": "Sin Especificar",
                "distrito_provincia": "Sin Especificar"
            })

            anio = info_ses["anio"]
            camara = info_ses["camara"]
            partido = info_parl["partido_politico"]
            provincia_orador = info_parl["distrito_provincia"]

            tipo_interv, n_palabras, es_sustantiva = clasificar_calidad_intervencion(texto, info_parl)
            rol_institucional = determinar_rol_institucional_orador(fila, info_parl, info_ses, texto)

            if tipo_interv == "DISCURSO_SUSTANTIVO":
                total_discursos_sustantivos += 1

            # 1. Registrar participación realista por (Año, Cámara, Rol Institucional, Partido, Provincia del Orador)
            clave_part = (anio, camara, rol_institucional, partido, provincia_orador)
            part_rec = participacion_realista[clave_part]
            part_rec["intervenciones_totales"] += 1
            part_rec["palabras_totales"] += n_palabras
            if id_ses:
                part_rec["sesiones_distintas"].add(id_ses)
            id_orador_activo = id_persona if (id_mandato is not None and id_persona is not None) else (id_mandato or id_parl_leg)
            if id_orador_activo:
                part_rec["oradores_distintos"].add(id_orador_activo)

            if tipo_interv == "DISCURSO_SUSTANTIVO":
                part_rec["discursos_sustantivos"] += 1
                part_rec["palabras_sustantivas"] += n_palabras
            elif tipo_interv == "INTERVENCION_BREVE":
                part_rec["intervenciones_breves"] += 1
                part_rec["palabras_sustantivas"] += n_palabras
            elif tipo_interv == "ACOTACION_O_INTERRUPCION":
                part_rec["acotaciones_interrupciones"] += 1
            else:
                part_rec["procedimentales"] += 1

            palabras_totales_por_anio_camara[(anio, camara)] += n_palabras

            # 2. Vocabulario frecuente para el Análisis Exploratorio del Corpus (EDA)
            if es_sustantiva:
                vocabulario_por_anio_camara[(anio, camara)].update(
                    extraer_frecuencias_vocabulario_comercial(texto)
                )

            # 3. Reconocimiento de Entidades Nombradas (NER)
            res_agregado, det_menciones = analizar_intervencion(
                id_interv, texto, buscadores, qwen_pool
            )

            if any(m["es_lista_oficial_pdf"] for m in det_menciones):
                part_rec["intervenciones_con_entidades_pdf"] += 1

            # 4. Ejes temáticos de Política Comercial y Especialización Productiva + ABSA
            ejes_detectados = detectar_ejes_tematicos_y_postura(texto)
            if ejes_detectados:
                part_rec["intervenciones_con_temas_comerciales"] += 1
                for eje in ejes_detectados:
                    # Contraste Oficialismo (Ministros) vs. Cámaras en cada eje temático
                    clave_contraste_eje = (
                        anio,
                        camara,
                        rol_institucional,
                        partido,
                        "EJE_TEMATICO_COMERCIAL",
                        eje["nombre_eje"]
                    )
                    c_eje = contraste_oficial_vs_camaras[clave_contraste_eje]
                    c_eje["frecuencia_menciones"] += eje["frecuencia_terminos"]
                    c_eje["intervenciones"] += 1
                    if tipo_interv == "DISCURSO_SUSTANTIVO":
                        c_eje["discursos_sustantivos"] += 1
                    c_eje["palabras_totales"] += n_palabras
                    c_eje["suma_polaridad"] += eje["score_polaridad"]
                    if eje["postura_absa"] == "A_FAVOR":
                        c_eje["a_favor"] += 1
                    elif eje["postura_absa"] == "EN_CONTRA":
                        c_eje["en_contra"] += 1
                    else:
                        c_eje["neutral"] += 1

                    # ABSA sobre Especialización Productiva y Política Comercial por Provincia y Partido
                    clave_absa_eje = (
                        anio,
                        camara,
                        partido,
                        provincia_orador,
                        rol_institucional,
                        "CONCEPTO_POLITICA_COMERCIAL",
                        eje["nombre_eje"]
                    )
                    ab_e = absa_socios_y_especializacion[clave_absa_eje]
                    ab_e["frecuencia"] += eje["frecuencia_terminos"]
                    ab_e["intervenciones"] += 1
                    if tipo_interv == "DISCURSO_SUSTANTIVO":
                        ab_e["discursos_sustantivos"] += 1
                    ab_e["suma_polaridad"] += eje["score_polaridad"]
                    if eje["postura_absa"] == "A_FAVOR":
                        ab_e["a_favor"] += 1
                    elif eje["postura_absa"] == "EN_CONTRA":
                        ab_e["en_contra"] += 1
                    else:
                        ab_e["neutral"] += 1

            # 5. Leyes mencionadas en la intervención + cruce con leyes tratadas en la sesión
            leyes_en_int = extraer_leyes_estructuradas(texto)
            leyes_contexto_ses = mapa_leyes_por_sesion.get(id_ses, [])
            for l_item in leyes_en_int:
                clave_ley = (
                    anio,
                    camara,
                    l_item["codigo_ley"],
                    partido,
                    provincia_orador,
                    rol_institucional
                )
                resumen_leyes_debates[clave_ley]["frecuencia"] += l_item["frecuencia"]
                resumen_leyes_debates[clave_ley]["intervenciones"] += 1
                resumen_leyes_debates[clave_ley]["descripcion"] = l_item["descripcion"]
                for ls in leyes_contexto_ses[:3]:
                    resumen_leyes_debates[clave_ley]["leyes_sesion"].add(ls)

            # 6. Actores corporativos/regionales emergentes (NLP)
            for act_em in detectar_actores_emergentes_nlp(texto, nombres_conocidos_low):
                conteo_actores_emergentes[act_em] += 1

            # 7. Menciones explícitas a Provincias y Territorios Nacionales en el discurso
            provs_en_int = detectar_provincias_en_texto(texto)
            for prov_nom, freq_p in provs_en_int.items():
                clave_prov_ac = (
                    anio,
                    camara,
                    prov_nom,
                    "Actores provinciales y regionales",
                    "ACTOR_PROVINCIAL_REGIONAL",
                    "PLAN_DE_TRABAJO"
                )
                resumen_anio_camara[clave_prov_ac]["frecuencia"] += freq_p
                resumen_anio_camara[clave_prov_ac]["intervenciones"] += 1
                if tipo_interv == "DISCURSO_SUSTANTIVO":
                    resumen_anio_camara[clave_prov_ac]["discursos_sustantivos"] += 1
                resumen_anio_camara[clave_prov_ac]["neutral"] += freq_p

                clave_prov_cruce = (
                    provincia_orador,
                    partido,
                    rol_institucional,
                    prov_nom,
                    "ACTOR_PROVINCIAL_REGIONAL"
                )
                resumen_actor_provincia[clave_prov_cruce]["frecuencia"] += freq_p
                resumen_actor_provincia[clave_prov_cruce]["intervenciones"] += 1
                if tipo_interv == "DISCURSO_SUSTANTIVO":
                    resumen_actor_provincia[clave_prov_cruce]["discursos_sustantivos"] += 1
                resumen_actor_provincia[clave_prov_cruce]["neutral"] += freq_p

            # 8. Procesar menciones de entidades detectadas
            if res_agregado:
                lote_resumen_db.extend(res_agregado)
                for m in det_menciones:
                    lote_menciones_db.append({
                        "id_intervencion": m["id_intervencion"],
                        "id_entidad": m["id_entidad"],
                        "termino_detectado": m["termino_detectado"],
                        "posicion_caracter": m["posicion_caracter"],
                        "contexto_mencion": m["contexto_mencion"],
                        "validado_llm": m["validado_llm"],
                        "postura_absa": m["postura_absa"],
                        "justificacion_llm": m["justificacion_llm"]
                    })
                total_menciones_halladas += len(det_menciones)

                entidades_vistas_ac = set()
                entidades_vistas_prov = set()
                entidades_vistas_oct26 = set()
                entidades_vistas_contraste = set()
                entidades_vistas_absa_socio = set()

                for m in det_menciones:
                    nom_can = m["nombre_canonico"]
                    nom_lista = m["nombre_lista"]
                    cat = m["categoria"]
                    t_actor = m["tipo_actor"]
                    postura = m["postura_absa"]
                    score_p = m.get("score_polaridad", 0.0)
                    es_pdf = m["es_lista_oficial_pdf"]

                    # A. Acumulador exclusivo de 'Lista Entidades - OCT26.pdf'
                    if es_pdf:
                        clave_oct = (anio, camara, cat, t_actor, nom_can)
                        r_oct = resumen_lista_oct26[clave_oct]
                        r_oct["frecuencia"] += 1
                        r_oct["suma_polaridad"] += score_p
                        r_oct["variantes_pdf"].add(nom_lista)

                        if rol_institucional == "PODER_EJECUTIVO_MINISTRO":
                            r_oct["menciones_ministros_pe"] += 1
                        elif rol_institucional == "CAMARA_DIPUTADOS":
                            r_oct["menciones_diputados"] += 1
                        elif rol_institucional == "CAMARA_SENADORES":
                            r_oct["menciones_senadores"] += 1

                        if postura == "A_FAVOR":
                            r_oct["a_favor"] += 1
                        elif postura == "EN_CONTRA":
                            r_oct["en_contra"] += 1
                        else:
                            r_oct["neutral"] += 1

                        if nom_can not in entidades_vistas_oct26:
                            r_oct["intervenciones"] += 1
                            if tipo_interv == "DISCURSO_SUSTANTIVO":
                                r_oct["discursos_sustantivos"] += 1
                                r_oct["palabras_contexto_discursos"] += n_palabras
                            entidades_vistas_oct26.add(nom_can)

                    # B. Resumen por Año y Cámara
                    clave_ac = (anio, camara, nom_can, cat, t_actor, m["origen_catalogo"])
                    resumen_anio_camara[clave_ac]["frecuencia"] += 1
                    if postura == "A_FAVOR":
                        resumen_anio_camara[clave_ac]["a_favor"] += 1
                    elif postura == "EN_CONTRA":
                        resumen_anio_camara[clave_ac]["en_contra"] += 1
                    else:
                        resumen_anio_camara[clave_ac]["neutral"] += 1

                    if nom_can not in entidades_vistas_ac:
                        resumen_anio_camara[clave_ac]["intervenciones"] += 1
                        if tipo_interv == "DISCURSO_SUSTANTIVO":
                            resumen_anio_camara[clave_ac]["discursos_sustantivos"] += 1
                        entidades_vistas_ac.add(nom_can)

                    # C. Cruce por Provincia del Legislador, Partido y Rol Institucional
                    clave_prov = (provincia_orador, partido, rol_institucional, nom_can, t_actor)
                    resumen_actor_provincia[clave_prov]["frecuencia"] += 1
                    if postura == "A_FAVOR":
                        resumen_actor_provincia[clave_prov]["a_favor"] += 1
                    elif postura == "EN_CONTRA":
                        resumen_actor_provincia[clave_prov]["en_contra"] += 1
                    else:
                        resumen_actor_provincia[clave_prov]["neutral"] += 1

                    if nom_can not in entidades_vistas_prov:
                        resumen_actor_provincia[clave_prov]["intervenciones"] += 1
                        if tipo_interv == "DISCURSO_SUSTANTIVO":
                            resumen_actor_provincia[clave_prov]["discursos_sustantivos"] += 1
                        entidades_vistas_prov.add(nom_can)

                    # D. Contraste Oficialismo (Ministros) vs. Cámaras sobre cada entidad
                    clave_con_ent = (anio, camara, rol_institucional, partido, t_actor, nom_can)
                    c_ent = contraste_oficial_vs_camaras[clave_con_ent]
                    c_ent["frecuencia_menciones"] += 1
                    c_ent["suma_polaridad"] += score_p
                    if postura == "A_FAVOR":
                        c_ent["a_favor"] += 1
                    elif postura == "EN_CONTRA":
                        c_ent["en_contra"] += 1
                    else:
                        c_ent["neutral"] += 1
                    if nom_can not in entidades_vistas_contraste:
                        c_ent["intervenciones"] += 1
                        if tipo_interv == "DISCURSO_SUSTANTIVO":
                            c_ent["discursos_sustantivos"] += 1
                        c_ent["palabras_totales"] += n_palabras
                        entidades_vistas_contraste.add(nom_can)

                    # E. Sentimiento ABSA hacia Socios Comerciales, Tratados e Intereses Privados
                    if t_actor in ("SOCIO_COMERCIAL_EXTRANJERO", "FENOMENO_PROCESO_HECHO", "INTERES_PRIVADO_CORPORATIVO", "ORGANISMO_INTERNACIONAL_EXTRANJERO"):
                        clave_absa_s = (anio, camara, partido, provincia_orador, rol_institucional, t_actor, nom_can)
                        ab_s = absa_socios_y_especializacion[clave_absa_s]
                        ab_s["frecuencia"] += 1
                        ab_s["suma_polaridad"] += score_p
                        if postura == "A_FAVOR":
                            ab_s["a_favor"] += 1
                        elif postura == "EN_CONTRA":
                            ab_s["en_contra"] += 1
                        else:
                            ab_s["neutral"] += 1
                        if nom_can not in entidades_vistas_absa_socio:
                            ab_s["intervenciones"] += 1
                            if tipo_interv == "DISCURSO_SUSTANTIVO":
                                ab_s["discursos_sustantivos"] += 1
                            entidades_vistas_absa_socio.add(nom_can)

                # F. Co-ocurrencias de entidades en una misma intervención sustantiva
                if len(entidades_vistas_ac) >= 2:
                    for ent_a, ent_b in combinations(sorted(entidades_vistas_ac), 2):
                        coocurrencias_entidades[(anio, camara, ent_a, ent_b)] += 1

        # Guardar resultados en Supabase en lotes seguros con deduplicación y reintentos
        if tablas_ner_supabase_activas and (lote_resumen_db or lote_menciones_db):
            if lote_resumen_db:
                dedup_res = list({(r["id_intervencion"], r["id_entidad"]): r for r in lote_resumen_db}.values())
                for i_chunk in range(0, len(dedup_res), 400):
                    chunk_r = dedup_res[i_chunk:i_chunk + 400]
                    for intento in range(3):
                        try:
                            supabase.table("intervencion_entidades").upsert(
                                chunk_r, on_conflict="id_intervencion,id_entidad"
                            ).execute()
                            break
                        except Exception as e:
                            if intento == 2:
                                print(f"   [!] Aviso al insertar lote en 'intervencion_entidades': {e}")
                            else:
                                time.sleep(1.5)
            if lote_menciones_db:
                dedup_menc = list({
                    (m["id_intervencion"], m["id_entidad"], m["posicion_caracter"]): m
                    for m in lote_menciones_db
                }.values())
                for i_chunk in range(0, len(dedup_menc), 400):
                    chunk_m = dedup_menc[i_chunk:i_chunk + 400]
                    for intento in range(3):
                        try:
                            supabase.table("intervencion_entidad_menciones").upsert(
                                chunk_m, on_conflict="id_intervencion,id_entidad,posicion_caracter"
                            ).execute()
                            break
                        except Exception as e:
                            if intento == 2:
                                print(f"   [!] Aviso al insertar lote en 'intervencion_entidad_menciones': {e}")
                            else:
                                time.sleep(1.5)

        print(
            f"   -> Procesadas {total_intervenciones_analizadas} intervenciones "
            f"(Discursos sustantivos: {total_discursos_sustantivos} | último ID={ultimo_id}) | "
            f"Menciones acumuladas: {total_menciones_halladas}"
        )

    # 3. Exportar la suite completa de reportes cuantitativos para el Plan de Trabajo
    exportar_reportes_cuantitativos(
        resumen_lista_oct26=resumen_lista_oct26,
        resumen_anio_camara=resumen_anio_camara,
        resumen_actor_provincia=resumen_actor_provincia,
        participacion_realista=participacion_realista,
        palabras_totales_por_anio_camara=palabras_totales_por_anio_camara,
        contraste_oficial_vs_camaras=contraste_oficial_vs_camaras,
        absa_socios_y_especializacion=absa_socios_y_especializacion,
        coocurrencias_entidades=coocurrencias_entidades,
        resumen_leyes_debates=resumen_leyes_debates,
        vocabulario_por_anio_camara=vocabulario_por_anio_camara,
        conteo_actores_emergentes=conteo_actores_emergentes
    )

    print(
        f"NER Y CUANTIFICACIÓN FINALIZADOS | Intervenciones: {total_intervenciones_analizadas} | "
        f"Discursos sustantivos: {total_discursos_sustantivos} | Menciones totales: {total_menciones_halladas}"
    )



def exportar_reportes_cuantitativos(
    resumen_lista_oct26: Dict,
    resumen_anio_camara: Dict,
    resumen_actor_provincia: Dict,
    participacion_realista: Dict,
    palabras_totales_por_anio_camara: Counter,
    contraste_oficial_vs_camaras: Dict,
    absa_socios_y_especializacion: Dict,
    coocurrencias_entidades: Counter,
    resumen_leyes_debates: Dict,
    vocabulario_por_anio_camara: Dict,
    conteo_actores_emergentes: Counter
):
    """
    Exporta a CSV todos los entregables cuantitativos requeridos en 'Plan de Trabajo - Lucas Barreiro.pdf'
    y 'Lista Entidades - OCT26.pdf'.
    """
    # 1. Reporte exclusivo de las 42 entidades de 'Lista Entidades - OCT26.pdf'
    ruta_oct26 = "ner_entidades_lista_oct26_resultados.csv"
    filas_oct26 = []
    for k, v in sorted(resumen_lista_oct26.items(), key=lambda x: (x[0][0], -x[1]["frecuencia"])):
        freq = max(v["frecuencia"], 1)
        balance = round((v["a_favor"] - v["en_contra"]) / freq, 4)
        filas_oct26.append({
            "anio": k[0],
            "camara": k[1],
            "categoria_pdf_oct26": k[2],
            "subtipo_analitico": k[3],
            "entidad_canonica": k[4],
            "entradas_pdf_detectadas": "; ".join(sorted(v["variantes_pdf"])),
            "frecuencia_menciones": v["frecuencia"],
            "intervenciones_totales": v["intervenciones"],
            "discursos_sustantivos": v["discursos_sustantivos"],
            "palabras_en_discursos_sustantivos": v["palabras_contexto_discursos"],
            "menciones_ministros_pe": v["menciones_ministros_pe"],
            "menciones_diputados": v["menciones_diputados"],
            "menciones_senadores": v["menciones_senadores"],
            "postura_a_favor": v["a_favor"],
            "postura_en_contra": v["en_contra"],
            "postura_neutral": v["neutral"],
            "indice_balance_postura": balance
        })
    if filas_oct26:
        with open(ruta_oct26, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(filas_oct26[0].keys()))
            writer.writeheader()
            writer.writerows(filas_oct26)
        print(f"   [OK] Exportado '{ruta_oct26}' ({len(filas_oct26)} filas de 'Lista Entidades - OCT26.pdf').")

    # 2. Frecuencia y postura general por Año, Cámara, Entidad y Tipo de Actor
    ruta_ac = "ner_resumen_entidades_por_anio_camara.csv"
    filas_ac = [
        {
            "anio": k[0],
            "camara": k[1],
            "entidad_canonica": k[2],
            "categoria": k[3],
            "tipo_actor": k[4],
            "origen_catalogo": k[5],
            "frecuencia_menciones": v["frecuencia"],
            "cantidad_intervenciones": v["intervenciones"],
            "discursos_sustantivos": v["discursos_sustantivos"],
            "postura_a_favor": v["a_favor"],
            "postura_en_contra": v["en_contra"],
            "postura_neutral": v["neutral"]
        }
        for k, v in sorted(resumen_anio_camara.items(), key=lambda x: (x[0][0], -x[1]["frecuencia"]))
    ]
    if filas_ac:
        with open(ruta_ac, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(filas_ac[0].keys()))
            writer.writeheader()
            writer.writerows(filas_ac)
        print(f"   [OK] Exportado '{ruta_ac}' ({len(filas_ac)} filas de agregación por Año/Cámara/Entidad).")

    # 3. Participación cruzada por Provincia del Legislador, Partido Político, Rol y Entidad (con postura ABSA)
    ruta_prov = "ner_participacion_provincias_y_partidos.csv"
    filas_prov = [
        {
            "distrito_provincia": k[0],
            "partido_politico": k[1],
            "rol_institucional": k[2],
            "entidad_canonica": k[3],
            "tipo_actor": k[4],
            "frecuencia_menciones": v["frecuencia"],
            "cantidad_intervenciones": v["intervenciones"],
            "discursos_sustantivos": v["discursos_sustantivos"],
            "postura_a_favor": v["a_favor"],
            "postura_en_contra": v["en_contra"],
            "postura_neutral": v["neutral"]
        }
        for k, v in sorted(resumen_actor_provincia.items(), key=lambda x: -x[1]["frecuencia"])
    ]
    if filas_prov:
        with open(ruta_prov, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(filas_prov[0].keys()))
            writer.writeheader()
            writer.writerows(filas_prov)
        print(f"   [OK] Exportado '{ruta_prov}' ({len(filas_prov)} filas de cruce Provincia/Partido/Rol/Entidad).")

    # 4. Cuantificación Realista de Participación Parlamentaria (Palabras, Discursos Sustantivos vs. Acotaciones)
    ruta_part = "ner_participacion_realista_oradores_partidos_provincias.csv"
    filas_part = []
    for k, v in sorted(participacion_realista.items(), key=lambda x: (x[0][0], -x[1]["palabras_sustantivas"])):
        anio_k, camara_k, rol_k, partido_k, prov_k = k
        total_pal_ac = max(palabras_totales_por_anio_camara[(anio_k, camara_k)], 1)
        share_pct = round((v["palabras_totales"] * 100.0) / total_pal_ac, 3)
        prom_pal = round(v["palabras_totales"] / max(v["intervenciones_totales"], 1), 1)
        filas_part.append({
            "anio": anio_k,
            "camara": camara_k,
            "rol_institucional": rol_k,
            "partido_politico": partido_k,
            "distrito_provincia": prov_k,
            "oradores_activos_distintos": len(v["oradores_distintos"]),
            "sesiones_con_participacion": len(v["sesiones_distintas"]),
            "intervenciones_totales": v["intervenciones_totales"],
            "discursos_sustantivos_80mas_palabras": v["discursos_sustantivos"],
            "intervenciones_breves_15a79_palabras": v["intervenciones_breves"],
            "acotaciones_interrupciones_menos15": v["acotaciones_interrupciones"],
            "intervenciones_procedimentales": v["procedimentales"],
            "palabras_totales_pronunciadas": v["palabras_totales"],
            "palabras_en_discursos_sustantivos": v["palabras_sustantivas"],
            "promedio_palabras_por_intervencion": prom_pal,
            "share_volumen_debate_anual_pct": share_pct,
            "intervenciones_con_entidades_lista_oct26": v["intervenciones_con_entidades_pdf"],
            "intervenciones_con_ejes_politica_comercial": v["intervenciones_con_temas_comerciales"]
        })
    if filas_part:
        with open(ruta_part, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(filas_part[0].keys()))
            writer.writeheader()
            writer.writerows(filas_part)
        print(f"   [OK] Exportado '{ruta_part}' ({len(filas_part)} filas de participación parlamentaria realista).")

    # 5. Contraste Postura Oficial (Ministros PE) vs. Cámaras (Diputados/Senadores) en Ejes y Entidades
    ruta_con = "ner_contraste_oficialismo_ministros_vs_camaras.csv"
    filas_con = []
    for k, v in sorted(contraste_oficial_vs_camaras.items(), key=lambda x: (x[0][0], -x[1]["frecuencia_menciones"])):
        n_int = max(v["intervenciones"], 1)
        filas_con.append({
            "anio": k[0],
            "camara": k[1],
            "rol_institucional": k[2],
            "partido_politico": k[3],
            "dimension_analizada": k[4],
            "tema_o_entidad": k[5],
            "frecuencia_menciones": v["frecuencia_menciones"],
            "cantidad_intervenciones": v["intervenciones"],
            "discursos_sustantivos": v["discursos_sustantivos"],
            "palabras_totales_asociadas": v["palabras_totales"],
            "postura_a_favor": v["a_favor"],
            "postura_en_contra": v["en_contra"],
            "postura_neutral": v["neutral"],
            "polaridad_media": round(v["suma_polaridad"] / n_int, 4)
        })
    if filas_con:
        with open(ruta_con, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(filas_con[0].keys()))
            writer.writeheader()
            writer.writerows(filas_con)
        print(f"   [OK] Exportado '{ruta_con}' ({len(filas_con)} filas de contraste Ministros vs. Cámaras).")

    # 6. Análisis de Sentimiento Basado en Aspectos (ABSA) sobre Especialización Productiva y Socios Comerciales
    ruta_absa = "ner_sentimiento_aspectos_socios_y_especializacion.csv"
    filas_absa = []
    for k, v in sorted(absa_socios_y_especializacion.items(), key=lambda x: -x[1]["frecuencia"]):
        n_int = max(v["intervenciones"], 1)
        filas_absa.append({
            "anio": k[0],
            "camara": k[1],
            "partido_politico": k[2],
            "distrito_provincia": k[3],
            "rol_institucional": k[4],
            "tipo_aspecto": k[5],
            "aspecto_socio_o_concepto": k[6],
            "frecuencia_menciones": v["frecuencia"],
            "cantidad_intervenciones": v["intervenciones"],
            "discursos_sustantivos": v["discursos_sustantivos"],
            "postura_a_favor": v["a_favor"],
            "postura_en_contra": v["en_contra"],
            "postura_neutral": v["neutral"],
            "score_polaridad_medio": round(v["suma_polaridad"] / n_int, 4)
        })
    if filas_absa:
        with open(ruta_absa, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(filas_absa[0].keys()))
            writer.writeheader()
            writer.writerows(filas_absa)
        print(f"   [OK] Exportado '{ruta_absa}' ({len(filas_absa)} filas de sentimiento ABSA sobre socios y especialización).")

    # 7. Red de Co-ocurrencias de Entidades en Discursos
    ruta_cooc = "ner_coocurrencias_entidades_y_temas.csv"
    filas_cooc = [
        {
            "anio": k[0],
            "camara": k[1],
            "entidad_a": k[2],
            "entidad_b": k[3],
            "intervenciones_compartidas": freq
        }
        for k, freq in coocurrencias_entidades.most_common(1500)
        if freq >= 2
    ]
    if filas_cooc:
        with open(ruta_cooc, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(filas_cooc[0].keys()))
            writer.writeheader()
            writer.writerows(filas_cooc)
        print(f"   [OK] Exportado '{ruta_cooc}' ({len(filas_cooc)} pares de co-ocurrencia de entidades).")

    # 8. Cuantificación de Leyes mencionadas en los debates parlamentarios
    ruta_leyes = "ner_leyes_mencionadas_en_debates.csv"
    filas_leyes = [
        {
            "anio": k[0],
            "camara": k[1],
            "codigo_ley": k[2],
            "descripcion_ley": v["descripcion"],
            "partido_politico": k[3],
            "distrito_provincia": k[4],
            "rol_institucional": k[5],
            "frecuencia_menciones": v["frecuencia"],
            "cantidad_intervenciones": v["intervenciones"],
            "leyes_tratadas_en_esa_sesion": "; ".join(sorted(list(v["leyes_sesion"]))[:3])
        }
        for k, v in sorted(resumen_leyes_debates.items(), key=lambda x: -x[1]["frecuencia"])
    ]
    if filas_leyes:
        with open(ruta_leyes, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(filas_leyes[0].keys()))
            writer.writeheader()
            writer.writerows(filas_leyes)
        print(f"   [OK] Exportado '{ruta_leyes}' ({len(filas_leyes)} filas de leyes citadas por Provincia/Partido/Rol).")

    # 9. Vocabulario económico-comercial frecuente por Año y Cámara (Análisis Exploratorio EDA)
    ruta_voc = "ner_exploratorio_vocabulario_por_anio.csv"
    filas_voc = []
    for (anio_v, cam_v), cnt_v in sorted(vocabulario_por_anio_camara.items()):
        for termino_v, freq_v in cnt_v.most_common(50):
            filas_voc.append({
                "anio": anio_v,
                "camara": cam_v,
                "termino_comercial": termino_v,
                "frecuencia": freq_v
            })
    if filas_voc:
        with open(ruta_voc, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(filas_voc[0].keys()))
            writer.writeheader()
            writer.writerows(filas_voc)
        print(f"   [OK] Exportado '{ruta_voc}' ({len(filas_voc)} filas de vocabulario frecuente por año para EDA).")

    # 10. Actores corporativos/regionales emergentes descubiertos por patrones NLP
    ruta_em = "ner_actores_emergentes_nlp.csv"
    filas_em = [
        {"actor_emergente_detectado": k, "frecuencia": v}
        for k, v in conteo_actores_emergentes.most_common(300)
        if v >= 2
    ]
    if filas_em:
        with open(ruta_em, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["actor_emergente_detectado", "frecuencia"])
            writer.writeheader()
            writer.writerows(filas_em)
        print(f"   [OK] Exportado '{ruta_em}' ({len(filas_em)} actores emergentes detectados por NLP).")



class ConsultorDebates1930:
    """
    Herramienta interactiva y programática para responder consultas puntuales de cuantificación
    (ej. '¿Cuánto participaron los diputados de Córdoba y Mendoza en debates sobre Roca-Runciman o la SRA?').
    Puede operar tanto sobre los CSV ya generados (instantáneo) como consultando Supabase en vivo.
    """
    def __init__(self):
        self.archivos_csv = {
            "lista_oct26": "ner_entidades_lista_oct26_resultados.csv",
            "anio_camara": "ner_resumen_entidades_por_anio_camara.csv",
            "provincias_partidos": "ner_participacion_provincias_y_partidos.csv",
            "participacion_realista": "ner_participacion_realista_oradores_partidos_provincias.csv",
            "ministros_vs_camaras": "ner_contraste_oficialismo_ministros_vs_camaras.csv",
            "absa_socios": "ner_sentimiento_aspectos_socios_y_especializacion.csv",
            "leyes_debates": "ner_leyes_mencionadas_en_debates.csv",
            "leyes_sumarios": "ner_entidades_en_leyes_y_sumarios.csv",
        }

    def consultar_csv(
        self,
        reporte: str = "lista_oct26",
        anio: Optional[str] = None,
        camara: Optional[str] = None,
        partido: Optional[str] = None,
        provincia: Optional[str] = None,
        rol_institucional: Optional[str] = None,
        entidad_o_tema: Optional[str] = None,
        top_n: int = 25,
        exportar_a: Optional[str] = None
    ) -> pd.DataFrame:
        ruta = self.archivos_csv.get(reporte, reporte)
        if not os.path.exists(ruta):
            print(f"[!] El archivo '{ruta}' aún no existe. Ejecuta primero el pipeline principal (`python motor_ner.py`).")
            return pd.DataFrame()

        df = pd.read_csv(ruta, encoding="utf-8-sig")
        if anio and "anio" in df.columns:
            df = df[df["anio"].astype(str).str.contains(str(anio), case=False, na=False)]
        if camara and "camara" in df.columns:
            df = df[df["camara"].astype(str).str.contains(str(camara), case=False, na=False)]
        if partido and "partido_politico" in df.columns:
            df = df[df["partido_politico"].astype(str).str.contains(str(partido), case=False, na=False)]
        if provincia and "distrito_provincia" in df.columns:
            df = df[df["distrito_provincia"].astype(str).str.contains(str(provincia), case=False, na=False)]
        if rol_institucional and "rol_institucional" in df.columns:
            df = df[df["rol_institucional"].astype(str).str.contains(str(rol_institucional), case=False, na=False)]
        if entidad_o_tema:
            cols_texto = [c for c in ("entidad_canonica", "tema_o_entidad", "aspecto_socio_o_concepto", "codigo_ley", "descripcion_ley", "titulo_proyecto") if c in df.columns]
            if cols_texto:
                mascara = False
                for c in cols_texto:
                    mascara = mascara | df[c].astype(str).str.contains(str(entidad_o_tema), case=False, na=False)
                df = df[mascara]

        if exportar_a and not df.empty:
            df.to_csv(exportar_a, index=False, encoding="utf-8-sig")
            print(f"[OK] Consulta personalizada exportada a '{exportar_a}' ({len(df)} filas).")

        return df.head(top_n)

    def consultar_supabase_3nf(
        self,
        anio: Optional[int] = None,
        camara: Optional[str] = None,
        partido: Optional[str] = None,
        coalicion: Optional[str] = None,
        provincia: Optional[str] = None,
        orador: Optional[str] = None,
        texto_contiene: Optional[str] = None,
        limite: int = 50
    ) -> pd.DataFrame:
        """
        Consulta directamente sobre las tablas normalizadas 3NF de Supabase
        (intervenciones, sesiones, tomos_diarios_sesiones, personas, mandatos_legislativos,
        partidos_politicos, provincias) usando relaciones nativas PostgREST, sin requerir vistas SQL.
        """
        q = supabase.table("intervenciones").select(
            "id_intervencion, orden_dialogo, nro_pagina, texto_canonico, "
            "sesiones!inner(id_sesion, fecha_exacta, numero_reunion, tipo_sesion, "
            "tomos_diarios_sesiones!inner(anio_legislativo, camara, codigo_tomo)), "
            "personas!inner(nombre_completo), "
            "mandatos_legislativos(cargo_especifico, partidos_politicos(nombre_oficial, coalicion_general), provincias(nombre))"
        )
        if anio is not None:
            q = q.eq("sesiones.tomos_diarios_sesiones.anio_legislativo", int(anio))
        if camara:
            q = q.ilike("sesiones.tomos_diarios_sesiones.camara", f"%{camara}%")
        if orador:
            q = q.ilike("personas.nombre_completo", f"%{orador}%")
        if texto_contiene:
            q = q.ilike("texto_canonico", f"%{texto_contiene}%")

        res = q.order("id_intervencion").limit(limite).execute()
        filas_planas = []
        for r in (res.data or []):
            ses = r.get("sesiones") or {}
            tomo = ses.get("tomos_diarios_sesiones") or {}
            per = r.get("personas") or {}
            mand = r.get("mandatos_legislativos") or {}
            pt = mand.get("partidos_politicos") or {}
            pr = mand.get("provincias") or {}
            nom_part = pt.get("nombre_oficial") or "Sin Especificar"
            nom_coal = pt.get("coalicion_general") or "Sin Especificar"
            nom_prov = pr.get("nombre") or "Sin Especificar"
            if partido and partido.lower() not in nom_part.lower():
                continue
            if coalicion and coalicion.lower() not in nom_coal.lower():
                continue
            if provincia and provincia.lower() not in nom_prov.lower():
                continue
            filas_planas.append({
                "id_intervencion": r["id_intervencion"],
                "fecha_exacta": ses.get("fecha_exacta"),
                "anio_legislativo": tomo.get("anio_legislativo"),
                "camara": tomo.get("camara"),
                "nombre_orador": per.get("nombre_completo"),
                "rol": mand.get("cargo_especifico") or "Institucional / Sin Banca",
                "partido_politico": nom_part,
                "coalicion_general": nom_coal,
                "distrito_provincia": nom_prov,
                "texto_canonico": r.get("texto_canonico")
            })
        return pd.DataFrame(filas_planas)


def generar_dashboard_desde_palabras(
    lista_palabras: List[str],
    titulo_dashboard: str = "Dashboard Analítico Reproducible de Intervenciones y NER (1929–1939)",
    subtitulo_dashboard: Optional[str] = None,
    ruta_salida: Optional[str] = None,
    forzar_recarga_supabase: bool = False,
) -> str:
    """
    Recibe una lista arbitraria de palabras o frases (`lista_palabras`), normaliza
    intrínsecamente los términos recibidos y las 64.636 intervenciones (insensible
    a mayúsculas, tildes, puntos, barras o guiones), y genera el Dashboard HTML
    interactivo estandarizado con todos los filtros multidimensionales y tabla plana.
    """
    from Creacion_graficos.generar_dashboard_ner import (
        generar_dashboard_desde_palabras as _generar_dashboard,
    )
    return _generar_dashboard(
        lista_palabras=lista_palabras,
        titulo_dashboard=titulo_dashboard,
        subtitulo_dashboard=subtitulo_dashboard,
        ruta_salida=ruta_salida,
        forzar_recarga_supabase=forzar_recarga_supabase,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Motor NER, ABSA y Cuantificación de Debates Parlamentarios (1929-1939)"
    )
    parser.add_argument(
        "--entidades",
        default="Lista Entidades - OCT26.pdf",
        help="Ruta al archivo de entidades (por defecto: 'Lista Entidades - OCT26.pdf')"
    )
    parser.add_argument(
        "--lote",
        type=int,
        default=500,
        help="Tamaño de lote para paginación sobre 'intervenciones' en Supabase"
    )
    parser.add_argument(
        "--dashboard-palabras",
        nargs="+",
        default=None,
        help="Lista de palabras para generar directamente el dashboard HTML interactivo reproducible."
    )
    parser.add_argument(
        "--salida-dashboard",
        type=str,
        default=None,
        help="Ruta del archivo HTML de salida para --dashboard-palabras."
    )
    parser.add_argument(
        "--consultar",
        type=str,
        default=None,
        help="Opcional: consultar un reporte CSV ya generado ('lista_oct26', 'provincias_partidos', 'participacion_realista', 'ministros_vs_camaras', 'absa_socios', 'leyes_debates')"
    )
    parser.add_argument("--anio", type=str, default=None, help="Filtro de año para consulta (ej. 1933)")
    parser.add_argument("--camara", type=str, default=None, help="Filtro de cámara ('Diputados' o 'Senadores')")
    parser.add_argument("--partido", type=str, default=None, help="Filtro de partido político")
    parser.add_argument("--provincia", type=str, default=None, help="Filtro de provincia/distrito")
    parser.add_argument("--rol", type=str, default=None, help="Filtro de rol ('PODER_EJECUTIVO_MINISTRO', 'CAMARA_DIPUTADOS', 'CAMARA_SENADORES')")
    parser.add_argument("--tema", type=str, default=None, help="Filtro de entidad, socio comercial, eje temático o ley")
    parser.add_argument("--exportar", type=str, default=None, help="Ruta CSV donde exportar la consulta personalizada")

    args = parser.parse_args()

    if args.dashboard_palabras:
        generar_dashboard_desde_palabras(
            lista_palabras=args.dashboard_palabras,
            ruta_salida=args.salida_dashboard,
        )
    elif args.consultar:
        consultor = ConsultorDebates1930()
        df_res = consultor.consultar_csv(
            reporte=args.consultar,
            anio=args.anio,
            camara=args.camara,
            partido=args.partido,
            provincia=args.provincia,
            rol_institucional=args.rol,
            entidad_o_tema=args.tema,
            exportar_a=args.exportar
        )
        if not df_res.empty:
            print(df_res.to_string(index=False))
    else:
        ejecutar_ner_sobre_intervenciones(
            ruta_archivo_entidades=args.entidades,
            tamano_pagina=args.lote
        )
