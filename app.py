# -*- coding: utf-8 -*-
from poll import Poll, NoMoreVotesError
from flask import Flask, request, jsonify, url_for, abort
from collections import namedtuple
import settings
import logging

app = Flask(__name__)
app.logger.setLevel(logging.INFO)


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


def _format_vote_count(poll, vote_count):
    """Returns the number of votes as a string for display."""
    total_votes = poll.num_votes()
    if total_votes != 0:
        rel_vote_count = 100*vote_count/total_votes
    else:
        rel_vote_count = 0.0
    return '{} ({:.1f}%)'.format(vote_count, rel_vote_count)


def get_poll(poll):
    """Returns the JSON representation of the given poll.
    """
    if not poll.is_finished():
        fields = [{
            'short': False,
            'value': "*Number of voters: {}*".format(poll.num_voters()),
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
        votes = [(vote, poll.count_votes(vote_id)) for vote_id, vote in
                 enumerate(poll.vote_options)]
        return {
            'response_type': 'in_channel',
            'attachments': [{
                'text': poll.message,
                'fields': [{
                    'short': False,
                    'value': "*Number of voters: {}*".format(poll.num_voters()),
                    'title': ""
                }] +
                [{
                    'short': True,
                    'title': vote,
                    'value': _format_vote_count(poll, vote_count)
                } for vote, vote_count in votes]
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
    """
    args = [arg.strip() for arg in command.split('--')]
    secret = False
    max_votes = 1
    try:
        i = [a.lower() for a in args].index('secret')
        args.pop(i)
        secret = True
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
                                         'secret', 'max_votes'])
    if args:
        return Arguments(args[0], args[1:], secret, max_votes)
    else:
        return Arguments('', [], secret, max_votes)


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
    if settings.MATTERMOST_TOKEN:
        token = request.form['token']
        if token != settings.MATTERMOST_TOKEN:
            return jsonify({
                'response_type': 'ephemeral',
                'text': "The integration is not correctly set up: Invalid token."
            })

    if 'user_id' not in request.form:
        abort(400)
    if 'text' not in request.form:
        abort(400)
    user_id = request.form['user_id']

    args = parse_slash_command(request.form['text'])
    if not args.message:
        return jsonify({
            'response_type': 'ephemeral',
            'text': "Please provide a message"
        })

    poll = Poll.create(user_id, args.message, args.vote_options,
                       args.secret, args.max_votes)

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

    poll = Poll.load(poll_id)

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

    poll = Poll.load(poll_id)

    app.logger.info('Ending poll "%s"', poll_id)
    if user_id == poll.creator_id:
        # only the creator may end a poll
        poll.end()
        return jsonify({
            'update': {
                'props': get_poll(poll)
            }
        })
    else:
        return jsonify({
            'ephemeral_text': "You are not allowed to end this poll"
        })
