from flask_oauthlib.client import OAuth
from flask import current_app, url_for, session, request

oauth = OAuth(current_app)


class OAuthSignIn(object):
    """Parent OAuth class"""
    providers = None

    def __init__(self, provider_name):
        self.provider_name = provider_name
        credentials = current_app.config['OAUTH_CREDENTIALS'][provider_name]
        self.consumer_id = credentials['id']
        self.consumer_secret = credentials['secret']

    def authorize(self, callback=False):
        pass

    def callback(self):
        pass

    def get_callback_url(self):
        return url_for(
            'auth_routes.oauth_callback',
            provider=self.provider_name,
            _external=True
        )

    @classmethod
    def get_provider(self, provider_name):
        if self.providers is None:
            self.providers = {}
            for provider_class in self.__subclasses__():
                provider = provider_class()
                self.providers[provider.provider_name] = provider
        return self.providers[provider_name]


class GoogleSignIn(OAuthSignIn):
    """Google OAuth provider class"""

    def __init__(self):
        super(GoogleSignIn, self).__init__('google')
        self.app = oauth.remote_app(
            'google',
            consumer_key=self.consumer_id,
            consumer_secret=self.consumer_secret,
            request_token_params={
                'scope': 'email'
            },
            base_url='https://www.googleapis.com/oauth2/v1/',
            request_token_url=None,
            access_token_method='POST',
            access_token_url='https://accounts.google.com/o/oauth2/token',
            authorize_url='https://accounts.google.com/o/oauth2/auth',
        )

        @self.app.tokengetter
        def get_token():
            return session.get('access_token')

    def authorize(self, callback=False):
        if callback:
            return self.app.authorize(callback=callback)
        return self.app.authorize(callback=self.get_callback_url())

    def callback(self):
        resp = self.app.authorized_response()
        if resp is None:
            return 'Access denied: reason=%s error=%s' % (
                request.args['error_reason'],
                request.args['error_description']
            )
        session['access_token'] = (resp['access_token'], '')
        this_user = self.app.get('userinfo')
        if 'name' in this_user.data:
            username = this_user.data['name']
        else:
            username = this_user.data['email'].split('@')[0]
        user_data = {
            "username": username,
            "email": this_user.data["email"],
            "related_ids": {
                "google": this_user.data["id"]
            }
        }
        return user_data
