# pylint: disable=missing-docstring
import pytest
import app

from test_utils import force_settings


@pytest.mark.parametrize(
    'command, exp_message, exp_options, \
    exp_progress, exp_public, exp_votes, exp_bars, exp_locale', [
        ('Some message --Option 1 --Second Option',
         'Some message', ['Option 1', 'Second Option'], True, False, 1, True, ''),

        ('Some message --Foo --Spam --progress',
         'Some message', ['Foo', 'Spam'], True, False, 1, True, ''),

        ('Some message --Foo --Spam --Noprogress',
         'Some message', ['Foo', 'Spam', 'Noprogress'], True, False, 1, True, ''),

        ('Some message --Foo --Spam --public',
         'Some message', ['Foo', 'Spam'], True, True, 1, True, ''),

        ('Some message --Foo --Spam --Public',
         'Some message', ['Foo', 'Spam', 'Public'], True, False, 1, True, ''),

        ('Some message --Foo --Spam --locale=en',
         'Some message', ['Foo', 'Spam'], True, False, 1, True, 'en'),

        ('Some message --Foo --Spam --locale=de',
         'Some message', ['Foo', 'Spam'], True, False, 1, True, 'de'),

        ('Some message --Foo --Spam --locale',
         'Some message', ['Foo', 'Spam'], True, False, 1, True, ''),

        ('Some message --Foo --Spam --locale=',
         'Some message', ['Foo', 'Spam'], True, False, 1, True, ''),

        ('# heading\nSome *markup*<br>:tada: --More ~markup~ --:tada: --Spam-!',
         '# heading\nSome *markup*<br>:tada:',
         ['More ~markup~', ':tada:', 'Spam-!'], True, False, 1, True, ''),

        ('No whitespace--Foo--Bar--Spam--noprogress--public',
         'No whitespace', ['Foo', 'Bar', 'Spam'], False, True, 1, True, ''),

        ('   Trim  whitespace   --   Foo-- Spam  Spam  -- noprogress',
         'Trim  whitespace', ['Foo', 'Spam  Spam'], False, False, 1, True, ''),

        ('Some message --Foo --Spam --noprogress --votes=3',
         'Some message', ['Foo', 'Spam'], False, False, 3, True, ''),

        ('Some message --Foo --Spam --noprogress --votes=-1',
         'Some message', ['Foo', 'Spam'], False, False, 1, True, ''),

        ('Some message --Foo --Spam --noprogress --votes=bob',
         'Some message', ['Foo', 'Spam'], False, False, 1, True, ''),

        ('Some message --Foo --Spam --noprogress --votes',
         'Some message', ['Foo', 'Spam'], False, False, 1, True, ''),

        ('Some message --votes=-1 --Foo --Spam',
         'Some message', ['Foo', 'Spam'], True, False, 1, True, ''),

        ('Some message --votes=0 --Foo --Spam',
         'Some message', ['Foo', 'Spam'], True, False, 1, True, ''),

        ('Some message --bars --Foo --Spam',
         'Some message', ['Foo', 'Spam'], True, False, 1, True, ''),

        ('Some message --nobars --Foo --Spam',
         'Some message', ['Foo', 'Spam'], True, False, 1, False, ''),

        ('Some message --Foo --bars --Spam --noprogress --public',
         'Some message', ['Foo', 'Spam'], False, True, 1, True, ''),

        ('Some message --Foo --bars --Spam --noprogress --public --locale=en',
         'Some message', ['Foo', 'Spam'], False, True, 1, True, 'en'),
    ])
def test_parse_slash_command(command, exp_message, exp_options,
                             exp_progress, exp_public, exp_votes,
                             exp_bars, exp_locale):
    args = app.parse_slash_command(command)
    assert args.message == exp_message
    assert args.vote_options == exp_options
    assert args.progress == exp_progress
    assert args.public == exp_public
    assert args.max_votes == exp_votes
    assert args.bars == exp_bars
    assert args.locale == exp_locale


def test_parse_slash_command_defaults():
    with force_settings(
        PUBLIC_BY_DEFAULT=True,
        PROGRESS_BY_DEFAULT=True,
        BARS_BY_DEFAULT=True
    ):
        args = app.parse_slash_command('msg')
        assert args.progress == True
        assert args.public == True
        assert args.bars == True

    with force_settings(
        PUBLIC_BY_DEFAULT=False,
        PROGRESS_BY_DEFAULT=False,
        BARS_BY_DEFAULT=False
    ):
        args = app.parse_slash_command('msg')
        assert args.progress == False
        assert args.public == False
        assert args.bars == False

    with force_settings(PUBLIC_BY_DEFAULT=True):
        args = app.parse_slash_command('msg --anonym')
        assert args.public == False

    with force_settings(PUBLIC_BY_DEFAULT=False):
        args = app.parse_slash_command('msg --progress')
        assert args.progress == True

    with force_settings(PROGRESS_BY_DEFAULT=True):
        args = app.parse_slash_command('msg --noprogress')
        assert args.progress == False

    with force_settings(BARS_BY_DEFAULT=False):
        args = app.parse_slash_command('msg --bars')
        assert args.bars == True

    with force_settings(BARS_BY_DEFAULT=True):
        args = app.parse_slash_command('msg --nobars')
        assert args.bars == False


def test_empty_slash_command():
    args = app.parse_slash_command('')
    assert args.message == ''
    assert args.vote_options == []
    assert args.progress
    assert not args.public
    assert args.bars
