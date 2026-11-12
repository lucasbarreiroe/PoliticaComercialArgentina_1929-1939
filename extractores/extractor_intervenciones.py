"""
Extractor de intervenciones parlamentarias desde los diarios de sesiones (PDF).

La lógica principal es:
1. Cortar cada página al medio geométricamente para leer primero toda la
   columna izquierda y luego la derecha (evitando que se mezclen líneas).
2. Filtrar cabeceras repetitivas y ruido típico de imprenta.
3. Reconstruir los discursos uniendo palabras cortadas con guion al final de línea.
4. Mapear cada orador con el padrón histórico en Supabase usando similitud de texto.
"""

import os
import sys
import re
import difflib
import pdfplumber
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
DIR_DB = ROOT_DIR / "base_de_datos"
if str(DIR_DB) not in sys.path:
    sys.path.insert(0, str(DIR_DB))

from database_connection import supabase

# Guardamos el padrón en memoria para no pegarle a Supabase en cada discurso
CACHE_PARLAMENTARIOS = []
ID_GENERICO_NO_IDENTIFICADO = None

def inicializar_cache():
    """Descarga el padrón una sola vez al inicio para que el matcheo sea rápido."""
    global CACHE_PARLAMENTARIOS, ID_GENERICO_NO_IDENTIFICADO
    print("-> Sincronizando padrón maestro desde Supabase...")
    
    res = supabase.table("parlamentarios").select("id_parlamentario, nombre_apellido").execute()
    for row in res.data:
        nombre_db = str(row['nombre_apellido'])
        apellido = nombre_db.split(',')[0].strip().lower() if ',' in nombre_db else nombre_db.lower()
        CACHE_PARLAMENTARIOS.append({"id": row['id_parlamentario'], "apellido": apellido})
        
        if nombre_db == "NO IDENTIFICADO / FUNCIONARIO":
            ID_GENERICO_NO_IDENTIFICADO = row['id_parlamentario']
            
    # Si todavía no existe el comodín para oradores no identificados, lo creamos
    if not ID_GENERICO_NO_IDENTIFICADO:
        res = supabase.table("parlamentarios").insert({
            "nombre_apellido": "NO IDENTIFICADO / FUNCIONARIO",
            "rol": "Externo"
        }).execute()
        ID_GENERICO_NO_IDENTIFICADO = res.data[0]['id_parlamentario']

def buscar_parlamentario_seguro(orador_crudo):
    """
    Busca al legislador por apellido con tolerancia a erratas de OCR.
    Usamos un umbral de 75% para no asociar oradores equivocados.
    """
    orador_limpio = re.sub(r'\(.*?\)', '', orador_crudo).strip().lower()
    apellidos_conocidos = [p['apellido'] for p in CACHE_PARLAMENTARIOS]
    
    # Buscamos el apellido más parecido
    matches = difflib.get_close_matches(orador_limpio, apellidos_conocidos, n=1, cutoff=0.75)
    
    if matches:
        apellido_encontrado = matches[0]
        ratio = difflib.SequenceMatcher(None, orador_limpio, apellido_encontrado).ratio()
        
        for p in CACHE_PARLAMENTARIOS:
            if p['apellido'] == apellido_encontrado:
                print(f"      [Match] '{orador_crudo}' -> {apellido_encontrado.title()} (Similitud: {ratio:.2f})")
                return p['id']
                
    # Si no hubo match seguro, lo mandamos como externo/no identificado
    print(f"      [No Identificado] '{orador_crudo}' -> Asignado a Funcionario/Externo")
    return ID_GENERICO_NO_IDENTIFICADO

