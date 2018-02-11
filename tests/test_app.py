# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch
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
            'Some message --Foo --Spam --secret',
            'Some message --Foo --Spam --Secret',
            'Some message --Foo --Spam --public',
            'Some message --Foo --Spam --Public',
            '# heading\nSome **markup**<br>:tada: --More ~~markup~~ --:tada: --Spam-!',
            'No whitespace--Foo--Bar--Spam--secret--public',
            '   Trim  whitespace   --   Foo-- Spam  Spam  -- secret',
            'Some message --Foo --Spam --secret --votes=3',
            'Some message --votes=-1 --Foo --Spam',
            'Some message --votes=0 --Foo --Spam',
        ]
        expected = [
            ('Some message', ['Option 1', 'Second Option'], False, False, 1),
            ('Some message', ['Foo', 'Spam'], True, False, 1),
            ('Some message', ['Foo', 'Spam', 'Secret'], False, False, 1),
            ('Some message', ['Foo', 'Spam'], False, True, 1),
            ('Some message', ['Foo', 'Spam', 'Public'], False, False, 1),
            ('# heading\nSome **markup**<br>:tada:',
             ['More ~~markup~~', ':tada:', 'Spam-!'],
             False, False, 1),
            ('No whitespace', ['Foo', 'Bar', 'Spam'], True, True, 1),
            ('Trim  whitespace', ['Foo', 'Spam  Spam'], True, False, 1),
            ('Some message', ['Foo', 'Spam'], True, False, 3),
            ('Some message', ['Foo', 'Spam'], False, False, 1),
            ('Some message', ['Foo', 'Spam'], False, False, 1),
        ]

        for c, e in zip(commands, expected):
            with self.subTest(command=c):
                args = app.parse_slash_command(c)
                self.assertEqual(args.message, e[0])
                self.assertEqual(args.vote_options, e[1])
                self.assertEqual(args.secret, e[2])
                self.assertEqual(args.public, e[3])
                self.assertEqual(args.max_votes, e[4])

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

    def test_vote_to_string(self):
        with self.subTest('Single vote'):
            poll = Poll.create(creator_id='user0', message='Message',
                               vote_options=['Sure', 'Maybe', 'No'])
            poll.vote('user0', 0)
            poll.vote('user1', 2)

            self.assertEqual(app.vote_to_string(poll, 'user0'),
                             'Sure ✓, Maybe ✗, No ✗')
            self.assertEqual(app.vote_to_string(poll, 'user1'),
                             'Sure ✗, Maybe ✗, No ✓')
            self.assertEqual(app.vote_to_string(poll, 'user2'),
                             'Sure ✗, Maybe ✗, No ✗')

        with self.subTest('Two votes'):
            poll = Poll.create(creator_id='user0', message='Message',
                               vote_options=['Sure', 'Maybe', 'No'],
                               max_votes=2)
            poll.vote('user0', 0)
            poll.vote('user0', 2)
            poll.vote('user1', 2)

            self.assertEqual(app.vote_to_string(poll, 'user0'),
                             'Sure ✓, Maybe ✗, No ✓')
            self.assertEqual(app.vote_to_string(poll, 'user1'),
                             'Sure ✗, Maybe ✗, No ✓')
            self.assertEqual(app.vote_to_string(poll, 'user2'),
                             'Sure ✗, Maybe ✗, No ✗')

    def resolve_usernames(user_ids):
        return user_ids

    @patch('app.resolve_usernames', side_effect=resolve_usernames)
    def test_get_poll(self, resolve_usernames):
        with self.subTest('Running poll'):
            poll = Poll.create(creator_id='user0', message='# Spam? **:tada:**',
                               vote_options=['Sure', 'Maybe', 'No'], secret=False)
            poll.vote('user0', 0)
            poll.vote('user1', 1)
            poll.vote('user2', 2)
            poll.vote('user3', 2)

            with app.app.test_request_context(base_url='http://localhost:5005'):
                poll_dict = app.get_poll(poll)

            self.assertIn('response_type', poll_dict)
            self.assertIn('attachments', poll_dict)

            self.assertEqual(poll_dict['response_type'], 'in_channel')
            attachments = poll_dict['attachments']
            self.assertEqual(len(attachments), 1)
            self.assertIn('text', attachments[0])
            self.assertIn('actions', attachments[0])
            self.assertIn('fields', attachments[0])
            self.assertEqual(attachments[0]['text'], poll.message)
            self.assertEqual(len(attachments[0]['actions']), 4)

            fields = attachments[0]['fields']
            self.assertEqual(len(fields), 1)
            self.assertIn('short', fields[0])
            self.assertIn('title', fields[0])
            self.assertIn('value', fields[0])
            self.assertEqual(False, fields[0]['short'])
            self.assertEqual("", fields[0]['title'])
            self.assertEqual('*Number of voters: 4*', fields[0]['value'])

        with self.subTest('Running poll, multiple votes'):
            poll = Poll.create(creator_id='user0', message='# Spam? **:tada:**',
                               vote_options=['Sure', 'Maybe', 'No'],
                               secret=False, max_votes=2)
            poll.vote('user0', 0)
            poll.vote('user1', 1)
            poll.vote('user2', 2)
            poll.vote('user0', 2)

            with app.app.test_request_context(base_url='http://localhost:5005'):
                poll_dict = app.get_poll(poll)

            self.assertIn('response_type', poll_dict)
            self.assertIn('attachments', poll_dict)

            self.assertEqual(poll_dict['response_type'], 'in_channel')
            attachments = poll_dict['attachments']
            self.assertEqual(len(attachments), 1)
            self.assertIn('text', attachments[0])
            self.assertIn('actions', attachments[0])
            self.assertIn('fields', attachments[0])
            self.assertEqual(attachments[0]['text'], poll.message)
            self.assertEqual(len(attachments[0]['actions']), 4)

            fields = attachments[0]['fields']
            self.assertEqual(len(fields), 2)
            self.assertIn('short', fields[0])
            self.assertIn('title', fields[0])
            self.assertIn('value', fields[0])
            self.assertEqual(False, fields[0]['short'])
            self.assertEqual("", fields[0]['title'])
            self.assertEqual('*Number of voters: 3*', fields[0]['value'])

            self.assertIn('short', fields[1])
            self.assertIn('title', fields[1])
            self.assertIn('value', fields[1])
            self.assertEqual(False, fields[1]['short'])
            self.assertEqual("", fields[1]['title'])
            self.assertEqual('*You have 2 votes*', fields[1]['value'])

        with self.subTest('Finished poll'):
            poll = Poll.create(creator_id='user0', message='# Spam? **:tada:**',
                               vote_options=['Sure', 'Maybe', 'No'], secret=False)
            poll.vote('user0', 0)
            poll.vote('user1', 1)
            poll.vote('user2', 2)
            poll.vote('user3', 2)
            poll.end()

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
            self.assertEqual(len(fields), 4)

            self.assertIn('short', fields[0])
            self.assertIn('title', fields[0])
            self.assertIn('value', fields[0])
            self.assertEqual(False, fields[0]['short'])
            self.assertEqual("", fields[0]['title'])
            self.assertEqual('*Number of voters: 4*', fields[0]['value'])

            expected = [
                (poll.vote_options[0], '1 (25.0%)'),
                (poll.vote_options[1], '1 (25.0%)'),
                (poll.vote_options[2], '2 (50.0%)'),
            ]
            for field, (title, value) in zip(fields[1:], expected):
                self.assertIn('short', field)
                self.assertIn('title', field)
                self.assertIn('value', field)
                self.assertEqual(True, field['short'])
                self.assertEqual(title, field['title'])
                self.assertEqual(value, field['value'])

        with self.subTest('Finished public poll'):
            poll = Poll.create(creator_id='user0', message='# Spam? **:tada:**',
                               vote_options=['Sure', 'Maybe', 'No'],
                               public=True)
            poll.vote('user0', 0)
            poll.vote('user1', 1)
            poll.vote('user2', 2)
            poll.vote('user3', 2)
            poll.end()

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
            self.assertEqual(len(fields), 4)

            self.assertIn('short', fields[0])
            self.assertIn('title', fields[0])
            self.assertIn('value', fields[0])
            self.assertEqual(False, fields[0]['short'])
            self.assertEqual("", fields[0]['title'])
            self.assertEqual('*Number of voters: 4*', fields[0]['value'])

            expected = [
                (poll.vote_options[0], '1 (25.0%)', ['user0']),
                (poll.vote_options[1], '1 (25.0%)', ['user1']),
                (poll.vote_options[2], '2 (50.0%)', ['user2', 'user3']),
            ]
            for field, (title, value, users) in zip(fields[1:], expected):
                self.assertIn('short', field)
                self.assertIn('title', field)
                self.assertIn('value', field)
                self.assertEqual(True, field['short'])
                self.assertEqual(title, field['title'])
                self.assertIn(value, field['value'])
                for user in users:
                    self.assertIn(user, field['value'])
