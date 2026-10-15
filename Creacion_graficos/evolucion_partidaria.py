import os
import sys
import pandas as pd
import plotly.express as px

# Crear carpeta de gráficos si no existe
os.makedirs("graficos", exist_ok=True)

ruta_padre = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ruta_padre)

from database_connection import supabase

print("Descargando datos para la línea de tiempo...")
todas_las_filas = []
inicio = 0
tamaño_lote = 1000

while True:
    respuesta = supabase.table("intervenciones") \
        .select("id_intervencion, texto_gemini, texto_limpio, sesiones(fecha), parlamentarios(partido_politico)") \
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
        
        if "sesiones" in fila:
            del fila["sesiones"]
        if "parlamentarios" in fila:
            del fila["parlamentarios"]
            
    todas_las_filas.extend(filas)
    inicio += tamaño_lote
    print(f"Descargados {len(todas_las_filas)} registros temporales...")

df = pd.DataFrame(todas_las_filas)

print("\nProcesando fechas y limpieza de textos...")

def obtener_texto_final(row):
    t_gemini = row.get('texto_gemini')
    t_limpio = row.get('texto_limpio')
    
    t_gemini = '' if pd.isna(t_gemini) or t_gemini is None else str(t_gemini).strip()
    t_limpio = '' if pd.isna(t_limpio) or t_limpio is None else str(t_limpio).strip()
    
    if t_gemini and t_gemini != 'OMITIDO_POR_LARGO':
        return t_gemini
    return t_limpio

df['texto_final'] = df.apply(obtener_texto_final, axis=1)
df = df[df['texto_final'] != '']

df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
df['anio'] = df['fecha'].dt.year

df = df.dropna(subset=['anio'])
df['anio'] = df['anio'].astype(int)
df = df[(df['anio'] >= 1929) & (df['anio'] <= 1939)]
df = df[df['partido'] != 'No Identificado']

df_agrupado = df.groupby(['anio', 'partido']).size().reset_index(name='intervenciones')
df_agrupado = df_agrupado.sort_values(['anio', 'intervenciones'], ascending=[True, False])
df_top10 = df_agrupado.groupby('anio').head(10).reset_index(drop=True)

años_posibles = range(1929, 1940)
partidos_top10_historico = df_top10['partido'].unique()

grilla = pd.MultiIndex.from_product([años_posibles, partidos_top10_historico], names=['anio', 'partido']).to_frame(index=False)
df_final = pd.merge(grilla, df_top10, on=['anio', 'partido'], how='left').fillna(0)
df_final = df_final.sort_values(by=['anio', 'intervenciones'], ascending=[True, False])

print("Generando el archivo HTML interactivo...")

max_y = df_final['intervenciones'].max() * 1.25 

fig = px.bar(
    df_final, 
    x="partido", 
    y="intervenciones", 
    color="partido", 
    animation_frame="anio", 
    animation_group="partido",
    range_y=[0, max_y], 
    title="Top 10 Partidos por Año: Evolución de Intervenciones (1929-1939)",
    labels={'intervenciones': 'Nº de Intervenciones', 'partido': 'Partido Político', 'anio': 'Año'},
    template="plotly_white",
    text="intervenciones" # Muestra los números
)

fig.update_traces(textposition='outside', textfont_size=12, cliponaxis=False)

fig.update_layout(
    xaxis={'categoryorder': 'total descending'},
    margin=dict(l=50, r=50, t=80, b=150),
    plot_bgcolor="rgba(245,245,245,0.8)",
    transition=dict(duration=0) # BLOQUEA ANIMACION INICIAL (no corre solo)
)

# BLOQUEA BOTONES Y ANIMACION DEL SLIDER
fig.layout.updatemenus = []
if fig.layout.sliders:
    for step in fig.layout.sliders[0].steps:
        step.args[1]["transition"]["duration"] = 0
        step.args[1]["frame"]["duration"] = 0

ruta_archivo = os.path.join("graficos", "evolucion_partidaria_1929_1939.html")
# Formato ligero para compartir a otros 
fig.write_html(ruta_archivo, include_plotlyjs='cdn')

print(f"¡Listo! Se creó el archivo '{ruta_archivo}'.")