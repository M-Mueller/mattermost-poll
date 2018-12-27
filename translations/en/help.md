Starts a poll visible to all users in the channel. The text after the command will be used as the message of the poll.
By default a Yes/No poll is generated:
```
{command} Do you like chocolate?
```
The message can contain markdown formatted text.

Instead of Yes/No, custom options can be displayed by separating them with `--`:
```
{command} What is your favourite colour? --Red --Green --Blue
```

Additionally there are some special options that change the appearance and/or behaviour of the poll:
- `--progress`: Show the number of votes while the poll is running.
- `--noprogress`: Don't show the number of votes while the poll is running.
- `--public`: Show which user voted for what at the end of the poll
- `--anonym`: Don't show which user voted for what at the end of the poll
- `--votes=X`: Allows users to place a total of X votes.  Default is 1.  Each individual option can still only be voted once.
- `--bars`: Show results as a bar chart at the end of the poll.
- `--nobars`: Don't show the bar chart at the end of the poll.
- `--locale=X`: Use a specific locale for the poll. Supported values are en and de. By default your account language is used.

Each of these options is case sensitive and must appear alone, e.g.:
```
{command} Please place your orders --Pizza --Burger --Fries --public --votes=3
```
