FROM python:3.11-slim

WORKDIR /app

# Set non-interactive and unbuffered python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true

COPY . .

# Run scheduled agent every 6 hours by default
ENTRYPOINT ["python3", "-m", "winamax_agent.cli"]
CMD ["--schedule", "--interval-hours", "6"]
