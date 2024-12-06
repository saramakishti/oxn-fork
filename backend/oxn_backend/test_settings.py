from .settings import *

# Use in-memory SQLite for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
}

# Use container path
OXN_DATA_DIR = '/mnt/oxn-data'