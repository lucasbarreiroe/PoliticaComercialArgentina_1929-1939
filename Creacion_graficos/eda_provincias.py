import os
import sys
import re
import pandas as pd
import plotly.express as px

ruta_padre = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ruta_padre)

from database_connection import supabase

print("Descargando textos y datos de parlamentarios...")
todas_las_filas = []
inicio = 0
tamaño_lote = 1000

while True:
    respuesta = supabase.table("intervenciones") \
        .select("id_intervencion, id_parlamentario, texto_gemini, sesiones(fecha), parlamentarios(partido_politico, distrito_provincia)") \
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
        fila["provincia"] = parla_data.get("distrito_provincia", "No Identificada")
        
        if "sesiones" in fila: del fila["sesiones"]
        if "parlamentarios" in fila: del fila["parlamentarios"]
            
    todas_las_filas.extend(filas)
    inicio += tamaño_lote
    print(f"Descargados {len(todas_las_filas)} registros...")

df = pd.DataFrame(todas_las_filas)

print("\nLimpiando ruido procedimental y procesando fechas...")
df['texto_gemini'] = df['texto_gemini'].fillna('')
df['num_palabras'] = df['texto_gemini'].apply(lambda x: len(str(x).split()))

df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
df['anio'] = df['fecha'].dt.year
df = df.dropna(subset=['anio'])
df['anio'] = df['anio'].astype(int)
df = df[(df['anio'] >= 1929) & (df['anio'] <= 1939)]

patrones = [
    r"se va a votar", r"se votará", r"resulta afirmativa", r"resulta negativa",
    r"queda levantada la sesión", r"queda abierta la sesión", r"se lee el artículo",
    r"tiene la palabra", r"leyendo:", r"queda aprobado", r"a la comisión de",
    r"votan \d+ señores diputados", r"se va a dar cuenta", r"concederá la palabra", 
    r"orden del día", r"cuarto intermedio", r"asentimiento", r"se va a leer", 
    r"mándela a la papelera", r"prosecretario", r"secretario", r"comuníquese al poder ejecutivo", 
    r"dios guarde a vuestra honorabilidad", r"goce de dieta, la licencia", 
    r"no haciéndose observación", r"nada en discusión", r"el texto proporcionado está vacío"
]

def clasificar_intervencion(row):
    t_lower = str(row['texto_gemini']).lower()
    if row['partido'] not in ["No Identificado", "NO IDENTIFICADO / FUNCIONARIO"]: return row['partido']
    for p in patrones:
        if re.search(p, t_lower): return "Trámite"
    return "No Identificado (Real)"

df['partido_limpio'] = df.apply(clasificar_intervencion, axis=1)
df_politico = df[~df['partido_limpio'].isin(["Trámite", "No Identificado (Real)"])]

def generar_html(df_plot, x_col, y_col, color_col, titulo, archivo, barmode='relative', max_y_mult=1.1, label_y='Valor'):
    max_y = df_plot[y_col].max() * max_y_mult
    fig = px.bar(
        df_plot, x=x_col, y=y_col, color=color_col, 
        animation_frame="anio", animation_group=x_col,
        range_y=[0, max_y], title=titulo, barmode=barmode,
        labels={y_col: label_y, x_col: x_col.capitalize(), 'anio': 'Año'},
        template="plotly_white"
    )
    fig.update_layout(
        xaxis={'categoryorder': 'total descending'},
        margin=dict(l=50, r=50, t=80, b=150),
        updatemenus=[dict(
            type="buttons", showactive=False, y=1.15, x=0.05, xanchor="left", yanchor="top",
            buttons=[dict(label="Reproducir Evolución", method="animate", args=[None, dict(frame=dict(duration=1000, redraw=True), fromcurrent=True)])]
        )],
        sliders=[dict(y=1.1, x=0.2, len=0.75, xanchor="left", yanchor="top")]
    )
    fig.write_html(archivo)
    print(f" [✓] {archivo}")

df_part = df_politico.groupby(['anio', 'partido_limpio']).agg(ints=('id_intervencion', 'count'), pals=('num_palabras', 'sum')).reset_index()

totales_anio_part = df_part.groupby('anio').agg(tot_pals=('pals', 'sum')).reset_index()
df_part = pd.merge(df_part, totales_anio_part, on='anio')
df_part['pct_palabras'] = (df_part['pals'] / df_part['tot_pals']) * 100

df_unicos_part = df_politico.drop_duplicates(subset=['anio', 'id_parlamentario', 'partido_limpio'])
df_bancas = df_unicos_part.groupby(['anio', 'partido_limpio']).size().reset_index(name='bancas_activas')

# Calculamos el % de bancas sobre el total de legisladores que participaron ese año
totales_bancas_anio = df_bancas.groupby('anio').agg(tot_bancas=('bancas_activas', 'sum')).reset_index()
df_bancas = pd.merge(df_bancas, totales_bancas_anio, on='anio')
df_bancas['pct_bancas'] = (df_bancas['bancas_activas'] / df_bancas['tot_bancas']) * 100

