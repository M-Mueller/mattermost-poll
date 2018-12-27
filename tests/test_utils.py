# pylint: disable=missing-docstring
import contextlib
import settings


@contextlib.contextmanager
def force_settings(**kwargs):
    """Temporary changes a value in settings."""
    original = {}
    for key, value in kwargs.items():
        if not hasattr(settings, key):
            assert False, "Cannot force invalid setting: " + key
        original[key] = getattr(settings, key)
        setattr(settings, key, value)

    yield

    for key, value in original.items():
        setattr(settings, key, value)


