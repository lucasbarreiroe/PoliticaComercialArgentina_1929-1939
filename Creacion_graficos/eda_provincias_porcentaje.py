import os
import sys
import re
import pandas as pd
import plotly.express as px

# Crear carpeta de gráficos si no existe
os.makedirs("graficos", exist_ok=True)

ruta_padre = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ruta_padre)

from database_connection import supabase

print("==================================================")
print("  GENERADOR DE PORCENTAJES PROVINCIALES (ESTILIZADO) ")
print("==================================================")

print("[+] Descargando textos y datos de parlamentarios...")
todas_las_filas = []
inicio = 0
tamaño_lote = 1000

while True:
    respuesta = supabase.table("intervenciones") \
        .select("id_intervencion, texto_gemini, texto_limpio, sesiones(fecha), parlamentarios(partido_politico, distrito_provincia)") \
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
    print(f"  ... Descargados {len(todas_las_filas)} registros...")

df = pd.DataFrame(todas_las_filas)

print("\n[+] Limpiando ruido procedimental y procesando fechas...")

def obtener_texto_final(row):
    t_gemini = row.get('texto_gemini')
    t_limpio = row.get('texto_limpio')
    
    t_gemini = '' if pd.isna(t_gemini) or t_gemini is None else str(t_gemini).strip()
    t_limpio = '' if pd.isna(t_limpio) or t_limpio is None else str(t_limpio).strip()
    
    if t_gemini and t_gemini != 'OMITIDO_POR_LARGO':
        return t_gemini
    return t_limpio

df['texto_final'] = df.apply(obtener_texto_final, axis=1)
df = df[df['texto_final'] != '']

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
    t_lower = str(row['texto_final']).lower()
    if row['partido'] not in ["No Identificado", "NO IDENTIFICADO / FUNCIONARIO"]: return row['partido']
    for p in patrones:
        if re.search(p, t_lower): return "Trámite"
    return "No Identificado (Real)"

df['partido_limpio'] = df.apply(clasificar_intervencion, axis=1)

df_politico = df[~df['partido_limpio'].isin(["Trámite", "No Identificado (Real)"])]
df_provs = df_politico[df_politico['provincia'] != 'No Identificada']

print("[+] Calculando porcentajes por año...")

df_prov = df_provs.groupby(['anio', 'provincia']).size().reset_index(name='ints_provincia')
totales_anio = df_prov.groupby('anio')['ints_provincia'].sum().reset_index(name='ints_totales_anio')

df_prov = pd.merge(df_prov, totales_anio, on='anio')
df_prov['pct_intervenciones'] = (df_prov['ints_provincia'] / df_prov['ints_totales_anio']) * 100

df_prov = df_prov.sort_values(['anio', 'pct_intervenciones'], ascending=[True, False])
df_prov_top10 = df_prov.groupby('anio').head(10).reset_index(drop=True)

anios = range(1929, 1940)
provs_top = df_prov_top10['provincia'].unique()
grilla_prov = pd.MultiIndex.from_product([anios, provs_top], names=['anio', 'provincia']).to_frame(index=False)

df_final = pd.merge(grilla_prov, df_prov_top10, on=['anio', 'provincia'], how='left').fillna(0)
df_final = df_final.sort_values(by=['anio', 'pct_intervenciones'], ascending=[True, False])

df_final['texto_mostrar'] = df_final['pct_intervenciones'].apply(lambda x: f"{x:.1f}%" if x > 0 else "")

print("\n[+] Generando archivo HTML de alto impacto visual...")

max_y = df_final['pct_intervenciones'].max() * 1.25
colores_vibrantes = px.colors.qualitative.Bold + px.colors.qualitative.Vivid

fig = px.bar(
    df_final, 
    x="provincia", 
    y="pct_intervenciones", 
    color="provincia", 
    animation_frame="anio", 
    animation_group="provincia",
    range_y=[0, max_y], 
    title="<b>Composición Porcentual del Debate por Provincias (1929-1939)</b><br><sup style='color:#7f8c8d'>¿Quién dominaba la palabra en el Congreso Nacional?</sup>",
    labels={'pct_intervenciones': '% de Participación', 'provincia': '', 'anio': 'Año Legislativo'},
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

# BLOQUEAMOS TRANSICIONES (cambios instantáneos) Y EL BOTÓN DE PLAY
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

# GENERAR Y MODIFICAR EL HTML PARA ELIMINAR EL AUTOPLAY (La "magia" para que no empiece a correr)
html_bruto = fig.to_html(include_plotlyjs='cdn')
html_limpio = html_bruto.replace("Plotly.animate(", "//Plotly.animate(")

archivo_salida = os.path.join("graficos", "porcentaje_intervenciones_provincias.html")
with open(archivo_salida, 'w', encoding='utf-8') as f:
    f.write(html_limpio)

print(f"[✓] ¡Boom! Gráfico generado y SIN AUTOPLAY: '{archivo_salida}'")