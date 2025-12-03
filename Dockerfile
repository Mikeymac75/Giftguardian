FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy data for add-on
COPY run.sh /
COPY requirements.txt /tmp/
COPY wsgi.py /app/
COPY app /app/app

WORKDIR /app

# Install python dependencies
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Fix permissions
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
