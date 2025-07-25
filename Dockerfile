# Use a slim Python base image for a smaller final image size
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for Chromium and its driver
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    --no-install-recommends

# Install the stable version of Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install the matching version of ChromeDriver
RUN CHROME_DRIVER_VERSION=$(wget -q -O - "https://storage.googleapis.com/chrome-for-testing-public/LATEST_RELEASE_STABLE") \
    && wget -q --continue -P /tmp "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_DRIVER_VERSION}/linux64/chromedriver-linux64.zip" \
    && unzip /tmp/chromedriver-linux64.zip -d /usr/bin \
    && rm /tmp/chromedriver-linux64.zip

# Copy the requirements file into the container
COPY requirements.txt requirements.txt

# Install the Python dependencies specified in the requirements file
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Expose the port that the application will run on
EXPOSE 8080

# The command to run the application using Gunicorn, a production-ready web server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "300", "app:app"]
