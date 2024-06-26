import os
import re

from collections import OrderedDict
from datetime import datetime, timedelta

from flask import current_app
from flask_login import LoginManager, UserMixin, current_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from synchronizer.connectors.base import ExportException
from synchronizer.connectors.manager import ConnectorManager
from synchronizer.utils import AESCipher, DateAndTime

lm = LoginManager()
db = SQLAlchemy()
migrate = Migrate()
aes = AESCipher(os.environ.get('SECRET_KEY'))


def current_user_id_or_none():
    """Returns current user ID"""
    try:
        return current_user.get_id()
    except Exception as err:
        print(err)
        return None


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64))
    email = db.Column(db.String(120))
    date_last_sync = db.Column(
        db.DateTime(timezone=True)
    )
    date_created = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow
    )

    issue_id_pattern = r'^\[((?P<cn>.*?):)?(?P<issue_id>.*?)\]\s*(?P<comment>.*)'

    timezone_id = db.Column(
        db.Integer,
        db.ForeignKey('timezones.id'),
        default=588
    )

    # Default Target connector
    default_target_id = db.Column(
        db.Integer,
        db.ForeignKey('connectors.id')
    )

    default_target = db.relationship(
        'Connector',
        foreign_keys=[default_target_id]
    )

    timezone = db.relationship(
        'Timezone',
        backref='timezones',
        foreign_keys=[timezone_id]
    )

    def __repr__(self):
        return '<User %r>' % (self.username)

    def get_id(self):
        """
        Returns user ID
        """
        return self.id

    @classmethod
    def create(cls, username, email):
        """
        Returns new user
        """
        u = User(username=username, email=email, timezone_id=1)
        db.session.add(u)
        db.session.commit()
        return u

    def update(self, **kwargs):
        """
        Updates user
        """
        for k, v in kwargs.items():
            setattr(self, k, v)
        db.session.commit()
        return True

    def get_days_from_sync(self):
        """
        Returns number of days after last sync
        """
        if current_user.date_last_sync:
            return (
                DateAndTime(current_user.timezone.name).now()
                - current_user.date_last_sync
            ).days
        return None


class Timezone(db.Model):
    __tablename__ = 'timezones'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))

    def __repr__(self):
        return self.name

    @classmethod
    def create(cls, timezone):
        """
        Returns new user
        """
        t = Timezone(name=timezone)
        db.session.add(t)
        db.session.commit()
        return t


