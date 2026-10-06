import asyncio
from groq import AsyncGroq
from database_connection import supabase

# ==========================================
# CONFIGURACIÓN DEL POOL DE CLAVES GROQ
# ==========================================
# Agrega todas las claves que hayas generado
API_KEYS = [
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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"
]

# Inicializamos un cliente asincrónico por cada clave
clientes_groq = [AsyncGroq(api_key=key) for key in API_KEYS]
indice_cliente_actual = 0  # Comienza con el primer cliente

instrucciones_sistema = """
Eres un curador experto en documentos históricos y debates parlamentarios de la República Argentina (década de 1930). 
Tu tarea es tomar textos extraídos mediante OCR y corregir sus errores técnicos, devolviendo un texto limpio y legible.

REGLAS ESTRICTAS DE PROCESAMIENTO:
1. CORRECCIÓN DE OCR: Arregla errores típicos de escaneo (ej: 'H. Cánara' -> 'H. Cámara', 'lcy' -> 'ley').
2. FRAGMENTACIÓN: Une las palabras cortadas por guiones de fin de línea.
3. FIDELIDAD HISTÓRICA: Mantén la gramática, el tono formal y el vocabulario de la época.
4. INTEGRIDAD: Preserva absolutamente todos los nombres propios, números de leyes y cifras económicas.
5. PROHIBICIÓN DE ALTERACIÓN: NO resumas el texto. NO omitas párrafos. NO agregues comentarios.

Devuelve ÚNICAMENTE el texto corregido. No incluyas frases introductorias ni bloques markdown. Tampoco repeticiones ilógicas de las mismas palabras.
"""

LOTE_ACTUALIZACION = 100
CONCURRENCIA = 2  

MODELOS_CASCADA = [
    "allam-2-7b"
]

async def procesar_con_cascada(id_int, texto_crudo, semaforo):
    async with semaforo:
        if not texto_crudo or len(texto_crudo.strip()) < 10:
            return id_int, None, "OMITIDO_CORTO"

        cantidad_palabras = len(texto_crudo.split())
        if cantidad_palabras > 5000:
            return id_int, None, "OMITIDO_LARGO"
        
        # Iteramos una vez por cada clave en el pool
        for intento_clave in range(len(API_KEYS)):
            cliente_activo = clientes_groq[intento_clave]
            
            for modelo in MODELOS_CASCADA:
                try:
                    respuesta = await cliente_activo.chat.completions.create(
                        messages=[
                            {"role": "system", "content": instrucciones_sistema},
                            {"role": "user", "content": texto_crudo}
                        ],
                        model=modelo,
                        temperature=0.1
                    )
                    texto_limpio = respuesta.choices[0].message.content.strip()
                    if texto_limpio:
                        return id_int, texto_limpio, f"EXITO ({modelo} | Clave {intento_clave + 1})"

                except Exception as e:
                    mensaje_error = str(e).lower()
                    
                    if "rate limit" in mensaje_error or "429" in mensaje_error or "capacity" in mensaje_error:
                        continue 
                    
                    if "context length" in mensaje_error or "too large" in mensaje_error:
                        return id_int, None, "OMITIDO_LARGO"
                    
                    continue
            
            # Si llegamos aquí, la clave actual está saturada. Pasamos a la siguiente silenciosamente.
            pass
            
        # NUEVO COMPORTAMIENTO: Drenaje Continuo
        # Si salimos de los bucles, TODOS los modelos en TODAS las claves están saturados.
        # No hay pausa. Devolvemos "LIMITE_TOTAL" y dejamos el registro en NULL.
        return id_int, None, "LIMITE_TOTAL"

async def curar_base_con_pool():
    print("==================================================")
    print(f"INICIANDO MOTOR (GROQ) CON POOL DE {len(API_KEYS)} CLAVES")
    print("==================================================")

    ultimo_id = 0
    procesados_totales = 0
    semaforo = asyncio.Semaphore(CONCURRENCIA)

    while True:
        print(f"[+] Buscando registros desde ID {ultimo_id}...")
        
        try:
            respuesta = supabase.table("intervenciones") \
                .select("id_intervencion, texto_corregido, texto_gemini") \
                .gt("id_intervencion", ultimo_id) \
                .or_("texto_gemini.is.null,texto_gemini.eq.OMITIDO_POR_LARGO") \
                .order("id_intervencion") \
                .limit(LOTE_ACTUALIZACION) \
                .execute()
        except Exception as e:
            print(f"[!] Error conectando con Supabase. Reintentando... ({e})")
            await asyncio.sleep(5)
            continue
            
        lote = respuesta.data
        if not lote:
            print(f"\n[✓] ¡Misión cumplida! Se procesó todo.")
            break
            
        tareas = []
        for row in lote:
            tareas.append(procesar_con_cascada(row['id_intervencion'], row['texto_corregido'], semaforo))
            ultimo_id = max(ultimo_id, row['id_intervencion'])
        
        for tarea_completada in asyncio.as_completed(tareas):
            id_int, texto_limpio, estado = await tarea_completada
            
            if estado.startswith("EXITO") and texto_limpio:
                await asyncio.to_thread(
                    lambda: supabase.table("intervenciones").update({
                        "texto_gemini": texto_limpio
                    }).eq("id_intervencion", id_int).execute()
                )
                procesados_totales += 1
                print(f" [✓] ID {id_int} -> {estado}")
                
            elif estado == "OMITIDO_LARGO":
                await asyncio.to_thread(
                    lambda: supabase.table("intervenciones").update({
                        "texto_gemini": "OMITIDO_POR_LARGO"
                    }).eq("id_intervencion", id_int).execute()
                )
                print(f" [>] ID {id_int} -> Omitido (Más de 5000 palabras)")
                
            elif estado == "LIMITE_TOTAL":
                # Al fallar, simplemente lo informa y sigue de largo. El registro en Supabase sigue siendo NULL.
                print(f" [x] ID {id_int} -> Suspendido (Pool saturado). Se deja en NULL para próxima pasada.")
            elif estado == "OMITIDO_CORTO":
                print(f" [>] ID {id_int} -> Omitido (Demasiado corto)")
            else:
                print(f" [x] ID {id_int} -> FALLÓ ({estado})")
                
            await asyncio.sleep(1.5)

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(curar_base_con_pool())