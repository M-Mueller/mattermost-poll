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
Additionally there are some special options that change the appearance and/or behaviour of the plot:
- `--secret`: Do not display the number of votes until the poll is ended
- `--public`: Show who voted for what at the end of the poll
- `--votes=X`: Allows users to place a total of X votes.  Default is 1.  Each individual option can still only be voted once.
- `--bars`: Show results as a bar chart at the end of the poll.
Each of these options is case sensitive and must appear alone, e.g.:
```
{command} Please place your orders --Pizza --Burger --Fries --public --votes=3
```
