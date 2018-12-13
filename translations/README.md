Localization
============

The localization is based on [Babel](http://babel.pocoo.org/en/latest/index.html). All translatable strings must be wrapped with the `tr` function. 

To update the translations:

```sh
pybabel extract -k tr -F babel.cfg -o messages.pot .
pybabel update -i messages.pot -d translations
# Edit translations/<locale>/message.po
pybabel compile -d translations
```

Translation currently exist for the following locales:

- en - English (default)
- de - German

To add a new locale (e.g. fr - French):

```sh
pybabel init -i messages.pot -d translations -l fr
# Edit translations/fr/message.po
pybabel compile -d translations
```
