FROM python:3.8-slim

ENV PORT 5000
ENV METRICS_PORT 8000

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "run_gunicorn.py"]
