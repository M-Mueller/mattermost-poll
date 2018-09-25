# pylint: disable=missing-docstring
import pytest
import formatters as frmts
import app
from poll import Poll


@pytest.mark.parametrize('votes, secret, exp_actions', [
    ([], False, ['Yes (0)', 'No (0)']),
    ([0, 0, 0, 1, 1], False, ['Yes (3)', 'No (2)']),
    ([0, 0, 0, 1, 1], True, ['Yes', 'No'])
])
def test_format_actions(votes, secret, exp_actions):
    poll = Poll.create(creator_id='user0', message='Message',
                       vote_options=['Yes', 'No'], secret=secret)

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

    poll = Poll.create(creator_id='user0', message='# Spam? **:tada:**',
                       vote_options=['Sure', 'Maybe', 'No'], secret=False)
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

    poll = Poll.create(creator_id='user0', message='# Spam? **:tada:**',
                       vote_options=['Sure', 'Maybe', 'No'],
                       secret=False, max_votes=2)
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

    poll = Poll.create(creator_id='user0', message='# Spam? **:tada:**',
                       vote_options=['Sure', 'Maybe', 'No'],
                       public=True)
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


def test_format_poll_finished(mocker):
    mocker.patch('formatters.resolve_usernames', new=lambda user_ids: user_ids)

    poll = Poll.create(creator_id='user0', message='# Spam? **:tada:**',
                       vote_options=['Sure', 'Maybe', 'No'], secret=False)
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
        (poll.vote_options[0], '1 (25.0%)'),
        (poll.vote_options[1], '1 (25.0%)'),
        (poll.vote_options[2], '2 (50.0%)'),
    ]
    for field, (title, value) in zip(fields[1:], expected):
        assert 'short' in field
        assert 'title' in field
        assert 'value' in field
        assert field['short']
        assert title == field['title']
        assert value == field['value']


def test_format_poll_finished_public(mocker):
    mocker.patch('formatters.resolve_usernames', new=lambda user_ids: user_ids)

    poll = Poll.create(creator_id='user0', message='# Spam? **:tada:**',
                       vote_options=['Sure', 'Maybe', 'No'],
                       public=True)
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
        (poll.vote_options[0], '1 (25.0%)', ['user0']),
        (poll.vote_options[1], '1 (25.0%)', ['user1']),
        (poll.vote_options[2], '2 (50.0%)', ['user2', 'user3']),
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


def test_vote_to_string_single():
    poll = Poll.create(creator_id='user0', message='Message',
                       vote_options=['Sure', 'Maybe', 'No'])
    poll.vote('user0', 0)
    poll.vote('user1', 2)

    assert frmts.format_user_vote(poll, 'user0') == ('Sure ✓, Maybe ✗, No ✗')
    assert frmts.format_user_vote(poll, 'user1') == ('Sure ✗, Maybe ✗, No ✓')
    assert frmts.format_user_vote(poll, 'user2') == ('Sure ✗, Maybe ✗, No ✗')


def test_vote_to_string_multi():
    poll = Poll.create(creator_id='user0', message='Message',
                       vote_options=['Sure', 'Maybe', 'No'],
                       max_votes=2)
    poll.vote('user0', 0)
    poll.vote('user0', 2)
    poll.vote('user1', 2)

    assert frmts.format_user_vote(poll, 'user0') == ('Sure ✓, Maybe ✗, No ✓')
    assert frmts.format_user_vote(poll, 'user1') == ('Sure ✗, Maybe ✗, No ✓')
    assert frmts.format_user_vote(poll, 'user2') == ('Sure ✗, Maybe ✗, No ✗')
