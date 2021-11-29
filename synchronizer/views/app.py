"""App views"""

from flask import Blueprint, abort, redirect, render_template, request, url_for, flash
from flask_login import current_user, login_required
from synchronizer.models import ConnectorType

from synchronizer.forms import ConnectorForm, SyncForm, UserForm, WorklogForm
from synchronizer.models import Connector, Synchronization, User, Worklog, db, lm
from synchronizer.connectors.manager import ConnectorManager


app_routes = Blueprint(
    'app_routes',
    __name__,
    template_folder='templates'
)


# Load user for flask_login
@lm.user_loader
def load_user(user_id):
    """
    Return user object by ID
    """
    return User.query.get(user_id)


######
# App routes
######


@app_routes.route('/')
@login_required
def index():
    """
    Render main page
    """
    return render_template(
        "main.html",
        title="Time Synchronizer"
    )


@app_routes.route('/settings', methods=["GET", "POST"])
@login_required
def render_settings():
    """
    Renders settings page
    """
    form = UserForm(obj=current_user)

    if form.validate_on_submit():
        current_user.update(
            username=form.username.data,
            timezone_id=form.timezone.raw_data[0],
            default_target_id=(
                form.default_target.raw_data[0]
                if form.default_target.data else None
            )
        )
    return render_template("forms/settings.html", form=form, title="Settings")


@app_routes.route('/help', methods=['GET'])
@login_required
def render_help():
    return render_template(
        'help.html',
        title="Help"
    )

######
# Connectors routes
######


@app_routes.route('/connectors', methods=["GET", "POST"])
@login_required
def get_connectors():
    """
    Get list of connectors
    """
    connectors = Connector.query.filter_by(user_id=current_user.get_id()).all()
    return render_template(
        "connectors.html",
        connectors=connectors,
        title="Connectors"
    )


@app_routes.route('/connector/add', methods=["GET", "POST"])
@login_required
def add_connector():
    """
    Adds a new connector
    """
    form = ConnectorForm()
    if form.validate_on_submit():
        connector_type = ConnectorType.query.get(form.connector_type.raw_data[0])
        connector = ConnectorManager.get_connector(connector_type.name)

        if not connector.validate(
            server=form.server.data,
            login=form.login.data,
            api_token=form.api_token.data,
        ):
            flash("Connector is not valid. Check spelling or correctness of fields and try again", "error")
            return redirect(url_for("app_routes.add_connector"))

        Connector.create(
            name=form.name.data,
            server=form.server.data,
            login=form.login.data,
            password=form.password.data,
            api_token=form.api_token.data,
            connector_type_id=form.connector_type.raw_data[0],
            user_id=current_user.get_id()
        )

        return redirect(url_for("app_routes.get_connectors"))

    return render_template(
        "forms/connector.html",
        headline='Add a new connector',
        action="/connector/add",
        form=form)


@app_routes.route('/connector/delete/<connector_id>', methods=["GET"])
@login_required
def delete_connector(connector_id):
    """
    Deletes connector
    """
    Connector.delete(connector_id)
    return redirect(url_for("app_routes.get_connectors"))


@app_routes.route('/connector/edit/<int:connector_id>', methods=["GET", "POST"])
@login_required
def edit_connector(connector_id):
    """
    Edits connector
    """
    connector = Connector.query.filter_by(id=connector_id).first()

    if connector.user_id != current_user.get_id():
        abort(401)

    form = ConnectorForm(obj=connector)

    if form.validate_on_submit():
        connector.update(form=form)
        return redirect(url_for("app_routes.get_connectors"))

    return render_template(
        "forms/connector.html",
        headline='Edit a connector',
        form=form)


######
# Worklogs routes
######


@app_routes.route('/worklogs', methods=["GET"])
@login_required
def get_worklogs():
    """
    Get list of connectors
    """
    worklogs = Worklog.query.filter(
        Worklog.user_id == current_user.get_id(),
        Worklog.parent_id == None  # NOQA
    ).order_by(Worklog.date_started).all()
    return render_template(
        "worklogs.html",
        worklogs=worklogs,
        title="My Worklogs"
    )


