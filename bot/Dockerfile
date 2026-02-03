FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir aiogram==3.13.1 SQLAlchemy==2.0.34 aiomysql==0.2.0

COPY bot.py ./

CMD ["python", "bot.py"]
