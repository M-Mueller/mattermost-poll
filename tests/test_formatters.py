# pylint: disable=missing-docstring
import pytest
import formatters as frmts
import app
from poll import Poll
from test_utils import force_settings


def default_img_url(rel_width):
    width = int(max(2, rel_width*450))
    return 'http://localhost:5005/img/bar_{}.png'.format(width)


@pytest.mark.parametrize('votes, secret, exp_actions', [
    ([], False, ['Yes (0)', 'No (0)']),
    ([0, 0, 0, 1, 1], False, ['Yes (3)', 'No (2)']),
    ([0, 0, 0, 1, 1], True, ['Yes', 'No'])
])
def test_format_actions(votes, secret, exp_actions):
    poll = Poll.create(
        creator_id='user0',
        message='Message',
        vote_options=['Yes', 'No'],
        secret=secret,
        bars=False,
    )

    for voter, vote in enumerate(votes):
        poll.vote('user{}'.format(voter), vote)

    with app.app.test_request_context(base_url='http://localhost:5005'):
        actions = frmts.format_actions(poll)
    assert len(actions) == 3

    for action, (vote_id, name) in zip(actions[:-1], enumerate(exp_actions)):
        assert 'name' in action
        assert 'integration' in action

        assert action['name'] == name
        integration = action['integration']
        assert 'context' in integration
        assert 'url' in integration
        assert integration['url'] == 'http://localhost:5005/vote'

        context = integration['context']
        assert 'vote' in context
        assert 'poll_id' in context
        assert context['vote'] == vote_id
        assert context['poll_id'] == poll.id

    # the last action is always 'End Poll'
    action = actions[-1]
    assert 'name' in action
    assert 'integration' in action

    assert action['name'] == 'End Poll'
    integration = action['integration']
    assert 'context' in integration
    assert 'url' in integration
    assert integration['url'] == 'http://localhost:5005/end'

    context = integration['context']
    assert 'poll_id' in context
    assert context['poll_id'] == poll.id


def test_format_poll_running(mocker):
    mocker.patch('formatters.resolve_usernames', new=lambda user_ids: user_ids)

    poll = Poll.create(
        creator_id='user0',
        message='# Spam? **:tada:**',
        vote_options=['Sure', 'Maybe', 'No'],
        secret=False,
        bars=False,
    )

    poll.vote('user0', 0)
    poll.vote('user1', 1)
    poll.vote('user2', 2)
    poll.vote('user3', 2)

    with app.app.test_request_context(base_url='http://localhost:5005'):
        poll_dict = frmts.format_poll(poll)

    assert 'response_type' in poll_dict
    assert 'attachments' in poll_dict

    assert poll_dict['response_type'] == 'in_channel'
    attachments = poll_dict['attachments']
    assert len(attachments) == 1
    assert 'text' in attachments[0]
    assert 'actions' in attachments[0]
    assert 'fields' in attachments[0]
    assert attachments[0]['text'] == poll.message
    assert len(attachments[0]['actions']) == 4

    fields = attachments[0]['fields']
    assert len(fields) == 1
    assert 'short' in fields[0]
    assert 'title' in fields[0]
    assert 'value' in fields[0]
    assert not fields[0]['short']
    assert not fields[0]['title']
    assert fields[0]['value'] == '*Number of voters: 4*'


def test_format_poll_running_multi(mocker):
    mocker.patch('formatters.resolve_usernames', new=lambda user_ids: user_ids)

    poll = Poll.create(
        creator_id='user0',
        message='# Spam? **:tada:**',
        vote_options=['Sure', 'Maybe', 'No'],
        secret=False,
        max_votes=2,
        bars=False,
    )
    poll.vote('user0', 0)
    poll.vote('user1', 1)
    poll.vote('user2', 2)
    poll.vote('user0', 2)

    with app.app.test_request_context(base_url='http://localhost:5005'):
        poll_dict = frmts.format_poll(poll)

    assert 'response_type' in poll_dict
    assert 'attachments' in poll_dict

    assert poll_dict['response_type'] == 'in_channel'
    attachments = poll_dict['attachments']
    assert len(attachments) == 1
    assert 'text' in attachments[0]
    assert 'actions' in attachments[0]
    assert 'fields' in attachments[0]
    assert attachments[0]['text'] == poll.message
    assert len(attachments[0]['actions']) == 4

    fields = attachments[0]['fields']
    assert len(fields) == 2
    assert 'short' in fields[0]
    assert 'title' in fields[0]
    assert 'value' in fields[0]
    assert not fields[0]['short']
    assert not fields[0]['title']
    assert fields[0]['value'] == '*Number of voters: 3*'

    assert 'short' in fields[1]
    assert 'title' in fields[1]
    assert 'value' in fields[1]
    assert not fields[1]['short']
    assert not fields[1]['title']
    assert fields[1]['value'] == '*You have 2 votes*'


