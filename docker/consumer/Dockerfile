FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY ./docker/consumer/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt


# Copy the consumer code
COPY ../app/consumer.py ./consumer.py

# Set the entry point
CMD ["python", "consumer.py"]
