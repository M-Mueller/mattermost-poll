# -*- coding: utf-8 -*-
import os.path

from flask import url_for
from flask_babel import force_locale, gettext as tr, ngettext

import settings
from mattermost_api import resolve_usernames


def _is_superfluous(line):
    """
    Check if a description of an option is superfluous
    because the option is set by default.
    """
    options_for_setting = {
        "PUBLIC_BY_DEFAULT": ["anonym", "public"],
        "PROGRESS_BY_DEFAULT": ["noprogress", "progress"],
        "BARS_BY_DEFAULT": ["nobars", "bars"],
    }
    for setting, args in options_for_setting.items():
        index = int(getattr(settings, setting))
        superfluous_option = "- `--{}`".format(args[index])
        if line.startswith(superfluous_option):
            return True
    return False


def format_help(command, locale='en'):
    """Returns a help string describing the poll slash command."""
    help_lines = []

    help_file = os.path.join(
        os.path.dirname(__file__),
        'translations',
        locale,
        'help.md'
    )
    try:
        with open(help_file) as f:
            help_lines = f.readlines()
    except FileNotFoundError:
        if locale != 'en':
            return format_help(command, 'en')

    if not help_lines:
        return tr("Help file not found.")  # pragma: no cover

    # remove the description of all superfluous options
    help_text = ''.join([
        line
        for line
        in help_lines
        if not _is_superfluous(line)
    ])

    # replace placeholder for slash command
    help_text = help_text.format(command=command)

    return help_text


def format_poll(poll):
    """Returns the JSON representation of the given poll.
    """
    with force_locale(poll.locale):
        if poll.is_finished():
            return _format_finished_poll(poll)
        return _format_running_poll(poll)


def _format_running_poll(poll):
    fields = [{
        'short': False,
        'value': tr("*Number of voters: {}*").format(poll.num_voters()),
        'title': ""
    }]
    if poll.public:
        fields += [{
            'short': False,
            'value': tr(":warning: *This poll is public. When it closes the"
                        " participants and their answers will be visible.*"),
            'title': ""
        }]
    if poll.max_votes > 1:
        fields += [{
            'short': False,
            'value': tr("*You have {} votes*").format(poll.max_votes),
            'title': ""
        }]
    if not poll.secret and poll.bars:
        votes = [
            (vote, vote_id)
            for vote_id, vote
            in enumerate(poll.vote_options)
            if poll.count_votes(vote_id) > 0
        ]

        fields += [{
            'short': False,
            'title': vote,
            'value': _format_vote_end_text(poll, vote_id)
        } for vote, vote_id in votes]

    return {
        'response_type': 'in_channel',
        'attachments': [{
            'text': poll.message,
            'actions': format_actions(poll),
            'fields': fields
        }]
    }


def _format_finished_poll(poll):
    votes = [
        (vote, vote_id)
        for vote_id, vote
        in enumerate(poll.vote_options)
    ]

    return {
        'response_type': 'in_channel',
        'attachments': [{
            'text': poll.message,
            'fields': [{
                'short': False,
                'value': tr("*Number of voters: {}*").format(
                    poll.num_voters()),
                'title': ""
            }] + [{
                'short': not poll.bars,
                'title': vote,
                'value': _format_vote_end_text(poll, vote_id)
            } for vote, vote_id in votes]
        }]
    }


def _format_vote_end_text(poll, vote_id):
    vote_count = poll.count_votes(vote_id)
    total_votes = poll.num_votes()
    if total_votes != 0:
        rel_vote_count = 100*vote_count/total_votes
    else:
        rel_vote_count = 0.0

    text = ''

    if poll.bars:
        bar_min_width = 2  # even 0% should show a tiny bar
        bar_width = max(bar_min_width, int(450*rel_vote_count/100))
        if settings.BAR_IMG_URL:
            # resize the image with markdown (won't work in native apps though)
            text += '![Bar]({} ={}x25) '.format(settings.BAR_IMG_URL, bar_width)
        else:
            # send_img will dynamically create a correctly sized bar for us
            filename = "bar_{}.png".format(bar_width)
            png_path = url_for('send_img', filename=filename, _external=True)
            text += '![Bar]({}) '.format(png_path)

    votes = ngettext('%(num)d Vote', '%(num)d Votes', vote_count)
    text += '{} ({:.1f}%)'.format(votes, rel_vote_count)

    if poll.public:
        voters = resolve_usernames(poll.voters(vote_id))

        if len(voters):
            text += '\n' + ', '.join(voters)

    return text


def format_actions(poll):
    """Returns the JSON data of all available actions of the given poll.
    Additional to the options of the poll, a 'End Poll' action
    is appended.
    The returned list looks similar to this:
    ```
    [{
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
    }]
    ```
    """
    with force_locale(poll.locale):
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
            'name': tr("End Poll"),
            'integration': {
                'url': url_for('end_poll', _external=True),
                'context': {
                    'poll_id': poll.id
                }
            }
        })
        return actions


def format_user_vote(poll, user_id):
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
