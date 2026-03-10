# Builder stage
FROM python:3.13-slim AS builder

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_VERSION=0.5.21

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && pip install --upgrade pip \
    && pip install "uv==$UV_VERSION"

WORKDIR /app

COPY pyproject.toml uv.lock /app/

# Use poetry to install dependencies
RUN uv export --format requirements-txt --no-hashes -o /app/requirements.txt
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r /app/requirements.txt

# Final stage
FROM python:3.13-slim AS final

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r /tmp/requirements.txt \
    && rm -rf /wheels /tmp/requirements.txt

# Setup app user and directory
RUN useradd -U liara \
    && install -d -m 0755 -o liara -g liara /app/staticfiles \
    && install -d -m 0755 -o liara -g liara /app/media \
    && install -d -m 0755 -o liara -g liara /app/data

WORKDIR /app

COPY --chown=liara:liara . .

USER liara:liara

RUN python manage.py collectstatic --noinput

ENTRYPOINT [ "/app/entrypoint.sh" ]
CMD [ "server" ]
