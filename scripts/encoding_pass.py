from cryptography.fernet import Fernet
import os
from models.db import Connector
from utils import get_session
from dotenv import load_dotenv

load_dotenv()


if __name__ == "__main__":

    def encrypt(key, password):
        """
        Encryptes password from db with helper key
        params should be converted to bytes

        :param string key: Helper key for encode and decode
        :param string password: password from db to be decoded
        :return: string
        """
        return Fernet(key.encode()).encrypt(password.encode()).decode()
    
    with get_session(os.environ.get('SQLALCHEMY_DATABASE_URI')) as session:
        connectors = session.query(Connector).all()
        for connector in connectors:
            connector.password = encrypt(os.environ.get('ENCRYPTED_KEY'), connector.password)
            session.commit()