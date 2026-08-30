import os
import re
import pdfplumber
import pandas as pd
from database_connection import supabase

def extraer_texto_doble_columna(ruta_pdf):
    """Extrae el texto de TODAS las páginas de un PDF a doble columna."""
    texto_completo = ""
    with pdfplumber.open(ruta_pdf) as pdf:
        paginas_totales = len(pdf.pages)
        print(f"Total de páginas a procesar en este tomo: {paginas_totales}")
        
        for i in range(paginas_totales):
            # Mostramos un aviso cada 50 páginas para no pensar que se colgó
            if i % 50 == 0 and i > 0:
                print(f"   ... Procesando página {i} de {paginas_totales}")
                
            pagina = pdf.pages[i]
            ancho, alto = pagina.width, pagina.height
            mitad = ancho / 2
            
            texto_izq = pagina.crop((0, 0, mitad, alto)).extract_text()
            texto_der = pagina.crop((mitad, 0, ancho, alto)).extract_text()
            
            if texto_izq: texto_completo += texto_izq + "\n"
            if texto_der: texto_completo += texto_der + "\n"
            
    return texto_completo

def parsear_intervenciones(texto_completo):
    """Estructura los diálogos atrapando a los oradores."""
    intervenciones = []
    orador_actual, texto_actual = None, []
    patron_orador = re.compile(r"^Sr\.\s+(.*?)\.?\s*[-—]\s*(.*)")

    for linea in texto_completo.split('\n'):
        linea = linea.strip()
        
        if not linea or "CONGRESO NACIONAL" in linea or "CÁMARA DE DIPUTADOS" in linea:
            continue
            
        match = patron_orador.match(linea)
        if match:
            if orador_actual:
                intervenciones.append({
                    "orador": orador_actual, 
                    "texto": " ".join(texto_actual)
                })
            orador_actual = match.group(1).strip()
            texto_actual = [match.group(2).strip()]
        elif orador_actual:
            texto_actual.append(linea)
            
    if orador_actual and texto_actual:
        intervenciones.append({
            "orador": orador_actual, 
            "texto": " ".join(texto_actual)
        })
        
    return intervenciones

def procesar_corpus(ruta_raiz):
    """Recorre todos los PDFs y genera los CSVs completos."""
    for directorio_actual, _, archivos in os.walk(ruta_raiz):
        for archivo in archivos:
            if archivo.lower().endswith('.pdf'):
                ruta_completa = os.path.join(directorio_actual, archivo)
                carpeta_anio = os.path.basename(directorio_actual)
                
                print(f"\n========================================")
                print(f"Iniciando: {archivo} (Año: {carpeta_anio})")
                print(f"========================================")
                
                # Leemos todo el PDF (Sin límites)
                texto = extraer_texto_doble_columna(ruta_completa)
                
                print("Estructurando los diálogos y aplicando Regex...")
                datos_parseados = parsear_intervenciones(texto)
                
                if datos_parseados:
                    df = pd.DataFrame(datos_parseados)
                    df['archivo_origen'] = archivo
                    df['anio'] = carpeta_anio
                    
                    nombre_csv = f"output_{carpeta_anio}_{archivo}.csv"
                    df.to_csv(nombre_csv, index=False, encoding='utf-8')
                    print(f"¡Éxito! Extraídas {len(df)} intervenciones masivas en {nombre_csv}")

if __name__ == "__main__":
    # La ruta de tu Google Drive para Escritorio
    ruta_fuentes = r"G:\Mi unidad\Fuentes" 
    procesar_corpus(ruta_fuentes)