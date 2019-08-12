# pylint: disable=missing-docstring
import json
import jsonschema
import pytest
import app
import settings
from tests import schemas


@pytest.fixture
def base_url():
    return 'http://www.example.com:5005/'


@pytest.fixture
def client():
    app.app.testing = True
    return app.app.test_client()


def test_status(base_url, client):
    response = client.get('/', base_url=base_url)
    assert response.status_code == 200


def test_no_username(base_url, client):
    response = client.post('/', base_url=base_url)
    assert response.status_code == 400
    assert response.data.decode('utf-8')


def __validate_reponse(base_url, response_json, message, vote_options):
    """Validates the response against the json schema expected by
    Mattermost.
    """
    # validate the schema
    jsonschema.validate(response_json, schemas.poll)

    # validate the values
    assert response_json['attachments'][0]['text'] == message
    actions = response_json['attachments'][0]['actions']
    assert len(actions) == len(vote_options) + 1

    for action, vote in zip(actions[:-1], vote_options):
        assert vote in action['name']
        integration = action['integration']
        assert integration['url'] == base_url + 'vote'

    integration = actions[-1]['integration']
    assert integration['url'] == base_url + 'end'


def __validate_vote_response(base_url, response_json, message, vote_options,
                             voted_id):
    """Validates the response after a vote."""
    jsonschema.validate(response_json, schemas.vote)

    if 'update' in response_json:
        poll_json = response_json['update']['props']
        __validate_reponse(base_url, poll_json, message, vote_options)


def __validate_end_response(response_json, message, vote_options):
    """Validates the response when the vote ends."""
    jsonschema.validate(response_json, schemas.end)

    # check if all fields are there (content of fields is
    # tested in test_app)
    fields = response_json['update']['props']['attachments'][0]['fields']
    assert len(fields) == len(vote_options) + 1


@pytest.mark.parametrize('data, status_code, message, vote_options', [
    ({}, 400, 'Message', ['Yes', 'No']),
    ({'user_id': 'user0'}, 400, '', ['Yes', 'No']),
    ({'text': 'bla'}, 400, '', ['Yes', 'No']),
    ({'user_id': 'user0', 'text': 'Poll message'}, 200, 'Poll message', ['Yes', 'No']),
    ({'user_id': 'user0', 'text': 'Poll message --First --Second --Third'}, 200, 'Poll message', ['First', 'Second', 'Third']),
], ids=['No data', 'No test', 'No user_id', 'Defaults options', 'Explicit options'])
def test_poll(base_url, client, data, status_code, message, vote_options):
    response = client.post('/', data=data, base_url=base_url)
    assert response.status_code == status_code
    if status_code != 200:
        return

    rd = json.loads(response.data.decode('utf-8'))
    __validate_reponse(base_url, rd, message, vote_options)


def test_poll_no_message(base_url, client):
    data = {
        'user_id': 'user0',
        'text': '',
        'command': '/poll',
    }
    response = client.post('/', data=data, base_url=base_url)
    assert response.status_code == 200

    rd = json.loads(response.data.decode('utf-8'))
    jsonschema.validate(rd, schemas.ephemeral)


@pytest.mark.parametrize('max_votes, votes, expected', [
    (1, [('user2', 2)], (0, 0, 1)),
    (1, [('user0', 0), ('user1', 1), ('user2', 2)], (1, 1, 1)),
    (1, [('user0', 0), ('user1', 1), ('user0', 1)], (0, 2, 0)),
    (2, [('user0', 0), ('user1', 1), ('user0', 1)], (1, 2, 0)),
    (2, [('user0', 0), ('user0', 1), ('user0', 1)], (1, 0, 0)),
    (2, [('user0', 0), ('user0', 1), ('user0', 2)], (1, 1, 0)),

], ids=['1 vote', '3 votes', 'Changed votes', 'Multi, 3 votes',
        'Multi, unvote', 'Multi, overvote'])
