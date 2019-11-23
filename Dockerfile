FROM python:alpine

ARG port=5000
ARG mattermost_url="None"
ARG mattermost_tokens="None"
ARG mattermost_pa_token="None"

# Alternative: "http://<your-mattermost-url>:<poll-port>/img/bar.png"
ARG bar_img_url="\"https://raw.githubusercontent.com/M-Mueller/mattermost-poll/v1.1/img/bar.png\""

COPY requirements.txt /
RUN pip install -r requirements.txt && \
    pip install gunicorn

EXPOSE $port

RUN mkdir app app/volume
WORKDIR app
COPY *.py ./
COPY translations ./translations
COPY img ./img
COPY settings.py.example settings.py
RUN echo -e "\n\
DATABASE = \"volume/poll.db\"\n\
MATTERMOST_URL = $mattermost_url\n\
MATTERMOST_TOKENS = $mattermost_tokens\n\
MATTERMOST_PA_TOKEN = $mattermost_pa_token\n\
BAR_IMG_URL = $bar_img_url\n\
import logging\n\
logging.basicConfig(filename='volume/poll.log', level=logging.INFO)\n\
" >> settings.py

ENV GUNICORN_CMD_ARGS="--workers 4 --bind poll:$port"

ENTRYPOINT ["gunicorn", "app:app"]
