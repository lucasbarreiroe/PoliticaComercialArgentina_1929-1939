import pandas as pd
import plotly.express as px
from database_connection import supabase

print("Descargando datos para la línea de tiempo...")
todas_las_filas = []
inicio = 0
tamaño_lote = 1000

while True:
    respuesta = supabase.table("intervenciones") \
        .select("id_intervencion, sesiones(fecha), parlamentarios(partido_politico)") \
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

print("\nProcesando fechas...")
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

# Ordenamos por año y luego por intervenciones descendente para que el Top 10 quede a la izquierda
df_final = df_final.sort_values(by=['anio', 'intervenciones'], ascending=[True, False])

print("Generando el archivo HTML interactivo...")

max_y = df_final['intervenciones'].max() * 1.1 

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
    template="plotly_white"
)

fig.update_layout(
    xaxis={'categoryorder': 'total descending'},
    margin=dict(l=50, r=50, t=80, b=150),
    updatemenus=[dict(
        type="buttons", 
        showactive=False,
        x=0.05,
        xanchor="left",
        yanchor="top",
        buttons=[dict(label="Reproducir Evolución", method="animate", args=[None, dict(frame=dict(duration=1000, redraw=True), fromcurrent=True)])]
    )],
    sliders=[dict(
        y=1.1, 
        x=0.2,
        len=0.75,
        xanchor="left",
        yanchor="top"
    )]
)

nombre_archivo = "evolucion_partidaria_1929_1939.html"
fig.write_html(nombre_archivo)

print(f"¡Listo! Se creó el archivo '{nombre_archivo}' en tu carpeta.")