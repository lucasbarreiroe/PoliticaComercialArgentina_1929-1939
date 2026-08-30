import os
import pdfplumber

def extraer_texto_doble_columna(ruta_pdf, pagina_inicio, pagina_fin):
    """Abre un PDF local/virtual y extrae el texto respetando las dos columnas."""
    texto_completo = ""
    with pdfplumber.open(ruta_pdf) as pdf:
        paginas_totales = len(pdf.pages)
        fin_real = min(pagina_fin, paginas_totales)
        
        for i in range(pagina_inicio, fin_real):
            pagina = pdf.pages[i]
            ancho = pagina.width
            alto = pagina.height
            
            # Cortamos la página en dos mitades
            mitad = ancho / 2
            columna_izq = pagina.crop((0, 0, mitad, alto))
            columna_der = pagina.crop((mitad, 0, ancho, alto))
            
            # Extraemos el texto
            texto_izq = columna_izq.extract_text()
            texto_der = columna_der.extract_text()
            
            if texto_izq: texto_completo += texto_izq + "\n"
            if texto_der: texto_completo += texto_der + "\n"
                
    return texto_completo

def procesar_corpus(ruta_raiz):
    """Recorre todas las subcarpetas, encuentra los PDFs y los procesa."""
    
    print(f"Buscando archivos en: {ruta_raiz}...\n")
    
    # os.walk recorre automáticamente todas las subcarpetas ("1929", "1930-1932", etc.)
    for directorio_actual, subdirectorios, archivos in os.walk(ruta_raiz):
        for archivo in archivos:
            if archivo.lower().endswith('.pdf'):
                ruta_completa = os.path.join(directorio_actual, archivo)
                
                # Extraemos el año basándonos en el nombre de la subcarpeta en la que estamos
                carpeta_anio = os.path.basename(directorio_actual) 
                
                print(f"--- Procesando: {archivo} (Año: {carpeta_anio}) ---")
                
                try:
                    # Probamos extraer 3 páginas (ajustá estos números según veas el PDF)
                    print("Extrayendo texto a doble columna...")
                    texto = extraer_texto_doble_columna(ruta_completa, 40, 43)
                    
                    # Acá en el futuro irá el INSERT a la tabla 'sesiones' e 'intervenciones' de Supabase
                    
                    # Guardamos un log temporal para ver que la extracción funcionó
                    nombre_txt = f"test_{carpeta_anio}_{archivo.replace('.pdf', '')}.txt"
                    with open(nombre_txt, "w", encoding="utf-8") as f:
                        f.write(texto)
                        
                    print(f"Éxito. Texto guardado temporalmente en {nombre_txt}\n")
                    
                    # Rompemos el ciclo después del primer archivo para probar
                    return 
                    
                except Exception as e:
                    print(f"Error al procesar {archivo}: {e}\n")

if __name__ == "__main__":
    # Ajustá la letra del disco según cómo te lo asigne Google Drive para Escritorio
    # Cuidado con las barras invertidas en Windows, usamos r"" al principio.
    ruta_fuentes = r"G:\Mi unidad\Fuentes" 
    
    procesar_corpus(ruta_fuentes)