class Worklog(db.Model):
    __tablename__ = 'worklogs'
    id = db.Column(db.Integer, primary_key=True)
    synchronization_id = db.Column(
        db.Integer,
        db.ForeignKey('synchronizations.id'),
        nullable=False
    )
    date_started = db.Column(db.DateTime(timezone=True))
    date_stopped = db.Column(db.DateTime(timezone=True))
    date_created = db.Column(db.DateTime(timezone=True))
    date_synchronized = db.Column(
        db.DateTime(timezone=True),
        default=datetime.now()
    )
    duration = db.Column(db.Integer)
    comment = db.Column(db.String(2000))
    source_id = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    issue_id = db.Column(db.String(128), default='')

    parent_id = db.Column(
        db.Integer,
        db.ForeignKey('worklogs.id'),
        nullable=True
    )

    is_valid = db.Column(db.Boolean, default=True)
    user = db.relationship('User', backref='users')
    parent = db.relationship(
        'Worklog',
        backref='children',
        remote_side=[id]
    )

    def __repr__(self):
        return '<Worklog %r>' % (self.comment)

    def update(self, **kwargs):
        """
        Updates worklog
        """
        for k, v in kwargs.items():
            setattr(self, k, v)
        db.session.commit()
        return True

    def get_id(self):
        """
        Returns worklog ID
        """
        return self.id

    @classmethod
    def delete(cls, worklog_id):
        """
        Deletes worklog
        """
        w = cls.query.get(worklog_id)
        if w and w.user_id == current_user.get_id():
            db.session.delete(w)
            db.session.commit()
        return True

    @classmethod
    def delete_from_sync(cls, sync_id):
        """
        Deletes all worklogs from synchronization
        """
        worklogs = cls.query.filter_by(synchronization_id=sync_id)
        for w in worklogs:
            db.session.delete(w)
        db.session.commit()

    @classmethod
    def create_all(cls, sync_id, raw_worklogs, connector_name):
        """
        Writes a new worklogs into database
        """
        # Sort worklogs by date_started
        raw_worklogs.sort(key=lambda rw: rw['date_started'])

        # Split list of worklogs to groups by date and comment
        grouped_worklogs = OrderedDict()

        # Preprocess and group worklogs
        for w in raw_worklogs:
            # Try to extract issue ID from comment.
            # Strip to avoid issues with trailing spaces
            issue_id, comment = cls.parse_issue_id(
                w['comment'].strip(),
                connector_name
            )

            w['issue_id'] = issue_id
            w['comment'] = comment
            # If no issue ID - mark worklog as invalid
            w['is_valid'] = True if issue_id else False

            w_hash = '{date_started}-{issue_id}-{comment}'.format(
                date_started=str(w['date_started'].date()),
                issue_id=w['issue_id'],
                comment=w['comment']
            )

            if w_hash in grouped_worklogs:
                grouped_worklogs[w_hash].append(w)
            else:
                grouped_worklogs[w_hash] = [w]

        for w_hash, worklogs in grouped_worklogs.items():
            # No parent by default
            parent_id = None

            # Leave only new worklogs
            new_worklogs = [w for w in worklogs if not cls.is_exists(w)]

            if len(new_worklogs) > 1:
                # Create common parent
                parent_worklog_data = {
                    # We sorted worklogs by date_started so use first worklog
                    # date_started and last worklog date_stopped
                    'date_started': new_worklogs[0]['date_started'],
                    'date_stopped': new_worklogs[-1]['date_stopped'],
                    'issue_id': new_worklogs[0]['issue_id'],
                    'comment': new_worklogs[0]['comment'],
                    'is_valid': new_worklogs[0]['is_valid'],
                    # TODO: What value should be used?
                    'date_created': None,
                    # Parent worklog doesn't have source_id!
                    'source_id': None,
                    'duration': sum([w['duration'] for w in new_worklogs]),
                    'user_id': current_user.get_id(),
                    'synchronization_id': sync_id
                }

                pw = Worklog(**parent_worklog_data)
                db.session.add(pw)
                db.session.commit()

                parent_id = pw.id

            for worklog in new_worklogs:
                # Make a filtered copy of worklog dict to avoid errors with
                # extra attributes
                worklog_data = {
                    'date_started': worklog['date_started'],
                    'date_stopped': worklog['date_stopped'],
                    'date_created': worklog['date_created'],
                    'issue_id': worklog['issue_id'],
                    'comment': worklog['comment'],
                    'is_valid': worklog['is_valid'],
                    'source_id': worklog['source_id'],
                    'duration': worklog['duration'],
                    'user_id': current_user.get_id(),
                    'synchronization_id': sync_id,
                    'parent_id': parent_id
                }
                w = Worklog(**worklog_data)
                db.session.add(w)
                db.session.commit()

        return True

    @staticmethod
    def group(worklogs):
        """
        Groups worklogs
        """
        pass

    @classmethod
    def is_exists(cls, worklog):
        """
        Checks if worklog already exists in DB
        """
        # Search by source ID and check if valid
        existing_worklog = cls.query.filter_by(
            source_id=worklog['source_id'],
            user_id=current_user.get_id(),
            is_valid=True
        ).first()

        if existing_worklog:
            # Uncomment code below to additionally check by duration
            # If duration the same - exists
            # if worklog['duration'] == existing_worklog.duration:
            #     return True
            return True
        return False

    @staticmethod
    def parse_issue_id(comment, connector_name):
        descr_regex = re.compile(current_user.issue_id_pattern)
        res = descr_regex.search(comment)

        if res and res.group('issue_id'):
            # We can parse issue in two cases:
            # a) Connector name specified
            # b) User has default target specified
            if (
                res.group('cn') and
                res.group('cn').lower() == connector_name.lower()
            ) or (
                not res.group('cn') and
                current_user.default_target and
                current_user.default_target.connector_type.name.lower() ==
                    connector_name.lower()
            ):
                return (
                    res.group('issue_id').strip(),
                    res.group('comment').strip()
                )
        return None, comment.strip()


class ConnectorType(db.Model):
    __tablename__ = 'connector_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    ctype = db.Column(db.String(64))
    date_created = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow
    )

    def __repr__(self):
        return '{} [{}]'.format(self.name, self.ctype)

    def get_id(self):
        """
        Returns connector type ID
        """
        return self.id

    @classmethod
    def create(cls, name, ctype):
        """
        Returns new user
        """
        ct = cls(name=name, ctype=ctype)
        db.session.add(ct)
        db.session.commit()


class Connector(db.Model):
    __tablename__ = 'connectors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    server = db.Column(db.String(128), default="")
    login = db.Column(db.String(64), default="")
    _password = db.Column('password', db.String(64), default="")
    _api_token = db.Column('api_token', db.String(512), default="")
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )
    date_created = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow
    )

    connector_type_id = db.Column(
        db.Integer,
        db.ForeignKey('connector_types.id'),
        nullable=False
    )
    connector_type = db.relationship(
        'ConnectorType',
        backref='connector_types'
    )

    @property
    def is_valid(self):
        connector = ConnectorManager.get_connector(self.connector_type.name)
        return connector.validate(
            server=self.server,
            login=self.login,
            api_token=self.api_token,
        )

    @property
    def password(self):
        return aes.decrypt(self._password)

    @password.setter
    def password(self, value):
        self._password = aes.encrypt(value)

    @property
    def api_token(self):
        return aes.decrypt(self._api_token)

    @api_token.setter
    def api_token(self, value):
        self._api_token = aes.encrypt(value)

    def get_id(self):
        """
        Returns connector ID
        """
        return self.id

    def __repr__(self):
        return self.name

    @classmethod
    def create(cls, with_commit=True, **kwargs):
        """
        Returns new connector
        """
        c = cls(**kwargs)

        db.session.add(c)

        if with_commit:
            db.session.commit()

        return c

    @classmethod
    def delete(cls, connector_id):
        """
        Deletes connector
        """
        c = cls.query.get(connector_id)
        if c and c.user_id == current_user.get_id():
            db.session.delete(c)
            db.session.commit()
        return True

    def update(self, form=None, **kwargs):
        """
        Updates connector
        """
        if form:
            form.populate_obj(self)
        else:
            for k, v in kwargs.items():
                setattr(self, k, v)

        db.session.commit()
        return True