def test_format_poll_running_public(mocker):
    mocker.patch('formatters.resolve_usernames', new=lambda user_ids: user_ids)

    poll = Poll.create(
        creator_id='user0',
        message='# Spam? **:tada:**',
        vote_options=['Sure', 'Maybe', 'No'],
        public=True,
        bars=False,
    )
    poll.vote('user0', 0)
    poll.vote('user1', 1)
    poll.vote('user2', 2)
    poll.vote('user0', 2)

    with app.app.test_request_context(base_url='http://localhost:5005'):
        poll_dict = frmts.format_poll(poll)

    assert 'response_type' in poll_dict
    assert 'attachments' in poll_dict

    assert poll_dict['response_type'] == 'in_channel'
    attachments = poll_dict['attachments']
    assert len(attachments) == 1
    assert 'text' in attachments[0]
    assert 'actions' in attachments[0]
    assert 'fields' in attachments[0]
    assert attachments[0]['text'] == poll.message
    assert len(attachments[0]['actions']) == 4

    fields = attachments[0]['fields']
    assert len(fields) == 2
    assert 'short' in fields[0]
    assert 'title' in fields[0]
    assert 'value' in fields[0]
    assert not fields[0]['short']
    assert not fields[0]['title']
    assert fields[0]['value'] == '*Number of voters: 3*'

    assert 'short' in fields[1]
    assert 'title' in fields[1]
    assert 'value' in fields[1]
    assert not fields[1]['short']
    assert not fields[1]['title']
    assert ":warning:" in fields[1]['value']


def test_format_poll_running_public_bars(mocker):
    mocker.patch('formatters.resolve_usernames', new=lambda user_ids: user_ids)

    poll = Poll.create(
        creator_id='user0',
        message='# Spam? **:tada:**',
        vote_options=['Sure', 'Maybe', 'No'],
        public=True,
        bars=True,
    )
    poll.vote('user0', 2)
    poll.vote('user1', 1)
    poll.vote('user2', 2)
    poll.vote('user3', 2)

    with app.app.test_request_context(base_url='http://localhost:5005'):
        poll_dict = frmts.format_poll(poll)

    assert 'response_type' in poll_dict
    assert 'attachments' in poll_dict

    assert poll_dict['response_type'] == 'in_channel'
    attachments = poll_dict['attachments']
    assert len(attachments) == 1
    assert 'text' in attachments[0]
    assert 'actions' in attachments[0]
    assert 'fields' in attachments[0]
    assert attachments[0]['text'] == poll.message
    assert len(attachments[0]['actions']) == 4

    fields = attachments[0]['fields']
    assert len(fields) == 4
    assert 'short' in fields[0]
    assert 'title' in fields[0]
    assert 'value' in fields[0]
    assert not fields[0]['short']
    assert not fields[0]['title']
    assert fields[0]['value'] == '*Number of voters: 4*'

    assert 'short' in fields[1]
    assert 'title' in fields[1]
    assert 'value' in fields[1]
    assert not fields[1]['short']
    assert not fields[1]['title']
    assert ":warning:" in fields[1]['value']

    users = ['user0', 'user1', 'user2', 'user3']
    expected = [
        (poll.vote_options[1], '1 Vote (25.0%)', 0.25, ['user1']),
        (poll.vote_options[2], '3 Votes (75.0%)', 0.75, ['user0', 'user2', 'user3']),
    ]
    for field, (title, value, bar_length, users) in zip(fields[2:], expected):
        assert 'short' in field
        assert 'title' in field
        assert 'value' in field
        assert not field['short']
        assert title == field['title']
        assert value in field['value']
        image = '![Bar]({})'.format(default_img_url(bar_length))
        assert image in field['value']
        for user in users:
            assert user in field['value']


