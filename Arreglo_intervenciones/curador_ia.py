import asyncio
from openai import AsyncOpenAI
from database_connection import supabase

# ==========================================
# CONFIGURACIÓN OPENAI (TIER 1 - PAGO POR USO)
# ==========================================
API_KEY = "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"
cliente_ai = AsyncOpenAI(api_key=API_KEY)

MODELO = "gpt-4o-mini"
CONCURRENCIA = 15  
LOTE_ACTUALIZACION = 100

# ==========================================
# INSTRUCCIONES OPTIMIZADAS (INGLÉS)
# Ahorra aprox 40% de Input Tokens frente al español
# ==========================================
instrucciones_sistema = """
You are an expert curator of 1930s Argentine parliamentary debates. Fix OCR errors in the provided Spanish text.

STRICT RULES:
1. Fix scanning typos (e.g., 'H. Cánara' -> 'H. Cámara', 'lcy' -> 'ley').
2. Join words split by line-break hyphens.
3. Maintain original 1930s Spanish grammar, formal tone, and vocabulary.
4. Keep all proper nouns, law numbers, and economic figures perfectly intact.
5. DO NOT summarize, omit paragraphs, or add comments.

Output ONLY the corrected Spanish text. Do not use markdown blocks or introductory phrases.
"""

async def procesar_con_openai(id_int, texto_crudo, semaforo):
    async with semaforo:
        if not texto_crudo or len(texto_crudo.strip()) < 10:
            return id_int, None, "OMITIDO_CORTO"

        # REINCORPORADO: Límite de 5000 palabras para el barrido inicial
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
    print("==================================================")
    print(f"INICIANDO MOTOR (OPENAI - {MODELO.upper()} - PROMPT OPTIMIZADO)")
    print("==================================================")

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