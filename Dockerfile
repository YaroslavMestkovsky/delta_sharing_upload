FROM python:3.10-slim

RUN mkdir "app"
COPY app/requirements.txt app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt

COPY app /app
WORKDIR /app

CMD ["tail", "-f", "/dev/null"]
