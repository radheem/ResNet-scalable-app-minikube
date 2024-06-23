FROM python:3.9-slim
# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY . .

# Install the dependencies specified in the requirements file
RUN apt-get update && apt-get install -y build-essential \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*
# Copy the rest of the application code into the container


# Expose the port on which the app will run
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]