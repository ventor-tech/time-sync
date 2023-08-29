import os
import sentry_sdk

from flask import Flask
from sentry_sdk.integrations.flask import FlaskIntegration


def create_app(dev=False):
    """
    Creates and initializes a new app object. Defines helpers for Jinja2
    templates system
    """
    app = Flask(__name__)

    app.config.from_object(
        os.environ.get('CONFIG') or 'synchronizer.config.ProdConfiguration'
    )

    if app.config.get('SENTRY_DSN'):
        # Initialize Sentry
        sentry_sdk.init(
            dsn=(app.config['SENTRY_DSN']),
            integrations=[FlaskIntegration()]
        )

    from synchronizer.models import lm, db, migrate

    db.init_app(app)
    migrate.init_app(app, db, compare_type=True)

    @app.context_processor
    def helpers():
        def local_time(utc_datetime):
            from flask_login import current_user
            import pytz

            return utc_datetime.astimezone(
                pytz.timezone(current_user.timezone.name)
            ).strftime("%Y-%m-%d %H:%M:%S")

        def seconds_to_time(seconds):
            from datetime import timedelta
            # Hack to support subtract time
            if seconds >= 0:
                return str(timedelta(seconds=seconds))
            else:
                return '-' + str(timedelta(seconds=-seconds))

        def seconds_to_hours(seconds):
            return round(seconds / (60 * 60), 3)  # (minutes * hours)

        return dict(
            local_time=local_time,
            seconds_to_time=seconds_to_time,
            seconds_to_hours=seconds_to_hours
        )

    lm.init_app(app)
    lm.login_view = 'auth_routes.sign_in'

    from synchronizer.views.app import app_routes
    from synchronizer.views.auth import auth_routes
    from synchronizer.views.api import api_routes

    app.register_blueprint(app_routes)
    app.register_blueprint(auth_routes)
    app.register_blueprint(api_routes, url_prefix='/api')

    return app
