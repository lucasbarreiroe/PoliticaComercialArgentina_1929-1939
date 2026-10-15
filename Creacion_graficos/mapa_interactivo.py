import os
import sys
import re
import requests
import pandas as pd
import plotly.graph_objects as go

# Crear carpeta de gráficos si no existe
os.makedirs("graficos", exist_ok=True)

ruta_padre = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ruta_padre)

from database_connection import supabase

print("==================================================")
print(" MAPA DE INTERVENCIONES CON TABLA INFERIOR CENTRADA")
print("==================================================")

print("[+] Descargando cartografía oficial de Argentina...")
url_geojson = "https://apis.datos.gob.ar/georef/api/provincias.geojson?max=24"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

try:
    respuesta = requests.get(url_geojson, headers=headers)
    mapa_arg = respuesta.json()
except Exception as e:
    print(f"[!] Error al descargar el GeoJSON: {e}")
    sys.exit()

print("[+] Descargando textos de la base de datos...")
todas_las_filas = []
inicio = 0
tamaño_lote = 1000

while True:
    respuesta = supabase.table("intervenciones") \
        .select("id_intervencion, texto_gemini, texto_limpio, sesiones(fecha), parlamentarios(partido_politico, distrito_provincia)") \
        .range(inicio, inicio + tamaño_lote - 1) \
        .execute()
    
    filas = respuesta.data
    if not filas:
        break 
        
    for fila in filas:
        sesion_data = fila.get("sesiones") or {}
        fila["fecha"] = sesion_data.get("fecha", None)
        
        parla_data = fila.get("parlamentarios") or {}
        fila["partido"] = parla_data.get("partido_politico", "No Identificado")
        fila["provincia"] = parla_data.get("distrito_provincia", "No Identificada")
        
        if "sesiones" in fila: del fila["sesiones"]
        if "parlamentarios" in fila: del fila["parlamentarios"]
            
    todas_las_filas.extend(filas)
    inicio += tamaño_lote
    print(f"  ... Descargados {len(todas_las_filas)} registros...")

df = pd.DataFrame(todas_las_filas)

print("\n[+] Limpiando ruido y procesando fechas...")

def obtener_texto_final(row):
    t_gemini = row.get('texto_gemini')
    t_limpio = row.get('texto_limpio')
    t_gemini = '' if pd.isna(t_gemini) or t_gemini is None else str(t_gemini).strip()
    t_limpio = '' if pd.isna(t_limpio) or t_limpio is None else str(t_limpio).strip()
    if t_gemini and t_gemini != 'OMITIDO_POR_LARGO': return t_gemini
    return t_limpio

df['texto_final'] = df.apply(obtener_texto_final, axis=1)
df = df[df['texto_final'] != '']

df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
df['anio'] = df['fecha'].dt.year
df = df.dropna(subset=['anio'])
df['anio'] = df['anio'].astype(int)
df = df[(df['anio'] >= 1929) & (df['anio'] <= 1939)]

patrones = [
    r"se va a votar", r"se votará", r"resulta afirmativa", r"resulta negativa",
    r"queda levantada la sesión", r"queda abierta la sesión", r"se lee el artículo",
    r"tiene la palabra", r"leyendo:", r"queda aprobado", r"a la comisión de",
    r"votan \d+ señores diputados", r"se va a dar cuenta", r"concederá la palabra", 
    r"orden del día", r"cuarto intermedio", r"asentimiento", r"se va a leer"
]

def clasificar_intervencion(row):
    t_lower = str(row['texto_final']).lower()
    if row['partido'] not in ["No Identificado", "NO IDENTIFICADO / FUNCIONARIO"]: return row['partido']
    for p in patrones:
        if re.search(p, t_lower): return "Trámite"
    return "No Identificado (Real)"

df['partido_limpio'] = df.apply(clasificar_intervencion, axis=1)

mapeo_provincias = {
    'CABA': 'Ciudad Autónoma de Buenos Aires',
    'Cdad. Autónoma de Bs. As.': 'Ciudad Autónoma de Buenos Aires',
    'Capital Federal': 'Ciudad Autónoma de Buenos Aires',
    'RíoNegro': 'Río Negro',
    'Stgo. del Estero': 'Santiago del Estero',
    'T. del Fuego': 'Tierra del Fuego, Antártida e Islas del Atlántico Sur'
}
df['provincia'] = df['provincia'].replace(mapeo_provincias)

df_politico = df[~df['partido_limpio'].isin(["Trámite", "No Identificado (Real)"])]
df_provs = df_politico[df_politico['provincia'] != 'No Identificada']

print("[+] Calculando porcentajes...")

df_prov = df_provs.groupby(['anio', 'provincia']).size().reset_index(name='ints_provincia')
totales_anio = df_prov.groupby('anio')['ints_provincia'].sum().reset_index(name='ints_totales_anio')

df_prov = pd.merge(df_prov, totales_anio, on='anio')
df_prov['pct_intervenciones'] = (df_prov['ints_provincia'] / df_prov['ints_totales_anio']) * 100

anios = range(1929, 1940)
todas_las_provincias = [feature['properties']['nombre'] for feature in mapa_arg['features']]
grilla_prov = pd.MultiIndex.from_product([anios, todas_las_provincias], names=['anio', 'provincia']).to_frame(index=False)

df_final = pd.merge(grilla_prov, df_prov, on=['anio', 'provincia'], how='left').fillna(0)
df_final = df_final.sort_values(by=['anio', 'provincia'])

