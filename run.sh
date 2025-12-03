#!/bin/bash

echo "Starting GiftGuardian..."

# Ensure the data directory exists for persistence
if [ ! -d "/data/images" ]; then
    mkdir -p /data/images
fi

# Export the data directory environment variable so the app knows where to save things
export DATA_DIR="/data"

# Start the Flask application
# We listen on 0.0.0.0 to allow external connections (Ingress)
# Port 5000 matches the ingress_port in config.yaml
# using gunicorn or similar is better for prod, but python directly is okay for simple usage
# We use the wsgi.py entrypoint to ensure imports work correctly
python3 wsgi.py
