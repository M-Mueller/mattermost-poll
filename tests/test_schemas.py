# pylint: disable=missing-docstring
"""Tests if the schemas behave as we expect."""
import json
import jsonschema
import pytest
from tests import schemas


def test_poll_valid():
    sample = json.loads("""
    {
        "response_type": "in_channel",
        "attachments": [{
            "text": "# Who wants **Pizza**?",
            "actions": [
            {
                "name": ":pizza: (0)",
                "integration": {
                    "context": {
                        "poll_id": "abc123",
                        "vote": 0
                    },
                    "url": "http://localhost:5000/vote"
                }
            },
            {
                "name": "Bah (0)",
                "integration": {
                    "context": {
                        "poll_id": "abc123",
                        "vote": 1
                    },
                    "url": "http://localhost:5000/vote"
                }
            },
            {
                "name": "End Poll",
                "integration": {
                    "url": "http://localhost:5000/end",
                    "context": {
                        "poll_id": "abc123"
                    }
                }
            }],
            "fields": [
            {
                "short": false,
                "title": "",
                "value": "Number of Votes: 1"
            }]
        }]
    }
    """)
    jsonschema.validate(sample, schemas.poll)


def test_poll_missing_text():
    sample = json.loads("""
    {
        "response_type": "in_channel",
        "attachments": [{
            "actions": [
            {
                "name": ":pizza: (0)",
                "integration": {
                    "context": {
                        "poll_id": "abc123",
                        "vote": 0
                    },
                    "url": "http://localhost:5000/vote"
                }
            },
            {
                "name": "End Poll",
                "integration": {
                    "url": "http://localhost:5000/end",
                    "context": {
                        "poll_id": "abc123"
                    }
                }
            }]
        }]
    }
    """)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(sample, schemas.poll)


def test_poll_not_enough_actions():
    sample = json.loads("""
    {
        "response_type": "in_channel",
        "attachments": [{
            "text": "Foo",
            "actions": [
            {
                "name": "End Poll",
                "integration": {
                    "url": "http://localhost:5000/end",
                    "context": {
                        "poll_id": "abc123"
                    }
                }
            }]
        }]
    }
    """)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(sample, schemas.poll)


def test_ephemeral_valid():
    sample = json.loads("""
    {
        "response_type": "ephemeral",
        "text": "Please provide a message"
    }
    """)
    jsonschema.validate(sample, schemas.ephemeral)


def test_ephemeral_invalid():
    sample = json.loads("""
    {
        "response_type": "ephemeral"
    }
    """)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(sample, schemas.ephemeral)


def test_vote_valid():
    sample = json.loads("""
    {
        "ephemeral_text": "Your vote has been updated to 'Bah'",
        "update": {
            "props": {
                "response_type": "in_channel",
                "attachments": [{
                    "text": "# Who wants **Pizza**?",
                    "actions": [
                    {
                        "name": ":pizza: (0)",
                        "integration": {
                            "context": {
                                "poll_id": "abc123",
                                "vote": 0
                            },
                            "url": "http://localhost:5000/vote"
                        }
                    },
                    {
                        "name": "Bah (0)",
                        "integration": {
                            "context": {
                                "poll_id": "abc123",
                                "vote": 1
                            },
                            "url": "http://localhost:5000/vote"
                        }
                    },
                    {
                        "name": "End Poll",
                        "integration": {
                            "url": "http://localhost:5000/end",
                            "context": {
                                "poll_id": "abc123"
                            }
                        }
                    }]
                }]
            }
        }
    }
    """)
    jsonschema.validate(sample, schemas.vote)


def test_end_valid():
    sample = json.loads("""
    {
        "update": {
            "props": {
                "attachments": [
                    {
                        "fields": [
                            {
                                "short": false,
                                "title": "",
                                "value": "Number of Votes: 1"
                            },
                            {
                                "short": true,
                                "title": "Spam",
                                "value": "1 (33.3%)"
                            },
                            {
                                "short": true,
                                "title": "Foo",
                                "value": "1 (33.3%)"
                            },
                            {
                                "short": true,
                                "title": "Bar",
                                "value": "1 (33.3%)"
                            }
                        ],
                        "text": "Message"
                    }
                ],
                "response_type": "in_channel"
            }
        }
    }
    """)
    jsonschema.validate(sample, schemas.end)
