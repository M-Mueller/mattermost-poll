import sqlite3

from flask_babel import force_locale, gettext as tr

import settings


class NoMoreVotesError(Exception):
    """Raised when user tries to vote but has no votes left."""
    pass


class InvalidPollError(Exception):
    """Raised when Poll creation or loading failed."""
    pass


def init_database(con):
    """Initializes the database. Is automatically called the first time a Poll
    is created."""
    cur = con.cursor()
    cur.execute("""PRAGMA user_version = 1""")
    cur.execute("""CREATE TABLE IF NOT EXISTS Polls (
                   poll_id integer PRIMARY KEY,
                   creator text NOT NULL,
                   message text NOT NULL,
                   locale text NOT NULL,
                   finished integer NOT NULL,
                   secret integer NOT NULL,
                   public integer NOT NULL,
                   max_votes integer NOT NULL,
                   bars integer NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS VoteOptions (
                   poll_id integer REFERENCES Polls (poll_id)
                   ON DELETE CASCADE ON UPDATE NO ACTION,
                   number integer NOT NULL,
                   name text NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS Votes (
                   poll_id integer REFERENCES Polls (poll_id)
                   ON DELETE CASCADE ON UPDATE NO ACTION,
                   voter text NOT NULL,
                   vote integer NOT NULL,
                   CONSTRAINT single_vote UNIQUE
                   (poll_id, voter, vote) ON CONFLICT REPLACE)""")
    con.commit()

    cur.execute("""PRAGMA table_info(Polls)""")
    if 'bars' not in (c[1] for c in cur.fetchall()):
        print("Outdated database version detected, adding 'bars' column.")
        cur.execute("""ALTER TABLE Polls
                       ADD COLUMN bars integer NOT NULL DEFAULT 0""")
        con.commit()

    cur.execute("""PRAGMA table_info(Polls)""")
    if 'locale' not in (c[1] for c in cur.fetchall()):
        print("Outdated database version detected, adding 'locale' column.")
        cur.execute("""ALTER TABLE Polls
                       ADD COLUMN locale text NOT NULL DEFAULT "en" """)
        con.commit()


