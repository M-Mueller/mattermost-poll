import sqlite3
import settings


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
    vote_options:
        A list of all available poll choices.
    secret: boolean
        A secret poll does not show the number of votes until the poll ended.
    """
    def __init__(self, connection, id):
        """Creates a new poll without any votes.
        Empty vote_options will be replaced by ['Yes', 'No'].
        """
        self.connection = connection
        self.id = id

        self.vote_options = []
        cur = self.connection.cursor()
        for (name,) in cur.execute("""SELECT name FROM VoteOptions
                       WHERE poll_id=?
                       ORDER BY number ASC""", (self.id,)):
            self.vote_options.append(name)

        cur.execute("""SELECT creator, message, secret FROM Polls
                       WHERE poll_id=?""", (self.id,))
        self.creator_id, self.message, self.secret = cur.fetchone()

    @classmethod
    def create(cls, creator_id, message, vote_options=[], secret=False):
        con = sqlite3.connect(settings.DATABASE)
        cur = con.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS Polls (
                       poll_id integer PRIMARY KEY,
                       creator text NOT NULL,
                       message text NOT NULL,
                       finished integer NOT NULL,
                       secret integer NOT NULL)""")
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
                       CONSTRAINT single_vote UNIQUE (poll_id, voter)
                       ON CONFLICT REPLACE)""")
        con.commit()

        if not vote_options:
            vote_options = ['Yes', 'No']

        cur.execute("""INSERT INTO Polls
                       (creator, message, finished, secret) VALUES
                       (?, ?, ?, ?)""",
                    (creator_id, message, False, secret))
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
        con = sqlite3.connect(settings.DATABASE)
        return cls(con, id)

    def num_votes(self):
        """Returns the total number of votes."""
        cur = self.connection.cursor()
        cur.execute("""SELECT * FROM Votes WHERE poll_id=?""",
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
        # the table constraint makes sure only the last vote is stored
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
        cur = self.connection.cursor()
        cur.execute("""SELECT finished FROM Polls WHERE poll_id=?""",
                    (self.id,))
        return cur.fetchone()[0] == 1