@app_routes.route('/worklogs/delete/<worklog_id>', methods=["GET"])
@login_required
def delete_worklog(worklog_id):
    """
    Deletes worklog
    """
    Worklog.delete(worklog_id)
    return redirect(request.args.get("next") or url_for("app_routes.index"))


@app_routes.route('/worklogs/edit/<worklog_id>', methods=["GET", "POST"])
@login_required
def edit_worklog(worklog_id):
    """
    Edit worklog
    """
    # TODO: Do not allow to edit child worklogs!
    w = Worklog.query.get(worklog_id)

    form = WorklogForm(obj=w)

    form.sync_id.data = w.synchronization.id
    form.issue_id.choices = [(w.issue_id, w.issue_id)]

    if form.validate_on_submit():
        # Save a new synchronization
        w.comment = form.comment.data
        w.issue_id = form.issue_id.data

        # Mark as valid when both comment and issue_id presented
        w.is_valid = bool(form.comment.data and form.issue_id.data)

        db.session.add(w)
        db.session.commit()

        return redirect(
            request.args.get("next") or url_for("app_routes.index")
        )
    return render_template(
        "worklog.html",
        form=form,
        worklog_id=worklog_id,
        title="Edit worklog"
    )


######
# Synchronizations
######


@app_routes.route('/synchronizations', methods=["GET"])
@login_required
def get_synchronizations():
    """
    Get list of connectors
    """
    synchronizations = Synchronization.query.filter_by(
        user_id=current_user.get_id()
    ).order_by(Synchronization.date_created).all()
    return render_template(
        "synchronizations.html",
        synchronizations=synchronizations,
        title="My Synchronizations"
    )


@app_routes.route('/synchronizations/delete/<synchronization_id>', methods=["GET"])
@login_required
def delete_synchronization(synchronization_id):
    """
    Deletes synchronization
    """
    Synchronization.delete(synchronization_id)
    return redirect(request.args.get("next") or url_for("app_routes.index"))


######
# Synchronization views
######


@app_routes.route('/sync', methods=["GET", "POST"])
@login_required
def run_sync():
    """
    Render start synchronization page
    """
    if not current_user.timezone or not current_user.issue_id_pattern:
        return render_template(
            "start.html",
            title='Synchronize worklogs',
            errors='Please specify timezone and issue id pattern in \
                <a class="alert-link" href="/settings">settings</a> \
                before synchronize worklogs'
        )

    form = SyncForm()

    if form.validate_on_submit():
        if not form.source.data or not form.target.data:
            errors = 'Please select source and/or target connectors!'
            return render_template(
                "sync.html",
                form=form,
                title="Synchronize worklogs",
                errors=errors
            )

        # Save a new synchronization
        new_sync = Synchronization.create(
            source_id=form.source.raw_data[0],
            target_id=form.target.raw_data[0],
            date_started_from=form.date_started_from.data,
            user_id=current_user.get_id()
        )

        try:
            new_sync.import_worklogs()
            new_sync.validate_worklogs()
        except Exception as err:
            # If something went wrong remove sync and render error page
            Synchronization.delete(new_sync.id)

            errors = (
                f'Something went wrong: {err}'
            )

            return render_template(
                "sync.html",
                form=form,
                title="Synchronize worklogs",
                errors=errors
            )

        return redirect(
            url_for(
                "app_routes.validate_worklogs",
                sync_id=new_sync.get_id()
            )
        )

    # Show warning about not finished synchronizations
    errors = None
    unfinished_syncs = [
        s for s in current_user.synchronizations
        if not s.is_completed and not s.is_cancelled
    ]

    if unfinished_syncs:
        errors = (
            'There are unfinished synchronizations that could include '
            'worklogs to sychronize! Please check it on '
            '<a href="/synchronizations">Synchronization</a> tab'
        )

    return render_template(
        "sync.html",
        form=form,
        title="Synchronize worklogs",
        errors=errors
    )


