from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import (DateTimeField, HiddenField, PasswordField, SelectField,
                     StringField, TextAreaField, validators)
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.ext.sqlalchemy.orm import model_form

from synchronizer.models import Connector, ConnectorType, User, db

def enabled_connectors():
    return Connector.query.filter_by(user_id=current_user.get_id())

class ConnectorForm(FlaskForm):

    name = StringField()
    server = StringField()
    login = StringField()
    password = PasswordField()
    api_token = StringField()
    connector_type = QuerySelectField(
        query_factory=enabled_connectors,
        allow_blank=True
    )


class SyncForm(FlaskForm):

    date_started_from = DateTimeField(format='%Y-%m-%d')

    source = QuerySelectField(
        query_factory=enabled_connectors,
        allow_blank=True
    )
    target = QuerySelectField(
        query_factory=enabled_connectors,
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
