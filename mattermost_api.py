# -*- coding: utf-8 -*-
import json
import logging
import requests

import settings

logger = logging.getLogger('flask.app')


def user_locale(user_id):
    """Returns the locale of the user with the given user_id."""
    if not settings.MATTERMOST_PA_TOKEN:
        return "en"

    try:
        header = {'Authorization': 'Bearer ' + settings.MATTERMOST_PA_TOKEN}
        url = settings.MATTERMOST_URL + '/api/v4/users/' + user_id

        r = requests.get(url, headers=header)
        if r.ok:
            locale = json.loads(r.text)['locale']
            if locale:
                return locale
    except KeyError as e:
        logger.error(e)
    return "en"


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