@app_routes.route('/validate/<sync_id>', methods=['GET'])
@login_required
def validate_worklogs(sync_id):
    """
    Render worklogs validation page
    """
    sync = Synchronization.query.get(sync_id)
    if sync:
        if not sync.is_active():
            return redirect(
                url_for('app_routes.view_synchronization', sync_id=sync_id)
            )
        worklogs = Worklog.query.filter_by(
            synchronization_id=sync_id,
            user_id=current_user.get_id(),
            parent_id=None
        ).order_by(Worklog.date_started).all()

        return render_template(
            "validation.html",
            worklogs=worklogs,
            title="Validate worklogs",
            sync_id=sync_id,
            total_synchronized=sum(
                [x.duration for x in worklogs if x.is_valid]
            ),
            total_skipped=sum([x.duration for x in worklogs if not x.is_valid]),
            connector_name=sync.target.connector_type.name,
        )
    return render_template(
        "error.html",
        title="Validate worklogs",
        errors="Sorry, but this synchronization is not available."
    )


@app_routes.route('/export/<sync_id>', methods=['GET'])
@login_required
def submit_synchronization(sync_id):
    """
    Render export worklogs page
    """
    sync = Synchronization.query.get(sync_id)
    if sync:
        if not sync.is_active():
            return redirect(
                url_for('app_routes.view_synchronization', sync_id=sync_id)
            )
        try:
            sync.export_worklogs()
        except Exception as err:
            print(err)
            return render_template(
                "error.html",
                title="Something goes wrong",
                errors=err.message or "Sorry, but something goes wrong \
                when we try to export your worklogs. \
                We saved only successfully synchronized worklogs. \
                Try again or contact administrator."
            )
        # Fetch all synchronized worklogs
        worklogs = Worklog.query.filter_by(
            synchronization_id=sync_id,
            user_id=current_user.get_id(),
            parent_id=None
        ).order_by(Worklog.date_started).all()
        return render_template(
            "export.html",
            worklogs=worklogs,
            title="Export worklogs",
            sync_id=sync_id,
            total_synchronized=sum(
                [x.duration for x in worklogs if x.is_valid]
            ),
            total_skipped=sum([x.duration for x in worklogs if not x.is_valid])
        )
    return render_template(
        "error.html",
        title="Export worklogs",
        errors="Sorry, but this synchronization is not available."
    )


@app_routes.route('/sync/<sync_id>', methods=['GET'])
@login_required
def view_synchronization(sync_id):
    """
    Render synchronization page
    """
    sync = Synchronization.query.get(sync_id)
    if sync:
        if sync.is_active():
            return render_template(
                "message.html",
                title="Already completed",
                message="This synchronization is still in progress"
            )
        # Fetch all synchronized worklogs
        worklogs = Worklog.query.filter_by(
            synchronization_id=sync_id,
            user_id=current_user.get_id(),
            parent_id=None
        ).order_by(Worklog.date_started).all()
        return render_template(
            "export.html",
            worklogs=worklogs,
            title="Export worklogs",
            sync_id=sync_id,
            total_synchronized=sum(
                [x.duration for x in worklogs if x.is_valid]
            ),
            total_skipped=sum([x.duration for x in worklogs if not x.is_valid])
        )
    return render_template(
        "error.html",
        title="Export worklogs",
        errors="Sorry, but this synchronization is not available."
    )


@app_routes.route('/cancel/<sync_id>', methods=['GET'])
@login_required
def cancel_synchronization(sync_id):
    """
    Render cancel synchronization page
    """
    sync = Synchronization.query.get(sync_id)
    if sync:
        sync.cancel()
        Synchronization.delete(sync_id)
        return render_template(
            "message.html",
            title="Cancel synchronization",
            message="Successfully cancelled synchronization!"
        )
    return render_template(
        "error.html",
        title="Cancel synchronization",
        message="Sorry, but this synchronization is not available."
    )