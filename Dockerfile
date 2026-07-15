# Dockerfile
FROM python:3.11-slim

# Установка системных утилит для работы с сетью и временем
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем структуру папок проекта
COPY . .

RUN mkdir -p /app/data

# Позволяет Python беспрепятственно видеть вложенные модули
ENV PYTHONPATH=/app

CMD ["python", "bot.py"]