def test_format_poll_running_secret(mocker):
    mocker.patch('formatters.resolve_usernames', new=lambda user_ids: user_ids)

    poll = Poll.create(
        creator_id='user0',
        message='# Spam? **:tada:**',
        vote_options=['Sure', 'Maybe', 'No'],
        public=True,
        bars=True,
        secret=True,
    )
    poll.vote('user0', 2)
    poll.vote('user1', 1)
    poll.vote('user2', 2)
    poll.vote('user3', 2)

    with app.app.test_request_context(base_url='http://localhost:5005'):
        poll_dict = frmts.format_poll(poll)

    assert 'response_type' in poll_dict
    assert 'attachments' in poll_dict

    assert poll_dict['response_type'] == 'in_channel'
    attachments = poll_dict['attachments']
    assert len(attachments) == 1
    assert 'text' in attachments[0]
    assert 'actions' in attachments[0]
    assert 'fields' in attachments[0]
    assert attachments[0]['text'] == poll.message
    assert len(attachments[0]['actions']) == 4

    fields = attachments[0]['fields']
    assert len(fields) == 2
    assert 'short' in fields[0]
    assert 'title' in fields[0]
    assert 'value' in fields[0]
    assert not fields[0]['short']
    assert not fields[0]['title']
    assert fields[0]['value'] == '*Number of voters: 4*'

    assert 'short' in fields[1]
    assert 'title' in fields[1]
    assert 'value' in fields[1]
    assert not fields[1]['short']
    assert not fields[1]['title']
    assert ":warning:" in fields[1]['value']


def test_format_poll_finished(mocker):
    mocker.patch('formatters.resolve_usernames', new=lambda user_ids: user_ids)

    poll = Poll.create(
        creator_id='user0',
        message='# Spam? **:tada:**',
        vote_options=['Sure', 'Maybe', 'No'],
        secret=False,
        bars=False,
    )
    poll.vote('user0', 0)
    poll.vote('user1', 1)
    poll.vote('user2', 2)
    poll.vote('user3', 2)
    poll.end()

    with app.app.test_request_context(base_url='http://localhost:5005'):
        poll_dict = frmts.format_poll(poll)

    assert 'response_type' in poll_dict
    assert 'attachments' in poll_dict

    assert poll_dict['response_type'] == 'in_channel'
    attachments = poll_dict['attachments']
    assert len(attachments) == 1
    assert 'text' in attachments[0]
    assert 'actions' not in attachments[0]
    assert 'fields' in attachments[0]
    assert attachments[0]['text'] == poll.message

    fields = attachments[0]['fields']
    assert len(fields) == 4

    assert 'short' in fields[0]
    assert 'title' in fields[0]
    assert 'value' in fields[0]
    assert not fields[0]['short']
    assert not fields[0]['title']
    assert fields[0]['value'] == '*Number of voters: 4*'

    users = ['user0', 'user1', 'user2', 'user3']
    expected = [
        (poll.vote_options[0], '1 Vote (25.0%)'),
        (poll.vote_options[1], '1 Vote (25.0%)'),
        (poll.vote_options[2], '2 Votes (50.0%)'),
    ]
    for field, (title, value) in zip(fields[1:], expected):
        assert 'short' in field
        assert 'title' in field
        assert 'value' in field
        assert field['short']
        assert title == field['title']
        assert value == field['value']
        for user in users:
            assert user not in field['value']


