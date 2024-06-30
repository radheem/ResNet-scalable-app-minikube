FROM python:3.8-slim

ENV PORT 5000
ENV METRICS_PORT 8000

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]
