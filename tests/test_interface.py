from tests import schemas
import app
import settings
import unittest
import json
import jsonschema
import tempfile
from collections import namedtuple


class InterfaceTest(unittest.TestCase):
    def setUp(self):
        app.app.testing = True
        self.base_url = 'http://www.example.com:5005/'
        self.app = app.app.test_client()

        # Since each request creates a new database connection, we cannot
        # use :memory: here
        self.dbfile = tempfile.NamedTemporaryFile()
        settings.DATABASE = self.dbfile.name

        settings.MATTERMOST_TOKEN = None

    def test_no_username(self):
        response = self.app.post('/', base_url=self.base_url)
        self.assertEqual(response.status_code, 400)

    def __validate_reponse(self, response_json, message, vote_options):
        """Validates the response against the json schema expected by
        Mattermost.
        """
        # validate the schema
        jsonschema.validate(response_json, schemas.poll)

        # validate the values
        self.assertEqual(response_json['attachments'][0]['text'], message)
        actions = response_json['attachments'][0]['actions']
        self.assertEqual(len(actions), len(vote_options) + 1)

        for action, vote in zip(actions[:-1], vote_options):
            self.assertIn(vote, action['name'])
            integration = action['integration']
            self.assertEqual(integration['url'], self.base_url + 'vote')

        integration = actions[-1]['integration']
        self.assertEqual(integration['url'], self.base_url + 'end')

    def __validate_vote_response(self, response_json, message, vote_options,
                                 voted_id):
        """Validates the response after a vote."""
        jsonschema.validate(response_json, schemas.vote)

        poll_json = response_json['update']['props']
        self.__validate_reponse(poll_json, message, vote_options)

        # check if the message to the user contains the voted text
        message = response_json['ephemeral_text']
        self.assertIn(vote_options[voted_id], message)

    def __validate_end_response(self, response_json, message, vote_options):
        """Validates the response when the vote ends."""
        jsonschema.validate(response_json, schemas.end)

        # check if all fields are there (content of fields is 
        # tested in test_app)
        fields = response_json['update']['props']['attachments'][0]['fields']
        self.assertEqual(len(fields), len(vote_options) + 1)

    def test_poll(self):
        SubTest = namedtuple('SubTest', ['data', 'status_code',
                                         'message', 'vote_options'])
        sub_tests = {
            'No data': SubTest({}, 400, 'Message', ['Yes', 'No']),
            'No text': SubTest({'user_id': 'user0'}, 400, '', ['Yes', 'No']),
            'No user_id': SubTest({'text': 'bla'}, 400, '', ['Yes', 'No']),
            'Default options': SubTest(
                {
                    'user_id': 'user0',
                    'text': 'Poll message'
                }, 200,
                'Poll message', ['Yes', 'No']
            ),
            'Explicit options': SubTest(
                {
                    'user_id': 'user0',
                    'text': 'Poll message --First --Second --Third'
                }, 200,
                'Poll message', ['First', 'Second', 'Third']
            ),
        }

        for name, subTest in sub_tests.items():
            with self.subTest(name):
                response = self.app.post('/', data=subTest.data, base_url=self.base_url)
                self.assertEqual(subTest.status_code, response.status_code)
                if subTest.status_code != 200:
                    continue

                rd = json.loads(response.data)
                self.__validate_reponse(rd, subTest.message,
                                        subTest.vote_options)

        with self.subTest('No message'):
            data = {
                'user_id': 'user0',
                'text': ''
            }
            response = self.app.post('/', data=data, base_url=self.base_url)
            self.assertEqual(200, response.status_code)

            rd = json.loads(response.data)
            jsonschema.validate(rd, schemas.ephemeral)

    def test_vote(self):
        SubTest = namedtuple('SubTest', ['votes', 'expected'])
        subTests = {
            'One vote': SubTest(
                [('user2', 2)],
                (0, 0, 1)
            ),
            'Three votes': SubTest(
                [('user0', 0), ('user1', 1), ('user2', 2)],
                (1, 1, 1)
            ),
            'Changed vote': SubTest(
                [('user0', 0), ('user1', 1), ('user0', 1)],
                (0, 2, 0)
            ),
        }

        for name, subTest in subTests.items():
            with self.subTest(name):
                # create a new poll
                data = {
                    'user_id': 'user0',
                    'text': 'Message --Spam --Foo --Bar'
                }
                response = self.app.post('/', data=data, base_url=self.base_url)
                rd = json.loads(response.data)

                actions = rd['attachments'][0]['actions']
                self.assertEqual(len(actions), 4)
                action_urls = [a['integration']['url'].replace(self.base_url, '')
                               for a in actions]
                action_contexts = [a['integration']['context'] for a in actions]

                # place votes by calling the url in the action with the
                # corresponding context (i.e. what Mattermost is doing)
                for user, vote in subTest.votes:
                    context = action_contexts[vote]
                    data = json.dumps({
                        'user_id': user,
                        'context': context
                    })
                    response = self.app.post(action_urls[vote],
                                             data=data,
                                             content_type='application/json',
                                             base_url=self.base_url)
                    self.assertEqual(200, response.status_code)

                    rd = json.loads(response.data)
                    self.__validate_vote_response(rd, 'Message',
                                                  ['Spam', 'Foo', 'Bar'], vote)

                # check if the number of votes is contained in the actions name
                actions = rd['update']['props']['attachments'][0]['actions']
                self.assertEqual(len(actions), 4)
                for action, num_votes in zip(actions, subTest.expected):
                    self.assertIn(str(num_votes), action['name'])

    def test_end(self):
        SubTest = namedtuple('SubTest', ['votes', 'expected'])
        subTests = {
            'No votes': SubTest(
                [],
                (0, 0, 0)
            ),
            'Three votes': SubTest(
                [('user0', 0), ('user1', 1), ('user2', 2)],
                (1, 1, 1)
            )
        }

        for name, subTest in subTests.items():
            with self.subTest(name):
                # create a new poll
                data = {
                    'user_id': 'user0',
                    'text': 'Message --Spam --Foo --Bar'
                }
                response = self.app.post('/', data=data, base_url=self.base_url)
                rd = json.loads(response.data)

                actions = rd['attachments'][0]['actions']
                self.assertEqual(len(actions), 4)
                action_urls = [a['integration']['url'].replace(self.base_url, '')
                               for a in actions]
                action_contexts = [a['integration']['context'] for a in actions]

                # place the votes
                for user, vote in subTest.votes:
                    context = action_contexts[vote]
                    data = json.dumps({
                        'user_id': user,
                        'context': context
                    })
                    response = self.app.post(action_urls[vote],
                                             data=data,
                                             content_type='application/json',
                                             base_url=self.base_url)
                    self.assertEqual(200, response.status_code)

                context = action_contexts[-1]
                data = json.dumps({
                    'user_id': 'user0',
                    'context': context
                })
                response = self.app.post(action_urls[-1],
                                         data=data,
                                         content_type='application/json',
                                         base_url=self.base_url)
                self.assertEqual(200, response.status_code)

                rd = json.loads(response.data)
                self.__validate_end_response(rd, 'Message', ['Spam', 'Foo', 'Bar'])