def test_format_poll_finished_public(mocker):
    mocker.patch('formatters.resolve_usernames', new=lambda user_ids: user_ids)

    poll = Poll.create(
        creator_id='user0',
        message='# Spam? **:tada:**',
        vote_options=['Sure', 'Maybe', 'No'],
        public=True,
        bars=False,
    )
    poll.vote('user0', 0)
    poll.vote('user1', 1)
    poll.vote('user2', 2)
    poll.vote('user3', 2)
    poll.end()

    with app.app.test_request_context(base_url='http://localhost:5005'):
        poll_dict = frmts.format_poll(poll)

    assert 'response_type' in poll_dict
    assert 'attachments' in poll_dict

    assert poll_dict['response_type'] == 'in_channel'
    attachments = poll_dict['attachments']
    assert len(attachments) == 1
    assert 'text' in attachments[0]
    assert 'actions' not in attachments[0]
    assert 'fields' in attachments[0]
    assert attachments[0]['text'] == poll.message

    fields = attachments[0]['fields']
    assert len(fields) == 4

    assert 'short' in fields[0]
    assert 'title' in fields[0]
    assert 'value' in fields[0]
    assert not fields[0]['short']
    assert not fields[0]['title']
    assert fields[0]['value'] == '*Number of voters: 4*'

    expected = [
        (poll.vote_options[0], '1 Vote (25.0%)', ['user0']),
        (poll.vote_options[1], '1 Vote (25.0%)', ['user1']),
        (poll.vote_options[2], '2 Votes (50.0%)', ['user2', 'user3']),
    ]
    for field, (title, value, users) in zip(fields[1:], expected):
        assert 'short' in field
        assert 'title' in field
        assert 'value' in field
        assert field['short']
        assert title == field['title']
        assert value in field['value']
        for user in users:
            assert user in field['value']


def test_format_poll_finished_bars(mocker):
    mocker.patch('formatters.resolve_usernames', new=lambda user_ids: user_ids)

    poll = Poll.create(
        creator_id='user0',
        message='# Spam? **:tada:**',
        vote_options=['Sure', 'Maybe', 'No'],
        bars=True,
    )
    poll.vote('user0', 0)
    poll.vote('user1', 1)
    poll.vote('user2', 2)
    poll.vote('user3', 2)
    poll.end()

    with app.app.test_request_context(base_url='http://localhost:5005'):
        poll_dict = frmts.format_poll(poll)

    assert 'response_type' in poll_dict
    assert 'attachments' in poll_dict

    assert poll_dict['response_type'] == 'in_channel'
    attachments = poll_dict['attachments']
    assert len(attachments) == 1
    assert 'text' in attachments[0]
    assert 'actions' not in attachments[0]
    assert 'fields' in attachments[0]
    assert attachments[0]['text'] == poll.message

    fields = attachments[0]['fields']
    assert len(fields) == 4

    assert 'short' in fields[0]
    assert 'title' in fields[0]
    assert 'value' in fields[0]
    assert not fields[0]['short']
    assert not fields[0]['title']
    assert fields[0]['value'] == '*Number of voters: 4*'

    users = ['user0', 'user1', 'user2', 'user3']
    expected = [
        (poll.vote_options[0], '1 Vote (25.0%)', 0.25),
        (poll.vote_options[1], '1 Vote (25.0%)', 0.25),
        (poll.vote_options[2], '2 Votes (50.0%)', 0.5),
    ]
    for field, (title, value, bar_length) in zip(fields[1:], expected):
        assert 'short' in field
        assert 'title' in field
        assert 'value' in field
        assert not field['short']
        assert title == field['title']
        assert value in field['value']
        image = '![Bar]({})'.format(default_img_url(bar_length))
        assert image in field['value']
        for user in users:
            assert user not in field['value']


def test_format_poll_finished_public_bars(mocker):
    mocker.patch('formatters.resolve_usernames', new=lambda user_ids: user_ids)

    poll = Poll.create(
        creator_id='user0',
        message='# Spam? **:tada:**',
        vote_options=['Sure', 'Maybe', 'No'],
        bars=True,
        public=True,
    )
    poll.vote('user0', 0)
    poll.vote('user1', 1)
    poll.vote('user2', 2)
    poll.vote('user3', 2)
    poll.end()

    with app.app.test_request_context(base_url='http://localhost:5005'):
        poll_dict = frmts.format_poll(poll)

    assert 'response_type' in poll_dict
    assert 'attachments' in poll_dict

    assert poll_dict['response_type'] == 'in_channel'
    attachments = poll_dict['attachments']
    assert len(attachments) == 1
    assert 'text' in attachments[0]
    assert 'actions' not in attachments[0]
    assert 'fields' in attachments[0]
    assert attachments[0]['text'] == poll.message

    fields = attachments[0]['fields']
    assert len(fields) == 4

    assert 'short' in fields[0]
    assert 'title' in fields[0]
    assert 'value' in fields[0]
    assert not fields[0]['short']
    assert not fields[0]['title']
    assert fields[0]['value'] == '*Number of voters: 4*'

    expected = [
        (poll.vote_options[0], '1 Vote (25.0%)', 0.25, ['user0']),
        (poll.vote_options[1], '1 Vote (25.0%)', 0.25, ['user1']),
        (poll.vote_options[2], '2 Votes (50.0%)', 0.5, ['user2', 'user3']),
    ]
    for field, (title, value, bar_length, users) in zip(fields[1:], expected):
        assert 'short' in field
        assert 'title' in field
        assert 'value' in field
        assert not field['short']
        assert title == field['title']
        assert value in field['value']
        image = '![Bar]({})'.format(default_img_url(bar_length))
        assert image in field['value']
        for user in users:
            assert user in field['value']


