# El Giro en la Política Comercial Argentina entre Crisis (1929–1939)

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![UNSAM](https://img.shields.io/badge/UNSAM-Ciencia%20de%20Datos-004B87?style=for-the-badge)](https://www.unsam.edu.ar/)
[![CONICET](https://img.shields.io/badge/CONICET-IIP--EPyG-1E3A8A?style=for-the-badge)](https://iip.unsam.edu.ar/)
[![Supabase](https://img.shields.io/badge/Database-Supabase%20PostgreSQL%203NF-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
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

1. **Extracción y Estructuración Documental (3NF)**:
   Procesamiento de los 209 tomos de actas taquigráficas históricas en formato PDF (diseño tradicional a doble columna), desagregando las **1.282 sesiones parlamentarias individuales** con su fecha exacta (`YYYY-MM-DD`), separando oradores, cámara (Diputados y Senadores), ministros del Poder Ejecutivo y representación distrital bajo un modelo relacional estricto en **Tercera Forma Normal (3NF)**.

2. **Curaduría de Texto con Asistencia de IA**:
   Tratamiento de roturas de palabras y errores propios del escaneo y OCR histórico mediante modelos de lenguaje y heurísticas de expresión regular, preservando tanto el texto canónico curado como las versiones alternativas de procesamiento.

3. **Reconocimiento de Entidades Nombradas (NER) y Postura Ideológica (ABSA)**:
   Detección automatizada de instituciones económicas oficiales y corporativas (BCRA, Juntas Reguladoras, SRA, UIA, CAC, CARBAP, FAA), socios comerciales (Reino Unido, Estados Unidos, Alemania) y tratados (Pacto Roca-Runciman, Conferencia de Ottawa), evaluando la polaridad y postura argumentativa (*Aspect-Based Sentiment Analysis*) de cada intervención.

4. **Análisis Exploratorio y Ponderación Per Cápita**:
   Evaluación de la participación parlamentaria tanto en términos absolutos como ponderada por el número de bancas asignadas constitucionalmente a cada provincia, visualizada en series de tiempo y mapas coropléticos interactivos.

5. **Modelado de Tópicos (Topic Modeling)**:
   Aplicación de modelos de tópicos guiados para identificar los grandes ejes de discusión comercial (aranceles, tratados bilaterales, régimen cambiario y producción agropecuaria) y contrastar la prevalencia temática del Poder Ejecutivo frente a las cámaras legislativas.

---

## 🗄️ Estructura de la Base de Datos en Supabase

La base de datos en **Supabase (PostgreSQL)** está organizada en **Tercera Forma Normal (3NF)** a través de **13 tablas** distribuidas en **5 subsistemas** (catálogos invariantes, estructura institucional, publicaciones y sesiones, normas y proyectos, y debate parlamentario). Por su parte, el Reconocimiento de Entidades Nombradas (NER) y la generación del dashboard interactivo operan como un módulo analítico independiente en Python sobre los datos de estas tablas.

---

### Diagrama Entidad-Relación (DER)

```mermaid
erDiagram
    PROVINCIAS ||--o{ MANDATOS_LEGISLATIVOS : "representa (id_provincia)"
    PARTIDOS_POLITICOS ||--o{ MANDATOS_LEGISLATIVOS : "pertenece a (id_partido)"
    PERSONAS ||--o{ MANDATOS_LEGISLATIVOS : "ejerce (id_persona)"

    TOMOS_DIARIOS_SESIONES ||--o{ SESIONES : "contiene (id_tomo)"
    SESIONES ||--o{ SESIONES_AUTORIDADES : "presidida por (id_sesion)"
    PERSONAS ||--o{ SESIONES_AUTORIDADES : "actua como autoridad (id_persona)"
    SESIONES ||--o{ SESION_SUMARIOS : "indexa (id_sesion)"

    SESIONES ||--o{ INICIATIVAS_LEGISLATIVAS : "trata en recinto (id_sesion)"
    SESION_SUMARIOS |o--o{ INICIATIVAS_LEGISLATIVAS : "origina en sumario (id_sumario)"
    LEYES |o--o{ INICIATIVAS_LEGISLATIVAS : "sanciona o modifica (id_ley_sancionada)"
    INICIATIVAS_LEGISLATIVAS ||--o{ ARTICULOS_INICIATIVA : "desglosa en (id_iniciativa)"

    SESIONES ||--o{ INTERVENCIONES : "registra discurso (id_sesion)"
    PERSONAS ||--o{ INTERVENCIONES : "pronunciado por (id_persona)"
    MANDATOS_LEGISLATIVOS |o--o{ INTERVENCIONES : "bajo banca o cargo (id_mandato)"
    SESION_SUMARIOS |o--o{ INTERVENCIONES : "sobre tema (id_sumario)"

    INTERVENCIONES ||--o{ INTERVENCIONES_LEYES_MENCIONADAS : "cita norma (id_intervencion)"
    LEYES ||--o{ INTERVENCIONES_LEYES_MENCIONADAS : "es citada en (id_ley)"

    PROVINCIAS {
        int id_provincia PK
        varchar nombre UK
        varchar codigo_indec
        varchar region_geografica
        boolean es_territorio_nacional
    }

    PARTIDOS_POLITICOS {
        int id_partido PK
        varchar nombre_oficial UK
        varchar sigla
        varchar coalicion_general
        boolean es_oficialista_decada_30
    }

    PERSONAS {
        int id_persona PK
        varchar nombre
        varchar apellido
        varchar nombre_completo UK
        text link_biografia
    }

    MANDATOS_LEGISLATIVOS {
        int id_mandato PK
        int id_persona FK
        varchar camara
        varchar cargo_especifico
        int id_provincia FK
        int id_partido FK
        int anio_inicio
        int anio_fin
    }

    TOMOS_DIARIOS_SESIONES {
        int id_tomo PK
        varchar codigo_tomo UK
        varchar camara
        int anio_legislativo
        varchar numero_tomo
        text archivo_pdf_origen
    }

    SESIONES {
        int id_sesion PK
        int id_tomo FK
        varchar numero_reunion
        date fecha_exacta
        varchar tipo_sesion
        varchar periodo_legislativo
        varchar presidente_texto_origen
        text observaciones
    }

    SESIONES_AUTORIDADES {
        int id_sesion PK, FK
        int id_persona PK, FK
        varchar rol_presidencia PK
    }

    SESION_SUMARIOS {
        int id_sumario PK
        int id_sesion FK
        varchar seccion_sumario
        text titulo_tema
        text pagina_referencia
    }

    LEYES {
        int id_ley PK
        varchar numero_ley UK
        int numero_entero
        int anio_sancion
        date fecha_promulgacion
        text denominacion
    }

    INICIATIVAS_LEGISLATIVAS {
        int id_iniciativa PK
        int id_sesion FK
        int id_sumario FK
        int id_ley_sancionada FK
        varchar tipo_iniciativa
        varchar instancia_legislativa
        int orden_en_sesion
        text titulo_iniciativa
        text resumen_sumario
    }

    ARTICULOS_INICIATIVA {
        int id_articulo PK
        int id_iniciativa FK
        int orden_articulo
        varchar etiqueta_articulo
        text texto_articulo
    }

    INTERVENCIONES {
        int id_intervencion PK
        int id_sesion FK
        int id_persona FK
        int id_mandato FK
        int id_sumario FK
        int orden_dialogo
        int nro_pagina
        varchar nombre_extraido_ocr
        text texto_canonico
    }

    INTERVENCIONES_LEYES_MENCIONADAS {
        int id_intervencion PK, FK
        int id_ley PK, FK
    }
```

---

### Detalle de las 13 Tablas de la Base de Datos en Supabase

| # | Subsistema | Tabla en Supabase (`public`) | Clave Primaria (PK) | Claves Foráneas (FK) | Registros Verificados | Propósito en la Base de Datos |
| :-: | :--- | :--- | :--- | :--- | --: | :--- |
| **01** | **1. Catálogos** | `provincias` | `id_provincia` | — | **15** | Provincias históricas y Capital Federal normalizadas con código INDEC y región geográfica. |
| **02** | **1. Catálogos** | `partidos_politicos` | `id_partido` | — | **25** | Fuerzas políticas unificadas de la década de 1930, sigla y mapeo a coalición (`Concordancia`, `UCR`, `PS`, etc.). |
| **03** | **1. Catálogos** | `personas` | `id_persona` | — | **586** | Padrón depurado de personas físicas (legisladores, ministros del PE y autoridades de cámara). |
| **04** | **2. Institucional** | `mandatos_legislativos` | `id_mandato` | `id_persona`, `id_provincia`, `id_partido` | **744** | Bancas y cargos temporales ejercidos por cada persona (`camara`, `cargo_especifico`, `anio_inicio`, `anio_fin`). |
| **05** | **3. Sesiones** | `tomos_diarios_sesiones` | `id_tomo` | — | **209** | Volúmenes físicos/PDF de los *Diarios de Sesiones* (`1929` a `1939`). |
| **06** | **3. Sesiones** | `sesiones` | `id_sesion` | `id_tomo` | **1.282** | Reuniones parlamentarias individuales extraídas de los PDFs con su `fecha_exacta` (`YYYY-MM-DD`). |
| **07** | **3. Sesiones** | `sesiones_autoridades` | `(id_sesion, id_persona, rol_presidencia)` | `id_sesion`, `id_persona` | **1.276** | Autoridades que presidieron cada sesión parlamentaria. |
| **08** | **3. Sesiones** | `sesion_sumarios` | `id_sumario` | `id_sesion` | **7.469** | Entradas del índice/sumario temático de cada sesión vinculadas a su reunión. |
| **09** | **4. Normas y Proyectos** | `leyes` | `id_ley` | — | **2.136** | Catálogo de leyes nacionales: las **1.087 leyes sancionadas en 1929–1939** (`11.544` a `12.630`) + **1.049 leyes históricas pre-1929** (`48` a `11.543`). |
| **10** | **4. Normas y Proyectos** | `iniciativas_legislativas` | `id_iniciativa` | `id_sesion`, `id_ley_sancionada` | **9.669** | Cabecera deduplicada de proyectos de ley, despachos en recinto y las 1.087 leyes sancionadas. |
| **11** | **4. Normas y Proyectos** | `articulos_iniciativa` | `id_articulo` | `id_iniciativa` | **50.329** | Desglose individual artículo por artículo (`Art. 1°`, `Art. 2°`, etc.) de cada iniciativa y ley sancionada. |
| **12** | **5. Debate Parlamentario** | `intervenciones` | `id_intervencion` | `id_sesion`, `id_persona`, `id_mandato`, `id_sumario` | **64.636** | Universo completo de intervenciones parlamentarias vinculadas a su sesión, página, fecha exacta y orador. |
| **13** | **5. Debate Parlamentario** | `intervenciones_leyes_mencionadas` | `(id_intervencion, id_ley)` | `id_intervencion`, `id_ley` | **8.563** | Tabla puente que registra cada ley nacional citada dentro de una intervención. |

---

## 📂 Estructura del Repositorio

A continuación se detalla la organización limpia y modular del repositorio:

```text
├── curacion_intervenciones/
│   └── curador_ia.py                     # Curaduría y saneamiento de texto de intervenciones
├── Creacion_graficos/
│   ├── graficos/                         # Visualizaciones interactivas en HTML (Plotly y Dashboards)
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
│   │   ├── dashboard_roca_runciman_ner.html
│   │   ├── dashboard_topic_modeling.html
│   │   ├── evolucion_partidaria_1929_1939.html
│   │   ├── mapa_provincias_diputados_per_capita.html
│   │   ├── mapa_provincias_senadores.html
│   │   ├── porcentaje_provincias_diputados_per_capita.html
│   │   ├── porcentaje_provincias_diputados_ratio.html
│   │   ├── porcentaje_provincias_senadores.html
│   │   └── volumen_total_intervenciones.html
│   ├── bancas_diputados.py               # Diccionario de bancas e ingesta directa desde las tablas 3NF
│   ├── eda_provincias.py                 # Análisis exploratorio provincial (absoluto y relativo)
│   ├── eda_provincias_porcentaje.py      # Participación provincial en términos proporcionales
│   ├── evolucion_composicion.py          # Análisis de la composición de las cámaras
│   ├── evolucion_partidaria.py           # Dinámica de los partidos políticos en el tiempo
│   ├── generar_dashboard_ner.py          # Generador unificado del Dashboard NER multi-nivel (4 capas)
│   ├── interv_totales.py                 # Cálculo de totales y agregados del corpus
│   ├── mapa_interactivo.py               # Generación de mapas coropléticos con Plotly
│   └── provincias.geojson                # Geometrías de las provincias argentinas
├── database_connection.py                # Módulo de conexión a base de datos Supabase
├── motor_ner.py                          # Motor de Reconocimiento de Entidades (NER) y ABSA sobre 3NF
├── Lista Entidades - OCT26.pdf           # Catálogo de referencia de entidades políticas y comerciales
├── extractor_intervenciones.py           # Parser y extractor de discursos parlamentarios a doble columna
├── extractor_provincias.py               # Extractor del padrón histórico de legisladores y provincias
├── extractor_sumarios_leyes.py           # Extractor de sumarios temáticos, proyectos y leyes sancionadas
├── extractor_fechas_sesiones.py          # Extractor de sesiones, fechas y autoridades sobre los 209 tomos PDF
├── .gitignore                            # Exclusiones de control de versiones
└── README.md                             # Documentación general y arquitectura 3NF del repositorio
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
pip install numpy pandas plotly supabase python-dotenv pymupdf openai
```

### Variables de Entorno (`.env`)
Para la conexión a la base de datos o utilidades de curaduría:

```env
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-clave-anon-o-service-role
GEMINI_API_KEY=tu-api-key-de-gemini  # Opcional para curador_ia
```

### Ejecución del Motor NER y Generación de Gráficos
```bash
# Ejecutar el motor NER y ABSA directamente sobre las tablas 3NF
python motor_ner.py --lote 1000

# Generar el Dashboard interactivo NER unificado (4 capas metodológicas)
python Creacion_graficos/generar_dashboard_ner.py
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
