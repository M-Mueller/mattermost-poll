# pylint: disable=missing-docstring
import pytest
import sqlite3
import settings
from poll import Poll, NoMoreVotesError, InvalidPollError


def test_init():
    creator_id = 'user01234'
    message = '## Markdown message<br>Test **bla**'
    vote_options = ['Option 1', 'Another option', 'Spam!']
    poll = Poll.create(creator_id, message, 'de', vote_options,
                       True, True, 2, True)
    assert poll.creator_id == creator_id
    assert poll.message == message
    assert poll.locale == 'de'
    assert poll.vote_options == vote_options
    assert poll.secret
    assert poll.public
    assert poll.max_votes == 2
    assert poll.bars


def test_init_defaults():
    creator_id = 'user01234'
    message = '## Markdown message<br>Test **bla**'
    poll = Poll.create(creator_id, message)
    assert poll.creator_id == creator_id
    assert poll.message == message
    assert poll.locale == 'en'
    assert poll.vote_options == ['Yes', 'No']
    assert not poll.secret
    assert not poll.public
    assert poll.max_votes == 1
    assert not poll.bars


def test_update_database():
    con = sqlite3.connect(':memory:')
    cur = con.cursor()

    # restore database that is missing 'bars' column in Poll table
    with open('tests/old_db.sql') as f:
        cur.executescript(f.read())

    cur.execute("""PRAGMA table_info(Polls)""")
    assert 'bars' not in (c[1] for c in cur.fetchall())
    assert 'locale' not in (c[1] for c in cur.fetchall())

    poll = Poll(con, 1)
    assert poll.creator_id == '9eu8hqt36tgg8q6w6ypu4ww1ch'
    assert poll.message == 'Spam with...'
    assert poll.locale == "en"
    assert poll.vote_options == ['Eggs', 'Bacon', 'More Spam']
    assert not poll.secret
    assert poll.public
    assert poll.max_votes == 2
    assert not poll.bars


def test_vote():
    poll = Poll.create('user0123', 'Spam?', 'en', ['Yes', 'Maybe', 'No'])
    assert poll.num_votes() == 0
    assert poll.count_votes(0) == 0
    assert poll.count_votes(1) == 0
    assert poll.count_votes(2) == 0
    assert poll.count_votes(3) == 0

    poll.vote('user0', 0)
    poll.vote('user1', 2)
    poll.vote('user2', 2)
    assert poll.num_votes() == 3
    assert poll.count_votes(0) == 1
    assert poll.count_votes(1) == 0
    assert poll.count_votes(2) == 2
    assert poll.count_votes(3) == 0

    poll.vote('user0', 0)
    poll.vote('user0', 0)
    assert poll.num_votes() == 3
    assert poll.count_votes(0) == 1
    assert poll.count_votes(1) == 0
    assert poll.count_votes(2) == 2
    assert poll.count_votes(3) == 0

    poll.vote('user2', 1)
    assert poll.num_votes() == 3
    assert poll.count_votes(0) == 1
    assert poll.count_votes(1) == 1
    assert poll.count_votes(2) == 1
    assert poll.count_votes(3) == 0

    with pytest.raises(IndexError):
        poll.vote('user2', 3)
    with pytest.raises(IndexError):
        poll.vote('user2', -2)
    assert poll.num_votes() == 3
    assert poll.count_votes(0) == 1
    assert poll.count_votes(1) == 1
    assert poll.count_votes(2) == 1
    assert poll.count_votes(3) == 0


