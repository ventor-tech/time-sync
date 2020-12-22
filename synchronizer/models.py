import re
from datetime import datetime

from flask import current_app
from flask_login import UserMixin, current_user, LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from synchronizer.connectors.base import ExportException, WrongIssueIDException
from synchronizer.connectors.manager import ConnectorManager
from synchronizer.utils import DateAndTime

lm = LoginManager()
db = SQLAlchemy()
migrate = Migrate()


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
        default=datetime.utcnow()
    )

    issue_id_pattern = r'^\[((?P<cn>.*):)?(?P<issue_id>.*)\]\s*(?P<comment>.*)'

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
    issue_id = db.Column(db.String(32), default='')
    correct_id = db.Column(db.Boolean, default=None)

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
        from collections import OrderedDict
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
            # If duration the same - exists
            if worklog['duration'] == existing_worklog.duration:
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
        default=datetime.utcnow()
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
    password = db.Column(db.String(120), default="")
    api_token = db.Column(db.String(120), default="")
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )
    date_created = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow()
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

    def get_id(self):
        """
        Returns connector ID
        """
        return self.id

    def __repr__(self):
        return self.name

    @staticmethod
    def create(**kwargs):
        """
        Returns new connector
        """
        c = Connector(**kwargs)
        db.session.add(c)
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
        default=datetime.utcnow()
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
    
    def validate_worklogs_in_jira(self):
        """
        Check existing worklog's task id in target resource
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
        imported_worklogs = Worklog.query \
            .filter(
                Worklog.synchronization_id == self.get_id(),
                Worklog.is_valid,
                Worklog.parent_id == None  # NOQA
            )

        for worklog in imported_worklogs:
            try:
                data = {
                    'started': target_connector.convert_datetime(worklog.date_started),
                    'timeSpentSeconds': target_connector.round_seconds(
                        worklog.duration
                    ),
                    'comment': worklog.comment
                }

                target_connector._get(
                    'issue/{0}/worklog'.format(worklog.issue_id),
                    data,
                    params={'notifyUsers': 'false'}
                )
            except WrongIssueIDException as err:
                current_app.logger.warning('Wrong issue id in jira.')
                worklog.correct_id = False
                db.session.add(worklog)
                db.session.commit()
                continue

            worklog.correct_id = True
            db.session.add(worklog)
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
            DateAndTime(current_user.timezone.name).now().isoformat('T')
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

        self.is_cancelled = True
        db.session.commit()
        return True

    def complete(self):
        if self.user_id != current_user.get_id():
            return False

        if self.is_cancelled:
            return False  # can't complete cancelled sync
        self.is_completed = True
        db.session.commit()
        return True