class Poll:
    """The Poll class represents a single poll with a message and multiple
    options.
    Each user has one vote and can change it until the poll is ended.
    Internally each Poll is saved in a database.

    Attributes
    ----------
    id:
        A unique identifier for this poll
    creator_id:
        User ID of the user that created the poll.
    message:
        The message of the poll (may contain markup).
    locale:
        The locale with which the poll was created.
    vote_options:
        A list of all available poll choices.
    secret: boolean
        A secret poll does not show the number of votes until the poll ended.
    public: boolean
        In a public vote, who voted for what is displayed at the end of the
        poll
    bars: bollean
        Show result as bar chart
    max_votes: int
        Number of votes each user has.
    """
    def __init__(self, connection, id):
        """Loads the poll with `id` from the database connection.
        Use `create` or `load` instead.
        """
        init_database(connection)
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self.id = id

        try:
            self.vote_options = []
            cur = self.connection.cursor()
            for (name,) in cur.execute("""SELECT name FROM VoteOptions
                           WHERE poll_id=?
                           ORDER BY number ASC""", (self.id,)):
                self.vote_options.append(name)

            if not self.vote_options:
                raise InvalidPollError()

            cur.execute("""SELECT creator, message, locale,
                                  secret, public, max_votes, bars FROM Polls
                           WHERE poll_id=?""", (self.id,))
            row = cur.fetchone()
            if not row:
                raise InvalidPollError()

            self.creator_id = row['creator']
            self.message = row['message']
            self.locale = row['locale']
            self.secret = row['secret']
            self.public = row['public']
            self.max_votes = row['max_votes']
            self.bars = row['bars']

        except sqlite3.Error as e:
            raise InvalidPollError() from e

    @classmethod
    def create(cls, creator_id, message, locale='en', vote_options=[],
               secret=False, public=False, max_votes=1, bars=False):
        """Creates a new poll without any votes.
        Empty vote_options will be replaced by ['Yes', 'No'].
        """
        con = sqlite3.connect(settings.DATABASE)
        init_database(con)
        cur = con.cursor()

        if not vote_options:
            with force_locale(locale):
                vote_options = [tr('Yes'), tr('No')]
        # clamp to 1 to len(vote_options)
        max_votes = max(1, min(max_votes, len(vote_options)))

        cur.execute("""INSERT INTO Polls
                       (creator, message, locale, finished,
                        secret, public, max_votes, bars) VALUES
                       (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (creator_id, message, locale, False,
                     secret, public, max_votes, bars))
        id = cur.lastrowid
        for number, name in enumerate(vote_options):
            cur.execute("""INSERT INTO VoteOptions
                           (poll_id, name, number) VALUES
                           (?, ?, ?)""",
                        (id, name, number))
        con.commit()
        return cls(con, id)

    @classmethod
    def load(cls, id):
        """Loads a poll from the database.
        Raise a InvalidPollError if no poll with that id
        exists.
        """
        con = sqlite3.connect(settings.DATABASE)
        return cls(con, id)

    def num_votes(self):
        """Returns the total number of votes."""
        cur = self.connection.cursor()
        cur.execute("""SELECT * FROM Votes WHERE poll_id=?""",
                    (self.id,))
        return len(cur.fetchall())

    def num_voters(self):
        """Returns the total number of users which voted."""
        cur = self.connection.cursor()
        cur.execute("""SELECT COUNT(vote) FROM Votes
                       WHERE poll_id=?
                       GROUP BY voter""",
                    (self.id,))
        return len(cur.fetchall())

    def count_votes(self, vote_id):
        """Returns the number of votes for the given option.
        The `vote_id` is the index of an option in the vote_options.
        If the vote_id does not exists, 0 is returned.
        """
        cur = self.connection.cursor()
        cur.execute("""SELECT * FROM Votes
                       WHERE poll_id=? AND vote=?""",
                    (self.id, vote_id))
        return len(cur.fetchall())

    def voters(self, vote_id):
        """Returns all voters for a given vote_id."""
        cur = self.connection.cursor()
        cur.execute("""SELECT voter FROM Votes
                       WHERE poll_id=? AND vote=?""",
                    (self.id, vote_id))
        return [voter[0] for voter in cur.fetchall()]

    def votes(self, user_id):
        """Returns a list of `vote_id`s the user voted for.
        The `vote_id` is the index of an option in the vote_options.
        """
        cur = self.connection.cursor()
        cur.execute("""SELECT vote FROM Votes
                       WHERE poll_id=? AND voter=?""",
                    (self.id, user_id))
        return [v[0] for v in cur.fetchall()]

    def vote(self, user_id, vote_id):
        """Places a vote of the given user.
        The `vote_id` is the index of an option in the vote_options.
        Voting is only possible when the poll is not finished yet.
        Invalid `vote_id`s raise an IndexError.
        Each user only has a single vote.
        When voting multiple times for different options, only the
        last vote will remain.
        """
        if self.is_finished():
            return
        if vote_id < 0 or vote_id >= len(self.vote_options):
            raise IndexError('Invalid vote_id: {}'.format(vote_id))

        cur = self.connection.cursor()

        votes = self.votes(user_id)
        if vote_id in votes:
            # unvote
            cur.execute("""DELETE FROM Votes
                        WHERE poll_id=? AND voter=? AND vote=?""",
                        (self.id, user_id, vote_id))
        else:
            # check if the user hasn't used all his votes yet
            if len(votes) >= self.max_votes:
                if self.max_votes == 1:
                    # remove the other vote automatically
                    cur.execute("""DELETE FROM Votes
                                   WHERE poll_id=? AND voter=?""",
                                (self.id, user_id))
                else:
                    raise NoMoreVotesError()
            cur.execute("""INSERT INTO Votes
                           (poll_id, voter, vote) VALUES
                           (?, ?, ?)""",
                        (self.id, user_id, vote_id))
        self.connection.commit()

    def end(self):
        """Ends the poll.
        After the poll ends, voting is not possible anymore.
        """
        cur = self.connection.cursor()
        cur.execute("""UPDATE Polls SET finished=1 WHERE poll_id=?""",
                    (self.id,))
        self.connection.commit()

    def is_finished(self):
        """Return True if the poll is finished or False otherwise."""
        cur = self.connection.cursor()
        cur.execute("""SELECT finished FROM Polls WHERE poll_id=?""",
                    (self.id,))
        return cur.fetchone()[0] == 1
