import json
from io import BytesIO

import boto3
import pandas as pd
import streamlit as st
from botocore.exceptions import BotoCoreError, ClientError


st.set_page_config(
    page_title="Titanic con AWS!",
    page_icon="🚢",
    layout="wide"
)

# Rutas reales de tu bucket de Amazon S3.
BUCKET = "xideralaws-curso-jazmin-ibieta"
CSV_KEY = "tictanic.csv"
SUMMARY_KEY = "titanic/resumen_titanic.json"


@st.cache_data(ttl=300)
def cargar_csv_desde_s3():
    """Lee el archivo original del Titanic desde S3 usando boto3."""
    s3 = boto3.client("s3")

    response = s3.get_object(
        Bucket=BUCKET,
        Key=CSV_KEY
    )

    contenido = response["Body"].read()
    return pd.read_csv(BytesIO(contenido))


@st.cache_data(ttl=300)
def cargar_resumen_desde_s3():
    """Lee el resumen generado por Lambda desde S3 usando boto3."""
    s3 = boto3.client("s3")

    response = s3.get_object(
        Bucket=BUCKET,
        Key=SUMMARY_KEY
    )

    contenido = response["Body"].read().decode("utf-8")
    return json.loads(contenido)


st.title("🚢 Titanic Dataset")
st.caption("Amazon S3 → AWS Lambda con boto3 → Amazon S3 → Streamlit")

try:
    df = cargar_csv_desde_s3()
    resumen = cargar_resumen_desde_s3()

    st.success(
        f"Datos cargados correctamente desde "
        f"s3://{BUCKET}/{CSV_KEY}"
    )

    columna1, columna2, columna3, columna4 = st.columns(4)

    columna1.metric(
        "Total de pasajeros",
        resumen["total_pasajeros"]
    )

    columna2.metric(
        "Sobrevivientes",
        resumen["sobrevivientes"]
    )

    columna3.metric(
        "No sobrevivientes",
        resumen["no_sobrevivientes"]
    )

    columna4.metric(
        "Edad promedio",
        f'{resumen["edad_promedio"]} años'
    )

    st.subheader("Datos del Titanic")
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    grafica1, grafica2 = st.columns(2)

    with grafica1:
        st.subheader("Supervivencia")

        supervivencia = (
            df["Survived"]
            .map({
                0: "No sobrevivió",
                1: "Sobrevivió"
            })
            .value_counts()
        )

        st.bar_chart(supervivencia)

    with grafica2:
        st.subheader("Pasajeros por clase")

        clases = (
            df["Pclass"]
            .map({
                1: "Primera clase",
                2: "Segunda clase",
                3: "Tercera clase"
            })
            .value_counts()
        )

        st.bar_chart(clases)

    st.subheader("Resumen generado por Lambda")
    st.json(resumen)

except (ClientError, BotoCoreError) as error:
    st.error("No se pudieron leer los archivos desde Amazon S3.")
    st.code(str(error))
    st.info(
        "Revisa los permisos s3:GetObject del rol de EC2, "
        "el nombre del bucket y las rutas de los archivos."
    )

except Exception as error:
    st.error("Ocurrió un error al mostrar los datos.")
    st.code(str(error))
