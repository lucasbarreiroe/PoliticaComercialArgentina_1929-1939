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
print(" VOLUMEN TOTAL DE INTERVENCIONES POR AÑO          ")
print("==================================================")

df = cargar_datos_intervenciones(supabase)

# Agrupar intervenciones por año
df_agrupado = df.groupby("anio")["id_intervencion"].count().reset_index()
df_agrupado = df_agrupado.rename(columns={"id_intervencion": "total_intervenciones"})
df_agrupado['anio'] = pd.to_numeric(df_agrupado['anio'])
df_agrupado = df_agrupado.sort_values(by="anio")

fig = px.bar(
    df_agrupado, 
    x="anio", 
    y="total_intervenciones", 
    title="<b>Volumen Total de Intervenciones Parlamentarias por Año (1929-1939)</b>",
    labels={"anio": "Año Legislativo", "total_intervenciones": "Total de Intervenciones"},
    text="total_intervenciones",
    color="total_intervenciones",
    color_continuous_scale=px.colors.sequential.Viridis
)

fig.update_traces(textposition='outside', textfont_size=12)
fig.update_layout(
    xaxis=dict(tickmode='linear', dtick=1),
    yaxis=dict(title="Cantidad Acumulada", range=[0, df_agrupado["total_intervenciones"].max() * 1.15]),
    plot_bgcolor="rgba(245,245,245,0.8)",
    font=dict(size=14),
    margin=dict(t=80, b=50, l=50, r=50)
)

ruta_archivo = os.path.join(dir_graficos, "volumen_total_intervenciones.html")
fig.write_html(ruta_archivo, include_plotlyjs='cdn')
print(f"[OK] Archivo generado exitosamente: '{ruta_archivo}'.")
