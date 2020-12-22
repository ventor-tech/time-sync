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

    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')  # NOQA
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

    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')

    OAUTH_CREDENTIALS = {
        'google': {
            'id': (
                '1065737064092-huolpcfqs78p0tavq48sme8eagst65q6'
                # '213737460043-j645q79uk648f4kekcdf7j026c3veqan'
                '.apps.googleusercontent.com'
            ),
            'secret': '2C5Z-57U6OK5it_TMc2MqOeZ'
            # 'secret': 'AcIwMNvJfCe-g0LvoCPm5YJs'
        }
    }
