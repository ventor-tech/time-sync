import re
import requests

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from .base import BaseConnector, WrongIssueIDException


class JiraConnector(BaseConnector):
    NAME = 'Jira'
    FORM_FIELDS = ['name', 'server', 'login', 'api_token', ]

    def __init__(self, **kwargs):
        self.server = kwargs['server']
        self.auth = requests.auth.HTTPBasicAuth(
            kwargs['login'],
            kwargs['api_token']
        )
        # Apply delays between attempts to connection to
        # jira server in case of maximum requests quota
        self.session = requests.Session()
        self.retry = Retry(connect=3, backoff_factor=0.5)
        self.adapter = HTTPAdapter(max_retries=self.retry)
        self.session.mount('https://', self.adapter)

    def _api(self, method, endpoint, data=None, params=None):
        response = self.session.request(
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

    def validate_issue(self, issue_id):
        """
        Check if issue exists in JIRA.

        :param str issue_id: Issue id of task in target source
        :rtype: bool
        """
        try:
            self._get('issue/{0}/'.format(issue_id))
            return True
        except WrongIssueIDException:
            return False


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

    def search_issues(self, term):
        """
        Returns list of issue tuples like 
        [
            (issue_id_1, issue_name_1),
            (issue_id_2, issue_name_2),
            ...
        ]
        """
        search_condition = 'summary ~ "{0}"'

        # If possible match with issue keys append additional condition
        if re.search(r'(?:\s|^)([A-Z]+-[0-9]+)(?=\s|$)', term.upper()):
            search_condition += ' OR id = "{0}"'

        res = self._get(
            'search',
            params={
                'jql':  search_condition.format(term),
                'fields': ['summary']})

        results = [
            {'id': i['key'], 'name': i['fields']['summary']}
            for i in res['issues']
        ]
        return results

    @staticmethod
    def validate_connector(**kwargs):
        if "jira" in kwargs["connector_type"].lower():
            auth = requests.auth.HTTPBasicAuth(
                kwargs['login'],
                kwargs['api_token']
            )

            response = requests.request(
                "GET",
                "https://{0}/rest/api/2/myself".format(kwargs['server']),
                auth=auth,
            )

            return response.status_code == 200