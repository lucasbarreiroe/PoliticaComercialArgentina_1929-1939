import asyncio
import re
from openai import AsyncOpenAI
from database_connection import supabase

API_KEY = "" #saque mi api key de open ai para subir el repo.
cliente_ai = AsyncOpenAI(api_key=API_KEY)
MODELO = "gpt-4o-mini"
CONCURRENCIA = 5  # No necesitamos tantos hilos

instrucciones_sistema = """
You are an expert curator of 1930s Argentine parliamentary debates.
Fix the OCR errors in the provided Spanish text.
WARNING: A previous AI attempted to fix this text and fell into a repetitive loop hallucination.
Ignore any repetitive nonsense. Read the raw OCR carefully and reconstruct the logical 1930s Spanish text.
DO NOT repeat words endlessly. Output ONLY the corrected text.
"""

def es_delirio(texto):
    """
    Función heurística en Python para detectar alucinaciones de IA sin gastar tokens.
    """
    if not texto: 
        return False
        
    palabras = texto.lower().split()
    total_palabras = len(palabras)
    
    if total_palabras < 15:
        return False
        
    vocabulario = set(palabras)
    ratio_riqueza = len(vocabulario) / total_palabras
    
    if total_palabras > 30 and ratio_riqueza < 0.25:
        return True
        
    if re.search(r'(\b.+?\b)(?:\s+\1){4,}', texto, re.IGNORECASE):
        return True
        
    return False

async def reparar_delirio(id_int, texto_crudo, texto_alucinado, semaforo):
    async with semaforo:
        try:
            respuesta = await cliente_ai.chat.completions.create(
                model=MODELO,
                messages=[
                    {"role": "system", "content": instrucciones_sistema},
                    {"role": "user", "content": texto_crudo} # Le pasamos el OCR original, no el alucinado
                ],
                temperature=0.1
            )
            texto_limpio = respuesta.choices[0].message.content.strip()
            return id_int, texto_limpio, True
        except Exception as e:
            print(f" [!] Error reparando ID {id_int}: {e}")
            return id_int, None, False

async def cazar_y_reparar():

    ultimo_id = 0
    tamaño_lote = 500
    semaforo = asyncio.Semaphore(CONCURRENCIA)
    
    alucinaciones_detectadas = 0
    reparadas = 0

    while True:
        # Traemos SOLO los que ya fueron procesados y tienen texto_gemini
        try:
            respuesta = supabase.table("intervenciones") \
                .select("id_intervencion, texto_corregido, texto_gemini") \
                .gt("id_intervencion", ultimo_id) \
                .not_.is_("texto_gemini", "null") \
                .neq("texto_gemini", "OMITIDO_POR_LARGO") \
                .order("id_intervencion") \
                .limit(tamaño_lote) \
                .execute()
        except Exception as e:
            print(f"Error de red: {e}. Reintentando...")
            await asyncio.sleep(5)
            continue
            
        lote = respuesta.data
        if not lote:
            print(f"\n[✓] Análisis completado.")
            print(f"Resumen: {alucinaciones_detectadas} delirios detectados | {reparadas} reparados exitosamente.")
            break
            
        tareas_reparacion = []
        
        for row in lote:
            ultimo_id = max(ultimo_id, row['id_intervencion'])
            
            if es_delirio(row['texto_gemini']):
                alucinaciones_detectadas += 1
                print(f" [!] Bucle detectado en ID {row['id_intervencion']}. Enviando a OpenAI para reparación...")
                tareas_reparacion.append(
                    reparar_delirio(row['id_intervencion'], row['texto_corregido'], row['texto_gemini'], semaforo)
                )
        
        if tareas_reparacion:
            for tarea_completada in asyncio.as_completed(tareas_reparacion):
                id_int, texto_limpio, exito = await tarea_completada
                
                if exito and texto_limpio:
                    # Sobreescribimos el delirio con la nueva versión limpia
                    await asyncio.to_thread(
                        lambda: supabase.table("intervenciones").update({
                            "texto_gemini": texto_limpio
                        }).eq("id_intervencion", id_int).execute()
                    )
                    reparadas += 1
                    print(f"   [✓] ID {id_int} curado y guardado en Supabase.")

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(cazar_y_reparar())