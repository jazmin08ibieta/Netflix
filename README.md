# Tarea Netflix - Streamlit en EC2 con GitHub Actions

Proyecto de auditoría, limpieza y visualización del dataset de Netflix usando Streamlit.

## Estructura

```text
.
├── .github/workflows/docker-image.yml
├── .streamlit/config.toml
├── Dockerfile
├── app.py
├── docker-compose.yml
├── netflix_titles.csv
├── requirements.txt
└── README.md
```

## Ejecución local con Docker

```bash
docker compose up -d --build
```

Abrir:

```text
http://localhost:8501
```

## Despliegue con GitHub Actions + EC2

Este proyecto está preparado para correr con un runner self-hosted en EC2.

El workflow se ejecuta cuando haces push a `main` y levanta la aplicación con Docker Compose.

La app queda disponible en:

```text
http://IP_PUBLICA_EC2:8501
```

## Requisitos en EC2

- Runner self-hosted de GitHub en estado Online.
- Docker instalado.
- Docker Compose disponible.
- Puerto 8501 abierto en el Security Group de AWS.
