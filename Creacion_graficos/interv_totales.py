import os
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import re

# ==========================================
# 1. CONFIGURACIÓN DE SUPABASE
# ==========================================
SUPABASE_URL = "https://ddrnsuylomdlbgoqezvz.supabase.co"
SUPABASE_KEY = "sb_secret_uc87xR1EcIAsE7LUe9TO_Q_uu8pSqVv"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 2. OBTENER DATOS DE LA BASE DE DATOS (CON PAGINACIÓN)
# ==========================================
def obtener_datos():
    print("Obteniendo datos masivos de Supabase (esto puede tardar unos segundos)...")
    
    # ⚠️ CAMBIA "fecha" POR EL NOMBRE EXACTO DE LA COLUMNA EN TU TABLA 'sesiones'
    nombre_columna_fecha = "fecha" 
    
    registros = []
    rango_inicio = 0
    tamaño_bloque = 1000 
    
    while True:
        # Hacemos la consulta paginada
        response = supabase.table("intervenciones") \
            .select(f"id_intervencion, sesiones({nombre_columna_fecha})") \
            .range(rango_inicio, rango_inicio + tamaño_bloque - 1) \
            .execute()
        
        data = response.data
        if not data:
            break
            
        for row in data:
            datos_sesion = row.get("sesiones")
            if datos_sesion and datos_sesion.get(nombre_columna_fecha):
                fecha_cruda = str(datos_sesion[nombre_columna_fecha])
                
                # Buscamos todos los números que empiecen con 19XX
                años_encontrados = re.findall(r'\b19\d{2}\b', fecha_cruda)
                
                if años_encontrados:
                    # Tomamos el ÚLTIMO año que aparezca en el texto
                    # Ej: "Acta 1921 del 4 de octubre de 1930" -> tomará "1930"
                    anio = años_encontrados[-1]
                    
                    # FILTRO ESTRICTO: Solo nos interesan los años de tu investigación
                    if 1929 <= int(anio) <= 1939:
                        registros.append({"anio": anio, "id_intervencion": row["id_intervencion"]})
        
        rango_inicio += tamaño_bloque
        print(f"  ... {len(registros)} registros extraídos y filtrados hasta ahora.")

    df = pd.DataFrame(registros)
    return df

# ==========================================
# 3. PROCESAR Y GRAFICAR DATOS
# ==========================================
def graficar(df):
    if df.empty:
        print("No se encontraron datos para graficar.")
        return

    # Contamos la cantidad de id_intervencion únicos agrupados por año
    df_agrupado = df.groupby("anio")["id_intervencion"].count().reset_index()
    
    # Renombramos la columna para mayor claridad
    df_agrupado = df_agrupado.rename(columns={"id_intervencion": "total_intervenciones"})
    
    # Nos aseguramos de que el año sea numérico para ordenar el eje X de menor a mayor
    df_agrupado['anio'] = pd.to_numeric(df_agrupado['anio'])
    df_agrupado = df_agrupado.sort_values(by="anio")

    print("\n¡Datos listos! Generando gráfico interactivo...")
    
    # Crear gráfico interactivo
    fig = px.bar(
        df_agrupado, 
        x="anio", 
        y="total_intervenciones", 
        title="Volumen Total de Intervenciones Parlamentarias por Año",
        labels={"anio": "Año Legislativo", "total_intervenciones": "Total de Intervenciones"},
        text="total_intervenciones",
        color="total_intervenciones",
        color_continuous_scale=px.colors.sequential.Viridis
    )
    
    # Mejorar el diseño del gráfico
    fig.update_traces(textposition='outside', textfont_size=12)
    fig.update_layout(
        xaxis=dict(tickmode='linear', dtick=1), # Fuerza a que se muestren todos los años en el eje X
        yaxis=dict(title="Cantidad Acumulada", range=[0, df_agrupado["total_intervenciones"].max() * 1.15]), # Da espacio extra arriba para el texto
        plot_bgcolor="rgba(245,245,245,0.8)",
        font=dict(size=14),
        margin=dict(t=50, b=50, l=50, r=50)
    )

    fig.show()

# ==========================================
# EJECUCIÓN
# ==========================================
if __name__ == "__main__":
    df_intervenciones = obtener_datos()
    graficar(df_intervenciones)