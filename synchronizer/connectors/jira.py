import re
import requests

from flask import current_app
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

    def validate_worklogs(self, worklogs):
        """
        Check existing worklog's task id in target resource
        """
        for worklog in worklogs:
            try:
                data = {
                    'started': self.convert_datetime(worklog.date_started),
                    'timeSpentSeconds': self.round_seconds(
                        worklog.duration
                    ),
                    'comment': worklog.comment
                }

                self._get(
                    'issue/{0}/worklog'.format(worklog.issue_id),
                    data,
                    params={'notifyUsers': 'false'}
                )
            except WrongIssueIDException:
                from synchronizer.models import db

                worklog.is_valid = False
                db.session.add(worklog)
                db.session.commit()

                current_app.logger.warning(f'Wrong issue id {worklog.issue_id} in jira.')


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
