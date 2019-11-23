# Mattermost Poll

[![Build Status](https://travis-ci.com/M-Mueller/mattermost-poll.svg?branch=master)](https://travis-ci.com/M-Mueller/mattermost-poll) [![codecov](https://codecov.io/gh/M-Mueller/mattermost-poll/branch/master/graph/badge.svg)](https://codecov.io/gh/M-Mueller/mattermost-poll)

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
- Tornado
- A WSGI server (e.g. gunicorn or uWSGI)

## Setup

Copy `settings.py.example` to `settings.py` and customise your settings.

Start the server:

```bash
gunicorn --workers 4 --bind :5000 app:app
```

1. In Mattermost go to *Main Menu -> Integrations -> Slash Commands* and add a new slash command with the URL of the server including the configured port number, e.g. http://localhost:5000.
1. Choose POST for the request method.
    - Optionally add the generated token to your `settings.py` (requires server restart).
1. Edit your Mattermost `config.json` to include "localhost" in the "AllowedUntrustedInternalConnections" setting, e.g. `"AllowedUntrustedInternalConnections": "localhost"`

To resolve usernames in `--public` polls and to provide localization, the server needs access to the
Mattermost API. For this a [personal access token](https://docs.mattermost.com/developer/personal-access-tokens.html) must be provided in your `settings.py`. Which user provides the token doesn't matter, e.g. you can create a dummy account. If no token is provided `--public` polls will not be available and all texts will be english.

## Docker

To integrate with [mattermost-docker](https://github.com/mattermost/mattermost-docker):

```bash
cd mattermost-docker
git submodule add git@github.com:M-Mueller/mattermost-poll.git poll
```

and add the following to the `services` section:

```yaml
  poll:
    build:
      context: poll
      args:
        - mattermost_url="http://web"
        - mattermost_tokens=['<mattermost-token-1>', '<mattermost-token-2>']
        - mattermost_pa_token="<personal-access-token>"
    ports:
      - "5000:5000"
    restart: unless-stopped
    volumes:
      - ./volumes/poll:/app/volume:rw
```

1. In Mattermost go to *Main Menu -> Integrations -> Slash Commands* and add a new slash command with the URL of the server including the configured port number, e.g. http://poll:5000.
1. Choose POST for the request method.
1. Edit your Mattermost `config.json` to include "poll" in the "AllowedUntrustedInternalConnections" setting, e.g. `"AllowedUntrustedInternalConnections": "poll"`
