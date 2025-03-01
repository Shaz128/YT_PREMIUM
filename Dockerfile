# Use an official Python image
FROM python:3.9

# Install ffmpeg and dependencies
RUN apt-get update && apt-get install -y ffmpeg

# Set the working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose Railway's dynamic port
EXPOSE 5000

# Run the Flask app
CMD ["python", "app.py"]
