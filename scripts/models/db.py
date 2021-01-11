from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ConnectorType(Base):
    __tablename__ = 'connector_types'
    id = Column(Integer, primary_key=True)
    name = Column(String(64))
    ctype = Column(String(64))
    date_created = Column(
        DateTime(timezone=True),
        default=datetime.utcnow()
    )


class Connector(Base):
    __tablename__ = 'connectors'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)
    server = Column(String(128), default="")
    login = Column(String(64), default="")
    password = Column(String(120), default="")
    api_token = Column(String(120), default="")
    user_id = Column(
        Integer,
        ForeignKey('users.id'),
        nullable=False
    )
    date_created = Column(
        DateTime(timezone=True),
        default=datetime.utcnow()
    )

    connector_type_id = Column(
        Integer,
        ForeignKey('connector_types.id'),
        nullable=False
    )


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(64))
    email = Column(String(120))
    date_last_sync = Column(
        DateTime(timezone=True)
    )
    date_created = Column(
        DateTime(timezone=True),
        default=datetime.utcnow()
    )

    timezone_id = Column(
        Integer,
        ForeignKey('timezones.id'),
        default=588
    )

    # Default Target connector
    default_target_id = Column(
        Integer,
        ForeignKey('connectors.id')
    )


class Timezone(Base):
    __tablename__ = 'timezones'
    id = Column(Integer, primary_key=True)
    name = Column(String(64))



