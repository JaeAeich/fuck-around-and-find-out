FROM jupyterhub/jupyterhub:latest

RUN pip install \
    oauthenticator \
    jupyterlab

COPY ./jupyterhub_config.py /srv/jupyterhub/