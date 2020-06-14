from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import DateTimeField, TextAreaField, SelectField, validators, HiddenField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.ext.sqlalchemy.orm import model_form

from synchronizer.models import db, Connector, ConnectorType, Worklog, User


class SyncForm(FlaskForm):

    @staticmethod
    def enabled_connectors():
        return Connector.query.filter_by(user_id=current_user.get_id())

    date_started_from = DateTimeField(format='%Y-%m-%d')

    source = QuerySelectField(
        query_factory=enabled_connectors.__func__,
        allow_blank=True
    )
    target = QuerySelectField(
        query_factory=enabled_connectors.__func__,
        allow_blank=True
    )


class WorklogForm(FlaskForm):
    id = HiddenField()
    sync_id = HiddenField()
    comment = TextAreaField(render_kw={'rows': 3})
    issue_id = SelectField(
        [validators.Required()],
        choices=[],
        validate_choice=False,
        render_kw={"placeholder": "Start typing..."})


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
