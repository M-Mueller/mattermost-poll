# -*- coding: utf-8 -*-
import warnings
import logging
from collections import namedtuple

from flask import Flask, request, jsonify, abort, send_from_directory

from poll import Poll, NoMoreVotesError, InvalidPollError
from formatters import format_help, format_poll, format_user_vote
import settings

app = Flask(__name__)
app.logger.propagate = True


def parse_slash_command(command):
    """Parses a slash command for supported arguments.
    Receives the form data of the request and returns all found arguments.
    Arguments are separated by '--'.
    Supported arguments:
        - message: str
        - vote_options: list of str
        - secret: boolean
        - public: boolean
        - num_votes: int
        - bars: boolean
    """
    args = [arg.strip() for arg in command.split('--')]
    secret = False
    public = False
    bars = False
    max_votes = 1
    try:
        i = [a for a in args].index('secret')
        args.pop(i)
        secret = True
    except:
        pass

    try:
        i = [a for a in args].index('public')
        args.pop(i)
        public = True
    except:
        pass
    try:
        i = [a for a in args].index('bars')
        args.pop(i)
        bars = True
    except:
        pass

    try:
        votes = [a for a in enumerate(args) if 'votes' in a[1].lower()]
        if len(votes) > 0:
            args.pop(votes[0][0])
            max_votes = int(votes[0][1].split('=')[1])
            max_votes = max(1, max_votes)
    except:
        pass

    message = args[0] if args else ''
    vote_options = args[1:] if args else []

    Arguments = namedtuple('Arguments', ['message', 'vote_options',
                                         'secret', 'public',
                                         'max_votes', 'bars'])
    return Arguments(message, vote_options, secret, public, max_votes, bars)


@app.after_request
def log_response(response):
    """Logs the complete response for debugging."""
    if app.logger.isEnabledFor(logging.DEBUG):
        app.logger.debug('Response status: %s', response.status)
        if not response.direct_passthrough:  # excludes send_from_directory
            app.logger.debug('Response data: %s',
                             response.get_data().decode('utf-8'))
    return response


@app.route('/', methods=['GET'])
def status():
    """Returns a simple message if the server is running."""
    return "Poll server is running"


@app.route('/', methods=['POST'])
def poll():
    """Creates a new poll.
    Directly called by Mattermost.
    Example response data:
    ```
    {
        "response_type": "in_channel",
        "attachments": [{
            "text": "<Poll message>",
            "actions": [
            {
                "name": "<First Option> (0)",
                "integration": {
                    "context": {
                        "poll_id": "<unique_id>",
                        "vote": 0
                    },
                    "url": "http://<hostname:port>/vote"
                }
            },
            ... additional entries for all poll options ...
            {
                "name": "End Poll",
                "integration": {
                    "url": "http://<hostname:port>/end",
                    "context": {
                        "poll_id": "<unique_id>"
                    }
                }
            }],
            "fields": [
            {
                "short": false,
                "title": "",
                "value": "Number of Votes: 1"
            }]
        }]
    }
    ```
    """
    if hasattr(settings, 'MATTERMOST_TOKEN'):
        warnings.warn("MATTERMOST_TOKEN is deprecated, use MATTERMOST_TOKENS \
                      instead", category=DeprecationWarning)
        settings.MATTERMOST_TOKENS = [settings.MATTERMOST_TOKEN]
        settings.MATTERMOST_TOKEN = None

    if settings.MATTERMOST_TOKENS:
        token = request.form['token']
        if token not in settings.MATTERMOST_TOKENS:
            return jsonify({
                'response_type': 'ephemeral',
                'text': "The integration is not correctly set up: Invalid token."
            })

    if 'user_id' not in request.form:
        abort(400)
    if 'text' not in request.form:
        abort(400)
    user_id = request.form['user_id']

    app.logger.debug('Received command: %s', request.form['text'])

    if request.form['text'].strip() == 'help':
        return jsonify({
            'response_type': 'ephemeral',
            'text': format_help(request.form['command'])
        })

    args = parse_slash_command(request.form['text'])
    if not args.message:
        return jsonify({
            'response_type': 'ephemeral',
            'text': "**Please provide a message.**\n\n**Usage:**\n{}"
                    .format(format_help(request.form['command']))
        })
    if args.public:
        if not settings.MATTERMOST_URL or not settings.MATTERMOST_PA_TOKEN:
            return jsonify({
                'response_type': 'ephemeral',
                'text': "Public polls are not available with the "
                        "current setup. Please check with you "
                        "system administrator."
            })

    poll = Poll.create(user_id,
                       message=args.message,
                       vote_options=args.vote_options,
                       secret=args.secret,
                       public=args.public,
                       max_votes=args.max_votes,
                       bars=args.bars)

    app.logger.info('Creating Poll: %s', poll.id)

    return jsonify(format_poll(poll))


@app.route('/vote', methods=['POST'])
def vote():
    """Places a vote for a user.
    Called through the URL in the corresponding action (see
    formatters.format_actions).
    The JSON `context` is expected to contain a valid poll_id and the
    vote_id to vote for.
    """
    json = request.get_json()
    user_id = json['user_id']
    poll_id = json['context']['poll_id']
    vote_id = json['context']['vote']

    try:
        poll = Poll.load(poll_id)
    except InvalidPollError:
        return jsonify({
            'ephemeral_text': "This poll is not valid anymore.\n"
                              "Sorry for the inconvenience."
        })

    app.logger.info('Voting in poll "%s" for user "%s": %i',
                    poll_id, user_id, vote_id)
    try:
        poll.vote(user_id, vote_id)
    except NoMoreVotesError:
        return jsonify({
            'ephemeral_text': "You already used all your votes.\n"
                              "Click on a vote to unselect it again."
        })

    return jsonify({
        'update': {
            'props': format_poll(poll)
        },
        'ephemeral_text': "Your vote has been updated:\n{}"
                          .format(format_user_vote(poll, user_id))
    })


@app.route('/end', methods=['POST'])
def end_poll():
    """Ends the poll.
    Called by the 'End Poll' actions.
    Only the user that created the poll is allowed to end it.
    All other user will receive an ephemeral error message.
    """
    json = request.get_json()
    user_id = json['user_id']
    poll_id = json['context']['poll_id']

    try:
        poll = Poll.load(poll_id)
    except InvalidPollError:
        return jsonify({
            'ephemeral_text': "This poll is not valid anymore.\n"
                              "Sorry for the inconvenience."
        })

    app.logger.info('Ending poll "%s"', poll_id)
    if user_id == poll.creator_id:
        # only the creator may end a poll
        poll.end()
        return jsonify({
            'update': {
                'props': format_poll(poll)
            }
        })

    return jsonify({
        'ephemeral_text': "You are not allowed to end this poll"
    })


@app.route('/img/<path:filename>')
def send_img(filename):
    return send_from_directory('img', filename)
