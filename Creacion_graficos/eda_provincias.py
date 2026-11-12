#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualizaciones de análisis exploratorio (EDA) por partido y provincia (1929-1939).

Genera los gráficos de barras interactivos con slider anual:
1. `animado_partidos_int_abs.html` y `animado_partidos_pal_abs.html`:
   Intervenciones y palabras por partido político en cada año.
2. `animado_provincias_diputados_per_capita_ints.html` y `..._pals.html`:
   Métricas niveladas por banca (per cápita) en Diputados.
3. `animado_provincias_senadores_int_abs.html` y `..._pal_abs.html`:
   Participación provincial en el Senado (2 bancas fijas por provincia).

Todos los gráficos se generan estáticos de entrada (sin reproducción automática)
para que el usuario avance año por año sin choques de texto ni saltos bruscos.
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
from bancas_diputados import (
    cargar_datos_intervenciones,
    calcular_metricas_provinciales_por_anio,
    obtener_bancas_diputados,
    TOTAL_BANCAS_DIPUTADOS,
    BANCAS_SENADORES_POR_PROVINCIA
)

print("  EDA PARLAMENTARIO: PARTIDOS Y PROVINCIAS (1929-1939)")
print("  Normalización y Per-Capitalización en Cámara de Diputados")

df = cargar_datos_intervenciones(supabase)

