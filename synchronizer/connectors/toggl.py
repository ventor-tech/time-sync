import requests

from .base import BaseConnector


class TogglConnector(BaseConnector):
    NAME = 'Toggl'
    FORM_FIELDS = ['name', 'api_token', ]

    def __init__(self, **kwargs):
        super(TogglConnector, self).__init__()
        self.auth = requests.auth.HTTPBasicAuth(
            kwargs['api_token'],
            'api_token'
        )

    def _api(self, method, endpoint, data=None, params=None):
        response = requests.request(
            method,
            'https://api.track.toggl.com/api/v8/{0}'.format(endpoint),
            json=data,
            auth=self.auth,
            params=params
        )
        response.raise_for_status()
        return response.json()

    def _get(self, *args, **kwargs):
        return self._api('get', *args, **kwargs)

    def _post(self, *args, **kwargs):
        return self._api('post', *args, **kwargs)

    def import_worklogs(self, start_date, end_date):
        params = {
            'start_date': start_date,
            'end_date': end_date
        }
        resp = self._get('time_entries', params=params)
        # filter duration less than zero for currently running time entries
        worklogs = [self.form_worklog(x) for x in resp if x['duration'] > 0]
        return worklogs

    @staticmethod
    def form_worklog(time_entry):
        return {
            "source_id": str(time_entry['id']),
            "duration": time_entry['duration'],
            "date_created": TogglConnector.parse_iso_str(time_entry['at']),
            "date_started": TogglConnector.parse_iso_str(time_entry['start']),
            "date_stopped": TogglConnector.parse_iso_str(time_entry['stop']),
            "comment": time_entry.get('description', '')
        }

    def export_worklogs(self, worklogs):
        raise NotImplementedError('Export for Toggl is not implemented')
