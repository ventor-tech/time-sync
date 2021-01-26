"""API views"""

from flask import jsonify, Blueprint, request
from flask_login import login_required

from synchronizer.connectors.manager import ConnectorManager
from synchronizer.models import Synchronization, ConnectorType


api_routes = Blueprint(
    'api_routes',
    __name__,
    template_folder='templates'
)


@api_routes.route('/')
@login_required
def index():
    """
    Render main page
    """
    return jsonify({'hello': 'world'})


@api_routes.route('/issues')
@login_required
def issues():
    """
    Returns all issues from all current source for keyword
    """
    results = []

    try:
        sync_id = request.args.get('sync_id')
        term = request.args.get('term')

        if not term:
            return jsonify({'results': []})

        s = Synchronization.query.get(sync_id)

        target_connector = ConnectorManager.create_connector(
            s.target.connector_type.name,
            server=s.target.server,
            api_token=s.target.api_token,
            login=s.target.login,
            password=s.target.password
        )

        raw_results = target_connector.search_issues(term)
        results = [
            {'id': r['id'], 'text': '[{}] {}'.format(r['id'], r['name'])}
            for r in raw_results
        ]
    except:
        pass

    if not results:
        results = [{'id': term, 'text': 'Use "{}" as issue ID'.format(term)}]

    return jsonify({'results': results})


@api_routes.route('/connector/<int:connector_type_id>')
@login_required
def get_connector_type_fields(connector_type_id):
    connector_type = ConnectorType.query.get(connector_type_id)

    if connector_type:
        connector = ConnectorManager.get_connector(connector_type.name)
        return jsonify({'fields': connector.FORM_FIELDS})

    raise Exception(
        'Connector type with id {} does not exist.'.format(connector_type_id))
