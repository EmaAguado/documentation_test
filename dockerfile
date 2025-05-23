FROM python:3.10.10-slim

WORKDIR /app

# COPY requirements.txt .
COPY . .
RUN pip install --upgrade pip && pip install -r requirements.txt

EXPOSE 8000

CMD ["mkdocs", "serve", "-a", "0.0.0.0:8000"]
