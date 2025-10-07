FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание директории для логов
RUN mkdir -p /app/logs

# Применение миграций Alembic при запуске
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8000

# Запуск приложения
CMD ["./entrypoint.sh"]