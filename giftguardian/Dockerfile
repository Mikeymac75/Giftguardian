ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
RUN \
  apk add --no-cache \
    python3 \
    py3-pip

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
