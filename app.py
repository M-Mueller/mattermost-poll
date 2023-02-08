# -*- coding: utf-8 -*-
import warnings
import logging
import re
import io
import os.path
from collections import namedtuple

import PIL.Image

from flask import Flask, request, jsonify, abort, send_file
from flask_babel import Babel, gettext as tr
import flask_babel

from poll import Poll, NoMoreVotesError, InvalidPollError
from formatters import format_help, format_poll, format_user_vote
from mattermost_api import user_locale, is_admin_user, is_team_admin
import settings


app = Flask(__name__)
app.logger.propagate = True

babel = Babel(app)

try:  # pragma: no cover
    if settings.APPLY_PROXY_FIX:
        # respect X-Forwarded-Proto from proxy server (see #21)
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)
except AttributeError:  # pragma: no cover
    pass

# Add missing settings
if not hasattr(settings, 'PUBLIC_BY_DEFAULT'):
    settings.PUBLIC_BY_DEFAULT = False
if not hasattr(settings, 'PROGRESS_BY_DEFAULT'):
    settings.PROGRESS_BY_DEFAULT = True
if not hasattr(settings, 'BARS_BY_DEFAULT'):
    settings.BARS_BY_DEFAULT = True
if not hasattr(settings, 'BAR_IMG_URL'):
    settings.BAR_IMG_URL = None
if not hasattr(settings, 'DEFAULT_QUESTION'):
    settings.DEFAULT_QUESTION = ''
if not hasattr(settings, 'DEFAULT_VOTES'):
    settings.DEFAULT_VOTES = []


def parse_slash_command(command):
    """Parses a slash command for supported arguments.
    Receives the form data of the request and returns all found arguments.
    Arguments are separated by '--'.
    Supported arguments:
        - message: str
        - vote_options: list of str
        - secret: boolean (deprecated)
        - progress: boolean
        - noprogress: boolean
        - public: boolean
        - anonym: boolean
        - num_votes: int
        - bars: boolean
        - nobars: boolean
        - locale: str
    """
    args = [arg.strip() for arg in command.split('--')]
    if not args[0]:
        message = settings.DEFAULT_QUESTION
        vote_options = settings.DEFAULT_VOTES
    else:
        message = args[0]
        vote_options = []
    progress = settings.PROGRESS_BY_DEFAULT
    public = settings.PUBLIC_BY_DEFAULT
    bars = settings.BARS_BY_DEFAULT
    locale = ''
    max_votes = 1
    for arg in args[1:]:
        if arg == 'secret' or arg == 'noprogress':
            progress = False
        elif arg == 'progress':
            progress = True
        elif arg == 'public':
            public = True
        elif arg == 'anonym':
            public = False
        elif arg == 'bars':
            bars = True
        elif arg == 'nobars':
            bars = False
        elif arg.startswith('locale'):
            try:
                _, locale = arg.split('=')
            except ValueError:
                pass
        elif arg.startswith('votes'):
            try:
                _, max_votes_str = arg.split('=')
                max_votes = max(1, int(max_votes_str))
            except ValueError:
                pass
        else:
            vote_options.append(arg)

    Arguments = namedtuple('Arguments', ['message', 'vote_options',
                                         'progress', 'public', 'max_votes',
                                         'bars', 'locale'])
    return Arguments(message, vote_options, progress,
                     public, max_votes, bars, locale)


@babel.localeselector
def get_locale():
    """Returns the locale for the current request."""
    try:
        return user_locale(request.user_id)
    except AttributeError as e:
        app.logger.warning(e)
    return "en"


@app.after_request
def log_response(response):
    """Logs the complete response for debugging."""
    if app.logger.isEnabledFor(logging.DEBUG):
        app.logger.debug('Response status: %s', response.status)
        if not response.direct_passthrough:  # excludes send_file
            app.logger.debug('Response data: %s',
                             response.get_data().decode('utf-8'))
    return response


@app.route('/', methods=['GET'])
def status():
    """Returns a simple message if the server is running."""
    return tr("Poll server is running")


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
                'text': tr("The integration is not correctly set up: "
                           "Invalid token.")
            })

    if 'user_id' not in request.form:
        abort(400)
    if 'text' not in request.form:
        abort(400)
    user_id = request.form['user_id']
    request.user_id = user_id

    app.logger.debug('Received command: %s', request.form['text'])

    # the poll should have a fixed locale, otherwise it
    # changes for everyone every time someone votes
    locale = flask_babel.get_locale().language

    if request.form['text'].strip() == 'help':
        return jsonify({
            'response_type': 'ephemeral',
            'text': format_help(request.form['command'], locale)
        })

    args = parse_slash_command(request.form['text'])
    if not args.message:
        text = tr("**Please provide a message.**\n\n"
                  "**Usage:**\n{help}").format(
                      help=format_help(request.form['command'], locale))
        return jsonify({
            'response_type': 'ephemeral',
            'text': text
        })
    if args.public:
        if not settings.MATTERMOST_URL or not settings.MATTERMOST_PA_TOKEN:
            return jsonify({
                'response_type': 'ephemeral',
                'text': tr("Public polls are not available with the "
                           "current setup. Please check with you "
                           "system administrator.")
            })

    if args.locale:
        locale = args.locale

    poll = Poll.create(user_id,
                       message=args.message,
                       locale=locale,
                       vote_options=args.vote_options,
                       secret=not args.progress,
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
    request.user_id = user_id

    try:
        poll = Poll.load(poll_id)
    except InvalidPollError:
        return jsonify({
            'ephemeral_text': tr("This poll is not valid anymore.\n"
                                 "Sorry for the inconvenience.")
        })

    app.logger.info('Voting in poll "%s" for user "%s": %i',
                    poll_id, user_id, vote_id)
    try:
        poll.vote(user_id, vote_id)
    except NoMoreVotesError:
        return jsonify({
            'ephemeral_text': tr("You already used all your votes.\n"
                                 "Click on a vote to unselect it again.")
        })

    return jsonify({
        'update': {
            'props': format_poll(poll)
        },
        'ephemeral_text': tr("Your vote has been updated:\n{}").format(
            format_user_vote(poll, user_id))
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
    team_id = json['team_id']
    poll_id = json['context']['poll_id']
    request.user_id = user_id

    try:
        poll = Poll.load(poll_id)
    except InvalidPollError:
        return jsonify({
            'ephemeral_text': tr("This poll is not valid anymore.\n"
                                 "Sorry for the inconvenience.")
        })

    app.logger.info('Ending poll "%s"', poll_id)

    # only the creator and admins may end a poll
    can_end_poll = \
        user_id == poll.creator_id or \
        is_admin_user(user_id) or \
        is_team_admin(user_id=user_id, team_id=team_id)

    if can_end_poll:
        poll.end()
        return jsonify({
            'update': {
                'props': format_poll(poll)
            }
        })

    return jsonify({
        'ephemeral_text': tr("You are not allowed to end this poll")
    })


bar_image_pattern = re.compile("^bar_(\d{1,3}).png$")
bar_image = PIL.Image.open(os.path.join(app.root_path, 'img', 'bar.png'))


@app.route('/img/<path:filename>')
def send_img(filename):
    match = re.match(bar_image_pattern, filename)
    if match:
        # resize the 1px template image to the requested width
        bar_width = int(match[1])
        bar_resized = bar_image.resize((bar_width, bar_image.height))
        buffer = io.BytesIO()
        bar_resized.save(buffer, "PNG")
        buffer.seek(0)
        return send_file(buffer, mimetype="image/png")
    else:
        raise ValueError("Invalid bar image path")
