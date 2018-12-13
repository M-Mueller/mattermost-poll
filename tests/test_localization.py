# pylint: disable=missing-docstring
import json
import pytest
import app


@pytest.fixture
def client():
    app.app.testing = True
    return app.app.test_client()


def patched_user_locale(user_id):
    if user_id == 'de_user':
        return 'de'
    if user_id == 'en_user':
        return 'en'
    assert False


@pytest.mark.parametrize('data, message, actions', [
    ({
        'user_id': 'en_user',
        'text': "How are you? --Good --Bad"
    }, "How are you?", ['Good', 'Bad', 'End Poll']),
    ({
        'user_id': 'de_user',
        'text': "Wie geht's? --Gut --Schlecht"
    }, "Wie geht's?", ['Gut', 'Schlecht', 'Umfrage beenden']),
    ({
        'user_id': 'de_user',
        'text': "Yes or No?"
    }, "Yes or No?", ['Ja', 'Nein', 'Umfrage beenden']),
    ({
        'user_id': 'de_user',
        'text': "Wie geht's? --Gut --Schlecht --locale=en"
    }, "Wie geht's?", ['Gut', 'Schlecht', 'End Poll']),
    ({
        'user_id': 'de_user',
        'text': "Ja oder Nein? --locale=en"
    }, "Ja oder Nein?", ['Yes', 'No', 'End Poll']),
])
def test_localized_poll(mocker, client, data, message, actions):
    mocker.patch('app.user_locale', new=patched_user_locale)

    response = client.post('/', data=data)
    assert response.status_code == 200

    response_json = json.loads(response.data.decode('utf-8'))

    actual_message = response_json['attachments'][0]['text']
    assert actual_message == message

    actual_actions = response_json['attachments'][0]['actions']
    assert len(actual_actions) == len(actions)
    for actual, expected in zip(actual_actions, actions):
        assert expected in actual['name']


def test_create_de_vote_en(mocker, client):
    """Test that the language of the poll does not change once created."""
    mocker.patch('app.user_locale', new=patched_user_locale)

    # create with german locale
    data = {
        'user_id': 'de_user',
        'text': 'Brezn?',
    }
    response = client.post('/', data=data)
    assert response.status_code == 200

    response_json = json.loads(response.data.decode('utf-8'))

    actual_message = response_json['attachments'][0]['text']
    assert actual_message == 'Brezn?'

    actions = ['Ja', 'Nein', 'Umfrage beenden']
    actual_actions = response_json['attachments'][0]['actions']
    assert len(actual_actions) == len(actions)
    for actual, expected in zip(actual_actions, actions):
        assert expected in actual['name']

    poll_id = actual_actions[0]['integration']['context']['poll_id']
    vote_id = actual_actions[0]['integration']['context']['vote']

    del response_json
    del actual_message
    del actual_actions

    # vote with english locale => poll stays german, ephemeral is english
    data = json.dumps({
        'user_id': 'en_user',
        'context': {
            'poll_id': poll_id,
            'vote': vote_id,
        }
    })
    response = client.post('/vote', data=data, content_type='application/json')
    assert response.status_code == 200

    response_json = json.loads(response.data.decode('utf-8'))

    actual_ephemeral = response_json['ephemeral_text']
    assert "Your vote has been updated" in actual_ephemeral

    attachements = response_json['update']['props']['attachments']
    actual_message = attachements[0]['text']
    assert actual_message == 'Brezn?'

    actual_actions = attachements[0]['actions']
    assert len(actual_actions) == len(actions)
    for actual, expected in zip(actual_actions, actions):
        assert expected in actual['name']

    del response_json
    del actual_ephemeral

    # vote with german locale => ephemeral is german
    data = json.dumps({
        'user_id': 'de_user',
        'context': {
            'poll_id': poll_id,
            'vote': vote_id,
        }
    })
    response = client.post('/vote', data=data, content_type='application/json')
    assert response.status_code == 200

    response_json = json.loads(response.data.decode('utf-8'))

    actual_ephemeral = response_json['ephemeral_text']
    assert "Ihre Wahl wurde aktualisiert" in actual_ephemeral