class Synchronization(db.Model):
    __tablename__ = 'synchronizations'

    id = db.Column(db.Integer, primary_key=True)

    source_id = db.Column(
        db.Integer,
        db.ForeignKey('connectors.id'),
        nullable=False
    )
    target_id = db.Column(
        db.Integer,
        db.ForeignKey('connectors.id'),
        nullable=False
    )
    date_started_from = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )
    date_created = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow
    )
    is_completed = db.Column(db.Boolean, default=False)
    is_cancelled = db.Column(db.Boolean, default=False)

    source = db.relationship(
        'Connector',
        backref=db.backref('source_syncs', cascade="all,delete"),
        foreign_keys=[source_id]
    )

    target = db.relationship(
        'Connector',
        backref=db.backref('target_syncs', cascade="all,delete"),
        foreign_keys=[target_id]
    )

    worklogs = db.relationship(
        'Worklog',
        backref='synchronization',
        cascade="all,delete"
    )

    user = db.relationship('User', backref='synchronizations')

    def get_id(self):
        """
        Returns synchronization ID
        """
        return self.id

    @staticmethod
    def create(**kwargs):
        """
        Returns new synchronization object
        """
        s = Synchronization(**kwargs)
        db.session.add(s)
        db.session.commit()
        return s

    @classmethod
    def delete(cls, sync_id):
        """
        Deletes synchronization
        """
        s = cls.query.get(sync_id)
        if s and s.user_id == current_user.get_id():
            db.session.delete(s)
            db.session.commit()
        return True

    def validate_worklogs(self):
        worklogs = self.worklogs
        target_name = self.target.connector_type.name

        target_connector = ConnectorManager.create_connector(
            target_name,
            server=self.target.server,
            api_token=self.target.api_token,
            login=self.target.login,
            password=self.target.password
        )
        
        for w in worklogs:
            if w.is_valid:
                if not target_connector.validate_issue(w.issue_id):
                    w.is_valid = False
                    current_app.logger.warning(f'Wrong issue id {w.issue_id} in {target_name}.')

        db.session.commit()

    def import_worklogs(self):
        """
        Imports worklogs from source
        """
        source_name = self.source.connector_type.name
        target_name = self.target.connector_type.name

        source_connector = ConnectorManager.create_connector(
            source_name,
            server=self.source.server,
            api_token=self.source.api_token,
            login=self.source.login,
            password=self.source.password
        )

        imported_worklogs = source_connector.import_worklogs(
            DateAndTime(
                current_user.timezone.name
            ).localize(
                self.date_started_from
            ).isoformat('T'),
            (
                # Added 1 day due to limitation of new Toggl API
                DateAndTime(current_user.timezone.name).now() + timedelta(days=1)
            ).isoformat('T')
        )

        Worklog.create_all(
            self.get_id(),
            imported_worklogs,
            target_name  # type of connector to parse task/issue ID
        )

    def export_worklogs(self):
        """
        Exports worklogs to target resource
        """
        target_name = self.target.connector_type.name
        target_connector = ConnectorManager.create_connector(
            target_name,
            server=self.target.server,
            api_token=self.target.api_token,
            login=self.target.login,
            password=self.target.password
        )

        # Get all valid worklogs from this synchronization
        worklogs_to_upload = Worklog.query \
            .filter(
                Worklog.synchronization_id == self.get_id(),
                Worklog.is_valid,
                Worklog.parent_id == None  # NOQA
            )

        try:
            target_connector.export_worklogs(worklogs_to_upload)
        except ExportException as err:
            # just delete worklogs
            # TODO: implement better solution
            worklogs_to_delete = worklogs_to_upload[err.index:]
            for w in worklogs_to_delete:
                Worklog.delete(w.get_id())
            db.session.commit()
            raise err

        current_user.update(date_last_sync=datetime.utcnow())
        self.complete()

    def is_active(self):
        """
        Returns True only if sync is in active state
        """
        return not (self.is_completed or self.is_cancelled)

    def cancel(self):
        if self.user_id != current_user.get_id():
            return False

        if self.is_completed:
            return False  # can't cancel completed sync

        # Remove worklogs for current sync
        Worklog.delete_from_sync(self.get_id())

        # self.is_cancelled = True
        # db.session.commit()
        return True

    def complete(self):
        if self.user_id != current_user.get_id():
            return False

        if self.is_cancelled:
            return False  # can't complete cancelled sync
        self.is_completed = True
        db.session.commit()
        return True
