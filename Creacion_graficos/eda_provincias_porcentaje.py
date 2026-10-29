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
from bancas_diputados import (
    cargar_datos_intervenciones,
    calcular_metricas_provinciales_por_anio,
    TOTAL_BANCAS_DIPUTADOS,
    BANCAS_SENADORES_POR_PROVINCIA
)

print("==================================================")
print("  GENERADOR DE PORCENTAJES PROVINCIALES (ESTILIZADO)")
print("  Normalización Per Cápita en Cámara de Diputados  ")
print("==================================================")

df = cargar_datos_intervenciones(supabase)

anios = range(1929, 1940)
colores_vibrantes = px.colors.qualitative.Bold + px.colors.qualitative.Vivid

def construir_grafico_estilizado(df_plot, y_col, titulo, subtitulo, label_y, archivo_salida, formato_texto=None, y_max_fijo=None):
    max_y = y_max_fijo if y_max_fijo else (df_plot[y_col].max() * 1.25 if not df_plot.empty and df_plot[y_col].max() > 0 else 10)
    
    if formato_texto:
        df_plot['texto_mostrar'] = df_plot[y_col].apply(formato_texto)
    else:
        df_plot['texto_mostrar'] = df_plot[y_col].apply(lambda x: f"{x:.1f}%" if x > 0 else "")

    fig = px.bar(
        df_plot, 
        x="provincia", 
        y=y_col, 
        color="provincia", 
        animation_frame="anio", 
        animation_group="provincia",
        range_y=[0, max_y], 
        title=f"<b>{titulo}</b><br><sup style='color:#7f8c8d'>{subtitulo}</sup>",
        labels={y_col: label_y, 'provincia': '', 'anio': 'Año Legislativo'},
        color_discrete_sequence=colores_vibrantes,
        text="texto_mostrar"
    )

    fig.update_traces(
        textposition='outside', 
        textfont=dict(size=14, family='Arial Black', color='#2C3E50'), 
        cliponaxis=False,
        marker_line_width=1.5,
        marker_line_color='#2C3E50',
        opacity=0.9
    )

    fig.update_layout(
        xaxis={'categoryorder': 'total descending', 'showgrid': False, 'tickfont': dict(size=13, family='Arial', color='#2C3E50'), 'tickangle': -45},
        yaxis={'showgrid': True, 'gridcolor': 'rgba(200, 200, 200, 0.4)', 'gridwidth': 1, 'tickfont': dict(color='#7f8c8d')},
        margin=dict(l=60, r=60, t=100, b=120),
        plot_bgcolor="rgba(255, 255, 255, 1)",
        paper_bgcolor="rgba(244, 246, 248, 1)",
        font=dict(family="Arial", color="#2C3E50"),
        title_x=0.5,
        title_font_size=24,
        showlegend=False,
        transition=dict(duration=0) 
    )

    fig.layout.updatemenus = []
    if fig.layout.sliders:
        for step in fig.layout.sliders[0].steps:
            step.args[1]["transition"]["duration"] = 0
            step.args[1]["frame"]["duration"] = 0
            
        slider = fig.layout.sliders[0]
        slider.currentvalue.font.color = "#E74C3C"
        slider.currentvalue.font.size = 24
        slider.currentvalue.font.family = "Arial Black"
        slider.currentvalue.prefix = "Año Activo: "
        slider.bgcolor = "rgba(41, 128, 185, 0.6)"
        slider.bordercolor = "#2C3E50"

    # Eliminar autoplay en HTML para consistencia
    html_bruto = fig.to_html(include_plotlyjs='cdn')
    html_limpio = html_bruto.replace("Plotly.animate(", "//Plotly.animate(")

    ruta_salida = os.path.join(dir_graficos, archivo_salida)
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        f.write(html_limpio)

    print(f" [OK] Generado: '{archivo_salida}'")


# ==============================================================
# 1. CÁMARA DE DIPUTADOS: CÁLCULO NORMALIZADO PER CÁPITA
# ==============================================================
print("\n[+] Calculando porcentajes para CÁMARA DE DIPUTADOS...")
df_dip = calcular_metricas_provinciales_por_anio(df, camara='Diputados')

todas_provs_dip = df_dip['provincia'].unique()
grilla_dip = pd.MultiIndex.from_product([anios, todas_provs_dip], names=['anio', 'provincia']).to_frame(index=False)
df_dip_completo = pd.merge(grilla_dip, df_dip, on=['anio', 'provincia'], how='left').fillna(0)

# A. Gráfico Principal Normalizado Per Cápita (Participación ponderada por diputado)
construir_grafico_estilizado(
    df_plot=df_dip_completo,
    y_col='pct_ints_per_capita',
    titulo="Composición Porcentual Per Cápita en Diputados (1929-1939)",
    subtitulo="Participación normalizada por número de diputados de c/jurisdicción (Nivelación del peso provincial)",
    label_y="% Participación Per Cápita",
    archivo_salida="porcentaje_provincias_diputados_per_capita.html"
)

# B. Ratio de Intensidad Discursiva (% Voz Real / % Bancas)
# 1.0 = Habla en proporción exacta a sus bancas; > 1.0 = Hiperactivo; < 1.0 = Subrepresentado
construir_grafico_estilizado(
    df_plot=df_dip_completo,
    y_col='ratio_intensidad_ints',
    titulo="Ratio de Sobrerrepresentación en Diputados (1929-1939)",
    subtitulo="Voz Real en Recinto (% Intervenciones) sobre Representación Formal (% Bancas) [Equilibrio = 1.0x]",
    label_y="Ratio (Voz / Bancas)",
    archivo_salida="porcentaje_provincias_diputados_ratio.html",
    formato_texto=lambda v: f"{v:.2f}x" if v > 0 else ""
)


# ==============================================================
# 2. CÁMARA DE SENADORES: 2 BANCAS POR JURISDICCIÓN
# ==============================================================
print("\n[+] Calculando porcentajes para CÁMARA DE SENADORES...")
df_sen = calcular_metricas_provinciales_por_anio(df, camara='Senadores')

todas_provs_sen = df_sen['provincia'].unique()
grilla_sen = pd.MultiIndex.from_product([anios, todas_provs_sen], names=['anio', 'provincia']).to_frame(index=False)
df_sen_completo = pd.merge(grilla_sen, df_sen, on=['anio', 'provincia'], how='left').fillna(0)

construir_grafico_estilizado(
    df_plot=df_sen_completo,
    y_col='pct_ints_bruto',
    titulo="Composición Porcentual del Debate en el Senado (1929-1939)",
    subtitulo="En el Senado cada jurisdicción posee exactamente 2 bancas (distribución equitativa)",
    label_y="% de Intervenciones en el Senado",
    archivo_salida="porcentaje_provincias_senadores.html"
)

print("\n¡Proceso de eda_provincias_porcentaje.py finalizado con éxito!")
