import os
import sys

from dotenv import load_dotenv

parent_path = os.path.dirname(os.path.abspath('synchronizer/'))

sys.path.append(parent_path)

from synchronizer.utils import AESCipher

from models.db import Connector
from utils import get_session

load_dotenv()

if __name__ == "__main__":
    with get_session(os.environ.get('SQLALCHEMY_DATABASE_URI')) as session:
        connectors = session.query(Connector).all()
        aes = AESCipher(os.environ.get('SECRET_KEY'))

        for connector in connectors:
            connector.password = aes.encrypt(connector.password)
            connector.api_token = aes.encrypt(connector.api_token)
            session.commit()
