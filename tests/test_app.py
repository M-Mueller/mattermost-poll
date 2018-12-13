# pylint: disable=missing-docstring
import pytest
import app


@pytest.mark.parametrize(
    'command, exp_message, exp_options, \
    exp_secret, exp_public, exp_votes, exp_bars, exp_locale', [
        ('Some message --Option 1 --Second Option',
         'Some message', ['Option 1', 'Second Option'], False, False, 1, False, ''),

        ('Some message --Foo --Spam --secret',
         'Some message', ['Foo', 'Spam'], True, False, 1, False, ''),

        ('Some message --Foo --Spam --Secret',
         'Some message', ['Foo', 'Spam', 'Secret'], False, False, 1, False, ''),

        ('Some message --Foo --Spam --public',
         'Some message', ['Foo', 'Spam'], False, True, 1, False, ''),

        ('Some message --Foo --Spam --Public',
         'Some message', ['Foo', 'Spam', 'Public'], False, False, 1, False, ''),

        ('Some message --Foo --Spam --locale=en',
         'Some message', ['Foo', 'Spam'], False, False, 1, False, 'en'),

        ('Some message --Foo --Spam --locale=de',
         'Some message', ['Foo', 'Spam'], False, False, 1, False, 'de'),

        ('Some message --Foo --Spam --locale',
         'Some message', ['Foo', 'Spam'], False, False, 1, False, ''),

        ('Some message --Foo --Spam --locale=',
         'Some message', ['Foo', 'Spam'], False, False, 1, False, ''),

        ('# heading\nSome *markup*<br>:tada: --More ~markup~ --:tada: --Spam-!',
         '# heading\nSome *markup*<br>:tada:',
         ['More ~markup~', ':tada:', 'Spam-!'], False, False, 1, False, ''),

        ('No whitespace--Foo--Bar--Spam--secret--public',
         'No whitespace', ['Foo', 'Bar', 'Spam'], True, True, 1, False, ''),

        ('   Trim  whitespace   --   Foo-- Spam  Spam  -- secret',
         'Trim  whitespace', ['Foo', 'Spam  Spam'], True, False, 1, False, ''),

        ('Some message --Foo --Spam --secret --votes=3',
         'Some message', ['Foo', 'Spam'], True, False, 3, False, ''),

        ('Some message --votes=-1 --Foo --Spam',
         'Some message', ['Foo', 'Spam'], False, False, 1, False, ''),

        ('Some message --votes=0 --Foo --Spam',
         'Some message', ['Foo', 'Spam'], False, False, 1, False, ''),

        ('Some message --bars --Foo --Spam',
         'Some message', ['Foo', 'Spam'], False, False, 1, True, ''),

        ('Some message --Foo --bars --Spam --secret --public',
         'Some message', ['Foo', 'Spam'], True, True, 1, True, ''),

        ('Some message --Foo --bars --Spam --secret --public --locale=en',
         'Some message', ['Foo', 'Spam'], True, True, 1, True, 'en'),
    ])
def test_parse_slash_command(command, exp_message, exp_options,
                             exp_secret, exp_public, exp_votes,
                             exp_bars, exp_locale):
    args = app.parse_slash_command('')
    assert args.message == ''
    assert args.vote_options == []
    assert not args.secret

    args = app.parse_slash_command(command)
    assert args.message == exp_message
    assert args.vote_options == exp_options
    assert args.secret == exp_secret
    assert args.public == exp_public
    assert args.max_votes == exp_votes
    assert args.bars == exp_bars
    assert args.locale == exp_locale
