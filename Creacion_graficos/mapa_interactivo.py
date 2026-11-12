#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de los mapas coropléticos interactivos de la Argentina (1929-1939).

Arma dos visualizaciones HTML independientes (una para Diputados y otra para el Senado):
1. Muestra en un mapa de calor la intensidad del debate por provincia ponderada per cápita
   (intervenciones divididas por la cantidad de bancas de cada distrito).
2. Incluye un marcador destacado para CABA con hover completo, para que no quede
   oculta por la escala geográfica de las provincias grandes.
3. Incorpora una tabla lateral ordenada por nivel de participación y una barra de años
   para recorrer la década de 1929 a 1939.
"""

import os
import sys
import json
import requests
import pandas as pd
import plotly.graph_objects as go

# Directorios
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
from bancas_diputados import (
    cargar_datos_intervenciones,
    calcular_metricas_provinciales_por_anio,
    obtener_bancas_diputados,
    TOTAL_BANCAS_DIPUTADOS,
    BANCAS_SENADORES_POR_PROVINCIA
)

print(" MAPA DE INTERVENCIONES NORMALIZADO PER CÁPITA   ")
print(" Cámara de Diputados y Senado (1929-1939)        ")

# 1. Cartografía oficial IGN
print("[+] Obteniendo cartografía oficial de Argentina...")
ruta_geojson_local = os.path.join(dir_actual, "provincias.geojson")
mapa_arg = None

if os.path.exists(ruta_geojson_local):
    try:
        with open(ruta_geojson_local, "r", encoding="utf-8") as f:
            mapa_arg = json.load(f)
    except Exception:
        pass

if not mapa_arg:
    url_geojson = "https://apis.datos.gob.ar/georef/api/provincias.geojson?max=24"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        respuesta = requests.get(url_geojson, headers=headers, timeout=15)
        mapa_arg = respuesta.json()
        with open(ruta_geojson_local, "w", encoding="utf-8") as f:
            json.dump(mapa_arg, f)
    except Exception as e:
        print(f"[!] Error al descargar el GeoJSON: {e}")
        sys.exit(1)

# Homologar CABA en el GeoJSON
for feature in mapa_arg['features']:
    if feature['properties'].get('nombre') in ['Ciudad Autónoma de Buenos Aires', 'Capital Federal']:
        feature['properties']['nombre'] = 'CABA'

# 2. Cargar intervenciones parlamentarias
df = cargar_datos_intervenciones(supabase)

anios = range(1929, 1940)
todas_las_provincias = [feature['properties']['nombre'] for feature in mapa_arg['features']]

rojos_fuertes = [
    [0.0, "#ffffff"],       
    [0.01, "#ffcccc"],      
    [0.4, "#e60000"],       
    [1.0, "#660000"]        
]

azules_senado = [
    [0.0, "#ffffff"],       
    [0.01, "#d4e6f1"],      
    [0.4, "#2980b9"],       
    [1.0, "#154360"]        
]


def generar_mapa_con_tabla(
    camara: str = 'Diputados',
    metrica_color: str = 'ints_per_capita',
    titulo: str = "Mapa del Debate Parlamentario en Diputados (Per Cápita)",
    subtitulo: str = "Intervenciones por diputado de cada jurisdicción (Nivelación formal)",
    label_barra: str = "Ints/Dip",
    archivo_salida: str = "mapa_provincias_con_tabla.html",
    es_senado: bool = False
):
    print(f"\n[+] Generando mapa interactivo para '{camara}' (Métrica: {metrica_color})...")
    df_metricas = calcular_metricas_provinciales_por_anio(
        df, camara=camara, usar_nombres_geojson=True
    )
    df_metricas['provincia'] = df_metricas['provincia'].replace({
        'Ciudad Autónoma de Buenos Aires': 'CABA',
        'Capital Federal': 'CABA'
    })

    grilla = pd.MultiIndex.from_product([anios, todas_las_provincias], names=['anio', 'provincia']).to_frame(index=False)
    df_final = pd.merge(grilla, df_metricas, on=['anio', 'provincia'], how='left').fillna(0)
    df_final = df_final.sort_values(by=['anio', 'provincia'])

    # Si es Diputados y bancas = 0 (provincias sin representación ese año), asegurar bancas históricas
    if camara == 'Diputados':
        df_final['bancas'] = df_final['provincia'].apply(obtener_bancas_diputados)
        df_final['pct_bancas'] = (df_final['bancas'] / float(TOTAL_BANCAS_DIPUTADOS)) * 100.0
    elif camara == 'Senadores':
        df_final['bancas'] = BANCAS_SENADORES_POR_PROVINCIA
        df_final['pct_bancas'] = (BANCAS_SENADORES_POR_PROVINCIA / 30.0) * 100.0

    max_z = df_final[metrica_color].max()
    if max_z <= 0:
        max_z = 10.0

    fig = go.Figure()
    frames = []
    slider_steps = []

    escala_color = azules_senado if es_senado else rojos_fuertes
    color_header = "#154360" if es_senado else "#E60000"

    hovertemplate_caba = (
        "<b style='font-size:16px;'>CABA (Capital Federal)</b><br><br>"
        "• Bancas: <b>%{customdata[0]}</b> (%{customdata[1]}% de la Cámara)<br>"
        "• Intervenciones Totales: <b>%{customdata[2]}</b> (%{customdata[3]}% del recinto)<br>"
        "• <b>Intervenciones / Diputado: %{marker.color:.2f}</b><br>"
        "• % Ponderado Per Cápita: <b>%{customdata[4]}%</b><br>"
        "• Ratio Intensidad (Voz/Bancas): <b>%{customdata[5]}x</b><extra></extra>"
        if not es_senado else
        "<b style='font-size:16px;'>CABA (Capital Federal)</b><br><br>"
        "• Bancas Senadores: <b>2</b> (6.7% de la Cámara)<br>"
        "• Intervenciones Totales: <b>%{customdata[2]}</b> (%{customdata[3]}% del debate)<br>"
        "• Intervenciones / Senador: <b>%{marker.color:.2f}</b><extra></extra>"
    )

    for anio in anios:
        df_anio = df_final[df_final['anio'] == anio].copy()
        
        # Datos para hover y tabla
        df_anio['custom_bancas'] = df_anio['bancas'].astype(int)
        df_anio['custom_pct_bancas'] = df_anio['pct_bancas'].round(1)
        df_anio['custom_ints'] = df_anio['ints'].astype(int)
        df_anio['custom_pct_ints'] = df_anio['pct_ints_bruto'].round(1)
        df_anio['custom_ints_pc'] = df_anio['ints_per_capita'].round(2)
        df_anio['custom_pct_pc'] = df_anio['pct_ints_per_capita'].round(1)
        df_anio['custom_ratio'] = df_anio['ratio_intensidad_ints'].round(2)

        customdata_mapa = df_anio[[
            'custom_bancas', 'custom_pct_bancas', 'custom_ints',
            'custom_pct_ints', 'custom_pct_pc', 'custom_ratio'
        ]].values

        # Datos específicos para CABA
        df_caba = df_anio[df_anio['provincia'] == 'CABA']
        caba_val = float(df_caba[metrica_color].values[0]) if not df_caba.empty else 0.0
        caba_custom = (
            df_caba[['custom_bancas', 'custom_pct_bancas', 'custom_ints', 'custom_pct_ints', 'custom_pct_pc', 'custom_ratio']].values
            if not df_caba.empty
            else [[32 if not es_senado else 2, 20.3 if not es_senado else 6.7, 0, 0, 0, 0]]
        )

        # Tabla: ordenar por métrica principal descendente
        df_tabla = df_anio[df_anio['ints'] > 0].sort_values(by=metrica_color, ascending=False)
        if df_tabla.empty:
            df_tabla = df_anio.head(5)

        t_provs = df_tabla['provincia'].tolist()
        t_bancas = [f"{int(b)}" for b in df_tabla['bancas']]
        t_ints = [f"{int(i):,}".replace(",", ".") for i in df_tabla['ints']]
        t_pc = [f"{v:.2f}" for v in df_tabla['ints_per_capita']]
        t_pct_bruto = [f"{v:.1f}%" for v in df_tabla['pct_ints_bruto']]
        t_ratio = [f"{v:.2f}x" for v in df_tabla['ratio_intensidad_ints']]

        if anio == 1929:
            # 1. Trace Coroplético
            fig.add_trace(
                go.Choropleth(
                    geojson=mapa_arg,
                    locations=df_anio['provincia'],
                    featureidkey='properties.nombre',
                    z=df_anio[metrica_color],
                    customdata=customdata_mapa,
                    colorscale=escala_color,
                    zmin=0, zmax=max_z,
                    marker_line_width=0.8,
                    marker_line_color='#2C3E50',
                    hovertemplate=(
                        "<b style='font-size:16px;'>%{location}</b><br><br>"
                        "• Bancas: <b>%{customdata[0]}</b> (%{customdata[1]}% de la Cámara)<br>"
                        "• Intervenciones Totales: <b>%{customdata[2]}</b> (%{customdata[3]}% del recinto)<br>"
                        "• <b>Intervenciones / Diputado: %{z:.2f}</b><br>"
                        "• % Ponderado Per Cápita: <b>%{customdata[4]}%</b><br>"
                        "• Ratio Intensidad (Voz/Bancas): <b>%{customdata[5]}x</b><extra></extra>"
                        if not es_senado else
                        "<b style='font-size:16px;'>%{location}</b><br><br>"
                        "• Bancas Senadores: <b>2</b> (6.7% de la Cámara)<br>"
                        "• Intervenciones Totales: <b>%{customdata[2]}</b> (%{customdata[3]}% del debate)<br>"
                        "• Intervenciones / Senador: <b>%{z:.2f}</b><extra></extra>"
                    ),
                    colorbar=dict(
                        title=f"<b>{label_barra}</b>",
                        thicknessmode="pixels", thickness=14,
                        lenmode="pixels", len=210,
                        yanchor="middle", y=0.72,
                        x=0.88,
                        ticks="outside",
                        tickfont=dict(size=11)
                    )
                )
            )

            # 2. Trace Marcador Destacado CABA
            fig.add_trace(
                go.Scattergeo(
                    lon=[-58.3816],
                    lat=[-34.6037],
                    mode='markers+text',
                    text=['<b>CABA</b>'],
                    textposition='top right',
                    textfont=dict(size=12, color=color_header, family='Arial Black'),
                    marker=dict(
                        size=15,
                        color=[caba_val],
                        colorscale=escala_color,
                        cmin=0,
                        cmax=max_z,
                        line=dict(width=2.5, color='#ffffff')
                    ),
                    customdata=caba_custom,
                    hovertemplate=hovertemplate_caba,
                    showlegend=False,
                    name='CABA'
                )
            )

            # 3. Trace Tabla Enriquecida Inferior
            columnas_header = (
                ["<b>Provincia</b>", "<b>Bancas</b>", "<b>Total Ints</b>", "<b>Ints / Diputado</b>", "<b>% Voz Real</b>", "<b>Ratio Intensidad</b>"]
                if not es_senado else
                ["<b>Provincia</b>", "<b>Bancas</b>", "<b>Total Ints</b>", "<b>Ints / Senador</b>", "<b>% Voz Real</b>"]
            )
            valores_celdas = (
                [t_provs, t_bancas, t_ints, t_pc, t_pct_bruto, t_ratio]
                if not es_senado else
                [t_provs, t_bancas, t_ints, t_pc, t_pct_bruto]
            )

            fig.add_trace(
                go.Table(
                    header=dict(
                        values=columnas_header,
                        fill_color=color_header,
                        align="center",
                        font=dict(color="white", size=12, family="Arial Black"),
                        height=28
                    ),
                    cells=dict(
                        values=valores_celdas,
                        fill_color="#F4F6F8",
                        align=["left", "center", "center", "center", "center", "center"] if not es_senado else ["left", "center", "center", "center", "center"],
                        font=dict(color="#2C3E50", size=11),
                        height=22
                    ),
                    domain=dict(x=[0.04, 0.96], y=[0.02, 0.35]) 
                )
            )

        # Frame de actualización
        frame_valores_celdas = (
            [t_provs, t_bancas, t_ints, t_pc, t_pct_bruto, t_ratio]
            if not es_senado else
            [t_provs, t_bancas, t_ints, t_pc, t_pct_bruto]
        )

        frame = go.Frame(
            data=[
                go.Choropleth(
                    locations=df_anio['provincia'],
                    z=df_anio[metrica_color],
                    customdata=customdata_mapa
                ),
                go.Scattergeo(
                    marker=dict(
                        size=15,
                        color=[caba_val],
                        colorscale=escala_color,
                        cmin=0,
                        cmax=max_z,
                        line=dict(width=2.5, color='#ffffff')
                    ),
                    customdata=caba_custom,
                    hovertemplate=hovertemplate_caba
                ),
                go.Table(cells=dict(values=frame_valores_celdas))
            ],
            traces=[0, 1, 2],
            name=str(anio)
        )
        frames.append(frame)

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

    sliders = [dict(
        active=0,
        y=0.41,
        yanchor="bottom",
        x=0.12,
        len=0.76,
        currentvalue=dict(
            font=dict(size=18, color=color_header, family="Arial Black"),
            prefix="Año Legislativo: "
        ),
        pad={"t": 15, "b": 10},
        steps=slider_steps,
        bgcolor="rgba(44, 62, 80, 0.6)",
        bordercolor="#2C3E50"
    )]

    fig.update_geos(
        scope="south america",
        visible=False,
        lataxis_range=[-55.5, -21.0], 
        lonaxis_range=[-74.0, -53.0],
        projection_type="mercator",
        domain=dict(x=[0.02, 0.98], y=[0.50, 0.95])
    )

    fig.update_layout(
        height=1250, 
        margin=dict(l=30, r=30, t=90, b=25),
        plot_bgcolor="rgba(255, 255, 255, 1)",
        paper_bgcolor="rgba(255, 255, 255, 1)",
        font=dict(family="Arial", color="#2C3E50"),
        title=f"<b>{titulo}</b><br><sup style='color:#7f8c8d; font-size:14px;'>{subtitulo}</sup>",
        title_x=0.5,
        title_font_size=23,
        sliders=sliders,
        updatemenus=[]
    )

    html_bruto = fig.to_html(include_plotlyjs='cdn')
    html_limpio = html_bruto.replace("Plotly.animate(", "//Plotly.animate(")

    ruta_salida = os.path.join(dir_graficos, archivo_salida)
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        f.write(html_limpio)

    print(f" [OK] Mapa guardado exitosamente: '{archivo_salida}'")


# 1. Mapa en Diputados: NORMALIZADO PER CÁPITA
generar_mapa_con_tabla(
    camara='Diputados',
    metrica_color='ints_per_capita',
    titulo="Mapa del Debate en Diputados: Intervenciones Per Cápita (1929-1939)",
    subtitulo="Intensidad discursiva normalizada por número de bancas de cada jurisdicción",
    label_barra="Ints / Diputado",
    archivo_salida="mapa_provincias_diputados_per_capita.html",
    es_senado=False
)

# 2. Mapa en Senado (2 senadores por provincia)
generar_mapa_con_tabla(
    camara='Senadores',
    metrica_color='ints_per_capita',
    titulo="Mapa del Debate en el Senado de la Nación (1929-1939)",
    subtitulo="Distribución territorial equitativa: 2 senadores por jurisdicción",
    label_barra="Ints / Senador",
    archivo_salida="mapa_provincias_senadores.html",
    es_senado=True
)

print("\n¡Proceso de mapa_interactivo.py finalizado con éxito!")
