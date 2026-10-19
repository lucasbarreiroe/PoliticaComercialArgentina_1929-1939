import asyncio
import textwrap
from groq import AsyncGroq
from database_connection import supabase

# ==========================================
# CONFIGURACIÓN DEL POOL DE CLAVES GROQ
# ==========================================
API_KEYS = [
]

clientes_groq = [AsyncGroq(api_key=key) for key in API_KEYS]
indice_cliente_actual = 0  

instrucciones_sistema = """
You are an expert text editor. Your task is to clean up OCR-extracted text from 1930s Argentine parliamentary debates.

STRICT RULES:
1. Fix common OCR typos and join words broken by hyphens at the end of lines.
2. Remove incorrect or extra spacing, and fix unnecessary line breaks to form proper, cohesive paragraphs.
3. DO NOT alter the historical vocabulary, grammar, or formal tone.
4. DO NOT summarize, omit paragraphs, or add any commentary.
5. Preserve all proper nouns, numbers, and legislative references exactly as they appear.

Return ONLY the cleaned text. Do not include introductory phrases or markdown blocks.
"""

LOTE_ACTUALIZACION = 100
CONCURRENCIA = 3
MODELO = "allam-2-7b"

# Límite seguro de caracteres por llamada para no explotar la ventana de contexto
MAX_CARACTERES = 15000 

async def procesar_texto_con_reintentos(id_int, texto_crudo, semaforo):
    global indice_cliente_actual
    
    async with semaforo:
        if not texto_crudo or len(str(texto_crudo).strip()) < 2:
            return id_int, None, "OMITIDO_CORTO"

        texto_str = str(texto_crudo)
        
        # CHUNKING: Cortamos el texto en fragmentos seguros
        fragmentos = textwrap.wrap(texto_str, width=MAX_CARACTERES, break_long_words=False, replace_whitespace=False)
        
        texto_curado_final = ""
        claves_usadas = set()
        
        for i, fragmento in enumerate(fragmentos):
            if len(fragmentos) > 1:
                print(f"      [~] ID {id_int}: Procesando parte {i+1} de {len(fragmentos)}...")
                
            fragmento_limpio = None
            
            # Bucle de reintento infinito para Rate Limits por cada fragmento
            while True:
                idx_usado = indice_cliente_actual
                cliente_activo = clientes_groq[idx_usado]
                
                try:
                    respuesta = await cliente_activo.chat.completions.create(
                        messages=[
                            {"role": "system", "content": instrucciones_sistema},
                            {"role": "user", "content": fragmento}
                        ],
                        model=MODELO,
                        temperature=0.1
                    )
                    fragmento_limpio = respuesta.choices[0].message.content.strip()
                    claves_usadas.add(str(idx_usado + 1))
                    break # Salió bien, rompemos el bucle While y avanzamos al siguiente fragmento

                except Exception as e:
                    mensaje_error = str(e).lower()
                    
                    # Si nos pasamos de límite (Rate Limit / 429), cambiamos de clave y ESPERAMOS 10 segundos
                    if "rate limit" in mensaje_error or "429" in mensaje_error or "capacity" in mensaje_error:
                        if indice_cliente_actual == idx_usado:
                            indice_cliente_actual = (indice_cliente_actual + 1) % len(API_KEYS)
                        print(f" [!] Rate limit (Clave {idx_usado + 1}). Esperando 10s y cambiando a Clave {indice_cliente_actual + 1}...")
                        await asyncio.sleep(10)
                        continue  
                    
                    # Si a pesar de todo tira error 400 (muy raro con fragmentos de 15k, pero por las dudas)
                    if "context length" in mensaje_error or "too large" in mensaje_error or "400" in mensaje_error or "reduce the length" in mensaje_error:
                        print(f" [!] Fragmento de ID {id_int} demasiado largo. Omitiendo.")
                        return id_int, None, "OMITIDO_LARGO"
                    
                    # Otro tipo de error
                    print(f" [!] Error raro en ID {id_int} (parte {i+1}): {mensaje_error[:50]}...")
                    await asyncio.sleep(5)
                    continue
            
            # Si el fragmento se limpió correctamente, lo sumamos al texto final
            if fragmento_limpio:
                texto_curado_final += fragmento_limpio + "\n\n"
                
            # Pequeña pausa entre fragmentos del mismo texto para cuidar la API
            if len(fragmentos) > 1:
                await asyncio.sleep(0.5)
                
        # Armamos el mensaje de estado final
        estado_final = f"EXITO (Clave/s {', '.join(claves_usadas)})"
        if len(fragmentos) > 1:
            estado_final += f" - [Unido de {len(fragmentos)} partes]"
            
        return id_int, texto_curado_final.strip(), estado_final

async def curar_base_con_pool():
    print("==================================================")
    print(f"INICIANDO MOTOR (GROQ) CON POOL DE {len(API_KEYS)} CLAVES")
    print("==================================================")

    ultimo_id = 0
    procesados_totales = 0
    semaforo = asyncio.Semaphore(CONCURRENCIA)

    while True:
        print(f"\n[+] Buscando registros desde ID {ultimo_id}...")
        
        try:
            respuesta = supabase.table("intervenciones") \
                .select("id_intervencion, texto_limpio, texto_gemini") \
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
            tareas.append(procesar_texto_con_reintentos(row['id_intervencion'], row.get('texto_limpio', ''), semaforo))
            ultimo_id = max(ultimo_id, row['id_intervencion'])
        
        for tarea_completada in asyncio.as_completed(tareas):
            id_int, texto_curado, estado = await tarea_completada
            
            if estado.startswith("EXITO") and texto_curado:
                await asyncio.to_thread(
                    lambda: supabase.table("intervenciones").update({
                        "texto_gemini": texto_curado
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
                print(f" [>] ID {id_int} -> Omitido (Supera límite de tokens)")
                
            elif estado == "OMITIDO_CORTO":
                print(f" [>] ID {id_int} -> Omitido (Demasiado corto o nulo)")
            else:
                print(f" [x] ID {id_int} -> FALLÓ ({estado})")
                
            await asyncio.sleep(1) # Pausa segura entre peticiones

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(curar_base_con_pool())