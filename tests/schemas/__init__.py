"""Provides JSON schemas for different responses.
The *schemas* namespace contains a object for each
JSON file in the package directory.
See https://spacetelescope.github.io/understanding-json-schema/index.html
for an introduction to JSON schema.
"""
import json


with open(__path__[0] + '/poll.json', 'r') as file:
    poll = json.load(file)
with open(__path__[0] + '/ephemeral.json', 'r') as file:
    ephemeral = json.load(file)
with open(__path__[0] + '/vote.json', 'r') as file:
    vote = json.load(file)
with open(__path__[0] + '/end.json', 'r') as file:
    end = json.load(file)
