import asyncio
import pandas as pd
from groq import AsyncGroq
from database_connection import supabase

# Aca estaban mis claves pero las saque para subir el repo.
API_KEYS = [
    
]

MODELOS_CASCADA = [
    "allam-2-7b"
]

CONCURRENCIA = 5  

clientes_groq = [AsyncGroq(api_key=key) for key in API_KEYS]

PROMPT_SISTEMA = """
Eres un experto analizando diarios de sesiones de Argentina en 1930. 
Analiza el siguiente fragmento de texto parlamentario.
Debes determinar si es la CONTINUACIÓN de un discurso de fondo de un diputado, o si es una intervención INSTITUCIONAL/PROCEDIMENTAL (ej: el presidente dando la palabra, un secretario leyendo, votaciones).

REGLA ESTRICTA: Responde ÚNICAMENTE con una de estas dos palabras. Cero explicaciones.
- CONTINUACION
- INSTITUCIONAL
"""

def obtener_datos():
    print("Descargando IDs para armar la línea temporal...")
    todas_las_filas = []
    inicio = 0
    tamaño_lote = 1000

    while True:
        respuesta = supabase.table("intervenciones") \
            .select("id_intervencion, id_parlamentario, texto_gemini") \
            .order("id_intervencion") \
            .range(inicio, inicio + tamaño_lote - 1) \
            .execute()
        
        filas = respuesta.data
        if not filas:
            break
            
        todas_las_filas.extend(filas)
        inicio += tamaño_lote
        print(f"Descargados {len(todas_las_filas)} registros temporales...")
        
    return pd.DataFrame(todas_las_filas)

def encontrar_sandwiches(df):
    print("\nBuscando el patrón [Diputado X] -> [789] -> [Diputado X]...")
    textos_a_evaluar = []
    
    i = 0
    while i < len(df):
        id_actual = df['id_parlamentario'].iloc[i]
        
        if id_actual != 789:
            start_idx = i
            j = i + 1
            
            while j < len(df) and df['id_parlamentario'].iloc[j] == 789:
                j += 1
                
            if j < len(df) and j > start_idx + 1:
                id_cierre = df['id_parlamentario'].iloc[j]
                
                if id_cierre == id_actual:
                    for k in range(start_idx + 1, j):
                        textos_a_evaluar.append({
                            'id_intervencion': int(df['id_intervencion'].iloc[k]),
                            'texto': str(df['texto_gemini'].iloc[k]),
                            'candidato_id': int(id_actual)
                        })
            i = j
        else:
            i += 1
            
    return textos_a_evaluar

async def procesar_sandwich_con_cascada(item, semaforo):
    async with semaforo:
        id_int = item['id_intervencion']
        texto_crudo = item['texto']
        id_candidato = item['candidato_id']

        if not texto_crudo or len(texto_crudo.strip()) < 15:
            return id_int, "OMITIDO_CORTO"

        cantidad_palabras = len(texto_crudo.split())
        if cantidad_palabras > 5000:
            return id_int, "OMITIDO_LARGO"
        
        # Iteramos una vez por cada clave en el pool
        for intento_clave in range(len(API_KEYS)):
            cliente_activo = clientes_groq[intento_clave]
            
            for modelo in MODELOS_CASCADA:
                try:
                    respuesta = await cliente_activo.chat.completions.create(
                        messages=[
                            {"role": "system", "content": PROMPT_SISTEMA},
                            {"role": "user", "content": f'Texto:\n"{texto_crudo}"'}
                        ],
                        model=modelo,
                        temperature=0.0
                    )
                    decision = respuesta.choices[0].message.content.strip().upper()
                    
                    if "CONTINUACION" in decision:
                        await asyncio.to_thread(
                            lambda: supabase.table("intervenciones").update({
                                "id_parlamentario": id_candidato
                            }).eq("id_intervencion", id_int).execute()
                        )
                        return id_int, f"IMPUTADO (Clave {intento_clave + 1})"
                    elif "INSTITUCIONAL" in decision:
                        return id_int, f"MANTENIDO_789 (Clave {intento_clave + 1})"
                    else:
                        return id_int, f"AMBIGUO: {decision}"

                except Exception as e:
                    mensaje_error = str(e).lower()
                    
                    # Manejo de errores de límites (429) o autenticación
                    if "rate limit" in mensaje_error or "429" in mensaje_error or "capacity" in mensaje_error:
                        continue 
                    
                    if "context length" in mensaje_error or "too large" in mensaje_error:
                        return id_int, "OMITIDO_LARGO"
                    
                    continue
            
            pass
            
        # Todas las claves fallaron
        return id_int, "LIMITE_TOTAL"

async def curar_sandwiches_con_pool():
    df = obtener_datos()
    sandwiches = encontrar_sandwiches(df)
    
    print(f"\nSe encontraron {len(sandwiches)} intervenciones huérfanas dentro de 'sándwiches'.")
    if not sandwiches:
        print("No hay nada que evaluar.")
        return
        
    
    semaforo = asyncio.Semaphore(CONCURRENCIA)
    tareas = [procesar_sandwich_con_cascada(item, semaforo) for item in sandwiches]
    
    procesados = 0
    for tarea_completada in asyncio.as_completed(tareas):
        id_int, estado = await tarea_completada
        procesados += 1
            
        await asyncio.sleep(0.5) 

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(curar_sandwiches_con_pool())