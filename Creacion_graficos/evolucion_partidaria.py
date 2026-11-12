#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evolución temporal de la participación parlamentaria por partido político (1929-1939).

Genera un gráfico de barras animado con Plotly que muestra el Top 10 de partidos con más intervenciones
en cada año. El gráfico inicia estático (sin auto-reproducción) para permitir explorar año por año
a través de la barra deslizante sin que se superpongan las etiquetas con el slider.
"""

import os
import sys
import pandas as pd
import plotly.express as px

# Directorios de trabajo y salida
dir_actual = os.path.dirname(os.path.abspath(__file__))
dir_graficos = os.path.join(dir_actual, "graficos")
os.makedirs(dir_graficos, exist_ok=True)

ruta_padre = os.path.abspath(os.path.join(dir_actual, '..'))
if ruta_padre not in sys.path:
    sys.path.insert(0, ruta_padre)
ruta_db = os.path.abspath(os.path.join(ruta_padre, 'base_de_datos'))
if ruta_db not in sys.path:
    sys.path.insert(0, ruta_db)
if dir_actual not in sys.path:
    sys.path.insert(0, dir_actual)

from database_connection import supabase
from bancas_diputados import cargar_datos_intervenciones

print(" EVOLUCIÓN TEMPORAL DE PARTIDOS (1929-1939)       ")

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
    labels={'intervenciones': 'Nº de Intervenciones', 'partido_limpio': '', 'anio': 'Año'},
    template="plotly_white",
    text="intervenciones"
)

fig.update_traces(textposition='outside', textfont_size=11, cliponaxis=False)
for frame in fig.frames:
    for d in frame.data:
        d.textposition = 'outside'
        d.cliponaxis = False
        d.textfont = dict(size=11)

fig.update_layout(
    xaxis=dict(categoryorder='total descending', title=None, tickangle=-35, tickfont=dict(size=11)),
    yaxis=dict(title='Nº de Intervenciones'),
    margin=dict(l=60, r=60, t=90, b=180),
    plot_bgcolor="rgba(245,245,245,0.8)",
    transition=dict(duration=0)
)

fig.layout.updatemenus = []
if fig.layout.sliders:
    fig.layout.sliders[0].y = -0.28
    fig.layout.sliders[0].pad = dict(t=25, b=10)
    fig.layout.sliders[0].currentvalue = dict(
        prefix="Año: ",
        font=dict(size=14, color="#1e293b", family="Arial Black")
    )
    for step in fig.layout.sliders[0].steps:
        step.args[1]["transition"]["duration"] = 0
        step.args[1]["frame"]["duration"] = 0

ruta_archivo = os.path.join(dir_graficos, "evolucion_partidaria_1929_1939.html")
html_bruto = fig.to_html(include_plotlyjs='cdn')
html_limpio = html_bruto.replace("Plotly.animate(", "//Plotly.animate(")
with open(ruta_archivo, 'w', encoding='utf-8') as f:
    f.write(html_limpio)