def test_multiple_votes():
    poll = Poll.create('user0123', 'Spam?', 'en', ['Yes', 'Maybe', 'No'],
                       max_votes=2)
    assert poll.num_votes() == 0
    assert poll.count_votes(0) == 0
    assert poll.count_votes(1) == 0
    assert poll.count_votes(2) == 0
    assert poll.count_votes(3) == 0

    poll.vote('user0', 0)
    poll.vote('user1', 2)
    poll.vote('user2', 2)
    assert poll.num_votes() == 3
    assert poll.count_votes(0) == 1
    assert poll.count_votes(1) == 0
    assert poll.count_votes(2) == 2
    assert poll.count_votes(3) == 0

    poll.vote('user0', 1)
    poll.vote('user1', 0)
    assert poll.num_votes() == 5
    assert poll.count_votes(0) == 2
    assert poll.count_votes(1) == 1
    assert poll.count_votes(2) == 2
    assert poll.count_votes(3) == 0

    # user has exhausted her votes
    with pytest.raises(NoMoreVotesError):
        poll.vote('user0', 2)
    assert poll.num_votes() == 5
    assert poll.count_votes(0) == 2
    assert poll.count_votes(1) == 1
    assert poll.count_votes(2) == 2
    assert poll.count_votes(3) == 0

    # voting for the same again is removes the vote
    poll.vote('user0', 1)
    assert poll.num_votes() == 4
    assert poll.count_votes(0) == 2
    assert poll.count_votes(1) == 0
    assert poll.count_votes(2) == 2
    assert poll.count_votes(3) == 0


@pytest.mark.parametrize('max_votes, expected_votes', [
    (1, ([1], [2], [])),
    (2, ([0, 1], [2], []))
], ids=['Single vote', 'Multiple votes'])
def test_votes(max_votes, expected_votes):
    poll = Poll.create('user0123', 'Spam?', 'en', ['Yes', 'Maybe', 'No'],
                       max_votes=max_votes)
    poll.vote('user0', 0)
    poll.vote('user1', 2)
    assert poll.votes('user0') == [0]
    assert poll.votes('user1') == [2]
    assert poll.votes('user2') == []

    poll.vote('user0', 1)
    assert poll.votes('user0') == expected_votes[0]
    assert poll.votes('user1') == expected_votes[1]
    assert poll.votes('user2') == expected_votes[2]


@pytest.mark.parametrize('max_votes, expected', [
    (1, (1, 2, 1, 1)),
    (1, (1, 2, 1, 1)),
], ids=['Single vote', 'Multiple votes'])
def test_num_voters(max_votes, expected):
    poll = Poll.create('user0123', 'Spam?', 'en', ['Yes', 'Maybe', 'No'],
                       max_votes=max_votes)
    assert poll.num_voters() == 0

    poll.vote('user0', 0)
    assert poll.num_voters() == expected[0]
    poll.vote('user1', 2)
    assert poll.num_voters() == expected[1]
    poll.vote('user0', 0)  # unvote
    assert poll.num_voters() == expected[2]
    poll.vote('user1', 1)
    assert poll.num_voters() == expected[3]


def test_end():
    poll = Poll.create('user0123', 'Spam?', 'en', ['Yes', 'Maybe', 'No'],
                       max_votes=2)
    poll.vote('user0', 0)
    poll.vote('user1', 2)
    poll.vote('user2', 2)
    assert poll.num_votes() == 3
    assert poll.count_votes(0) == 1
    assert poll.count_votes(1) == 0
    assert poll.count_votes(2) == 2

    poll.end()
    poll.vote('user3', 0)
    poll.vote('user4', 1)
    assert poll.num_votes() == 3
    assert poll.count_votes(0) == 1
    assert poll.count_votes(1) == 0
    assert poll.count_votes(2) == 2


def test_load():
    poll = Poll.create('user0123', 'Spam?', 'en', ['Yes', 'Maybe', 'No'],
                       secret=True, public=True, max_votes=2, bars=True)

    # because of :memory: database, load() cannot be used directly
    poll2 = Poll(poll.connection, poll.id)
    assert poll.creator_id == poll2.creator_id
    assert poll.message == poll2.message
    assert poll.secret == poll2.secret
    assert poll.public == poll2.public
    assert poll.max_votes == poll2.max_votes
    assert poll.vote_options == poll2.vote_options
    assert poll.bars == poll2.bars


def test_load_invalid():
    with pytest.raises(InvalidPollError):
        Poll.load('bla')

    with pytest.raises(InvalidPollError):
        poll = Poll.create('user0123', 'Spam?', 'en', ['Yes', 'Maybe', 'No'],
                           secret=True, public=True, max_votes=2)
        Poll(poll.connection, 'user3210')
