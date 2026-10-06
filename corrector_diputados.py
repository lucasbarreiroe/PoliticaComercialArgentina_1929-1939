import pandas as pd
import difflib
import csv
from database_connection import supabase


def limpiar_texto(texto):
    """Convierte nulos a string vacío y elimina espacios extra."""
    if pd.isna(texto):
        return ""
    return str(texto).strip()

def unificar_base_diputados():
    print("Cargando la realidad absoluta desde Diputados.xlsx...")
    df_excel = pd.read_excel('Diputados.xlsx')
    
    print("Obteniendo registros de Supabase...")
    respuesta_db = supabase.table("parlamentarios").select("*").eq("rol", "Diputado").execute()
    diputados_db = respuesta_db.data
    
    if not diputados_db:
        print("No se encontraron diputados en la base de datos.")
        return

    print(f"Total a analizar: {len(diputados_db)} registros en DB.\n")
    
    no_identificados = []
    umbral_similitud = 0.65

    for dip_db in diputados_db:
        id_db = dip_db.get('id_parlamentario') 
        # Adaptado a la columna 'nombre_apellido'
        nombre_db = limpiar_texto(dip_db.get('nombre_apellido'))
        
        mejor_match = None
        mejor_ratio = 0.0
        
        for index, row in df_excel.iterrows():
            nombre_excel = limpiar_texto(row['nombre'])
            
            # Comparamos en minúsculas
            ratio = difflib.SequenceMatcher(None, nombre_db.lower(), nombre_excel.lower()).ratio()
            
            if ratio > mejor_ratio:
                mejor_ratio = ratio
                mejor_match = row
                
        # Si supera el 65% de coincidencia
        if mejor_ratio >= umbral_similitud and mejor_match is not None:
            nuevo_nombre = limpiar_texto(mejor_match['nombre'])
            nuevo_partido = limpiar_texto(mejor_match['Partido'])
            nueva_provincia = limpiar_texto(mejor_match['Distrito'])
            
            print(f"[✓ MATCH {mejor_ratio:.2f}] DB: '{nombre_db}' -> Excel: '{nuevo_nombre}'")
            
            # Actualizamos usando las columnas exactas: nombre_apellido, partido_politico, distrito_provincia
            try:
                supabase.table("parlamentarios").update({
                    "nombre_apellido": nuevo_nombre,
                    "partido_politico": nuevo_partido,
                    "distrito_provincia": nueva_provincia
                }).eq("id_parlamentario", id_db).execute()
            except Exception as e:
                print(f"   [!] Error actualizando ID {id_db}: {e}")
                
        else:
            # Si no hay match (o es < 0.65), guardamos para el CSV
            nombre_cercano = limpiar_texto(mejor_match['nombre']) if mejor_match is not None else "Ninguno"
            print(f"[X NO MATCH] DB: '{nombre_db}' (Mejor intento: {nombre_cercano} con {mejor_ratio:.2f})")
            
            no_identificados.append({
                "ID_DB": id_db,
                "Nombre_en_DB": nombre_db,
                "Mejor_Coincidencia_Excel": nombre_cercano,
                "Porcentaje_Similitud": f"{mejor_ratio:.2f}"
            })

    # Generamos el archivo CSV para los que no superaron el filtro
    if no_identificados:
        nombre_csv = "diputados_no_identificados.csv"
        columnas = no_identificados[0].keys()
        
        with open(nombre_csv, 'w', newline='', encoding='utf-8') as f:
            escritor = csv.DictWriter(f, fieldnames=columnas)
            escritor.writeheader()
            escritor.writerows(no_identificados)
            
        print(f"\nProceso finalizado. Se exportaron {len(no_identificados)} casos no identificados en '{nombre_csv}'.")
    else:
        print("\n¡Proceso perfecto! Se logró match del 100% de los diputados.")

if __name__ == "__main__":
    unificar_base_diputados()