import os

c = get_config()

# Basic JupyterHub configuration
c.JupyterHub.ip = '0.0.0.0'
c.JupyterHub.port = 8000
c.JupyterHub.base_url = '/jupyter'
c.JupyterHub.admin_access = True
c.Spawner.default_url = '/lab'

# Use the Keycloak Authenticator
from oauthenticator.generic import GenericOAuthenticator

class KeycloakAuthenticator(GenericOAuthenticator):
    login_service = "Keycloak"
    client_id = os.environ.get('OAUTH_CLIENT_ID', 'jupyterhub')
    client_secret = os.environ.get('OAUTH_CLIENT_SECRET', 'jupyterhub-secret')
    oauth_callback_url = 'http://localhost/jupyter/hub/oauth_callback'
    authorize_url = 'http://keycloak:8080/realms/demo/protocol/openid-connect/auth'
    token_url = 'http://keycloak:8080/realms/demo/protocol/openid-connect/token'
    userdata_url = 'http://keycloak:8080/realms/demo/protocol/openid-connect/userinfo'
    scope = ['openid', 'profile', 'email']
    username_key = 'preferred_username'
    claim_groups_key = 'roles'
    allowed_groups = ['user', 'admin']

c.JupyterHub.authenticator_class = KeycloakAuthenticator

# Admin users
c.Authenticator.admin_users = admin = set()
pwd = os.path.dirname(__file__)
try:
    with open(os.path.join(pwd, 'userlist')) as f:
        for line in f:
            if not line:
                continue
            parts = line.split()
            name = parts[0]
            if len(parts) > 1 and parts[1] == 'admin':
                admin.add(name)
except:
    pass

# Default admin user from Keycloak
admin.add('alice')