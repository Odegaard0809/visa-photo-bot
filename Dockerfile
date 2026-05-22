FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

EXPOSE 3000

CMD ["gunicorn", "src.app:flask_app", "--bind", "0.0.0.0:3000", "--workers", "2", "--timeout", "60"]