# Unimos la métrica de palabras con la de bancas
df_part = pd.merge(df_part, df_bancas[['anio', 'partido_limpio', 'pct_bancas']], on=['anio', 'partido_limpio'], how='left')

df_part = df_part.sort_values(['anio', 'ints'], ascending=[True, False])
df_part_top10 = df_part.groupby('anio').head(10).reset_index(drop=True)

anios = range(1929, 1940)
partidos_top = df_part_top10['partido_limpio'].unique()
grilla_part = pd.MultiIndex.from_product([anios, partidos_top], names=['anio', 'partido_limpio']).to_frame(index=False)
df_part_final = pd.merge(grilla_part, df_part_top10, on=['anio', 'partido_limpio'], how='left').fillna(0)
df_part_final = df_part_final.sort_values(by=['anio', 'ints'], ascending=[True, False])

generar_html(df_part_final, 'partido_limpio', 'ints', 'partido_limpio', "Partidos: Intervenciones por Año (Absoluto)", "animado_partidos_int_abs.html", label_y="Nº Intervenciones")
generar_html(df_part_final, 'partido_limpio', 'pals', 'partido_limpio', "Partidos: Volumen de Palabras por Año (Absoluto)", "animado_partidos_pal_abs.html", label_y="Nº Palabras")

df_part_rel = df_part_final[['anio', 'partido_limpio', 'pct_bancas', 'pct_palabras']].melt(
    id_vars=['anio', 'partido_limpio'], value_vars=['pct_bancas', 'pct_palabras'], var_name='Métrica', value_name='Porcentaje'
)
df_part_rel['Métrica'] = df_part_rel['Métrica'].replace({'pct_bancas': '% Bancas Activas (Formal)', 'pct_palabras': '% Palabras (Real)'})
df_part_rel = df_part_rel.sort_values(by=['anio', 'partido_limpio', 'Métrica'])
generar_html(df_part_rel, 'partido_limpio', 'Porcentaje', 'Métrica', "Partidos: Representación Formal vs Voz Real por Año", "animado_partidos_relativo.html", barmode='group', max_y_mult=1.05)

print("Generando gráficos de Provincias...")
df_provs = df_politico[df_politico['provincia'] != 'No Identificada']
df_prov = df_provs.groupby(['anio', 'provincia']).agg(ints=('id_intervencion', 'count'), pals=('num_palabras', 'sum')).reset_index()

totales_anio_prov = df_prov.groupby('anio').agg(tot_ints=('ints', 'sum'), tot_pals=('pals', 'sum')).reset_index()
df_prov = pd.merge(df_prov, totales_anio_prov, on='anio')
df_prov['pct_ints'] = (df_prov['ints'] / df_prov['tot_ints']) * 100
df_prov['pct_pals'] = (df_prov['pals'] / df_prov['tot_pals']) * 100

df_prov = df_prov.sort_values(['anio', 'ints'], ascending=[True, False])
df_prov_top10 = df_prov.groupby('anio').head(10).reset_index(drop=True)

provs_top = df_prov_top10['provincia'].unique()
grilla_prov = pd.MultiIndex.from_product([anios, provs_top], names=['anio', 'provincia']).to_frame(index=False)
df_prov_final = pd.merge(grilla_prov, df_prov_top10, on=['anio', 'provincia'], how='left').fillna(0)
df_prov_final = df_prov_final.sort_values(by=['anio', 'ints'], ascending=[True, False])

generar_html(df_prov_final, 'provincia', 'ints', 'provincia', "Provincias: Intervenciones por Año (Absoluto)", "animado_provincias_int_abs.html", label_y="Nº Intervenciones")
generar_html(df_prov_final, 'provincia', 'pals', 'provincia', "Provincias: Volumen de Palabras por Año (Absoluto)", "animado_provincias_pal_abs.html", label_y="Nº Palabras")

df_prov_rel = df_prov_final[['anio', 'provincia', 'pct_ints', 'pct_pals']].melt(
    id_vars=['anio', 'provincia'], value_vars=['pct_ints', 'pct_pals'], var_name='Métrica', value_name='Porcentaje'
)
df_prov_rel['Métrica'] = df_prov_rel['Métrica'].replace({'pct_ints': '% Frecuencia de Habla', 'pct_pals': '% Volumen de Palabras'})
df_prov_rel = df_prov_rel.sort_values(by=['anio', 'provincia', 'Métrica'])
generar_html(df_prov_rel, 'provincia', 'Porcentaje', 'Métrica', "Provincias: Comportamiento Discursivo por Año (% Frecuencia vs % Volumen)", "animado_provincias_relativo.html", barmode='group', max_y_mult=1.05)

print("\n¡Proceso finalizado! Se generaron 6 archivos HTML interactivos en tu carpeta.")