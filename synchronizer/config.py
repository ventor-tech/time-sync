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
    SECRET_KEY = os.environ.get('SECRET_KEY', 'AhEsDfsje2KH57E')
    DEV = False
    DEBUG = False

    ALLOWED_REGISTRATION_DOMAINS = ['ventor.tech', ]

    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI', 'postgresql://postgres:postgres@localhost/time')
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
    SECRET_KEY = os.environ.get('SECRET_KEY', 'AhEsDfsje2KH57E')
    DEV = True
    DEBUG = True

    ALLOWED_REGISTRATION_DOMAINS = ['ventor.tech', ]

    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI', 'postgresql://postgres:postgres@localhost/time')

    OAUTH_CREDENTIALS = {
        'google': {
            'id': os.environ.get('GOOGLE_OAUTH_ID'),
            'secret': os.environ.get('GOOGLE_OAUTH_SECRET')
        }
    }
