from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import DateTimeField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.ext.sqlalchemy.orm import model_form

from synchronizer.models import db, Connector, ConnectorType, Worklog, User


class SyncForm(FlaskForm):

    @staticmethod
    def enabled_connectors():
        return Connector.query.filter_by(user_id=current_user.get_id())

    date_started_from = DateTimeField()
    source = QuerySelectField(
        query_factory=enabled_connectors.__func__,
        allow_blank=True
    )
    target = QuerySelectField(
        query_factory=enabled_connectors.__func__,
        allow_blank=True
    )


class GitlabReportingForm(FlaskForm):
    date_started = DateTimeField()
    date_ended = DateTimeField()


WorklogForm = model_form(Worklog, base_class=FlaskForm, db_session=db.session)

UserForm = model_form(User, base_class=FlaskForm, db_session=db.session)

# Replace default_target with custom select
UserForm.default_target = QuerySelectField(
    query_factory=lambda: Connector.query.join(ConnectorType).filter(
        Connector.user_id==current_user.get_id(),
        # connector_type_id=2
        ConnectorType.ctype=='target'
    ),
    allow_blank=True
)
