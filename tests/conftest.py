import os.path
import pytest

import settings


@pytest.fixture(autouse=True, scope='session')
def clear_database():
    if os.path.exists(settings.DATABASE):
        os.remove(settings.DATABASE)
