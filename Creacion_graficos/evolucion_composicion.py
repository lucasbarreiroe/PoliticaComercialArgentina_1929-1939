import os
import sys
import pandas as pd
import plotly.express as px

ruta_padre = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ruta_padre)

from database_connection import supabase

todas_las_filas = []
inicio = 0
tamaño_lote = 1000

while True:
    respuesta = supabase.table("intervenciones") \
        .select("id_parlamentario, sesiones(fecha), parlamentarios(partido_politico, rol)") \
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
        fila["rol"] = parla_data.get("rol", "Desconocido") 
        
        if "sesiones" in fila:
            del fila["sesiones"]
        if "parlamentarios" in fila:
            del fila["parlamentarios"]
            
    todas_las_filas.extend(filas)
    inicio += tamaño_lote
    print(f"Descargados {len(todas_las_filas)} registros...")

df = pd.DataFrame(todas_las_filas)

print("\nProcesando participación única por año...")
df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
df['anio'] = df['fecha'].dt.year
df = df.dropna(subset=['anio'])
df['anio'] = df['anio'].astype(int)

df = df[(df['anio'] >= 1929) & (df['anio'] <= 1939)]
df = df[~df['partido'].isin(['No Identificado', 'NO IDENTIFICADO / FUNCIONARIO'])]

df_unicos = df.drop_duplicates(subset=['anio', 'rol', 'id_parlamentario', 'partido'])

df_agrupado = df_unicos.groupby(['anio', 'rol', 'partido']).size().reset_index(name='representantes_activos')

def generar_html_animado(df_camara, nombre_camara, archivo_salida):
    if df_camara.empty:
        print(f"No hay datos suficientes para {nombre_camara}.")
        return

    df_camara = df_camara.sort_values(['anio', 'representantes_activos'], ascending=[True, False])
    df_top5 = df_camara.groupby('anio').head(10).reset_index(drop=True)

    años_posibles = range(1929, 1940)
    partidos_top_historico = df_top5['partido'].unique()
    
    grilla = pd.MultiIndex.from_product([años_posibles, partidos_top_historico], names=['anio', 'partido']).to_frame(index=False)
    df_final = pd.merge(grilla, df_top5, on=['anio', 'partido'], how='left').fillna(0)
    df_final = df_final.sort_values(by=['anio', 'representantes_activos'], ascending=[True, False])

    max_y = df_final['representantes_activos'].max() * 1.1 

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
        template="plotly_white"
    )

    fig.update_layout(
        xaxis={'categoryorder': 'total descending'},
        margin=dict(l=50, r=50, t=80, b=150),
        updatemenus=[dict(
            type="buttons", 
            showactive=False,
            y=1.15, 
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

    fig.write_html(archivo_salida)
    print(f" [✓] Archivo generado: '{archivo_salida}'")

# ==========================================
# 4. EJECUCIÓN POR CÁMARAS
# ==========================================
print("Generando gráficos interactivos...")

# Filtramos usando la columna 'rol'
df_diputados = df_agrupado[df_agrupado['rol'] == 'Diputado']
df_senadores = df_agrupado[df_agrupado['rol'] == 'Senador']

generar_html_animado(df_diputados, "Cámara de Diputados", "composicion_activa_diputados.html")
generar_html_animado(df_senadores, "Senado", "composicion_activa_senadores.html")

print("\n¡Proceso finalizado con éxito!")