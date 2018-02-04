import unittest
import settings
from poll import Poll, NoMoreVotesError


class PollTest(unittest.TestCase):
    def setUp(self):
        settings.DATABASE = ':memory:'

    def test_init(self):
        creator_id = 'user01234'
        message = '## Markdown message<br>Test **bla**'
        vote_options = ['Option 1', 'Another option', 'Spam!']
        poll = Poll.create(creator_id, message, vote_options, True)
        self.assertEqual(poll.creator_id, creator_id)
        self.assertEqual(poll.message, message)
        self.assertEqual(poll.vote_options, vote_options)
        self.assertEqual(poll.secret, True)

    def test_init_defaults(self):
        creator_id = 'user01234'
        message = '## Markdown message<br>Test **bla**'
        poll = Poll.create(creator_id, message)
        self.assertEqual(poll.creator_id, creator_id)
        self.assertEqual(poll.message, message)
        self.assertEqual(poll.vote_options, ['Yes', 'No'])
        self.assertEqual(poll.secret, False)

    def test_vote(self):
        poll = Poll.create('user0123', 'Spam?', ['Yes', 'Maybe', 'No'])
        self.assertEqual(poll.num_votes(), 0)
        self.assertEqual(poll.count_votes(0), 0)
        self.assertEqual(poll.count_votes(1), 0)
        self.assertEqual(poll.count_votes(2), 0)
        self.assertEqual(poll.count_votes(3), 0)

        poll.vote('user0', 0)
        poll.vote('user1', 2)
        poll.vote('user2', 2)
        self.assertEqual(poll.num_votes(), 3)
        self.assertEqual(poll.count_votes(0), 1)
        self.assertEqual(poll.count_votes(1), 0)
        self.assertEqual(poll.count_votes(2), 2)
        self.assertEqual(poll.count_votes(3), 0)

        poll.vote('user0', 0)
        poll.vote('user0', 0)
        self.assertEqual(poll.num_votes(), 3)
        self.assertEqual(poll.count_votes(0), 1)
        self.assertEqual(poll.count_votes(1), 0)
        self.assertEqual(poll.count_votes(2), 2)
        self.assertEqual(poll.count_votes(3), 0)

        poll.vote('user2', 1)
        self.assertEqual(poll.num_votes(), 3)
        self.assertEqual(poll.count_votes(0), 1)
        self.assertEqual(poll.count_votes(1), 1)
        self.assertEqual(poll.count_votes(2), 1)
        self.assertEqual(poll.count_votes(3), 0)

    def test_multiple_votes(self):
        poll = Poll.create('user0123', 'Spam?', ['Yes', 'Maybe', 'No'],
                           max_votes=2)
        self.assertEqual(poll.num_votes(), 0)
        self.assertEqual(poll.count_votes(0), 0)
        self.assertEqual(poll.count_votes(1), 0)
        self.assertEqual(poll.count_votes(2), 0)
        self.assertEqual(poll.count_votes(3), 0)

        poll.vote('user0', 0)
        poll.vote('user1', 2)
        poll.vote('user2', 2)
        self.assertEqual(poll.num_votes(), 3)
        self.assertEqual(poll.count_votes(0), 1)
        self.assertEqual(poll.count_votes(1), 0)
        self.assertEqual(poll.count_votes(2), 2)
        self.assertEqual(poll.count_votes(3), 0)

        poll.vote('user0', 1)
        poll.vote('user1', 0)
        self.assertEqual(poll.num_votes(), 5)
        self.assertEqual(poll.count_votes(0), 2)
        self.assertEqual(poll.count_votes(1), 1)
        self.assertEqual(poll.count_votes(2), 2)
        self.assertEqual(poll.count_votes(3), 0)

        # user has exhausted her votes
        with self.assertRaises(NoMoreVotesError):
            poll.vote('user0', 2)
        self.assertEqual(poll.num_votes(), 5)
        self.assertEqual(poll.count_votes(0), 2)
        self.assertEqual(poll.count_votes(1), 1)
        self.assertEqual(poll.count_votes(2), 2)
        self.assertEqual(poll.count_votes(3), 0)

        # voting for the same again is removes the vote
        poll.vote('user0', 1)
        self.assertEqual(poll.num_votes(), 4)
        self.assertEqual(poll.count_votes(0), 2)
        self.assertEqual(poll.count_votes(1), 0)
        self.assertEqual(poll.count_votes(2), 2)
        self.assertEqual(poll.count_votes(3), 0)

    def test_votes(self):
        with self.subTest('Single vote'):
            poll = Poll.create('user0123', 'Spam?', ['Yes', 'Maybe', 'No'])
            poll.vote('user0', 0)
            poll.vote('user1', 2)
            self.assertEqual(poll.votes('user0'), [0])
            self.assertEqual(poll.votes('user1'), [2])
            self.assertEqual(poll.votes('user2'), [])

            poll.vote('user0', 1)
            self.assertEqual(poll.votes('user0'), [1])
            self.assertEqual(poll.votes('user1'), [2])
            self.assertEqual(poll.votes('user2'), [])

        with self.subTest('Multiple vote'):
            poll = Poll.create('user0123', 'Spam?', ['Yes', 'Maybe', 'No'],
                               max_votes=2)
            poll.vote('user0', 0)
            poll.vote('user1', 2)
            self.assertEqual(poll.votes('user0'), [0])
            self.assertEqual(poll.votes('user1'), [2])
            self.assertEqual(poll.votes('user2'), [])

            poll.vote('user0', 1)
            self.assertEqual(poll.votes('user0'), [0, 1])
            self.assertEqual(poll.votes('user1'), [2])
            self.assertEqual(poll.votes('user2'), [])

    def test_num_voters(self):
        with self.subTest('Single vote'):
            poll = Poll.create('user0123', 'Spam?', ['Yes', 'Maybe', 'No'])
            self.assertEqual(poll.num_voters(), 0)

            poll.vote('user0', 0)
            self.assertEqual(poll.num_voters(), 1)
            poll.vote('user1', 2)
            self.assertEqual(poll.num_voters(), 2)

        with self.subTest('Multiple vote'):
            poll = Poll.create('user0123', 'Spam?', ['Yes', 'Maybe', 'No'],
                               max_votes=2)
            self.assertEqual(poll.num_voters(), 0)

            poll.vote('user0', 0)
            self.assertEqual(poll.num_voters(), 1)
            poll.vote('user1', 2)
            self.assertEqual(poll.num_voters(), 2)
            poll.vote('user0', 0)  # unvote
            self.assertEqual(poll.num_voters(), 1)
            poll.vote('user1', 1)
            self.assertEqual(poll.num_voters(), 1)

    def test_end(self):
        poll = Poll.create('user0123', 'Spam?', ['Yes', 'Maybe', 'No'],
                           max_votes=2)
        poll.vote('user0', 0)
        poll.vote('user1', 2)
        poll.vote('user2', 2)
        self.assertEqual(poll.num_votes(), 3)
        self.assertEqual(poll.count_votes(0), 1)
        self.assertEqual(poll.count_votes(1), 0)
        self.assertEqual(poll.count_votes(2), 2)

        poll.end()
        poll.vote('user3', 0)
        poll.vote('user4', 1)
        self.assertEqual(poll.num_votes(), 3)
        self.assertEqual(poll.count_votes(0), 1)
        self.assertEqual(poll.count_votes(1), 0)
        self.assertEqual(poll.count_votes(2), 2)
