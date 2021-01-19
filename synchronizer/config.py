import os

from dotenv import load_dotenv


# Load secure configuration parameters
load_dotenv()


class Configuration(object):
    """
    Class with different config variables
    """
    DEV = False
    DEBUG = False

    SQLALCHEMY_TRACK_MODIFICATIONS = True


class ProdConfiguration(object):
    """
    Class with different config variables
    """
    SECRET_KEY = 'AhEsDfsje2KH57E'
    DEV = False
    DEBUG = False

    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost/time'  # NOQA
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    OAUTH_CREDENTIALS = {
        'google': {
            'id': os.environ.get('GOOGLE_OAUTH_ID'),
            'secret': os.environ.get('GOOGLE_OAUTH_SECRET')
        }
    }


class DevConfiguration(Configuration):
    """
    Class with different config variables
    """
    SECRET_KEY = 'hello_world'
    DEV = True
    DEBUG = True

    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost/time_sync_master'

    OAUTH_CREDENTIALS = {
        'google': {
            'id': (
                '213737460043-j645q79uk648f4kekcdf7j026c3veqan'
                '.apps.googleusercontent.com'
            ),
            'secret': 'AcIwMNvJfCe-g0LvoCPm5YJs'
        }
    }
