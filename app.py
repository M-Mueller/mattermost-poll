# -*- coding: utf-8 -*-
import warnings
import json
import logging
import os.path
from collections import namedtuple

import requests
from flask import Flask, request, jsonify, url_for, abort

from poll import Poll, NoMoreVotesError, InvalidPollError
import settings

app = Flask(__name__)


def get_help(command):
    """Returns a help string describing the poll slash command."""
    help_file = os.path.join(os.path.dirname(__file__), 'help.md')
    with open(help_file) as f:
        return f.read().format(command=command)
    return "Help file not found."""


def get_actions(poll):
    """Returns the JSON data of all available actions of the given poll.
    Additional to the options of the poll, a 'End Poll' action
    is appended.
    """
    options = poll.vote_options
    name = "{name}"
    if not poll.secret:
        # display current number of votes
        name += " ({votes})"
    actions = [{
        'name': name.format(name=vote, votes=poll.count_votes(vote_id)),
        'integration': {
            'url': url_for('vote', _external=True),
            'context': {
                'vote': vote_id,
                'poll_id': poll.id
            }
        }
    } for vote_id, vote in enumerate(options)]
    # add action to end the poll
    actions.append({
        'name': "End Poll",
        'integration': {
            'url': url_for('end_poll', _external=True),
            'context': {
                'poll_id': poll.id
            }
        }
    })
    return actions


def resolve_usernames(user_ids):
    """Resolve the list of user ids to list of user names."""
    if len(user_ids) == 0:
        return []

    try:
        header = {'Authorization': 'Bearer ' + settings.MATTERMOST_PA_TOKEN}
        url = settings.MATTERMOST_URL + '/api/v4/users/ids'

        r = requests.post(url, headers=header, json=user_ids)
        if r.ok:
            return [user["username"] for user in json.loads(r.text)]
    except Exception as e:
        app.logger.error('Username query failed: %s', str(e))

    return ['<Failed to resolve usernames>']


def _format_vote_end_text(poll, vote_id):
    vote_count = poll.count_votes(vote_id)
    total_votes = poll.num_votes()
    if total_votes != 0:
        rel_vote_count = 100*vote_count/total_votes
    else:
        rel_vote_count = 0.0
    text = '{} ({:.1f}%)'.format(vote_count, rel_vote_count)

    if poll.public:
        voters = resolve_usernames(poll.voters(vote_id))

        if len(voters):
            text += '\n' + ', '.join(voters)

    return text


def get_poll(poll):
    """Returns the JSON representation of the given poll.
    """
    if not poll.is_finished():
        fields = [{
            'short': False,
            'value': "*Number of voters: {}*".format(poll.num_voters()),
            'title': ""
        }]
        if poll.public:
            fields += [{
                'short': False,
                'value': ":warning: *This poll is public. When it closes the"
                         " participants and their answers will be visible.*",
                'title': ""
            }]
        if poll.max_votes > 1:
            fields += [{
                'short': False,
                'value': "*You have {} votes*".format(poll.max_votes),
                'title': ""
            }]

        return {
            'response_type': 'in_channel',
            'attachments': [{
                'text': poll.message,
                'actions': get_actions(poll),
                'fields': fields
            }]
        }
    else:
        votes = [(vote, vote_id) for vote_id, vote in
                 enumerate(poll.vote_options)]
        return {
            'response_type': 'in_channel',
            'attachments': [{
                'text': poll.message,
                'fields': [{
                    'short': False,
                    'value': "*Number of voters: {}*".format(poll.num_voters()),
                    'title': ""
                }] + [{
                    'short': True,
                    'title': vote,
                    'value': _format_vote_end_text(poll, vote_id)
                } for vote, vote_id in votes]
            }]
        }


def vote_to_string(poll, user_id):
    """Returns the vote of the given user as a string.
       Example: 'Pizza ✓, Burger ✗, Extra Cheese ✓'"""
    string = ''
    for vote_id, vote in enumerate(poll.vote_options):
        string += vote
        if vote_id in poll.votes(user_id):
            string += ' ✓'
        else:
            string += ' ✗'
        string += ', '
    return string[:-2]  # remove trailing ,


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
    """
    args = [arg.strip() for arg in command.split('--')]
    secret = False
    public = False
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
        votes = [a for a in enumerate(args) if 'votes' in a[1].lower()]
        if len(votes) > 0:
            args.pop(votes[0][0])
            max_votes = int(votes[0][1].split('=')[1])
            max_votes = max(1, max_votes)
    except:
        pass

    Arguments = namedtuple('Arguments', ['message', 'vote_options',
                                         'secret', 'public', 'max_votes'])
    if args:
        return Arguments(args[0], args[1:], secret, public, max_votes)
    else:
        return Arguments('', [], secret, public, max_votes)


@app.after_request
def log_response(response):
    """Logs the complete response for debugging."""
    if app.logger.isEnabledFor(logging.DEBUG):
        app.logger.debug('Response status: %s', response.status)
        app.logger.debug('Response data: %s', response.get_data().decode('utf-8'))
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
            'text': get_help(request.form['command'])
        })

    args = parse_slash_command(request.form['text'])
    if not args.message:
        return jsonify({
            'response_type': 'ephemeral',
            'text': "Please provide a message"
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
                       max_votes=args.max_votes)

    app.logger.info('Creating Poll: %s', poll.id)

    return jsonify(get_poll(poll))


@app.route('/vote', methods=['POST'])
def vote():
    """Places a vote for a user.
    Called through the URL in the corresponding action (see get_actions).
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
            'props': get_poll(poll)
        },
        'ephemeral_text': "Your vote has been updated:\n{}"
                          .format(vote_to_string(poll, user_id))
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
                'props': get_poll(poll)
            }
        })

    return jsonify({
        'ephemeral_text': "You are not allowed to end this poll"
    })
