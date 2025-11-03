FROM python:3.11-slim-buster
LABEL authors="Damian Fryc"

WORKDIR /app


COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

CMD ["python", "main.py"]
