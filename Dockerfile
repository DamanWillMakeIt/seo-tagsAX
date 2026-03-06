# Use the official lightweight Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# 1. Copy requirements first (for better caching)
COPY requirements.txt .

# 2. Install dependencies
# We install curl to help with health checks if needed
RUN apt-get update && apt-get install -y curl && \
    pip install --no-cache-dir -r requirements.txt

# 3. Copy the rest of the application code
COPY . .

# 4. Make sure the SVG is definitely there (Explicit copy optional, but safe)
# COPY ondemand.svg . 

# Expose port 5000 for the Flask API
EXPOSE 5000

# Set environment variables to ensure Flask output is logged to terminal
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py

# 5. Run the application
# We use "--host=0.0.0.0" so the container is accessible from outside
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]