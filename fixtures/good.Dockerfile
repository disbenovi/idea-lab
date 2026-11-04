FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
FROM python:3.12-slim
COPY --from=builder /app /app
USER 1000:1000
HEALTHCHECK CMD python -c "print('ok')"
CMD ["python", "/app/app.py"]
