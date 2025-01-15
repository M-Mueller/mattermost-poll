# Mattermost Poll

[![codecov](https://codecov.io/gh/M-Mueller/mattermost-poll/branch/master/graph/badge.svg)](https://codecov.io/gh/M-Mueller/mattermost-poll)

Provides a slash command to create polls in Mattermost.

![Example](/doc/example_yes_no.gif)

By default, a poll will only offer the options *Yes* and *No*. However, users can also specify an arbitrary number of choices:

![Example](/doc/example_colours.png)

Choices are separated by `--`.

## Additional options

- `--noprogress`: Do not display the number of votes until the poll is ended
- `--public`: Show who voted for what at the end of the poll
- `--votes=X`: Allows users to place a total of *X* votes. Default is 1. Each individual option can still only be voted once.
- `--bars`: Show results as a bar chart at the end of the poll.
- `--locale=X`: Use a specific locale for the poll. Supported values are en and de. By default it's the users language.

## Help

`/poll help` will display full usage options. Only visible to you.

Set the "Autocomplete Hint" in the Slash Command settings to `See "/poll help" for full usage options`

## Requirements

- Python >= 3.6
- Flask
- A WSGI server (e.g. gunicorn or uWSGI)

## Setup

1. In Mattermost go to *Main Menu -> Integrations -> Slash Commands* and add a new slash command with the URL of the server including the configured port number, e.g. http://localhost:5000.
1. Choose POST for the request method.
1. Copy the generated token.
1. Copy `settings.py.example` to `settings.py` and customise your settings. Paste the token from the previous step in `MATTERMOST_TOKENS`.
1. Start the server:
   ```bash
   gunicorn --workers 4 --bind :5000 app:app
   ```
1. You might need to add the hostname of the poll server (e.g. `localhost`) to "System Settings > Developer > Allow untrusted internal connections to".

To resolve usernames in `--public` polls and to provide localization, the server needs access to the
Mattermost API. For this a [personal access token](https://docs.mattermost.com/developer/personal-access-tokens.html) must be provided in your `settings.py`. Which user provides the token doesn't matter, e.g. you can create a dummy account. If no token is provided `--public` polls will not be available and all texts will be english.

## Docker

To integrate with [mattermost-docker](https://github.com/mattermost/docker):

1. Create the integration in mattermost (see above). As URL use `http://poll:5000` and add `poll` to the allowed untrusted connections. Also enable "Image Proxy" (see `BAR_IMG_URL ` in [settings.py.example](settings.py.example) for details)
1. Copy [docker-compose.poll.yml](docker-compose.poll.yml) to the mattermost docker directory.
1. Add the following two lines to your `.env`:
   ```
   MATTERMOST_POLL_PATH=./volumes/poll
   MATTERMOST_POLL_TOKENS="['<your-integration-token>']"
   MATTERMOST_POLL_PA_TOKEN="<your-access-token>"
   ```
1. Include the service in the startup, e.g.:
   ```
   docker compose -f docker-compose.yml -f docker-compose.without-nginx.yml -f docker-compose.poll.yml up
   ```

The docker image reads all it's settings from environment variables (or uses a default value). See [settings.py.docker](settings.py.docker) for all available variables.
