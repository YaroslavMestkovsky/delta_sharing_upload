# Базовый образ для сборки
FROM python:3.10-slim AS builder

# Установка необходимых зависимостей для сборки
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей Python
RUN mkdir /app
COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Установка Cython
RUN pip install cython

# Копирование исходного кода
COPY app /app
WORKDIR /app

# Компиляция всех .py файлов в .so с помощью Cython
RUN find . -name "*.py" -exec cythonize -3 -i -b {} \;

# Удаление всех .py файлов после компиляции
RUN find . -name "*.py" -delete

# Этап финальной сборки
FROM python:3.10-slim

# Копирование только скомпилированных файлов (.so) и необходимых файлов
COPY --from=builder /app /app

# Установка зависимостей
RUN pip install --no-cache-dir -r /app/requirements.txt

# Настройка PYTHONPATH
ENV PYTHONPATH=/app:$PYTHONPATH

# Рабочая директория
WORKDIR /app

# Команда по умолчанию
CMD ["tail", "-f", "/dev/null"]