def test_vote(base_url, client, max_votes, votes, expected):
    command = '''Message --Spam --Foo --Bar --votes={}'''.format(max_votes)

    # create a new poll
    data = {
        'user_id': 'user0',
        'text': command
    }
    response = client.post('/', data=data, base_url=base_url)
    rd = json.loads(response.data.decode('utf-8'))

    actions = rd['attachments'][0]['actions']
    assert len(actions) == 4
    action_urls = [a['integration']['url'].replace(base_url, '')
                   for a in actions]
    action_contexts = [a['integration']['context'] for a in actions]

    # place votes by calling the url in the action with the
    # corresponding context (i.e. what Mattermost is doing)
    for user, vote in votes:
        url = action_urls[vote]
        context = action_contexts[vote]
        data = json.dumps({
            'user_id': user,
            'context': context
        })
        response = client.post(url, data=data,
                               content_type='application/json',
                               base_url=base_url)
        assert response.status_code == 200

        rd = json.loads(response.data.decode('utf-8'))
        __validate_vote_response(base_url, rd, 'Message',
                                 ['Spam', 'Foo', 'Bar'], vote)

    if 'update' in rd:
        # check if the number of votes is contained in the actions name
        actions = rd['update']['props']['attachments'][0]['actions']
        assert len(actions) == 4
        for action, num_votes in zip(actions, expected):
            assert str(num_votes) in action['name']


@pytest.mark.parametrize('votes, expected', [
    ([], (0, 0, 0)),
    ([('user0', 0), ('user1', 1), ('user2', 2)], (1, 1, 1)),

], ids=['No votes', '3 votes'])
def test_end(base_url, client, votes, expected):
    # create a new poll
    data = {
        'user_id': 'user0',
        'text': 'Message --Spam --Foo --Bar'
    }
    response = client.post('/', data=data, base_url=base_url)
    rd = json.loads(response.data.decode('utf-8'))

    actions = rd['attachments'][0]['actions']
    assert len(actions) == 4
    action_urls = [a['integration']['url'].replace(base_url, '')
                   for a in actions]
    action_contexts = [a['integration']['context'] for a in actions]

    # place the votes
    for user, vote in votes:
        url = action_urls[vote]
        context = action_contexts[vote]
        data = json.dumps({
            'user_id': user,
            'context': context
        })
        response = client.post(url, data=data,
                               content_type='application/json',
                               base_url=base_url)
        assert response.status_code == 200

    context = action_contexts[-1]
    data = json.dumps({
        'user_id': 'user0',
        'team_id': 'team0',
        'context': context
    })
    response = client.post(action_urls[-1], data=data,
                           content_type='application/json',
                           base_url=base_url)
    assert response.status_code == 200

    rd = json.loads(response.data.decode('utf-8'))
    __validate_end_response(rd, 'Message', ['Spam', 'Foo', 'Bar'])


def test_end_wrong_user(base_url, client):
    # create a new poll
    data = {
        'user_id': 'user0',
        'text': 'Message'
    }
    response = client.post('/', data=data, base_url=base_url)
    rd = json.loads(response.data.decode('utf-8'))

    actions = rd['attachments'][0]['actions']
    action_urls = [a['integration']['url'].replace(base_url, '')
                   for a in actions]
    action_contexts = [a['integration']['context'] for a in actions]

    context = action_contexts[-1]
    data = json.dumps({
        'user_id': 'user1',
        'team_id': 'team0',
        'context': context
    })
    response = client.post(action_urls[-1], data=data,
                           content_type='application/json',
                           base_url=base_url)
    assert response.status_code == 200

    rd = json.loads(response.data.decode('utf-8'))
    assert 'update' not in rd
    assert 'ephemeral_text' in rd
    assert rd['ephemeral_text'] == 'You are not allowed to end this poll'


def patched_is_admin_user(user_id):
    if user_id == 'user1':
        return True
    return False


def test_end_admin(mocker, base_url, client):
    mocker.patch('app.is_admin_user', new=patched_is_admin_user)

    # create a new poll
    data = {
        'user_id': 'user0',
        'text': 'Message'
    }
    response = client.post('/', data=data, base_url=base_url)
    rd = json.loads(response.data.decode('utf-8'))

    actions = rd['attachments'][0]['actions']
    action_urls = [a['integration']['url'].replace(base_url, '')
                   for a in actions]
    action_contexts = [a['integration']['context'] for a in actions]

    context = action_contexts[-1]
    data = json.dumps({
        'user_id': 'user1',
        'team_id': 'team0',
        'context': context
    })
    response = client.post(action_urls[-1], data=data,
                           content_type='application/json',
                           base_url=base_url)
    assert response.status_code == 200

    rd = json.loads(response.data.decode('utf-8'))
    __validate_end_response(rd, 'Message', ['Yes', 'No'])


