from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Netflix: auditoría y limpieza",
    page_icon="🎬",
    layout="wide",
)

DATA_PATH = Path(__file__).parent / "netflix_titles.csv"


@st.cache_data
def load_data() -> pd.DataFrame:
    """Carga el CSV incluido en el repositorio."""
    return pd.read_csv(DATA_PATH)


@st.cache_data
def clean_netflix_data(df_original: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Limpia el dataset de Netflix y regresa un resumen de decisiones."""
    df = df_original.copy()
    filas_inicio = len(df)

    # 1. Normalizar espacios en columnas de texto.
    text_cols = df.select_dtypes(include="object").columns
    for col in text_cols:
        df[col] = df[col].astype("string").str.strip()
        df[col] = df[col].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})

    # 2. Eliminar duplicados exactos.
    duplicados_eliminados = int(df.duplicated().sum())
    df = df.drop_duplicates().copy()

    # 3. Convertir fecha agregada a datetime.
    df["date_added"] = pd.to_datetime(df["date_added"], errors="coerce")

    # 4. Rellenar faltantes categóricos con etiquetas explícitas.
    fill_values = {
        "director": "No especificado",
        "cast": "No especificado",
        "country": "No especificado",
        "rating": "Sin clasificación",
    }
    for col, value in fill_values.items():
        if col in df.columns:
            df[col] = df[col].fillna(value)

    # 5. Marcar fechas faltantes sin inventarlas.
    df["date_added_missing"] = df["date_added"].isna().astype(int)

    # 6. Marcar duración faltante.
    df["duration"] = df["duration"].fillna("No especificado")

    # 7. Validar años razonables.
    current_year = pd.Timestamp.today().year
    filas_antes_anio = len(df)
    df = df[df["release_year"].between(1900, current_year)].copy()
    anios_eliminados = filas_antes_anio - len(df)

    # 8. Separar duración numérica y unidad.
    duration_parts = df["duration"].astype("string").str.extract(r"(\d+)\s*(\w+)")
    df["duration_number"] = pd.to_numeric(duration_parts[0], errors="coerce")
    df["duration_unit"] = duration_parts[1].fillna("No especificado")

    # 9. Variables de fecha.
    df["year_added"] = df["date_added"].dt.year
    df["month_added"] = df["date_added"].dt.month_name()

    # 10. Edad del contenido cuando fue agregado.
    df["content_age_when_added"] = df["year_added"] - df["release_year"]
    df.loc[df["content_age_when_added"] < 0, "content_age_when_added"] = np.nan

    # 11. País y género principal.
    df["main_country"] = df["country"].astype("string").str.split(",").str[0].str.strip()
    df["main_genre"] = df["listed_in"].astype("string").str.split(",").str[0].str.strip()

    # 12. Conteos derivados.
    df["cast_count"] = df["cast"].apply(count_list_items)
    df["genre_count"] = df["listed_in"].apply(count_list_items)

    # 13. Variables separadas para películas y series.
    df["movie_minutes"] = np.where(df["type"].eq("Movie"), df["duration_number"], np.nan)
    df["tv_seasons"] = np.where(df["type"].eq("TV Show"), df["duration_number"], np.nan)

    resumen = {
        "filas_inicio": filas_inicio,
        "filas_final": len(df),
        "filas_eliminadas": filas_inicio - len(df),
        "duplicados_eliminados": duplicados_eliminados,
        "anios_eliminados": anios_eliminados,
    }
    return df, resumen


def count_list_items(value) -> int:
    """Cuenta elementos separados por coma en columnas como cast o listed_in."""
    if pd.isna(value) or value == "No especificado":
        return 0
    return len([item for item in str(value).split(",") if item.strip()])


def missing_table(df: pd.DataFrame) -> pd.DataFrame:
    """Crea una tabla de faltantes por columna."""
    missing = df.isna().sum().sort_values(ascending=False)
    pct = (missing / len(df) * 100).round(2)
    return pd.DataFrame({"faltantes": missing, "porcentaje": pct})


def plot_bar(series: pd.Series, title: str, xlabel: str, ylabel: str, rotation: int = 0) -> None:
    """Muestra una gráfica de barras con Matplotlib dentro de Streamlit."""
    fig, ax = plt.subplots(figsize=(9, 5))
    series.plot(kind="bar", ax=ax)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=rotation)
    ax.grid(axis="y", alpha=0.3)
    st.pyplot(fig)


def section_divider() -> None:
    st.divider()


# ==============================
# Inicio de la aplicación
# ==============================

st.title("Netflix: revisión, auditoría y limpieza de datos")
st.write(
    "Esta aplicación trabaja el dataset de Netflix con un flujo completo de "
    "carga, auditoría, limpieza, creación de variables y visualización."
)

if not DATA_PATH.exists():
    st.error(
        "No se encontró el archivo netflix_titles.csv. "
        "Para correr desde GitHub, el CSV debe estar en la misma carpeta que app.py."
    )
    st.stop()

try:
    df_original = load_data()
except Exception as error:
    st.error(f"Ocurrió un problema al cargar el CSV: {error}")
    st.stop()

df_limpio, resumen_limpieza = clean_netflix_data(df_original)

# ==============================
# Barra lateral
# ==============================

with st.sidebar:
    st.header("Navegación")
    st.write("Dataset incluido en el repositorio:")
    st.code("netflix_titles.csv")
    st.metric("Filas originales", f"{df_original.shape[0]:,}")
    st.metric("Columnas originales", f"{df_original.shape[1]:,}")
    st.metric("Filas limpias", f"{df_limpio.shape[0]:,}")

# ==============================
# 1. Carga
# ==============================

st.header("1. Carga de datos")
col1, col2, col3 = st.columns(3)
col1.metric("Filas", f"{df_original.shape[0]:,}")
col2.metric("Columnas", f"{df_original.shape[1]:,}")
col3.metric("Duplicados exactos", f"{df_original.duplicated().sum():,}")

st.subheader("Vista previa del dataset original")
st.dataframe(df_original.head(10), use_container_width=True)

st.write(
    "Cada fila representa un título de Netflix. Las columnas principales son "
    "tipo de contenido, título, director, elenco, país, fecha agregada, año de lanzamiento, "
    "clasificación, duración, categoría y descripción."
)

section_divider()

# ==============================
# 2. Revisión inicial
# ==============================

st.header("2. Revisión inicial")
left, right = st.columns(2)

with left:
    st.subheader("Tipos de datos")
    tipos = df_original.dtypes.astype(str).to_frame("tipo")
    st.dataframe(tipos, use_container_width=True)

with right:
    st.subheader("Valores faltantes")
    st.dataframe(missing_table(df_original), use_container_width=True)

st.subheader("Resumen numérico")
st.dataframe(df_original.describe(include="number").T, use_container_width=True)

section_divider()

# ==============================
# 3. Auditoría
# ==============================

st.header("3. Auditoría de calidad")

fecha_convertida = pd.to_datetime(df_original["date_added"], errors="coerce")
fechas_invalidas = int(fecha_convertida.isna().sum())
anios_invalidos = int((~df_original["release_year"].between(1900, pd.Timestamp.today().year)).sum())

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Duplicados", f"{df_original.duplicated().sum():,}")
m2.metric("Fechas faltantes/no válidas", f"{fechas_invalidas:,}")
m3.metric("Años inválidos", f"{anios_invalidos:,}")
m4.metric("Rating faltante", f"{df_original['rating'].isna().sum():,}")
m5.metric("Duración faltante", f"{df_original['duration'].isna().sum():,}")

st.write(
    "La auditoría permite detectar problemas antes de graficar o interpretar datos. "
    "En este caso se revisaron duplicados, fechas, años fuera de rango, valores nulos "
    "y columnas con muchos valores únicos."
)

st.subheader("Cardinalidad por columna")
cardinalidad = df_original.nunique().sort_values(ascending=False).to_frame("valores_unicos")
st.dataframe(cardinalidad, use_container_width=True)

section_divider()

# ==============================
# 4. Limpieza
# ==============================

st.header("4. Limpieza de datos")
st.write(
    "La limpieza se hizo sin borrar información de forma agresiva. "
    "Los campos faltantes como director, elenco, país o clasificación se marcaron con "
    "etiquetas explícitas, porque la ausencia de información también es útil para auditar calidad."
)

st.subheader("Decisiones aplicadas")
st.write("1. Se quitaron espacios sobrantes en columnas de texto.")
st.write("2. Se eliminaron duplicados exactos.")
st.write("3. La columna date_added se convirtió a formato de fecha.")
st.write("4. Los faltantes categóricos se reemplazaron por No especificado o Sin clasificación.")
st.write("5. La duración se separó en número y unidad.")
st.write("6. Se validó que release_year estuviera entre 1900 y el año actual.")
st.write("7. Se crearon variables nuevas para facilitar el análisis.")

r1, r2, r3, r4 = st.columns(4)
r1.metric("Filas iniciales", f"{resumen_limpieza['filas_inicio']:,}")
r2.metric("Filas finales", f"{resumen_limpieza['filas_final']:,}")
r3.metric("Filas eliminadas", f"{resumen_limpieza['filas_eliminadas']:,}")
r4.metric("Duplicados eliminados", f"{resumen_limpieza['duplicados_eliminados']:,}")

left2, right2 = st.columns(2)
with left2:
    st.subheader("Faltantes antes")
    st.dataframe(missing_table(df_original), use_container_width=True)
with right2:
    st.subheader("Faltantes después")
    st.dataframe(missing_table(df_limpio), use_container_width=True)

section_divider()

# ==============================
# 5. Variables nuevas
# ==============================

st.header("5. Variables nuevas")

new_columns = [
    "date_added_missing",
    "year_added",
    "month_added",
    "content_age_when_added",
    "main_country",
    "main_genre",
    "cast_count",
    "genre_count",
    "duration_number",
    "duration_unit",
    "movie_minutes",
    "tv_seasons",
]

st.write(
    "Las variables nuevas ayudan a convertir columnas de texto en información más fácil de analizar. "
    "Por ejemplo, main_country toma el primer país listado, main_genre toma el primer género, "
    "y movie_minutes permite estudiar solo la duración de películas."
)

st.dataframe(df_limpio[new_columns].head(15), use_container_width=True)

section_divider()

# ==============================
# 6. Visualizaciones
# ==============================

st.header("6. Visualizaciones exploratorias")

viz1, viz2 = st.columns(2)
with viz1:
    st.subheader("Películas vs series")
    plot_bar(
        df_limpio["type"].value_counts(),
        "Cantidad de títulos por tipo",
        "Tipo",
        "Cantidad",
    )

with viz2:
    st.subheader("Clasificaciones más frecuentes")
    plot_bar(
        df_limpio["rating"].value_counts().head(10),
        "Top 10 clasificaciones",
        "Rating",
        "Cantidad",
        rotation=45,
    )

viz3, viz4 = st.columns(2)
with viz3:
    st.subheader("Top países principales")
    top_countries = (
        df_limpio[df_limpio["main_country"] != "No especificado"]["main_country"]
        .value_counts()
        .head(10)
    )
    plot_bar(top_countries, "Top 10 países principales", "País", "Cantidad", rotation=45)

with viz4:
    st.subheader("Top géneros principales")
    plot_bar(
        df_limpio["main_genre"].value_counts().head(10),
        "Top 10 géneros principales",
        "Género",
        "Cantidad",
        rotation=45,
    )

st.subheader("Títulos agregados por año")
yearly = df_limpio["year_added"].dropna().astype(int).value_counts().sort_index()
fig, ax = plt.subplots(figsize=(10, 5))
yearly.plot(kind="line", marker="o", ax=ax)
ax.set_title("Cantidad de títulos agregados por año")
ax.set_xlabel("Año agregado")
ax.set_ylabel("Cantidad de títulos")
ax.grid(alpha=0.3)
st.pyplot(fig)

st.subheader("Distribución de duración de películas")
movie_minutes = df_limpio["movie_minutes"].dropna()
fig, ax = plt.subplots(figsize=(10, 5))
movie_minutes.plot(kind="hist", bins=30, ax=ax)
ax.set_title("Duración de películas")
ax.set_xlabel("Minutos")
ax.set_ylabel("Cantidad de películas")
ax.grid(alpha=0.3)
st.pyplot(fig)

section_divider()

# ==============================
# 7. Explorador interactivo
# ==============================

st.header("7. Explorador interactivo")
st.write("Usa los filtros para revisar el catálogo limpio.")

filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    selected_type = st.multiselect(
        "Tipo",
        sorted(df_limpio["type"].dropna().astype(str).unique()),
    )

with filter_col2:
    selected_rating = st.multiselect(
        "Clasificación",
        sorted(df_limpio["rating"].dropna().astype(str).unique()),
    )

with filter_col3:
    selected_country = st.multiselect(
        "País principal",
        sorted(df_limpio["main_country"].dropna().astype(str).unique()),
    )

filtered = df_limpio.copy()
if selected_type:
    filtered = filtered[filtered["type"].astype(str).isin(selected_type)]
if selected_rating:
    filtered = filtered[filtered["rating"].astype(str).isin(selected_rating)]
if selected_country:
    filtered = filtered[filtered["main_country"].astype(str).isin(selected_country)]

st.metric("Registros filtrados", f"{len(filtered):,}")
st.dataframe(
    filtered[
        [
            "title",
            "type",
            "main_country",
            "main_genre",
            "release_year",
            "rating",
            "duration",
            "year_added",
        ]
    ].head(300),
    use_container_width=True,
)

section_divider()

# ==============================
# 8. Descarga y cierre
# ==============================

st.header("8. Descarga del dataset limpio")

st.download_button(
    label="Descargar CSV limpio",
    data=df_limpio.to_csv(index=False).encode("utf-8"),
    file_name="netflix_titles_limpio.csv",
    mime="text/csv",
)

st.header("Conclusión")
st.write(
    "En esta práctica se realizó un proceso completo de manejo de datos: carga, revisión inicial, "
    "auditoría, limpieza, creación de variables, visualización y descarga del resultado. "
    "El punto más importante es que limpiar datos no significa borrar todo lo incompleto, sino tomar "
    "decisiones justificadas para que el análisis sea más confiable."
)
