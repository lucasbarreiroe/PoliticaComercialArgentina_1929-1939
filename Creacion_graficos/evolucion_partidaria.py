import os
import sys
import pandas as pd
import plotly.express as px

# Directorios
dir_actual = os.path.dirname(os.path.abspath(__file__))
dir_graficos = os.path.join(dir_actual, "graficos")
os.makedirs(dir_graficos, exist_ok=True)

ruta_padre = os.path.abspath(os.path.join(dir_actual, '..'))
if ruta_padre not in sys.path:
    sys.path.insert(0, ruta_padre)
if dir_actual not in sys.path:
    sys.path.insert(0, dir_actual)

from database_connection import supabase
from bancas_diputados import cargar_datos_intervenciones

print("==================================================")
print(" EVOLUCIÓN TEMPORAL DE PARTIDOS (1929-1939)       ")
print("==================================================")

df = cargar_datos_intervenciones(supabase)
df = df[~df['partido_limpio'].isin(["Trámite", "No Identificado (Real)", "No Identificado"])]

df_agrupado = df.groupby(['anio', 'partido_limpio']).size().reset_index(name='intervenciones')
df_agrupado = df_agrupado.sort_values(['anio', 'intervenciones'], ascending=[True, False])
df_top10 = df_agrupado.groupby('anio').head(10).reset_index(drop=True)

años_posibles = range(1929, 1940)
partidos_top10_historico = df_top10['partido_limpio'].unique()

grilla = pd.MultiIndex.from_product([años_posibles, partidos_top10_historico], names=['anio', 'partido_limpio']).to_frame(index=False)
df_final = pd.merge(grilla, df_top10, on=['anio', 'partido_limpio'], how='left').fillna(0)
df_final = df_final.sort_values(by=['anio', 'intervenciones'], ascending=[True, False])

max_y = df_final['intervenciones'].max() * 1.25 

fig = px.bar(
    df_final, 
    x="partido_limpio", 
    y="intervenciones", 
    color="partido_limpio", 
    animation_frame="anio", 
    animation_group="partido_limpio",
    range_y=[0, max_y], 
    title="Top 10 Partidos por Año: Evolución de Intervenciones (1929-1939)",
    labels={'intervenciones': 'Nº de Intervenciones', 'partido_limpio': 'Partido Político', 'anio': 'Año'},
    template="plotly_white",
    text="intervenciones"
)

fig.update_traces(textposition='outside', textfont_size=12, cliponaxis=False)

fig.update_layout(
    xaxis={'categoryorder': 'total descending'},
    margin=dict(l=50, r=50, t=80, b=150),
    plot_bgcolor="rgba(245,245,245,0.8)",
    transition=dict(duration=0)
)

fig.layout.updatemenus = []
if fig.layout.sliders:
    for step in fig.layout.sliders[0].steps:
        step.args[1]["transition"]["duration"] = 0
        step.args[1]["frame"]["duration"] = 0

ruta_archivo = os.path.join(dir_graficos, "evolucion_partidaria_1929_1939.html")
fig.write_html(ruta_archivo, include_plotlyjs='cdn')
print(f"[OK] Archivo generado exitosamente: '{ruta_archivo}'.")