def generar_html(df_plot, x_col, y_col, color_col, titulo, archivo, barmode='relative', max_y_mult=1.25, label_y='Valor', texto_formato=None):
    max_y = df_plot[y_col].max() * max_y_mult if not df_plot.empty and df_plot[y_col].max() > 0 else 10
    
    col_texto = texto_formato if texto_formato and texto_formato in df_plot.columns else y_col
    
    fig = px.bar(
        df_plot, x=x_col, y=y_col, color=color_col, 
        animation_frame="anio", animation_group=x_col,
        range_y=[0, max_y], title=titulo, barmode=barmode,
        labels={y_col: label_y, x_col: '', 'anio': 'Año'},
        template="plotly_white",
        text=col_texto
    )
    
    fig.update_traces(textposition='outside', textfont_size=11, cliponaxis=False)
    for frame in fig.frames:
        for d in frame.data:
            d.textposition = 'outside'
            d.cliponaxis = False
            d.textfont = dict(size=11)
    
    fig.update_layout(
        xaxis=dict(
            categoryorder='total descending',
            title=None,
            tickangle=-35,
            tickfont=dict(size=11)
        ),
        yaxis=dict(title=label_y),
        margin=dict(l=60, r=60, t=90, b=170),
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
    
    ruta_archivo = os.path.join(dir_graficos, archivo)
    html_bruto = fig.to_html(include_plotlyjs='cdn')
    html_limpio = html_bruto.replace("Plotly.animate(", "//Plotly.animate(")
    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(html_limpio)
    print(f" [OK] {archivo}")


anios = range(1929, 1940)

print("\n[+] Procesando Partidos Políticos...")
df_politico = df[~df['partido_limpio'].isin(["Trámite", "No Identificado (Real)"])]

df_part = df_politico.groupby(['anio', 'partido_limpio']).agg(
    ints=('id_intervencion', 'count'), 
    pals=('num_palabras', 'sum')
).reset_index()

totales_anio_part = df_part.groupby('anio').agg(tot_pals=('pals', 'sum')).reset_index()
df_part = pd.merge(df_part, totales_anio_part, on='anio')
df_part['pct_palabras'] = ((df_part['pals'] / df_part['tot_pals']) * 100).round(2)

df_unicos_part = df_politico.drop_duplicates(subset=['anio', 'id_parlamentario', 'partido_limpio'])
df_bancas_part = df_unicos_part.groupby(['anio', 'partido_limpio']).size().reset_index(name='bancas_activas')

totales_bancas_anio = df_bancas_part.groupby('anio').agg(tot_bancas=('bancas_activas', 'sum')).reset_index()
df_bancas_part = pd.merge(df_bancas_part, totales_bancas_anio, on='anio')
df_bancas_part['pct_bancas'] = ((df_bancas_part['bancas_activas'] / df_bancas_part['tot_bancas']) * 100).round(2)

df_part = pd.merge(df_part, df_bancas_part[['anio', 'partido_limpio', 'pct_bancas']], on=['anio', 'partido_limpio'], how='left')

df_part = df_part.sort_values(['anio', 'ints'], ascending=[True, False])
df_part_top10 = df_part.groupby('anio').head(10).reset_index(drop=True)

partidos_top = df_part_top10['partido_limpio'].unique()
grilla_part = pd.MultiIndex.from_product([anios, partidos_top], names=['anio', 'partido_limpio']).to_frame(index=False)
df_part_final = pd.merge(grilla_part, df_part_top10, on=['anio', 'partido_limpio'], how='left').fillna(0)
df_part_final = df_part_final.sort_values(by=['anio', 'ints'], ascending=[True, False])

generar_html(df_part_final, 'partido_limpio', 'ints', 'partido_limpio', "Partidos: Intervenciones por Año (Absoluto)", "animado_partidos_int_abs.html", label_y="Nº Intervenciones")
generar_html(df_part_final, 'partido_limpio', 'pals', 'partido_limpio', "Partidos: Volumen de Palabras por Año (Absoluto)", "animado_partidos_pal_abs.html", label_y="Nº Palabras")

print("\n[+] Procesando Provincias en la CÁMARA DE DIPUTADOS (Normalizado por bancas)...")
df_dip_prov = calcular_metricas_provinciales_por_anio(df, camara='Diputados')

# Asegurar grilla completa de años y provincias para animación Plotly suave
todas_provs_dip = df_dip_prov['provincia'].unique()
grilla_dip = pd.MultiIndex.from_product([anios, todas_provs_dip], names=['anio', 'provincia']).to_frame(index=False)
df_dip_completo = pd.merge(grilla_dip, df_dip_prov, on=['anio', 'provincia'], how='left').fillna(0)

# Etiquetas formateadas uniformemente para todas las columnas
df_dip_completo['texto_pc_ints'] = df_dip_completo['ints_per_capita'].apply(lambda v: f"{v:.1f}")
df_dip_completo['texto_pc_pals'] = df_dip_completo['pals_per_capita'].apply(lambda v: f"{int(v):,}".replace(",", "."))

# A. Intervenciones Per Cápita (por Diputado)
generar_html(
    df_dip_completo, 'provincia', 'ints_per_capita', 'provincia',
    "<b>Diputados: Intervenciones Per Cápita por Jurisdicción (1929-1939)</b><br><sup style='color:#7f8c8d'>Normalizado por número de bancas asignadas a cada provincia</sup>",
    "animado_provincias_diputados_per_capita_ints.html",
    label_y="Intervenciones / Diputado",
    texto_formato='texto_pc_ints'
)

# B. Palabras Per Cápita (por Diputado)
generar_html(
    df_dip_completo, 'provincia', 'pals_per_capita', 'provincia',
    "<b>Diputados: Volumen de Palabras Per Cápita por Jurisdicción (1929-1939)</b><br><sup style='color:#7f8c8d'>Volumen discursivo promedio generado por cada diputado de la provincia</sup>",
    "animado_provincias_diputados_per_capita_pals.html",
    label_y="Palabras / Diputado",
    texto_formato='texto_pc_pals'
)

print("\n[+] Procesando Provincias en la CÁMARA DE SENADORES (2 senadores c/u)...")
df_sen_prov = calcular_metricas_provinciales_por_anio(df, camara='Senadores')

todas_provs_sen = df_sen_prov['provincia'].unique()
grilla_sen = pd.MultiIndex.from_product([anios, todas_provs_sen], names=['anio', 'provincia']).to_frame(index=False)
df_sen_completo = pd.merge(grilla_sen, df_sen_prov, on=['anio', 'provincia'], how='left').fillna(0)

generar_html(
    df_sen_completo, 'provincia', 'ints', 'provincia',
    "<b>Senado: Intervenciones por Provincia por Año</b><br><sup style='color:#7f8c8d'>Distribución equitativa: 2 senadores por jurisdicción</sup>",
    "animado_provincias_senadores_int_abs.html",
    label_y="Nº Intervenciones"
)
generar_html(
    df_sen_completo, 'provincia', 'pals', 'provincia',
    "<b>Senado: Volumen de Palabras por Provincia por Año</b><br><sup style='color:#7f8c8d'>Distribución equitativa: 2 senadores por jurisdicción</sup>",
    "animado_provincias_senadores_pal_abs.html",
    label_y="Nº Palabras"
)

print("\n¡Proceso de eda_provincias.py finalizado con éxito! Gráficos generados en 'graficos/'.")
