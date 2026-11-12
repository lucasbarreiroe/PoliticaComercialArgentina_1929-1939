#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Este script extrae la provincia de cada legislador a partir de las listas
de composición que figuran al inicio de los tomos.

Recorre las primeras páginas de cada PDF, busca los patrones 'Apellido, Nombre'
seguido de su provincia o distrito, corrige las fallas típicas de OCR en los nombres
de las provincias y genera un CSV limpio para vincular a cada persona con su provincia.
"""

import os
import sys
from pathlib import Path
import pdfplumber
import pandas as pd
import re

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Diccionario para corregir errores frecuentes de OCR en los nombres de provincias
provincias_map = {
    "Buenos Aires": "Buenos Aires",
    "Capital": "Capital Federal",
    "Catamarca": "Catamarca",
    "Catamaren": "Catamarca",
    "Córdoba": "Córdoba",
    "Corrientes": "Corrientes",
    "Entre Rios": "Entre Ríos",
    "Entre Ríos": "Entre Ríos",
    "Jujuy": "Jujuy",
    "La Rioja": "La Rioja",
    "Mendoza": "Mendoza",
    "Salta": "Salta",
    "San Juan": "San Juan",
    "San Luis": "San Luis",
    "Santa Fe": "Santa Fe",
    "S. del Estero": "Santiago del Estero",
    "Santiago del Estero": "Santiago del Estero",
    "Tucumán": "Tucumán",
    "Tucuman": "Tucumán"
}

# Patrón para identificar: "Apellido, Nombres" + "Provincia"
prov_regex = r"(" + "|".join(provincias_map.keys()) + r")"
# Captura el nombre (con tildes y signos), saltea caracteres de relleno y toma la provincia
pattern = re.compile(r"([A-ZÁÉÍÓÚÑÜ][a-záéíóúñüA-ZÁÉÍÓÚÑÜ\s\.\(\)]+?,\s+[A-ZÁÉÍÓÚÑÜ][a-záéíóúñüA-ZÁÉÍÓÚÑÜ\s\.\(\)]+?)\s*(?:\.+|\d+|[a-z]{1,3})?\s*" + prov_regex)

def procesar_catalogos_masivo(ruta_raiz, paginas_a_leer=30):
    datos_totales = []
    
    for directorio_actual, subdirectorios, archivos in os.walk(ruta_raiz):
        subdirectorios.sort()
        archivos.sort()
        
        for archivo in archivos:
            if archivo.lower().endswith('.pdf'):
                ruta_completa = os.path.join(directorio_actual, archivo)
                carpeta_anio = os.path.basename(directorio_actual)
                
                print(f"Buscando índice en: {archivo} ({carpeta_anio})...")
                
                try:
                    with pdfplumber.open(ruta_completa) as pdf:
                        fin_real = min(paginas_a_leer, len(pdf.pages))
                        for i in range(fin_real):
                            pagina = pdf.pages[i]
                            ancho, alto = pagina.width, pagina.height
                            mitad = ancho / 2
                            
                            texto_izq = pagina.crop((0, 0, mitad, alto)).extract_text()
                            texto_der = pagina.crop((mitad, 0, ancho, alto)).extract_text()
                            
                            texto_completo = ""
                            if texto_izq: texto_completo += texto_izq + "\n"
                            if texto_der: texto_completo += texto_der + "\n"
                            
                            for linea in texto_completo.split('\n'):
                                linea = re.sub(r'\s+', ' ', linea)
                                matches = pattern.findall(linea)
                                
                                for m in matches:
                                    nombre = m[0].strip().strip('.')
                                    provincia = provincias_map[m[1]]
                                    
                                    datos_totales.append({
                                        "nombre_oficial": nombre,
                                        "distrito_provincia": provincia,
                                        "anio_origen": carpeta_anio
                                    })
                except Exception as e:
                    print(f"   [!] Error leyendo {archivo}: {e}")

    df = pd.DataFrame(datos_totales)
    
    if not df.empty:
        print(f"\nSe encontraron {len(df)} registros brutos.")
        # Como procesamos la misma persona en varios años, nos quedamos solo con su primera mención
        df = df.drop_duplicates(subset=['nombre_oficial'], keep='first')
        
    return df

if __name__ == "__main__":
    ruta_fuentes = r"G:\Mi unidad\Fuentes" 
    
    
    df_catalogo = procesar_catalogos_masivo(ruta_fuentes)
    
    nombre_archivo_salida = "maestro_distritos_limpio.csv"
    df_catalogo.to_csv(nombre_archivo_salida, index=False, encoding='utf-8')
    