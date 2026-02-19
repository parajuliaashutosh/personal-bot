FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Cache dependency installation separately from app code
COPY pyproject.toml .
RUN pip install --no-cache-dir --no-build-isolation \
    $(python -c "import tomllib; data=tomllib.load(open('pyproject.toml','rb')); print(' '.join(data.get('project',{}).get('dependencies',[])))")

# Now copy source code
COPY . .

# Install the package itself (no -e)
RUN pip install --no-cache-dir .

RUN mkdir -p chroma_db data

EXPOSE 8000

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "3"]