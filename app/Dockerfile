# Используем официальный минимальный Python-образ
FROM python:3.13-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости (curl, gnupg2, unixODBC и т.п.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    apt-transport-https \
    ca-certificates \
    unixodbc \
    unixodbc-dev && \
    rm -rf /var/lib/apt/lists/*

# Добавляем репозиторий Microsoft и устанавливаем ODBC-драйвер
RUN curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Копируем requirements и устанавливаем Python-зависимости
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходники приложения
COPY app/ .

# Открываем порт (если приложение слушает HTTP)
EXPOSE 8000

# Команда по умолчанию
CMD ["python", "app.py"]
