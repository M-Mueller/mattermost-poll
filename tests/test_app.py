import unittest
import app
import settings
from poll import Poll


class AppTest(unittest.TestCase):
    def setUp(self):
        settings.DATABASE = ':memory:'

    def test_parse_slash_command(self):
        args = app.parse_slash_command('')
        self.assertEqual(args.message, '')
        self.assertEqual(args.vote_options, [])
        self.assertEqual(args.secret, False)

        commands = [
            'Some message --Option 1 --Second Option',
            'Some message --Foo --Spam --Secret',
            '# heading\nSome **markup**<br>:tada: --More ~~markup~~ --:tada: --Spam-!',
            'No whitespace--Foo--Bar--Spam--secret',
            '   Trim  whitespace   --   Foo-- Spam  Spam  --secret'
        ]
        expected = [
            ('Some message', ['Option 1', 'Second Option'], False),
            ('Some message', ['Foo', 'Spam'], True),
            ('# heading\nSome **markup**<br>:tada:',
             ['More ~~markup~~', ':tada:', 'Spam-!'],
             False),
            ('No whitespace', ['Foo', 'Bar', 'Spam'], True),
            ('Trim  whitespace', ['Foo', 'Spam  Spam'], True),
        ]

        for c, e in zip(commands, expected):
            with self.subTest(command=c):
                args = app.parse_slash_command(c)
                self.assertEqual(args.message, e[0])
                self.assertEqual(args.vote_options, e[1])
                self.assertEqual(args.secret, e[2])

    def test_get_actions(self):
        poll = Poll.create(creator_id='user0', message='Message',
                           vote_options=['Yes', 'No'], secret=False)

        with self.subTest('Fresh poll'):
            expected = [
                ('Yes (0)', 0),
                ('No (0)', 1),
            ]
            self.__test_get_actions(poll, expected)

        with self.subTest('With votes'):
            poll.vote('user0', 0)
            poll.vote('user1', 0)
            poll.vote('user2', 0)
            poll.vote('user3', 1)
            poll.vote('user4', 1)
            expected = [
                ('Yes (3)', 0),
                ('No (2)', 1),
            ]
            self.__test_get_actions(poll, expected)

        poll = Poll.create(creator_id='user0', message='Message',
                           vote_options=['Yes', 'No'], secret=True)

        with self.subTest('Secret vote'):
            poll.vote('user0', 0)
            poll.vote('user1', 0)
            poll.vote('user2', 0)
            poll.vote('user3', 1)
            poll.vote('user4', 1)
            expected = [
                ('Yes', 0),
                ('No', 1),
            ]
            self.__test_get_actions(poll, expected)

    def __test_get_actions(self, poll, expected):
        with app.app.test_request_context(base_url='http://localhost:5005'):
            actions = app.get_actions(poll)
        self.assertEqual(len(actions), 3)

        for action, (name, vote) in zip(actions[:-1], expected):
            self.assertIn('name', action)
            self.assertIn('integration', action)

            self.assertEqual(action['name'], name)
            integration = action['integration']
            self.assertIn('context', integration)
            self.assertIn('url', integration)
            self.assertEqual(integration['url'], 'http://localhost:5005/vote')

            context = integration['context']
            self.assertIn('vote', context)
            self.assertIn('poll_id', context)
            self.assertEqual(context['vote'], vote)
            self.assertEqual(context['poll_id'], poll.id)

        action = actions[-1]
        self.assertIn('name', action)
        self.assertIn('integration', action)

        self.assertEqual(action['name'], 'End Poll')
        integration = action['integration']
        self.assertIn('context', integration)
        self.assertIn('url', integration)
        self.assertEqual(integration['url'], 'http://localhost:5005/end')

        context = integration['context']
        self.assertIn('poll_id', context)
        self.assertEqual(context['poll_id'], poll.id)

    def test_get_poll(self):
        poll = Poll.create(creator_id='user0', message='# Spam? **:tada:**',
                           vote_options=['Sure', 'Maybe', 'No'], secret=False)
        poll.vote('user0', 0)
        poll.vote('user1', 1)
        poll.vote('user2', 2)
        poll.vote('user3', 2)

        with self.subTest('Running poll'):
            with app.app.test_request_context(base_url='http://localhost:5005'):
                poll_dict = app.get_poll(poll)

            self.assertIn('response_type', poll_dict)
            self.assertIn('attachments', poll_dict)

            self.assertEqual(poll_dict['response_type'], 'in_channel')
            attachments = poll_dict['attachments']
            self.assertEqual(len(attachments), 1)
            self.assertIn('text', attachments[0])
            self.assertIn('actions', attachments[0])
            self.assertNotIn('fields', attachments[0])
            self.assertEqual(attachments[0]['text'], poll.message)
            self.assertEqual(len(attachments[0]['actions']), 4)

        poll.end()

        with self.subTest('Finished poll'):
            with app.app.test_request_context(base_url='http://localhost:5005'):
                poll_dict = app.get_poll(poll)

            self.assertIn('response_type', poll_dict)
            self.assertIn('attachments', poll_dict)

            self.assertEqual(poll_dict['response_type'], 'in_channel')
            attachments = poll_dict['attachments']
            self.assertEqual(len(attachments), 1)
            self.assertIn('text', attachments[0])
            self.assertNotIn('actions', attachments[0])
            self.assertIn('fields', attachments[0])
            self.assertEqual(attachments[0]['text'], poll.message)

            fields = attachments[0]['fields']
            self.assertEqual(len(fields), 3)
            expected = [
                (poll.vote_options[0], '1 (25.0%)'),
                (poll.vote_options[1], '1 (25.0%)'),
                (poll.vote_options[2], '2 (50.0%)'),
            ]
            for field, (title, value) in zip(fields, expected):
                self.assertIn('short', field)
                self.assertIn('title', field)
                self.assertIn('value', field)
                self.assertEqual(True, field['short'])
                self.assertEqual(title, field['title'])
                self.assertEqual(value, field['value'])
