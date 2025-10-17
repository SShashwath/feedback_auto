# Use slim Python image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget unzip gnupg ca-certificates \
    fonts-liberation libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 \
    libexpat1 libfontconfig1 libgbm1 libgcc1 libglib2.0-0 \
    libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 \
    libx11-6 libx11-xcb1 libxcomposite1 libxcursor1 \
    libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 \
    libxrender1 libxss1 libxtst6 \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Install Chrome
ARG CHROME_VERSION=126.0.6478.126-1
RUN wget -q -O google-chrome.deb \
    "https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_${CHROME_VERSION}_amd64.deb" \
    && apt-get update && apt-get install -y ./google-chrome.deb \
    && rm google-chrome.deb && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
ARG CHROMEDRIVER_VERSION=126.0.6478.126
RUN wget -q -O /tmp/chromedriver.zip \
    "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" \
    && unzip /tmp/chromedriver.zip -d /tmp \
    && mv /tmp/chromedriver-linux64/chromedriver /usr/bin/chromedriver \
    && chmod +x /usr/bin/chromedriver \
    && rm -rf /tmp/chromedriver-linux64 /tmp/chromedriver.zip

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create /dev/shm for shared memory
RUN mkdir -p /dev/shm && chmod 1777 /dev/shm

EXPOSE 8080

# Start Gunicorn with config file
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]
