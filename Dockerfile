FROM python:alpine

ARG port=5000
ARG mattermost_token=""

COPY requirements.txt /
RUN pip install -r requirements.txt

EXPOSE $port

RUN mkdir app && mkdir volume
WORKDIR app
COPY *.py ./
COPY settings.py.example settings.py
RUN sed -i "s^\(DATABASE\s*=\s*\).*^\1'volume/poll.db'^" settings.py && \
	if [ -n "$mattermost_token" ]; then sed -i "s^\(MATTERMOST_TOKEN\s*=\s*\).*^\1$mattermost_token^" settings.py; fi && \
	sed -i "s^\(WEBSERVER_PORT\s*=\s*\).*^\1$port^" settings.py

ENTRYPOINT ["python", "run.py"]
