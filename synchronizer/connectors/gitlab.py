import re
import requests
import urllib.parse

from synchronizer.utils import DateAndTime
from .base import BaseConnector


class GitlabConnector(BaseConnector):
    NAME = 'Gitlab'

    def __init__(self, **kwargs):
        super(GitlabConnector, self).__init__()
        self.server = kwargs['server']
        self.headers = {
            'Private-Token': kwargs['api_token'],
        }

    def _api(
        self, method, endpoint,
        data=None, params=None, ignore_errors=False
    ):
        response = requests.request(
            method,
            'https://{0}/api/v4/{1}'.format(self.server, endpoint),
            data=data,
            params=params,
            headers=self.headers
        )
        if not ignore_errors:
            response.raise_for_status()
        return response.json()

    def _get(self, *args, **kwargs):
        return self._api('get', *args, **kwargs)

    def _post(self, *args, **kwargs):
        return self._api('post', *args, **kwargs)

    def import_worklogs(self, start_date, end_date, full=False):
        """
        Run import time reports from Gitlab
        """
        print('Start importing worklogs from Gitlab')
        worklogs = []
        # Step 1. Fetch all issues updated after start_date and before end_date
        issues_ids = self.get_all_issues(start_date)
        print('Found {} issues to check'.format(len(issues_ids)))
        for project_id, issue_iid in issues_ids:
            worklogs += self.get_worklogs_from_issue(
                project_id,
                issue_iid,
                start_date,
                end_date,
                full
            )
        # filter worklogs
        # Created at date should be greated that start_date!
        worklogs_between_dates = []
        for w in worklogs:
            print(GitlabConnector.parse_iso_str(w['date_started']))
            print(GitlabConnector.parse_iso_str(start_date))
            if (
                GitlabConnector.parse_iso_str(w['date_started'])
                >= GitlabConnector.parse_iso_str(start_date) and
                GitlabConnector.parse_iso_str(w['date_started'])
                <= GitlabConnector.parse_iso_str(end_date)
            ):
                worklogs_between_dates.append(w)
        return worklogs_between_dates

    def export_worklogs(self, worklogs):
        for i, worklog in enumerate(worklogs):
            try:
                # common structure: ns/project_id#issue_id
                project_id, issue_id = worklog.issue_id.split('#', 1)
                print('Parsed project and issue IDs: {}, {}'.format(
                    project_id, issue_id
                ))
                data = {
                    "body": "/spend {} {}".format(
                        self.convert_to_hr(worklog.duration),
                        self.convert_datetime(worklog.date_started)
                    )
                }
                self._post(
                    'projects/{}/issues/{}/notes'.format(
                        urllib.parse.quote_plus(project_id), issue_id
                    ),
                    data,
                    ignore_errors=True
                )
            except Exception as err:
                print(err)
                raise self.ExportException(i)

    def get_worklogs_from_issue(
        self, project_id, issue_iid, start_date, end_date, full=False
    ):
        """
        Fetch all worklogs from Gitlab
        """
        print('Process {}/{} issue'.format(project_id, issue_iid))
        # TODO: use start and end date
        page = 1
        issue_worklogs = []
        notes = []
        while True:
            issue_notes = self._get(
                'projects/{}/issues/{}/notes'.format(
                    project_id,
                    issue_iid
                ),
                data={
                    "page": page,
                    "per_page": 100,
                    "sort": 'asc'
                }
            )

            notes += issue_notes

            if not issue_notes:
                print('Finally, all notes is fetched!')
                break

            page += 1

        add_regex = re.compile(
            r'added ((?P<days>\d+)d\s)?((?P<hours>\d+)h\s)?'
            r'((?P<minutes>\d+)m\s)?((?P<seconds>\d+)s\s)?of time spent'
            r'(\sat\s(?P<date>'
            r'([12]\d{3})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])))?'
        )

        subtract_regex = re.compile(
            r'subtracted ((?P<days>\d+)d\s)?((?P<hours>\d+)h\s)?'
            r'((?P<minutes>\d+)m\s)?((?P<seconds>\d+)s\s)?of time spent'
            r'(\sat\s(?P<date>'
            r'([12]\d{3})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])))?'
        )

        remove_regex = re.compile(
            r'removed time spent'
        )

        for note in notes:
            m = add_regex.match(note['body'])
            if m:
                print('{}\t\t\t{}\t\t{}\t\t{}\t\t{}'.format(
                    note['author']['name'],
                    m.group('date') or '',
                    m.group('hours') or '',
                    m.group('minutes') or '',
                    m.group('seconds') or ''
                ))
                duration = (
                    (int(m.group('days') or 0))*8*60*60
                    + (int(m.group('hours') or 0))*60*60
                    + (int(m.group('minutes') or 0))*60
                    + (int(m.group('seconds') or 0))
                )
                # If time was added less than 24 hours ago note will have no
                # 'at year-mm-dd' part. So, we replace it manually with
                # datetime.now()
                issue_worklogs.append({
                    "issue_id": issue_iid,
                    "project_id": project_id,
                    "username": note['author']['name'],
                    "source_id": str(note['id']),
                    "duration": duration,
                    "date_created": note['created_at'],
                    "date_started": GitlabConnector.parse_iso_str(
                        # hack for this day time spent
                        m.group('date') or DateAndTime().now()
                    ),
                    "date_stopped": GitlabConnector.parse_iso_str(
                        # hack for this day time spent
                        m.group('date') or DateAndTime().now()
                    ),
                    "comment": "No comment for Gitlab spent time..."
                })
            else:
                m = subtract_regex.match(note['body'])
                if m and full:
                    print('Subtract time spent')
                    # TODO: implement subtract feature...
                    print('{}\t\t\t{}\t\t{}\t\t{}\t\t{}'.format(
                        note['author']['name'],
                        m.group('date') or '',
                        m.group('hours') or '',
                        m.group('minutes') or '',
                        m.group('seconds') or ''
                    ))
                    duration = -(
                        (int(m.group('hours') or 0))*60*60
                        + (int(m.group('minutes') or 0))*60
                        + (int(m.group('seconds') or 0))
                    )
                    issue_worklogs.append({
                        "issue_id": issue_iid,
                        "project_id": project_id,
                        "username": note['author']['name'],
                        "source_id": str(note['id']),
                        "duration": duration,
                        "date_created": note['created_at'],
                        "date_started": GitlabConnector.parse_iso_str(
                            # hack for this day time spent
                            m.group('date') or DateAndTime().now()
                        ),
                        "date_stopped": GitlabConnector.parse_iso_str(
                            # hack for this day time spent
                            m.group('date') or DateAndTime().now()
                        ),
                        "comment": "No comment for Gitlab spent time..."
                    })
                else:
                    if remove_regex.match(note['body']):
                        print('Remove all worklogs before this record')
                        # remove all worklogs before
                        issue_worklogs = []

        if full and issue_worklogs:
            print('Fetch Project Name and URL')
            project_name, project_url = self.get_project_by_id(project_id)
            for worklog in issue_worklogs:
                worklog['project_name'] = project_name
                worklog['project_url'] = project_url
                worklog['issue_url'] = '{}/issues/{}'.format(
                    project_url,
                    issue_iid
                )
        return issue_worklogs

    def get_project_by_id(self, project_id):
        """
        Returns Project URL and Name by ID
        """
        project_info = self._get(
            'projects/{}/'.format(
                project_id
            )
        )
        return (
            project_info['path_with_namespace'],
            project_info['web_url']
        )

    def get_all_projects(self):
        """
        Returns list of project IDs
        """
        page = 1
        project_ids = []

        while True:
            projects_next_page = self._get(
                'projects',
                data={
                    "simple": True,
                    "page": page,
                    "per_page": 100
                }
            )
            if not projects_next_page:
                print('Finally, all projects is fetched!')
                break
            project_ids += [x['id'] for x in projects_next_page]
            page += 1

        return project_ids

    def get_all_issues(self, updated_after):
        """
        Returns list of lists (project ID, issue IID)
        """
        print('Try to get all issues updated after'.format(updated_after))
        page = 1
        issues_ids = []

        while True:
            print('Page: {}'.format(page))
            issues_next_page = self._get(
                'issues',
                data={
                    "scope": "all",
                    "page": page,
                    "per_page": 100,
                    "updated_after": updated_after
                    # "updated_before": updated_before
                }
            )
            if not issues_next_page:
                print('Finally, all issues is fetched!')
                break
            for issue in issues_next_page:
                print(
                    issue['project_id'],
                    issue['iid'],
                    issue['web_url']
                )
            issues_ids += [
                (x['project_id'], x['iid']) for x in issues_next_page
            ]
            page += 1

        return issues_ids

    def convert_to_hr(self, seconds):
        """
        Converts seconds to human readable format: 3h6m2s
        """
        minutes = seconds // 60
        if minutes == 0:
            return '{}s'.format(seconds)
        else:
            seconds = seconds - minutes*60
            if minutes < 60:
                return '{}m{}s'.format(minutes, seconds)
            else:
                hours = minutes // 60
                minutes = minutes - hours*60
                return '{}h{}m{}s'.format(hours, minutes, seconds)

    @staticmethod
    def convert_datetime(datetime_to_convert):
        """
        Converts date to YYYY-mm-dd datetime format
        """
        return datetime_to_convert.strftime('%Y-%m-%d')
