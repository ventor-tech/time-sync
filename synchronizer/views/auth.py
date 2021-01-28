import re

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, session, url_for)
from flask_login import current_user, login_required, login_user, logout_user
from synchronizer.models import User
from synchronizer.oauth import OAuthSignIn

auth_routes = Blueprint(
    'auth_routes',
    __name__,
    template_folder='templates'
)


@auth_routes.route('/sign-in')
def sign_in():
    """
    Render sign in page
    """
    if current_user is not None and current_user.is_authenticated:
        return (
            redirect(request.args.get("next") or url_for("app_routes.index"))
        )

    return render_template("sign-in.html", title="Sign-in to start")


@auth_routes.route('/sign-out')
@login_required
def sign_out():
    """
    Render sign out page
    """
    logout_user()
    return redirect(url_for('app_routes.index'))


@auth_routes.route('/authorize/<provider>')
def oauth_authorize(provider):
    """
    Authentication through external OAuth services
    """
    if current_user is not None and current_user.is_authenticated:
        if current_user.has_external_account(provider):
            return (
                redirect(
                    request.args.get("next")or url_for("app_routes.index")
                )
            )

    # Save redirect URL
    session['redirect_url'] = request.args.get("next")

    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()


@auth_routes.route('/callback/<provider>')
def oauth_callback(provider):
    """
    Callback action for authentication through external providers
    """
    oauth = OAuthSignIn.get_provider(provider)
    user_info = oauth.callback()

    domains = current_app.config['ALLOWED_REGISTRATION_DOMAINS']
    email = user_info['email']
    if not any(re.search(f'@{domain}$', email) for domain in domains):
        flash(f'Only employees with domains: {",".join(domains)} can get access!', 'error')
        return redirect(url_for('app_routes.index'))

    if current_user is not None and current_user.is_authenticated:
        return (
            redirect(request.args.get("next") or url_for("app_routes.index"))
        )
    else:
        user = User.query.filter_by(email=user_info["email"]).first()
        if not user:
            user = User.create(user_info["username"], user_info["email"])
        login_user(user, True)
    if 'redirect_url' in session:
        redirect_url = session['redirect_url']
        session.pop('redirect_url', None)
        return redirect(redirect_url)
    return redirect(url_for('app_routes.index'))
