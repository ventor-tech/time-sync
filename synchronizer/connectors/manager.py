from .jira import JiraConnector
from .toggl import TogglConnector
from .gitlab import GitlabConnector
from .odoo import OdooConnector


class ConnectorManager(object):
    # List of available connectors
    CONNECTORS = [
        JiraConnector, TogglConnector,
        GitlabConnector, OdooConnector
    ]

    def __init__(self):
        pass

    @staticmethod
    def create_connector(connector_name, **kwargs):
        for connector in ConnectorManager.CONNECTORS:
            if connector.NAME == connector_name:
                return connector(**kwargs)
        raise NotImplementedError(
            'Connecter with name {} is not implemented'.format(connector_name)
        )