df_final['hover_text'] = df_final['pct_intervenciones'].apply(lambda x: f"{x:.2f}%")

print("\n[+] Generando diseño con espacios rígidos para evitar superposición...")

rojos_fuertes = [
    [0.0, "#ffffff"],       
    [0.01, "#ffcccc"],      
    [0.4, "#e60000"],       
    [1.0, "#660000"]        
]
max_pct = df_final['pct_intervenciones'].max()

# Instanciamos la figura vacía
fig = go.Figure()

frames = []
slider_steps = []

for anio in anios:
    df_anio = df_final[df_final['anio'] == anio].copy()
    
    # Tabla: excluir el 0% y ordenar
    df_tabla = df_anio[df_anio['pct_intervenciones'] > 0].sort_values(by='pct_intervenciones', ascending=False)
    provincias_tabla = df_tabla['provincia'].tolist()
    porcentajes_tabla = df_tabla['hover_text'].tolist()

    if anio == 1929:
        # A. EL MAPA
        fig.add_trace(
            go.Choropleth(
                geojson=mapa_arg,
                locations=df_anio['provincia'],
                featureidkey='properties.nombre',
                z=df_anio['pct_intervenciones'],
                text=df_anio['hover_text'], 
                colorscale=rojos_fuertes,
                zmin=0, zmax=max_pct,
                marker_line_width=0.8,
                marker_line_color='#2C3E50',
                hovertemplate="<b style='font-size:15px;'>%{location}</b><br><br>Participación: <b>%{text}</b><extra></extra>",
                colorbar=dict(
                    title="<b>%</b>",
                    thicknessmode="pixels", thickness=15,
                    lenmode="pixels", len=250,
                    yanchor="middle", y=0.75, # Alineado al sector superior
                    x=0.9,
                    ticks="outside"
                )
            )
        )
        
        # B. LA TABLA
        fig.add_trace(
            go.Table(
                header=dict(
                    values=["<b>Provincia</b>", "<b>Participación</b>"],
                    fill_color="#E60000",
                    align="center",
                    font=dict(color="white", size=14, family="Arial Black")
                ),
                cells=dict(
                    values=[provincias_tabla, porcentajes_tabla],
                    fill_color="#F4F6F8",
                    align=["left", "center"],
                    font=dict(color="#2C3E50", size=13),
                    height=25
                ),
                # ESPACIO DE LA TABLA: Ancho centrado (25% a 75%) y de altura llega SÓLO hasta el 30%
                domain=dict(x=[0.25, 0.75], y=[0.0, 0.30]) 
            )
        )

    # Frame para actualización
    frame = go.Frame(
        data=[
            go.Choropleth(
                locations=df_anio['provincia'],
                z=df_anio['pct_intervenciones'],
                text=df_anio['hover_text']
            ),
            go.Table(
                cells=dict(values=[provincias_tabla, porcentajes_tabla])
            )
        ],
        name=str(anio)
    )
    frames.append(frame)

    # Botón del slider
    step = dict(
        method="animate",
        args=[
            [str(anio)],
            {"frame": {"duration": 0, "redraw": True}, "mode": "immediate", "transition": {"duration": 0}}
        ],
        label=str(anio)
    )
    slider_steps.append(step)

fig.frames = frames

# Configuración del Slider
sliders = [dict(
    active=0,
    y=0.45, # ESPACIO DEL SLIDER: Está en el 45% (crea un buffer de 15% entre la tabla y el slider)
    yanchor="bottom", # Forzamos que crezca hacia arriba
    x=0.1,
    len=0.8,
    currentvalue=dict(
        font=dict(size=20, color="#E60000", family="Arial Black"),
        prefix="Año Legislativo: "
    ),
    pad={"t": 10, "b": 10},
    steps=slider_steps,
    bgcolor="rgba(44, 62, 80, 0.6)",
    bordercolor="#2C3E50"
)]

# Posición del Mapa
fig.update_geos(
    scope="south america",
    visible=False,
    lataxis_range=[-55.5, -21.0], 
    lonaxis_range=[-74.0, -53.0],
    projection_type="mercator",
    domain=dict(x=[0, 1], y=[0.55, 1.0]) # ESPACIO DEL MAPA: Ocupa el 45% superior (dejando 10% de buffer con el slider)
)

# Estilos Generales
fig.update_layout(
    height=1100, 
    margin=dict(l=0, r=0, t=80, b=20),
    plot_bgcolor="rgba(255, 255, 255, 1)",
    paper_bgcolor="rgba(255, 255, 255, 1)",
    font=dict(family="Arial", color="#2C3E50"),
    title="<b>Mapa del Debate Parlamentario (1929-1939)</b><br><sup style='color:#7f8c8d'>Distribución porcentual de las intervenciones por provincia</sup>",
    title_x=0.5,
    title_font_size=24,
    sliders=sliders,
    updatemenus=[]
)

print("[+] Guardando archivo...")

html_bruto = fig.to_html(include_plotlyjs='cdn')
html_limpio = html_bruto.replace("Plotly.animate(", "//Plotly.animate(")

archivo_salida = os.path.join("graficos", "mapa_provincias_con_tabla.html")
with open(archivo_salida, 'w', encoding='utf-8') as f:
    f.write(html_limpio)

print(f"[✓] ¡Listo! Mapa y tabla con distribución perfecta en: '{archivo_salida}'")