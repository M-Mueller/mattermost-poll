# pylint: disable=missing-docstring
from collections import namedtuple
import json
import pytest

import mattermost_api
import settings


Response = namedtuple('Response', ['ok', 'text'])


@pytest.fixture
def set_pa_token(request):
    assert settings.TEST_SETTINGS
    settings.MATTERMOST_PA_TOKEN = '123abc456xyz'

    def clean():
        settings.MATTERMOST_PA_TOKEN = None

    request.addfinalizer(clean)


@pytest.mark.usefixtures('set_pa_token')
@pytest.mark.parametrize("user_id, locale", [
    ('user1', 'en'),
    ('user2', 'de'),
    ('user3', 'en'),
    ('user4', 'en'),
    ('user5', 'en'),
])
def test_user_locale(mocker, user_id, locale):
    def requests_mock(url, headers):
        assert url == 'http://www.example.com/api/v4/users/' + user_id
        assert headers['Authorization'] == 'Bearer 123abc456xyz'
        if user_id == 'user1':
            return Response(True, json.dumps({'locale': 'en'}))
        if user_id == 'user2':
            return Response(True, json.dumps({'locale': 'de'}))
        if user_id == 'user3':
            return Response(True, json.dumps({'locale': ''}))
        if user_id == 'user4':
            return Response(True, json.dumps({}))
        if user_id == 'user5':
            return Response(False, json.dumps({}))
        assert False

    mocker.patch('requests.get', new=requests_mock)

    assert settings.MATTERMOST_PA_TOKEN

    actual_locale = mattermost_api.user_locale(user_id)
    assert actual_locale == locale


def test_user_locale_no_token(mocker):
    def requests_mock(url, headers):
        assert False

    mocker.patch('requests.get', new=requests_mock)

    assert not settings.MATTERMOST_PA_TOKEN

    actual_locale = mattermost_api.user_locale('user1')
    assert actual_locale == 'en'


@pytest.mark.usefixtures('set_pa_token')
@pytest.mark.parametrize("user_id, admin", [
    ('user1', False),
    ('user2', False),
    ('user3', True),
    ('user4', True),
    ('invalid', False),
])
def test_user_is_admin(mocker, user_id, admin):
    def requests_mock(url, headers):
        assert url == 'http://www.example.com/api/v4/users/' + user_id
        assert headers['Authorization'] == 'Bearer 123abc456xyz'
        if user_id == 'user1':
            return Response(True, json.dumps({'roles': ['admin', 'whatever']}))
        if user_id == 'user2':
            return Response(True, json.dumps({'roles': ['team_admin']}))
        if user_id == 'user3':
            return Response(True, json.dumps({'roles': ['whatever', 'system_admin']}))
        if user_id == 'user4':
            return Response(True, json.dumps({'roles': ['whatever', 'team_admin', 'system_admin']}))
        if user_id == 'invalid':
            return Response(True, json.dumps({}))
        assert False

    mocker.patch('requests.get', new=requests_mock)

    assert mattermost_api.is_admin_user(user_id) is admin


@pytest.mark.usefixtures('set_pa_token')
@pytest.mark.parametrize("user_id, team_admin", [
    ('user1', False),
    ('user2', True),
    ('user3', False),
    ('user4', True),
    ('invalid', False),
])
def test_user_is_team_admin(mocker, user_id, team_admin):
    def requests_mock(url, headers):
        assert url == 'http://www.example.com/api/v4/teams/myteam/members/' + user_id
        assert headers['Authorization'] == 'Bearer 123abc456xyz'
        if user_id == 'user1':
            return Response(True, json.dumps({'roles': ['admin', 'whatever']}))
        if user_id == 'user2':
            return Response(True, json.dumps({'roles': ['team_admin']}))
        if user_id == 'user3':
            return Response(True, json.dumps({'roles': ['whatever', 'system_admin']}))
        if user_id == 'user4':
            return Response(True, json.dumps({'roles': ['whatever', 'team_admin', 'system_admin']}))
        if user_id == 'invalid':
            return Response(True, json.dumps({}))
        assert False

    mocker.patch('requests.get', new=requests_mock)

    assert mattermost_api.is_team_admin(user_id, 'myteam') is team_admin
