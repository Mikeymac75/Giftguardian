#!/bin/bash

echo "Starting GiftGuardian..."

mkdir -p /data/images
export DATA_DIR="/data"

exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 wsgi:app