def test_vote_invalid_poll(base_url, client):
    data = json.dumps({
        'user_id': 'user0',
        'context': {
            'poll_id': 'invalid123',
            'vote': 0
        }
    })
    response = client.post('/vote', data=data,
                           content_type='application/json',
                           base_url=base_url)
    assert response.status_code == 200

    rd = json.loads(response.data.decode('utf-8'))
    assert 'update' not in rd
    assert 'ephemeral_text' in rd


def test_end_invalid_poll(base_url, client):
    data = json.dumps({
        'user_id': 'user0',
        'team_id': 'team0',
        'context': {
            'poll_id': 'invalid123',
            'vote': 0
        }
    })
    response = client.post('/end', data=data,
                           content_type='application/json',
                           base_url=base_url)
    assert response.status_code == 200

    rd = json.loads(response.data.decode('utf-8'))
    assert 'update' not in rd
    assert 'ephemeral_text' in rd


def test_help(base_url, client):
    data = {
        'user_id': 'user0',
        'text': 'help',
        'command': '/foo',
    }
    response = client.post('/', data=data, base_url=base_url)
    assert response.status_code == 200

    rd = json.loads(response.data.decode('utf-8'))
    jsonschema.validate(rd, schemas.ephemeral)

    assert '/foo' in rd['text']

    # Only a single help shows the help text
    data = {
        'user_id': 'user0',
        'text': 'help me',
        'command': '/foo',
    }
    response = client.post('/', data=data, base_url=base_url)
    assert response.status_code == 200

    rd = json.loads(response.data.decode('utf-8'))
    assert rd['response_type'] != 'ephemeral'


@pytest.fixture
def clean_token_setting(request):
    def clean():
        if hasattr(settings, 'MATTERMOST_TOKEN'):
            del settings.MATTERMOST_TOKEN
        settings.MATTERMOST_TOKENS = None

    assert settings.TEST_SETTINGS

    request.addfinalizer(clean)


@pytest.mark.usefixtures('clean_token_setting')
def test_mattermost_tokens_none(base_url, client):
    assert settings.TEST_SETTINGS
    settings.MATTERMOST_TOKENS = None
    data = {
        'user_id': 'user0',
        'text': 'Bla',
        'token': 'abc123'
    }
    response = client.post('/', data=data, base_url=base_url)
    assert response.status_code == 200

    rd = json.loads(response.data.decode('utf-8'))
    assert rd['response_type'] != 'ephemeral'


@pytest.mark.usefixtures('clean_token_setting')
def test_mattermost_tokens_valid(base_url, client):
    assert settings.TEST_SETTINGS
    settings.MATTERMOST_TOKENS = ['xyz321', 'abc123']
    data = {
        'user_id': 'user0',
        'text': 'Bla',
        'token': 'abc123'
    }
    response = client.post('/', data=data, base_url=base_url)
    assert response.status_code == 200

    rd = json.loads(response.data.decode('utf-8'))
    assert rd['response_type'] != 'ephemeral'

    data = {
        'user_id': 'user0',
        'text': 'Bla',
        'token': 'xyz321'
    }
    response = client.post('/', data=data, base_url=base_url)
    assert response.status_code == 200

    rd = json.loads(response.data.decode('utf-8'))
    assert rd['response_type'] != 'ephemeral'


@pytest.mark.usefixtures('clean_token_setting')
def test_mattermost_tokens_invalid(base_url, client):
    assert settings.TEST_SETTINGS
    settings.MATTERMOST_TOKENS = ['xyz321', 'abc123']
    data = {
        'user_id': 'user0',
        'text': 'Bla',
        'token': 'abc321'
    }
    response = client.post('/', data=data, base_url=base_url)
    assert response.status_code == 200

    rd = json.loads(response.data.decode('utf-8'))
    assert rd['response_type'] == 'ephemeral'
    assert 'invalid token' in rd['text'].lower()


@pytest.mark.usefixtures('clean_token_setting')
def test_mattermost_tokens_legacy(base_url, client):
    del settings.MATTERMOST_TOKENS
    settings.MATTERMOST_TOKEN = 'abc123'
    data = {
        'user_id': 'user0',
        'text': 'Bla',
        'token': 'abc123'
    }
    response = client.post('/', data=data, base_url=base_url)
    assert response.status_code == 200

    rd = json.loads(response.data.decode('utf-8'))
    assert rd['response_type'] != 'ephemeral'

    assert settings.MATTERMOST_TOKENS == ['abc123']
