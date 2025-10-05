FROM python:3.13.0
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY message_generation /app/message_generation
COPY randomize_process_id /app/randomize_process_id

ENTRYPOINT [ "/bin/bash" ]