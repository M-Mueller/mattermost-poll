# -*- coding: utf-8 -*-
import json
import logging
import requests

import settings

logger = logging.getLogger('flask.app')


def get_user(user_id):
    """Return the json data of the user."""
    if not settings.MATTERMOST_PA_TOKEN:
        return {}

    try:
        header = {'Authorization': 'Bearer ' + settings.MATTERMOST_PA_TOKEN}
        url = settings.MATTERMOST_URL + '/api/v4/users/' + user_id

        r = requests.get(url, headers=header)
        if r.ok:
            return json.loads(r.text)
    except KeyError as e:
        logger.error(e)
    return {}


def user_locale(user_id):
    """Return the locale of the user with the given user_id."""
    if not settings.MATTERMOST_PA_TOKEN:
        return "en"

    user = get_user(user_id)
    if 'locale' in user:
        locale = user['locale']
        if locale:
            return locale

    return "en"


def is_admin_user(user_id):
    """Return whether the user is an admin."""

    user = get_user(user_id)
    if 'roles' in user:
        return 'system_admin' in user['roles']

    return False


def is_team_admin(user_id, team_id):
    """Return whether the user is an admin in the given team."""
    if not settings.MATTERMOST_PA_TOKEN:
        return False

    try:
        header = {'Authorization': 'Bearer ' + settings.MATTERMOST_PA_TOKEN}
        url = settings.MATTERMOST_URL + '/api/v4/teams/' + team_id + '/members/' + user_id

        r = requests.get(url, headers=header)
        if r.ok:
            roles = json.loads(r.text)['roles']
            return 'team_admin' in roles
    except KeyError as e:
        logger.error(e)

    return False


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
        logger.error('Username query failed: %s', str(e))

    return ['<Failed to resolve usernames>']
