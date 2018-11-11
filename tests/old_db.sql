PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE Polls (
                       poll_id integer PRIMARY KEY,
                       creator text NOT NULL,
                       message text NOT NULL,
                       finished integer NOT NULL,
                       secret integer NOT NULL,
                       public integer NOT NULL,
                       max_votes integer NOT NULL);
INSERT INTO Polls VALUES(1,'9eu8hqt36tgg8q6w6ypu4ww1ch','Spam with...',0,0,1,2);
INSERT INTO Polls VALUES(2,'9eu8hqt36tgg8q6w6ypu4ww1ch','Spam with...',0,0,1,2);
CREATE TABLE VoteOptions (
                       poll_id integer REFERENCES Polls (poll_id)
                       ON DELETE CASCADE ON UPDATE NO ACTION,
                       number integer NOT NULL,
                       name text NOT NULL);
INSERT INTO VoteOptions VALUES(1,0,'Eggs');
INSERT INTO VoteOptions VALUES(1,1,'Bacon');
INSERT INTO VoteOptions VALUES(1,2,'More Spam');
INSERT INTO VoteOptions VALUES(2,0,'Eggs');
INSERT INTO VoteOptions VALUES(2,1,'Bacon');
INSERT INTO VoteOptions VALUES(2,2,'More Spam');
CREATE TABLE Votes (
                       poll_id integer REFERENCES Polls (poll_id)
                       ON DELETE CASCADE ON UPDATE NO ACTION,
                       voter text NOT NULL,
                       vote integer NOT NULL,
                       CONSTRAINT single_vote UNIQUE
                       (poll_id, voter, vote) ON CONFLICT REPLACE);
INSERT INTO Votes VALUES(1,'9eu8hqt36tgg8q6w6ypu4ww1ch',0);
INSERT INTO Votes VALUES(1,'adnq8psy6tr18n3gaiwg3ada9o',1);
INSERT INTO Votes VALUES(1,'adnq8psy6tr18n3gaiwg3ada9o',2);
INSERT INTO Votes VALUES(1,'93tjw16rub858beagfirpwqdyh',2);
INSERT INTO Votes VALUES(2,'9eu8hqt36tgg8q6w6ypu4ww1ch',0);
INSERT INTO Votes VALUES(2,'93tjw16rub858beagfirpwqdyh',2);
INSERT INTO Votes VALUES(2,'93tjw16rub858beagfirpwqdyh',1);
INSERT INTO Votes VALUES(2,'adnq8psy6tr18n3gaiwg3ada9o',2);
COMMIT;
