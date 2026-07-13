import json
import os
from datetime import datetime, timezone

import altair as alt
import boto3
import pandas as pd
import streamlit as st
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError


st.set_page_config(
    page_title="NYC Taxi Dashboard",
    page_icon="🚕",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================
# CONFIGURACIÓN S3
# =========================================================
S3_BUCKET = os.getenv("S3_BUCKET", "xideralaws-curso-jazmin-ibieta")
S3_KEY = os.getenv("S3_KEY", "taxisNY/raw/kpis/nyc_taxi_kpis.json")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
LOCAL_JSON = os.getenv("LOCAL_JSON", "nyc_taxi_kpis.json")


# =========================================================
# ESTILOS NYC TAXI
# =========================================================
st.markdown(
    """
    <style>
        :root {
            --taxi-yellow: #FFD400;
            --taxi-black: #111111;
            --taxi-gray: #6B7280;
            --taxi-light: #FFF8D8;
        }

        .stApp {
            background:
                radial-gradient(circle at top right, rgba(255, 212, 0, .20), transparent 30%),
                linear-gradient(180deg, #FFFDF4 0%, #FFFFFF 48%, #F7F7F7 100%);
            color: var(--taxi-black);
        }

        [data-testid="stHeader"] { background: transparent; }

        .block-container {
            max-width: 1380px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        .hero {
            position: relative;
            overflow: hidden;
            padding: 2.5rem;
            border-radius: 28px;
            color: white;
            background: linear-gradient(135deg, #111111 0%, #1F1F1F 52%, #2C2C2C 100%);
            box-shadow: 0 24px 60px rgba(0, 0, 0, .24);
            margin-bottom: 1.7rem;
            border: 3px solid #FFD400;
        }

        .hero::before {
            content: "";
            position: absolute;
            inset: 0 0 auto 0;
            height: 12px;
            background: repeating-linear-gradient(90deg, #FFD400 0 28px, #111111 28px 56px);
        }

        .hero::after {
            content: "NYC";
            position: absolute;
            right: 2rem;
            bottom: -1rem;
            font-size: 8rem;
            line-height: 1;
            font-weight: 1000;
            color: rgba(255, 212, 0, .08);
            letter-spacing: -.08em;
        }

        .hero-badge {
            position: relative;
            z-index: 1;
            display: inline-flex;
            padding: .48rem .85rem;
            border-radius: 999px;
            color: #111111;
            background: #FFD400;
            font-size: .82rem;
            font-weight: 900;
        }

        .hero h1 {
            position: relative;
            z-index: 1;
            margin: 1rem 0 .6rem;
            font-size: clamp(2.2rem, 4vw, 3.9rem);
            line-height: 1;
            letter-spacing: -.045em;
            color: white;
        }

        .hero p {
            position: relative;
            z-index: 1;
            max-width: 820px;
            margin: 0;
            color: rgba(255,255,255,.82);
            font-size: 1.04rem;
            line-height: 1.65;
        }

        .source-pill {
            position: relative;
            z-index: 1;
            display: inline-flex;
            margin-top: 1.2rem;
            padding: .48rem .78rem;
            border-radius: 999px;
            color: #111111;
            background: #FFF2A8;
            border: 1px solid #FFD400;
            font-size: .8rem;
            font-weight: 800;
        }

        .section-title {
            margin: 1.8rem 0 .25rem;
            color: #111111;
            font-size: 1.6rem;
            font-weight: 950;
            letter-spacing: -.025em;
        }

        .section-copy {
            color: #6B7280;
            margin-bottom: 1rem;
        }

        .metric-card {
            min-height: 190px;
            padding: 1.35rem;
            border-radius: 22px;
            background: rgba(255,255,255,.98);
            border: 1px solid #E8D97C;
            border-top: 7px solid #FFD400;
            box-shadow: 0 14px 32px rgba(17,17,17,.08);
        }

        .metric-icon {
            width: 48px;
            height: 48px;
            display: grid;
            place-items: center;
            border-radius: 15px;
            margin-bottom: 1rem;
            background: #FFF4B5;
            border: 1px solid #FFD400;
            font-size: 1.35rem;
        }

        .metric-label {
            color: #6B7280;
            font-size: .76rem;
            font-weight: 900;
            letter-spacing: .06em;
            text-transform: uppercase;
        }

        .metric-value {
            margin-top: .42rem;
            color: #111111;
            font-size: clamp(1.65rem, 2.4vw, 2.45rem);
            line-height: 1;
            font-weight: 950;
            letter-spacing: -.04em;
        }

        .metric-detail {
            margin-top: .8rem;
            color: #727272;
            font-size: .86rem;
            line-height: 1.4;
        }

        div[data-testid="stVegaLiteChart"] {
            background: white;
            border: 1px solid #E8D97C;
            border-radius: 20px;
            padding: 12px;
            box-shadow: 0 12px 28px rgba(17,17,17,.07);
        }

        div[data-testid="stAlert"] {
            border-radius: 16px;
            border-left: 7px solid #FFD400;
        }

        .footer {
            margin-top: 2.3rem;
            padding: 1.1rem 1rem;
            border-radius: 16px;
            background: #111111;
            color: rgba(255,255,255,.78);
            font-size: .82rem;
            display: flex;
            justify-content: space-between;
            gap: .8rem;
            flex-wrap: wrap;
            border-top: 7px solid #FFD400;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=300, show_spinner=False)
def load_json_from_s3(bucket: str, key: str, region: str) -> dict:
    client = boto3.client("s3", region_name=region)
    response = client.get_object(Bucket=bucket, Key=key)
    content = response["Body"].read().decode("utf-8")
    return json.loads(content)


@st.cache_data(ttl=300, show_spinner=False)
def load_json_local(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_payload() -> tuple[dict, str]:
    try:
        return load_json_from_s3(S3_BUCKET, S3_KEY, AWS_REGION), "Amazon S3"
    except (ClientError, BotoCoreError, NoCredentialsError, ValueError) as s3_error:
        try:
            return load_json_local(LOCAL_JSON), "Archivo local"
        except (OSError, json.JSONDecodeError) as local_error:
            raise RuntimeError(
                "No fue posible cargar los KPIs desde S3 ni desde el archivo local.\n\n"
                f"Error S3: {s3_error}\n"
                f"Error local: {local_error}"
            ) from local_error


def required_number(data: dict, key: str) -> float:
    value = data.get(key)
    if value is None:
        raise KeyError(f"El JSON no contiene el campo obligatorio: {key}")
    if not isinstance(value, (int, float)):
        raise TypeError(f"El campo '{key}' debe ser numérico.")
    return float(value)


def compact_number(value: float) -> str:
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f} mil M"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f} M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f} mil"
    return f"{value:,.0f}"


def compact_money(value: float) -> str:
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f} mil M"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f} M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.1f} mil"
    return f"${value:,.2f}"


def metric_card(icon: str, label: str, value: str, detail: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-icon">{icon}</div>
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-detail">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def line_chart(dataframe, x, y, title, x_title, y_title, tooltip_fields):
    return (
        alt.Chart(dataframe)
        .mark_line(point=True, strokeWidth=3, color="#111111")
        .encode(
            x=alt.X(x, title=x_title),
            y=alt.Y(y, title=y_title, scale=alt.Scale(zero=False)),
            tooltip=tooltip_fields,
        )
        .properties(title=title, height=330)
        .interactive()
    )


try:
    with st.spinner("Cargando indicadores desde Amazon S3..."):
        payload, source_name = load_payload()

    metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}

    has_full_structure = (
        isinstance(payload, dict)
        and isinstance(payload.get("kpi_resumen"), list)
        and len(payload.get("kpi_resumen", [])) > 0
    )

    has_spanish_flat_structure = (
        isinstance(payload, dict)
        and all(
            key in payload
            for key in [
                "total_viajes",
                "ingreso_total",
                "distancia_promedio",
                "propina_promedio",
            ]
        )
    )

    has_english_flat_structure = (
        isinstance(payload, dict)
        and all(
            key in payload
            for key in [
                "total_trips",
                "total_revenue",
                "avg_trip_distance",
                "avg_tip",
            ]
        )
    )

    if has_full_structure:
        resumen_data = payload["kpi_resumen"][0]
        por_dia = pd.DataFrame(payload.get("kpi_por_dia", []))
        calidad = pd.DataFrame(payload.get("kpi_calidad", []))

        total_trips = required_number(resumen_data, "total_trips")
        total_revenue = required_number(resumen_data, "total_revenue")
        avg_ticket = float(resumen_data.get("avg_ticket", 0))
        avg_trip_distance = required_number(resumen_data, "avg_trip_distance")
        avg_duration_min = float(resumen_data.get("avg_duration_min", 0))
        avg_tip = required_number(resumen_data, "avg_tip")
        avg_tip_pct = float(resumen_data.get("avg_tip_pct", 0))
        avg_passenger_count = float(resumen_data.get("avg_passenger_count", 0))

        if not por_dia.empty and "pickup_date" in por_dia.columns:
            por_dia["pickup_date"] = pd.to_datetime(
                por_dia["pickup_date"], errors="coerce"
            )

    elif has_spanish_flat_structure:
        total_trips = required_number(payload, "total_viajes")
        total_revenue = required_number(payload, "ingreso_total")
        avg_trip_distance = required_number(payload, "distancia_promedio")
        avg_tip = required_number(payload, "propina_promedio")
        avg_ticket = 0.0
        avg_duration_min = 0.0
        avg_tip_pct = 0.0
        avg_passenger_count = 0.0
        por_dia = pd.DataFrame()
        calidad = pd.DataFrame()

    elif has_english_flat_structure:
        total_trips = required_number(payload, "total_trips")
        total_revenue = required_number(payload, "total_revenue")
        avg_trip_distance = required_number(payload, "avg_trip_distance")
        avg_tip = required_number(payload, "avg_tip")
        avg_ticket = float(payload.get("avg_ticket", 0))
        avg_duration_min = float(payload.get("avg_duration_min", 0))
        avg_tip_pct = float(payload.get("avg_tip_pct", 0))
        avg_passenger_count = float(payload.get("avg_passenger_count", 0))
        por_dia = pd.DataFrame()
        calidad = pd.DataFrame()

    else:
        available_keys = list(payload.keys()) if isinstance(payload, dict) else []
        raise KeyError(
            "La estructura del JSON no coincide con ninguna de las estructuras "
            "soportadas. Campos encontrados: " + ", ".join(available_keys)
        )

except Exception as error:
    st.error("No se pudieron cargar los datos del dashboard.")
    st.code(str(error))
    st.stop()


dataset_name = metadata.get("dataset", "NYC Taxi")
sample_text = ""
if metadata.get("sample_enabled") is True:
    sample_fraction = metadata.get("sample_fraction")
    if isinstance(sample_fraction, (int, float)):
        sample_text = f" · Muestra utilizada: {sample_fraction:.0%}"


st.markdown(
    f"""
    <section class="hero">
        <div class="hero-badge">🚕 NYC YELLOW TAXI</div>
        <h1>NYC Taxi Dashboard</h1>
        <p>
            Panel interactivo con indicadores clave de viajes,
            ingresos, distancias y calidad de datos de los taxis
            amarillos de Nueva York.
        </p>
        <div class="source-pill">
            ☁️ Fuente activa: {source_name} · {dataset_name}{sample_text}
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)


st.markdown('<div class="section-title">Resumen general</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-copy">Indicadores generales obtenidos directamente desde Amazon S3.</div>',
    unsafe_allow_html=True,
)

if has_full_structure:
    row1 = st.columns(4, gap="large")
    with row1[0]:
        metric_card("🚕", "Total de viajes", compact_number(total_trips), f"{total_trips:,.0f} viajes")
    with row1[1]:
        metric_card("💵", "Ingreso total", compact_money(total_revenue), f"${total_revenue:,.2f}")
    with row1[2]:
        metric_card("🎫", "Ticket promedio", f"${avg_ticket:,.2f}", "Ingreso promedio por viaje")
    with row1[3]:
        metric_card("🗽", "Distancia promedio", f"{avg_trip_distance:,.2f} mi", "Distancia promedio por viaje")

    st.write("")

    row2 = st.columns(4, gap="large")
    with row2[0]:
        metric_card("⏱️", "Duración promedio", f"{avg_duration_min:,.2f} min", "Duración promedio por viaje")
    with row2[1]:
        metric_card("✨", "Propina promedio", f"${avg_tip:,.2f}", "Propina promedio por viaje")
    with row2[2]:
        metric_card("📊", "Porcentaje de propina", f"{avg_tip_pct:,.2f}%", "Porcentaje promedio de propina")
    with row2[3]:
        metric_card("👤", "Pasajeros promedio", f"{avg_passenger_count:,.2f}", "Pasajeros promedio por viaje")
else:
    row1 = st.columns(4, gap="large")
    with row1[0]:
        metric_card("🚕", "Total de viajes", compact_number(total_trips), f"{total_trips:,.0f} viajes")
    with row1[1]:
        metric_card("💵", "Ingreso total", compact_money(total_revenue), f"${total_revenue:,.2f}")
    with row1[2]:
        metric_card("🗽", "Distancia promedio", f"{avg_trip_distance:,.2f} mi", "Distancia promedio por viaje")
    with row1[3]:
        metric_card("✨", "Propina promedio", f"${avg_tip:,.2f}", "Propina promedio por viaje")

    st.info(
        "El JSON cargado solo contiene indicadores generales. "
        "Las gráficas aparecerán cuando la misma ruta contenga "
        "las secciones completas del proyecto."
    )


if has_full_structure and not por_dia.empty:
    st.markdown('<div class="section-title">Actividad de viajes</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">Evolución de viajes e ingresos con los datos disponibles.</div>',
        unsafe_allow_html=True,
    )

    daily_left, daily_right = st.columns(2, gap="large")

    with daily_left:
        daily_trips_chart = line_chart(
            por_dia,
            "pickup_date:T",
            "trips:Q",
            "Viajes por día",
            "Fecha",
            "Viajes",
            [
                alt.Tooltip("pickup_date:T", title="Fecha"),
                alt.Tooltip("trips:Q", title="Viajes", format=","),
            ],
        )
        st.altair_chart(daily_trips_chart, use_container_width=True)

    with daily_right:
        daily_revenue_chart = line_chart(
            por_dia,
            "pickup_date:T",
            "revenue:Q",
            "Ingresos por día",
            "Fecha",
            "Ingresos",
            [
                alt.Tooltip("pickup_date:T", title="Fecha"),
                alt.Tooltip("revenue:Q", title="Ingresos", format="$,.2f"),
            ],
        )
        st.altair_chart(daily_revenue_chart, use_container_width=True)


if has_full_structure and not calidad.empty:
    required_quality_columns = {"metric", "value"}

    if required_quality_columns.issubset(calidad.columns):
        st.markdown('<div class="section-title">Calidad de datos</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-copy">Indicadores del proceso de limpieza y validación.</div>',
            unsafe_allow_html=True,
        )

        quality_values = dict(zip(calidad["metric"], calidad["value"]))
        original_rows = float(quality_values.get("original_rows", 0))
        clean_rows = float(quality_values.get("clean_rows", 0))
        removed_rows = float(quality_values.get("removed_rows", 0))
        quality_score = float(quality_values.get("quality_score", 0))

        q1, q2, q3, q4 = st.columns(4, gap="large")
        with q1:
            metric_card("📥", "Filas originales", compact_number(original_rows), f"{original_rows:,.0f} registros")
        with q2:
            metric_card("✅", "Filas limpias", compact_number(clean_rows), f"{clean_rows:,.0f} registros")
        with q3:
            metric_card("🧹", "Filas eliminadas", compact_number(removed_rows), f"{removed_rows:,.0f} registros")
        with q4:
            metric_card("🏆", "Quality score", f"{quality_score:.2%}", "Puntuación incluida en el JSON")


st.markdown(
    f"""
    <div class="footer">
        <span>🚕 Proyecto NYC Taxi · Streamlit</span>
        <span>Bucket: {S3_BUCKET}</span>
        <span>S3 key: {S3_KEY}</span>
        <span>Consulta: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</span>
    </div>
    """,
    unsafe_allow_html=True,
)
