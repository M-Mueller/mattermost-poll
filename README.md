Mattermost Poll
===============
Provides a slash command to create polls in Mattermost.

![Example](/doc/example_yes_no.gif)

By default, a poll will only offer the options *Yes* and *No*. However, users can also specify an arbitrary number of choices:

![Example](/doc/example_colours.png)

Choices are separated by `--`.

### Additional options:
- `--secret`: Do not display the number of votes until the poll is ended

Requirements
------------
- Python 3
- Flask
- Tornado

Setup
-----
Copy `settings.py.example` to `settings.py` and customise your settings.

Start the server:
```
python run.py
```
In Mattermost go to *Main Menu -> Integrations -> Slash Commands* and add a new slash command with the URL of the server including the configured port number, e.g. http://localhost:5000.
Choose POST for the request method.
Optionally add the generated token to your `settings.py` (requires server restart).

Docker
------
To integrate with [mattermost-docker](https://github.com/mattermost/mattermost-docker):
```
cd mattermost-docker
git submodule add git@github.com:M-Mueller/mattermost-poll.git poll
```
and add the following to the ```services``` section:
```
  poll:
    build:
      context: poll
      args:
        - mattermost_token="<mattermost-token>"
    ports:
      - "5000:5000"
    restart: unless-stopped
```

In Mattermost use *http://poll:5000/* as the request url. *poll* needs to be added to "AllowedUntrustedInternalConnections" in the Mattermost *config.json*.

