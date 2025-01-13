FROM python:alpine

COPY requirements.txt /
RUN pip install -r requirements.txt && \
    pip install gunicorn

EXPOSE 5000

RUN mkdir /app /app/volume
WORKDIR /app
COPY *.py ./
COPY translations ./translations
COPY img ./img
COPY settings.py.docker settings.py

ENV GUNICORN_CMD_ARGS="--workers 4 --bind 0.0.0.0:5000"

ENTRYPOINT ["gunicorn", "app:app"]
