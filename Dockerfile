# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем структуру папок проекта
COPY . .

RUN mkdir -p /app/data

# Позволяет Python беспрепятственно видеть вложенные модули
ENV PYTHONPATH=/app

CMD ["python", "bot.py"]