from .gitlab import GitlabConnector
from .jira import JiraConnector
from .odoo import OdooConnector
from .toggl import TogglConnector


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
            if connector.NAME.lower() == connector_name.lower():
                return connector(**kwargs)
        raise NotImplementedError(
            'Connector with name {} is not implemented'.format(connector_name)
        )