def corregir_ocr(texto):
    """Corrige errores recurrentes del escáner en impresiones de los años treinta."""
    texto = re.sub(r'\bSoñor(es)?\b', 'Señor', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\bdo\b', 'de', texto)
    texto = re.sub(r'\s+\.', '.', texto)
    texto = re.sub(r'\s+,', ',', texto)
    texto = re.sub(r'\\[\s]*$', '', texto) 
    return texto.strip()

def es_ruido_de_imprenta(linea):
    """Detecta encabezados de página y números de reunión para no meterlos en el discurso."""
    patrones_basura = [
        r'^CONGRESO NACIONAL$',
        r'^C[AÁ]MARA DE (DIPUTADOS|SENADORES)$',
        r'^Reuni[oó]n n[uú]m\.',
        r'^[A-Z][a-z]+ \d+ de \d{4}$',
        r'^\d+$',
        r'^SUMARIO$'
    ]
    for patron in patrones_basura:
        if re.search(patron, linea, re.IGNORECASE):
            return True
    return False

def reconstruir_parrafo(lineas):
    """Une renglones sueltos de una intervención pegando palabras cortadas con guion."""
    texto_final = ""
    for linea in lineas:
        linea = linea.strip()
        if not linea: continue
        if texto_final.endswith("-"):
            texto_final = texto_final[:-1] + linea
        else:
            texto_final += " " + linea if texto_final else linea
            
    texto_final = re.sub(r'\s+', ' ', texto_final)
    return corregir_ocr(texto_final)

def extraer_texto_columnas(ruta_pdf):
    """
    Corta la página físicamente en mitad izquierda y derecha.
    Así leemos la primera columna de punta a punta y recién después pasamos a la segunda.
    """
    texto_completo = []
    
    with pdfplumber.open(ruta_pdf) as pdf:
        print(f"   -> Extrayendo {len(pdf.pages)} páginas con recorte estricto...")
        for pagina in pdf.pages:
            mitad = pagina.width / 2
            alto = pagina.height
            
            # Columna izquierda
            texto_izq = pagina.within_bbox((0, 0, mitad, alto)).extract_text(layout=False)
            # Columna derecha
            texto_der = pagina.within_bbox((mitad, 0, pagina.width, alto)).extract_text(layout=False)
            
            if texto_izq:
                renglones = [r.strip() for r in texto_izq.split('\n') if r.strip()]
                texto_completo.extend(renglones)
                
            if texto_der:
                renglones = [r.strip() for r in texto_der.split('\n') if r.strip()]
                texto_completo.extend(renglones)

    return texto_completo

    return texto_completo

def parsear_sesiones_e_intervenciones(lineas_texto, archivo, camara, anio_limpio):
    sesiones_detectadas = []
    sesion_actual = None
    orador_actual = None
    texto_acumulado = []
    
    patron_nueva_sesion = re.compile(r'^(\d+)[A-Z\sº°a]+REUNI[OÓ]N|^SESI[OÓ]N\s+(PREPARATORIA|ORDINARIA)', re.IGNORECASE)
    patron_fecha = re.compile(r"([A-Za-z]+)\s+(\d+)\s+de\s+(\d{4})", re.IGNORECASE)
    patron_orador = re.compile(r"^(?:Sr\.|Señores|Señor)\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s\(\)]+)[.\-—:]+\s*(.*)", re.IGNORECASE)

    for linea in lineas_texto:
        linea = linea.strip()
        if not linea or es_ruido_de_imprenta(linea):
            continue
            
        if patron_nueva_sesion.search(linea):
            if sesion_actual and orador_actual:
                sesion_actual['intervenciones'].append({
                    "orador": orador_actual, 
                    "texto": reconstruir_parrafo(texto_acumulado)
                })
                sesiones_detectadas.append(sesion_actual)
            
            sesion_actual = {
                "numero_reunion": archivo,
                "tipo_sesion": anio_limpio,
                "camara": camara,
                "fecha": f"{anio_limpio}-01-01", 
                "intervenciones": []
            }
            orador_actual = None
            texto_acumulado = []
            continue

        if not sesion_actual:
            continue

        match_fecha = patron_fecha.search(linea)
        if match_fecha and len(sesion_actual['intervenciones']) == 0:
            meses = {"enero": "01", "febrero": "02", "marzo": "03", "abril": "04", "mayo": "05", "junio": "06", 
                     "julio": "07", "agosto": "08", "septiembre": "09", "setiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"}
            mes = meses.get(match_fecha.group(1).lower(), "01")
            dia = match_fecha.group(2).zfill(2)
            anio = match_fecha.group(3)
            sesion_actual['fecha'] = f"{anio}-{mes}-{dia}"

        match_orador = patron_orador.match(linea)
        if match_orador:
            if orador_actual:
                sesion_actual['intervenciones'].append({
                    "orador": orador_actual, 
                    "texto": reconstruir_parrafo(texto_acumulado)
                })
            orador_actual = match_orador.group(1).strip().title()
            texto_acumulado = [match_orador.group(2).strip()]
        
        elif orador_actual:
            texto_acumulado.append(linea)

    if sesion_actual and orador_actual:
        sesion_actual['intervenciones'].append({
            "orador": orador_actual, 
            "texto": reconstruir_parrafo(texto_acumulado)
        })
        sesiones_detectadas.append(sesion_actual)
        
    return sesiones_detectadas

def procesar_y_subir(ruta_raiz):
    
    inicializar_cache()
    
    for dir_actual, _, archivos in os.walk(ruta_raiz):
        carpeta = os.path.basename(dir_actual).strip()
        if not carpeta.isdigit() or len(carpeta) != 4:
            continue
            
        anio = carpeta
        
        for archivo in sorted(archivos):
            if archivo.lower().endswith('.pdf'):
                ruta_completa = os.path.join(dir_actual, archivo)
                archivo_upper = archivo.upper()
                
                if archivo_upper.startswith('CS') or archivo_upper.startswith('DSS'):
                    camara = "Senadores"
                elif archivo_upper.startswith('CD'):
                    camara = "Diputados"
                else:
                    continue
                
                try:
                    check = supabase.table("sesiones").select("id_sesion").eq("numero_reunion", archivo).execute()
                    if check.data:
                        print(f"\n[*] Saltando: {archivo} (Ya procesado)")
                        continue
                except Exception as e:
                    pass
                
                print(f"\nLeyendo: {archivo} | Cámara: {camara} | Año: {anio}")
                lineas_limpias = extraer_texto_columnas(ruta_completa)
                sesiones = parsear_sesiones_e_intervenciones(lineas_limpias, archivo, camara, anio)
                
                for s in sesiones:
                    if not s['intervenciones']: continue
                    
                    max_reintentos = 3
                    id_sesion = None
                    
                    for intento in range(max_reintentos):
                        try:
                            res_sesion = supabase.table("sesiones").insert({
                                "numero_reunion": s['numero_reunion'],
                                "tipo_sesion": s['tipo_sesion'],
                                "camara": s['camara'],
                                "fecha": s['fecha']
                            }).execute()
                            id_sesion = res_sesion.data[0]['id_sesion']
                            break
                        except Exception as e:
                            print(f"      [!] Error creando sesión. Reintentando...")
                            time.sleep(5)
                            
                    if not id_sesion: continue
                    
                    print(f"   -> [Sesión {s['fecha']}] creada con ID {id_sesion}. Mapeando oradores...")
                    
                    lote_dialogos = []
                    for idx, inter in enumerate(s['intervenciones']):
                        id_parl = buscar_parlamentario_seguro(inter['orador'])
                        lote_dialogos.append({
                            "id_sesion": id_sesion,
                            "id_parlamentario": id_parl,
                            "orden_dialogo": idx + 1,
                            "texto_limpio": inter['texto']
                        })
                    
                    for i in range(0, len(lote_dialogos), 500):
                        lote = lote_dialogos[i:i+500]
                        for intento in range(max_reintentos):
                            try:
                                supabase.table("intervenciones").insert(lote).execute()
                                break
                            except Exception as e:
                                print(f"      [!] Error subiendo lote. Reintentando...")
                                time.sleep(5)

if __name__ == "__main__":
    ruta_fuentes = r"G:\Mi unidad\Fuentes" 
    procesar_y_subir(ruta_fuentes)