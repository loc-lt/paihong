# pull official base image
FROM python:3.12-slim

ENV APP_HOME=/usr/src/service
RUN mkdir $APP_HOME
RUN mkdir $APP_HOME/app
RUN mkdir $APP_HOME/core
RUN mkdir $APP_HOME/apis

WORKDIR /usr/src/service

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV POETRY_VIRTUALENVS_CREATE=False
ENV TZ=Asia/Ho_Chi_Minh

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpq-dev \
    tzdata \
    pkg-config \
    netcat-traditional \
    libfreetype6 \
    libpng16-16 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    shared-mime-info && \
    rm -rf /var/lib/apt/lists/*

RUN pip install -U pip poetry && rm -rf /root/.cache/pip
COPY ./poetry.lock ./pyproject.toml ./
RUN poetry install

COPY . $APP_HOME