def test_format_poll_bars_absolute_url(mocker):
    mocker.patch('formatters.resolve_usernames', new=lambda user_ids: user_ids)

    img_url = 'http://example.org/images/red_bar.png'
    with force_settings(BAR_IMG_URL=img_url):
        poll = Poll.create(
            creator_id='user0',
            message='# Spam? **:tada:**',
            vote_options=['Sure', 'Maybe', 'No'],
            bars=True,
        )
        poll.vote('user0', 0)
        poll.vote('user1', 1)
        poll.vote('user2', 2)
        poll.vote('user3', 2)
        poll.end()

        with app.app.test_request_context(base_url='http://localhost:5005'):
            poll_dict = frmts.format_poll(poll)

        assert 'response_type' in poll_dict
        assert 'attachments' in poll_dict

        attachments = poll_dict['attachments']
        fields = attachments[0]['fields']

        for field, bar_length in zip(fields[1:], [0.25, 0.25, 0.5]):
            image = '![Bar]({} ={}x25)'.format(img_url, int(max(2, bar_length*450)))
            assert image in field['value']
            assert 'localhost' not in field['value']


def test_vote_to_string_single():
    poll = Poll.create(
        creator_id='user0',
        message='Message',
        vote_options=['Sure', 'Maybe', 'No']
    )
    poll.vote('user0', 0)
    poll.vote('user1', 2)

    assert frmts.format_user_vote(poll, 'user0') == ('Sure ✓, Maybe ✗, No ✗')
    assert frmts.format_user_vote(poll, 'user1') == ('Sure ✗, Maybe ✗, No ✓')
    assert frmts.format_user_vote(poll, 'user2') == ('Sure ✗, Maybe ✗, No ✗')


def test_vote_to_string_multi():
    poll = Poll.create(
        creator_id='user0',
        message='Message',
        vote_options=['Sure', 'Maybe', 'No'],
        max_votes=2
    )
    poll.vote('user0', 0)
    poll.vote('user0', 2)
    poll.vote('user1', 2)

    assert frmts.format_user_vote(poll, 'user0') == ('Sure ✓, Maybe ✗, No ✓')
    assert frmts.format_user_vote(poll, 'user1') == ('Sure ✗, Maybe ✗, No ✓')
    assert frmts.format_user_vote(poll, 'user2') == ('Sure ✗, Maybe ✗, No ✗')


@pytest.mark.parametrize('locale, start', [
    ('en', 'Starts a poll'),
    ('de', 'Startet eine Umfrage'),
    ('zz', 'Starts a poll'),
])
def test_format_help(locale, start):
    help_text = frmts.format_help('/schwifty', locale)
    assert '/schwifty' in help_text
    assert '{command}' not in help_text
    assert help_text.startswith(start)


def test_format_help_remove_superfluous():
    with force_settings(
        PUBLIC_BY_DEFAULT=True,
        PROGRESS_BY_DEFAULT=True,
        BARS_BY_DEFAULT=True
    ):
        hlp = frmts.format_help('/poll')
        assert '`--public`' not in hlp
        assert '`--anonym`' in hlp
        assert '`--progress`' not in hlp
        assert '`--noprogress`' in hlp
        assert '`--bars`' not in hlp
        assert '`--nobars`' in hlp

    with force_settings(
        PUBLIC_BY_DEFAULT=False,
        PROGRESS_BY_DEFAULT=False,
        BARS_BY_DEFAULT=False
    ):
        hlp = frmts.format_help('/poll')
        assert '`--public`' in hlp
        assert '`--anonym`' not in hlp
        assert '`--progress`' in hlp
        assert '`--noprogress`' not in hlp
        assert '`--bars`' in hlp
        assert '`--nobars`' not in hlp
