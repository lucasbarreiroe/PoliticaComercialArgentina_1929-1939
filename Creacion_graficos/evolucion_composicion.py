#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evolución de la composición partidaria activa en ambas cámaras (1929-1939).

Calcula la cantidad de legisladores únicos de cada partido que hicieron uso de la palabra
al menos una vez en cada año parlamentario. Genera dos gráficos interactivos:
1. `composicion_activa_diputados.html`
2. `composicion_activa_senadores.html`
Ambos gráficos muestran los valores numéricos sobre cada barra, sin auto-reproducción
y con márgenes ajustados para evitar cualquier solapamiento.
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
if dir_actual not in sys.path:
    sys.path.insert(0, dir_actual)

from database_connection import supabase
from bancas_diputados import cargar_datos_intervenciones

print(" EVOLUCIÓN DE COMPOSICIÓN PARLAMENTARIA ACTIVA    ")
print(" (1929-1939) - Diputados y Senadores              ")

df = cargar_datos_intervenciones(supabase)

# Filtrar sin trámite y con partido identificado
df = df[~df['partido'].isin(['No Identificado', 'NO IDENTIFICADO / FUNCIONARIO'])]
df_unicos = df.drop_duplicates(subset=['anio', 'rol', 'id_parlamentario', 'partido'])

df_agrupado = df_unicos.groupby(['anio', 'rol', 'partido']).size().reset_index(name='representantes_activos')

def generar_html_animado(df_camara, nombre_camara, archivo_salida):
    if df_camara.empty:
        print(f"No hay datos suficientes para {nombre_camara}.")
        return

    df_camara = df_camara.sort_values(['anio', 'representantes_activos'], ascending=[True, False])
    df_top = df_camara.groupby('anio').head(10).reset_index(drop=True)

    años_posibles = range(1929, 1940)
    partidos_top_historico = df_top['partido'].unique()
    
    grilla = pd.MultiIndex.from_product([años_posibles, partidos_top_historico], names=['anio', 'partido']).to_frame(index=False)
    df_final = pd.merge(grilla, df_top, on=['anio', 'partido'], how='left').fillna(0)
    df_final = df_final.sort_values(by=['anio', 'representantes_activos'], ascending=[True, False])

    max_y = df_final['representantes_activos'].max() * 1.25 

    fig = px.bar(
        df_final, 
        x="partido", 
        y="representantes_activos", 
        color="partido", 
        animation_frame="anio", 
        animation_group="partido",
        range_y=[0, max_y], 
        title=f"Top 10 Partidos: Representantes Activos por Año - {nombre_camara} (1929-1939)",
        labels={'representantes_activos': 'Nº de Legisladores Activos', 'partido': '', 'anio': 'Año'},
        template="plotly_white",
        text="representantes_activos"
    )

    fig.update_traces(textposition='outside', textfont_size=11, cliponaxis=False)
    for frame in fig.frames:
        for d in frame.data:
            d.textposition = 'outside'
            d.cliponaxis = False
            d.textfont = dict(size=11)

    fig.update_layout(
        xaxis=dict(categoryorder='total descending', title=None, tickangle=-35, tickfont=dict(size=11)),
        yaxis=dict(title='Nº de Legisladores Activos'),
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

    ruta_archivo = os.path.join(dir_graficos, archivo_salida)
    html_bruto = fig.to_html(include_plotlyjs='cdn')
    html_limpio = html_bruto.replace("Plotly.animate(", "//Plotly.animate(")
    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(html_limpio)
    print(f" [OK] Archivo generado: '{archivo_salida}'")


print("\n[+] Generando gráficos interactivos de composición por cámara...")

df_diputados = df_agrupado[df_agrupado['rol'] == 'Diputado']
df_senadores = df_agrupado[df_agrupado['rol'] == 'Senador']

generar_html_animado(df_diputados, "Cámara de Diputados", "composicion_activa_diputados.html")
generar_html_animado(df_senadores, "Senado", "composicion_activa_senadores.html")

