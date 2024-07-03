FROM python:3.11.3-alpine AS build

RUN apk update && apk upgrade

# Install helm
RUN apk add --no-cache curl tar bash openssl
RUN curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
RUN chmod 700 get_helm.sh
RUN ./get_helm.sh

# Create direcotries for the app
RUN mkdir /app
RUN mkdir /app/templates
RUN mkdir /app/static

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt && rm requirements.txt

COPY helm_release_viewer.py .
COPY templates ./templates
COPY static ./static

# Set the PYTHONDONTWRITEBYTECODE environment variable
ENV PYTHONDONTWRITEBYTECODE 1

USER 1000

CMD gunicorn -w 1 -b :$APP_PORT --log-level $LOG_LEVEL helm_release_viewer:app -k gevent --timeout $TIMEOUT