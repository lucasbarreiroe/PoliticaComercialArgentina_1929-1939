# El Giro en la Política Comercial Argentina entre Crisis (1929–1939)

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![UNSAM](https://img.shields.io/badge/UNSAM-Ciencia%20de%20Datos-004B87?style=for-the-badge)](https://www.unsam.edu.ar/)
[![CONICET](https://img.shields.io/badge/CONICET-IIP--EPyG-1E3A8A?style=for-the-badge)](https://iip.unsam.edu.ar/)
[![Supabase](https://img.shields.io/badge/Database-Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
[![Plotly](https://img.shields.io/badge/Visualizaci%C3%B3n-Plotly%20HTML-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com/)

**Análisis de datos textuales, procesamiento de lenguaje natural y visualización interactiva sobre los debates del Congreso Nacional Argentino durante la década de 1930.**

</div>

---

## 📌 Contexto del Proyecto

* **Institución**: Universidad Nacional de San Martín (UNSAM) — Escuela de Ciencia y Tecnología (ECyT).
* **Marco de Investigación**: Instituto de Investigaciones Políticas (EPyG-UNSAM / CONICET).
* **Estudiante**: Lucas Barreiro ([lebarreiro@estudiantes.unsam.edu.ar](mailto:lebarreiro@estudiantes.unsam.edu.ar)).
* **Directora de Investigación**: Dra. Agustina Rayes (Investigadora Independiente CONICET / UNSAM).
* **Tutores Académicos**: Fabiana Taboada y Pablo Serrati.

---

## 🎯 Objetivo General

Estudiar los debates del Congreso Nacional Argentino vinculados a la política comercial exterior entre el inicio de la Gran Depresión (1929) y el estallido de la Segunda Guerra Mundial (1939). A través de técnicas de Ciencia de Datos y Procesamiento de Lenguaje Natural (NLP), se busca estructurar las fuentes documentales para analizar la participación por provincias, fuerzas políticas e instituciones de gobierno.

---

## 🔬 Metodología de Trabajo

1. **Extracción y Estructuración Documental**:
   Procesamiento de las actas taquigráficas históricas en formato PDF (diseño tradicional a doble columna), separando oradores, cámara (Diputados y Senadores), ministros del Poder Ejecutivo y representación distrital.

2. **Curaduría de Texto con Asistencia de IA**:
   Tratamiento de roturas de palabras y errores propios del escaneo y OCR histórico mediante modelos de lenguaje, incorporando scripts de validación para asegurar la fidelidad del texto original.

3. **Análisis Exploratorio y Ponderación Per Cápita**:
   Evaluación de la participación parlamentaria tanto en términos absolutos como ponderada por el número de bancas asignadas constitucionalmente a cada provincia, visualizada en series de tiempo y mapas coropléticos interactivos.

4. **Modelado de Tópicos (Topic Modeling)**:
   Aplicación de modelos de tópicos guiados para identificar los grandes ejes de discusión comercial (aranceles, tratados bilaterales como el Pacto Roca-Runciman, régimen cambiario y producción agropecuaria) y contrastar la prevalencia temática del Poder Ejecutivo frente a las cámaras legislativas.

---

## 📂 Estructura del Repositorio

A continuación se detalla la organización de los archivos actualmente disponibles en el repositorio:

```text
├── Arreglo_intervenciones/
│   └── curador_ia.py                 # Curaduría y saneamiento de texto de intervenciones
├── Creacion_graficos/
│   ├── graficos/                     # Visualizaciones interactivas en HTML (Plotly)
│   │   ├── animado_partidos_int_abs.html
│   │   ├── animado_partidos_pal_abs.html
│   │   ├── animado_partidos_relativo.html
│   │   ├── animado_provincias_diputados_per_capita_ints.html
│   │   ├── animado_provincias_diputados_per_capita_pals.html
│   │   ├── animado_provincias_diputados_relativo.html
│   │   ├── animado_provincias_senadores_int_abs.html
│   │   ├── animado_provincias_senadores_pal_abs.html
│   │   ├── composicion_activa_diputados.html
│   │   ├── composicion_activa_senadores.html
│   │   ├── evolucion_partidaria_1929_1939.html
│   │   ├── mapa_provincias_diputados_per_capita.html
│   │   ├── mapa_provincias_senadores.html
│   │   ├── porcentaje_provincias_diputados_per_capita.html
│   │   ├── porcentaje_provincias_diputados_ratio.html
│   │   ├── porcentaje_provincias_senadores.html
│   │   └── volumen_total_intervenciones.html
│   ├── bancas_diputados.py           # Diccionario histórico de bancas por distrito
│   ├── eda_provincias.py             # Análisis exploratorio provincial (absoluto y relativo)
│   ├── eda_provincias_porcentaje.py  # Participación provincial en términos proporcionales
│   ├── evolucion_composicion.py      # Análisis de la composición de las cámaras
│   ├── evolucion_partidaria.py       # Dinámica de los partidos políticos en el tiempo
│   ├── interv_totales.py             # Cálculo de totales y agregados del corpus
│   ├── mapa_interactivo.py           # Generación de mapas coropléticos con Plotly
│   └── provincias.geojson            # Geometrías de las provincias argentinas
├── extractor_avanzado.py             # Parser de actas parlamentarias a doble columna
├── extractor_provincias.py           # Asignación y normalización geográfica de oradores
├── curador_ia_gemini.py              # Curaduría de intervenciones asistida por IA
├── cazador_delirios.py               # Auditoría y control de calidad sobre texto curado
├── corrector_diputados.py            # Normalización de identidades de legisladores
├── corrector_intervenciones.py       # Estandarización y homogeneización de registros
├── database_connection.py            # Módulo de conexión a base de datos Supabase
├── .gitignore                        # Exclusiones de control de versiones
└── README.md                         # Documentación general del repositorio
```

---

## 🛠️ Requisitos e Instalación

### Requisitos Previos
* Python 3.10 o superior.
* Git.

### Configuración del Entorno

```bash
# Clonar el repositorio
git clone https://github.com/lucasbarreiroe/PoliticaComercialArgentina_1929-1939.git
cd PoliticaComercialArgentina_1929-1939

# Crear y activar entorno virtual
python -m venv venv

# En Windows PowerShell:
.\venv\Scripts\Activate.ps1
# En Linux/macOS:
source venv/bin/activate

# Instalar dependencias
pip install numpy pandas plotly supabase python-dotenv pymupdf
```

### Variables de Entorno (`.env`)
Para la conexión a la base de datos o utilidades de curaduría:

```env
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-clave-anon
GEMINI_API_KEY=tu-api-key-de-gemini  # Opcional para curador_ia
```

---

## 📊 Visualizaciones y Resultados

Los gráficos interactivos generados se encuentran en la carpeta [`Creacion_graficos/graficos/`](Creacion_graficos/graficos/) en formato HTML autocontenido (Plotly). Pueden abrirse directamente en cualquier navegador web para explorar:

* **Mapas provinciales per cápita**: Representación territorial de la actividad parlamentaria ajustada por bancas asignadas.
* **Evolución partidaria**: Trayectoria y volumen de discurso de los principales bloques a lo largo del período 1929–1939.
* **Composición activa de las cámaras**: Desglose anual de la participación de senadores y diputados.

---

## 📖 Fuentes de Datos

Los debates parlamentarios corresponden a transcripciones de acceso público de la **Biblioteca del Congreso de la Nación (BCN)**, digitalizadas con fines educativos, de divulgación e investigación histórica.

---

## ✉️ Contacto

* **Lucas Barreiro** — [lebarreiro@estudiantes.unsam.edu.ar](mailto:lebarreiro@estudiantes.unsam.edu.ar)
* **Dra. Agustina Rayes** — [arayes@unsam.edu.ar](mailto:arayes@unsam.edu.ar)
