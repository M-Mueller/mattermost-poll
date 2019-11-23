"""Dummy settings using during tests"""

TEST_SETTINGS = True

# Path to the database file.
DATABASE = 'poll_test.db'

# Optional Mattermost token
MATTERMOST_TOKENS = None

# URL of the Mattermost server
MATTERMOST_URL = 'http://www.example.com'

# Private access token of some user.
# Required to resolve username in 'public' polls.
# https://docs.mattermost.com/developer/personal-access-tokens.html
MATTERMOST_PA_TOKEN = None

# *_BY_DEFAULT settings are implicitly set by app.py (testing default values)
