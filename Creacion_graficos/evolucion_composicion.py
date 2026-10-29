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
print(" EVOLUCIÓN DE COMPOSICIÓN PARLAMENTARIA ACTIVA    ")
print(" (1929-1939) - Diputados y Senadores              ")
print("==================================================")

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
        labels={'representantes_activos': 'Nº de Legisladores Activos', 'partido': 'Partido Político', 'anio': 'Año'},
        template="plotly_white",
        text="representantes_activos"
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

    ruta_archivo = os.path.join(dir_graficos, archivo_salida)
    fig.write_html(ruta_archivo, include_plotlyjs='cdn')
    print(f" [OK] Archivo generado: '{archivo_salida}'")


print("\n[+] Generando gráficos interactivos de composición por cámara...")

df_diputados = df_agrupado[df_agrupado['rol'] == 'Diputado']
df_senadores = df_agrupado[df_agrupado['rol'] == 'Senador']

generar_html_animado(df_diputados, "Cámara de Diputados", "composicion_activa_diputados.html")
generar_html_animado(df_senadores, "Senado", "composicion_activa_senadores.html")

print("\n¡Proceso de evolucion_composicion.py finalizado con éxito!")
