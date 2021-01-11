import contextlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@contextlib.contextmanager
def get_session(db_string):
    """
    Create session for with statement
    Source: https://groups.google.com/forum/#!topic/sqlalchemy/_SN2BDipBw8
    """
    engine = create_engine(db_string)
    Session = sessionmaker(bind=engine, autoflush=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()

