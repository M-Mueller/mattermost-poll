FROM python:alpine

ARG port=5000
ARG mattermost_url=""
ARG mattermost_token=""
ARG mattermost_pa_token=""

COPY requirements.txt /
RUN pip install -r requirements.txt

EXPOSE $port

RUN mkdir app
WORKDIR app
COPY *.py ./
COPY settings.py.example settings.py
RUN mkdir volume && \
	sed -i "s^\(DATABASE\s*=\s*\).*^\1'volume/poll.db'^" settings.py && \
	sed -i "s^\(MATTERMOST_URL\s*=\s*\).*^\1$mattermost_url^" settings.py && \
	if [ -n "$mattermost_token" ]; then sed -i "s^\(MATTERMOST_TOKEN\s*=\s*\).*^\1$mattermost_token^" settings.py; fi && \
	if [ -n "$mattermost_pa_token" ]; then sed -i "s^\(MATTERMOST_PA_TOKEN\s*=\s*\).*^\1$mattermost_pa_token^" settings.py; fi && \
	sed -i "s^\(WEBSERVER_PORT\s*=\s*\).*^\1$port^" settings.py

ENTRYPOINT ["python", "run.py"]