import requests
from .base import BaseConnector, WrongIssueIDException


class JiraConnector(BaseConnector):
    NAME = 'Jira'

    def __init__(self, **kwargs):
        self.server = kwargs['server']
        self.auth = requests.auth.HTTPBasicAuth(
            kwargs['login'],
            kwargs['password']
        )

    def _api(self, method, endpoint, data=None, params=None):
        response = requests.request(
            method,
            'https://{0}/rest/api/2/{1}'.format(self.server, endpoint),
            json=data,
            auth=self.auth,
            params=params
        )

        # Catch wrong issue ID exceptions
        if response.status_code == 404:
            raise WrongIssueIDException()

        response.raise_for_status()
        return response.json()

    def _get(self, *args, **kwargs):
        return self._api('get', *args, **kwargs)

    def _post(self, *args, **kwargs):
        return self._api('post', *args, **kwargs)

    def import_worklogs(self, start_date, end_date):
        raise NotImplementedError('Import for Jira is not implemented')

    def export_worklogs(self, worklogs):
        for i, worklog in enumerate(worklogs):
            try:
                data = {
                    'started': self.convert_datetime(worklog.date_started),
                    'timeSpentSeconds': self.round_seconds(
                        worklog.duration
                    ),
                    'comment': worklog.comment
                }
                self._post(
                    'issue/{0}/worklog'.format(worklog.issue_id),
                    data,
                    params={'notifyUsers': 'false'}
                )
            except WrongIssueIDException:
                # When we got 404 error - wrong issue ID specified
                # Mark worklog as invalid
                worklog.update(is_valid=False)
            except Exception as err:
                # All other errors should be raised
                print(err)
                raise self.ExportException(i)

    @staticmethod
    def round_seconds(seconds):
        """
        Round duration in seconds to integer number of minutes.
        For example, 59 seconds to 60, 305 seconds to 360 seconds etc.
        It is JIRA specific requirement. For example:
        JIRA rounds 359 (6 minutes 59 seconds) seconds to 300 seconds (6 min).
        """
        if seconds % 60:
            # Add one more minute
            return 60 * (seconds // 60 + 1)

        return seconds

    @staticmethod
    def convert_datetime(datetime_to_convert):
        """
        Converts date to JIRA datetime format
        """
        return datetime_to_convert.strftime('%Y-%m-%dT%H:%M:%S.000%z')
