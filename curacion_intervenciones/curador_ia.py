#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Este script se encarga de curar los textos de las intervenciones legislativas con un LLM.

A veces el OCR de los diarios de sesiones de los años 30 deja errores difíciles
de resolver solo con reglas fijas (letras cambiadas, palabras cortadas o caracteres extraños).
Lo que hace este script es enviar los discursos por lotes y en paralelo a la API de OpenAI,
pidiéndole al modelo que corrija únicamente los defectos de digitalización sin modernizar
ni alterar el vocabulario de la época.
"""

import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI
from database_connection import supabase

load_dotenv()

# Configuración del cliente y parámetros de procesamiento
API_KEY = os.getenv("OPENAI_API_KEY")
cliente_ai = AsyncOpenAI(api_key=API_KEY)

MODELO = "gpt-4o-mini"
CONCURRENCIA = 15  # Cantidad de llamadas simultáneas
LOTE_ACTUALIZACION = 100

instrucciones_sistema = """
You are an expert paleographer, linguist, and data curator specialized in Argentine parliamentary history (1929-1939). Your task is to reconstruct and clean noisy OCR text from the "Diarios de Sesiones" 
of the National Congress, producing a flawless transcription that faithfully preserves the original historical speech.

### CORE OBJECTIVE
Fix all Optical Character Recognition (OCR) errors, reconstruct broken layouts, and output a clean, continuous Spanish text without altering the original meaning, style, or historical vocabulary.

### STRICT RULES & GUIDELINES:

1. ORTHOGRAPHY & OCR NOISE REPAIR:
   - Fix common OCR misreadings (e.g., 'Cánara' -> 'Cámara', 'lcy' -> 'ley', 'nacionaI' -> 'nacional', 'rn' read as 'm', '0' read as 'O', '8' read as 'B', 'c' read as 'e').
   - Restore missing accents/diacritics typical of Spanish, but do not change archaic spellings if they were standard in the 1930s.
   - Clean up spurious characters, random symbols (e.g., ©, %, *, #) inserted by the scanner, and erratic spacing before punctuation (e.g., "palabra ," -> "palabra,").

2. STRUCTURAL & LINE-BREAK FIXES:
   - Reconstruct words split across lines by hyphenation (e.g., "dipu-\ntado" -> "diputado").
   - Remove artificial line breaks that interrupt a single sentence or paragraph. Only preserve line breaks that clearly represent a new paragraph or structural element.
   - Fix corrupted structural headers and abbreviations (e.g., "Articulo 10" or "Artienio 1" -> "Artículo 1º").

3. HISTORICAL FIDELITY (DO NOT MODERNIZE):
   - Maintain the original 1930s Argentine parliamentary grammar, formal tone, and vocabulary. 
   - Keep formal addresses exactly as they appear (e.g., "Vuestra Honorabilidad", "Señor Presidente", "Honorable Cámara").
   - Do not "correct" the style, syntax, or flow of the speech, even if it sounds overly rhetorical, redundant, or archaic by modern standards.

4. PRESERVATION OF CRITICAL ENTITIES:
   - Pay special attention to Proper Nouns (politicians, provinces, historical actors, and institutions like "Caja Nacional", "Ferrocarriles del Estado").
   - Ensure Law numbers, decrees, and dates are perfectly intact (e.g., "ley 11.281").
   - Protect economic figures, percentages, and currencies exactly as formatted (e.g., "$ 50.000 m/n.", "£", "u$s"). If the OCR scrambled a number (e.g., "11.O00"), fix the obvious typo to ("11.000").

5. ABSOLUTE CONSTRAINTS (OUTPUT FORMAT):
   - DO NOT summarize, paraphrase, omit paragraphs, or add your own comments.
   - DO NOT hallucinate missing text; if a word is completely illegible, make the best logical phonetic fix based on the immediate context.
   - DO NOT wrap the output in markdown code blocks (```) or use XML tags.
   - DO NOT include ANY introductory or concluding conversational filler (e.g., "Here is the corrected text", "Done", "Understood"). 

OUTPUT ONLY THE RAW, CORRECTED SPANISH TEXT.
"""

async def procesar_con_openai(id_int, texto_crudo, semaforo):
    async with semaforo:
        # Descartamos textos vacíos o demasiado breves (saludos o aclaraciones mínimas)
        if not texto_crudo or len(texto_crudo.strip()) < 10:
            return id_int, None, "OMITIDO_CORTO"

        # Si supera las 5000 palabras lo salteamos en la primera pasada para no consumir tokens de más
        cantidad_palabras = len(texto_crudo.split())
        if cantidad_palabras > 5000:
            return id_int, None, "OMITIDO_LARGO"

        try:
            respuesta = await cliente_ai.chat.completions.create(
                model=MODELO,
                messages=[
                    {"role": "system", "content": instrucciones_sistema},
                    {"role": "user", "content": texto_crudo}
                ],
                temperature=0.1
            )
            texto_limpio = respuesta.choices[0].message.content.strip()
            if texto_limpio:
                return id_int, texto_limpio, "EXITO"

        except Exception as e:
            print(f" [!] Error en ID {id_int}: {str(e)}")
            return id_int, None, "ERROR_API"

async def curar_base_pago():

    ultimo_id = 0
    procesados_totales = 0
    semaforo = asyncio.Semaphore(CONCURRENCIA)

    while True:
        print(f"[+] Buscando lote de {LOTE_ACTUALIZACION} registros desde ID {ultimo_id}...")
        
        try:
            respuesta = supabase.table("intervenciones") \
                .select("id_intervencion, texto_corregido, texto_gemini") \
                .gt("id_intervencion", ultimo_id) \
                .or_("texto_gemini.is.null,texto_gemini.eq.OMITIDO_POR_LARGO") \
                .order("id_intervencion") \
                .limit(LOTE_ACTUALIZACION) \
                .execute()
        except Exception as e:
            print(f"[!] Error conectando con Supabase. Reintentando en 5s... ({e})")
            await asyncio.sleep(5)
            continue
            
        lote = respuesta.data
        if not lote:
            print(f"\n[✓] ¡Misión cumplida! Se procesaron {procesados_totales} textos en esta sesión.")
            break
            
        tareas = []
        for row in lote:
            tareas.append(procesar_con_openai(row['id_intervencion'], row['texto_corregido'], semaforo))
            ultimo_id = max(ultimo_id, row['id_intervencion'])
        
        for tarea_completada in asyncio.as_completed(tareas):
            id_int, texto_limpio, estado = await tarea_completada
            
            if estado == "EXITO" and texto_limpio:
                await asyncio.to_thread(
                    lambda: supabase.table("intervenciones").update({
                        "texto_gemini": texto_limpio
                    }).eq("id_intervencion", id_int).execute()
                )
                procesados_totales += 1
                print(f" [✓] ID {id_int} -> Corregido")
                
            elif estado == "OMITIDO_LARGO":
                await asyncio.to_thread(
                    lambda: supabase.table("intervenciones").update({
                        "texto_gemini": "OMITIDO_POR_LARGO"
                    }).eq("id_intervencion", id_int).execute()
                )
                print(f" [>] ID {id_int} -> Omitido (Más de 5000 palabras)")
                
            elif estado == "OMITIDO_CORTO":
                print(f" [>] ID {id_int} -> Omitido (Demasiado corto)")
                
            else:
                print(f" [x] ID {id_int} -> Suspendido por error. Se deja en NULL.")

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(curar_base_pago())