FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Expose port for FastAPI
EXPOSE 7860

# Default: run inference then start API server
# For HF Spaces, we start the API server (inference can be run separately)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
