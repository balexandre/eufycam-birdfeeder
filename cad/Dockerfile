FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libxrender1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir build123d==0.13.0 matplotlib==3.*
WORKDIR /work
