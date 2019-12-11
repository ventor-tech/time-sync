import xmlrpc.client

from .base import BaseConnector


class OdooConnector(BaseConnector):
    NAME = 'Odoo'
    PROJECT_NAME_TO_PROJECT_ID_MAPPING = {}
    PROJECT_NAME_TO_ACCOUNT_ID_MAPPING = {}

    def __init__(self, **kwargs):
        self.url, self.db = kwargs['server'].rsplit(':', 1)
        self.username = kwargs['login'],
        self.password = kwargs['password']
        self.common = xmlrpc.client.ServerProxy(
            '{}/xmlrpc/2/common'.format(self.url)
        )
        self.models = xmlrpc.client.ServerProxy(
            '{}/xmlrpc/2/object'.format(self.url)
        )

        # get a user identifier
        self.uid = self.common.authenticate(
            self.db,
            self.username,
            self.password,
            {}
        )

    def _api(self, method, endpoint, data=None, params=None):
        if params:
            print("""
            self.models.execute_kw(
                self.db, self.uid, self.password,
                {}, {},
                {},
                {}
            )
            """.format(endpoint, method, data, params))
            response = self.models.execute_kw(
                self.db, self.uid, self.password,
                endpoint, method,
                data,
                params
            )
        else:
            print("""
            self.models.execute_kw(
                self.db, self.uid, self.password,
                {}, {},
                {}
            )
            """.format(endpoint, method, data))
            response = self.models.execute_kw(
                self.db, self.uid, self.password,
                endpoint, method,
                data
            )
        return response

    def _get(self, *args, **kwargs):
        pass

    def _post(self, *args, **kwargs):
        pass

    def import_worklogs(self, start_date, end_date):
        raise NotImplementedError('Import for Jira is not implemented')

    def export_worklogs(self, worklogs):
        for i, worklog in enumerate(worklogs):
            try:
                project_name, ref_num = worklog.issue_id.split('#')
                print([worklog['issue_id'], project_name, ref_num])
                project_id, account_id \
                    = self.get_project_and_account_id(project_name)
                task_id = self.get_task_id(project_id, ref_num)
                print([project_id, account_id, task_id])

                new_timesheet = self.generate_empty_timesheet()

                new_timesheet.update({
                    'task_id': task_id,
                    'name': worklog.comment,
                    'date': self.convert_datetime(worklog.date_started),
                    'work_type': 'dev',
                    'unit_amount': worklog.duration/60/60,  # decimal
                    'account_id': account_id
                })

                # import pdb; pdb.set_trace()

                new_timesheet_id = self._api(
                    'create',
                    'hr.analytic.timesheet',
                    data=[
                        new_timesheet
                    ]
                )

                if not new_timesheet_id:
                    raise Exception('Not new timesheet id returned')
            except xmlrpc.client.Fault as err:
                print(err.faultString)
                raise self.ExportException(i, err.faultString)
            except Exception as err:
                print(err)
                raise self.ExportException(i)

    def get_project_and_account_id(self, project_name):
        """
        Returns account_id for specified project
        """
        if not project_name:
            raise Exception('No project ID specified')

        # check if account_id was already fetched
        # to avoid additional requests
        if project_name in self.PROJECT_NAME_TO_PROJECT_ID_MAPPING:
            return (
                self.PROJECT_NAME_TO_PROJECT_ID_MAPPING[project_name],
                self.PROJECT_NAME_TO_ACCOUNT_ID_MAPPING[project_name]
            )

        [project_id] = self._api(
            'search',
            'project.project',
            data=[[['name', '=', project_name]]]
        )

        if not project_id:
            raise Exception('No project ID found for name: {}'.format(
                project_name
            ))

        project = self._api(
            'read',
            'project.project',
            data=[project_id],
            params={'fields': ['id', 'name', 'analytic_account_id']}
        )

        if (
            'analytic_account_id' not in project
            or not project['analytic_account_id']
        ):
            raise Exception(
                'No analytic_account_id for project: {} ({})'.format(
                    project_name, project_id
                )
            )
        account_id = project['analytic_account_id'][0]

        self.PROJECT_NAME_TO_PROJECT_ID_MAPPING[project_name] = project_id
        self.PROJECT_NAME_TO_ACCOUNT_ID_MAPPING[project_name] = account_id
        return project_id, account_id

    def get_task_id(self, project_id, ref_num):
        """
        Get task ID by ref_num
        """
        [task_id] = self._api(
            'search',
            'project.task',
            data=[[['project_id', '=', project_id], ['ref_num', '=', ref_num]]]
        )

        if not task_id:
            raise Exception(
                'Cannot found task ID for project_id/ref_num: {}/{}'.format(
                    project_id,
                    ref_num
                )
            )
        return task_id

    def generate_empty_timesheet(self):
        """
        Returns empty timesheet entry template
        """
        new_timesheet = self._api(
            'default_get',
            'hr.analytic.timesheet',
            data=[
                [
                    'reported_user_id', 'state', 'journal_id', 'account_id',
                    'general_account_id', 'work_type', 'date', 'user_id',
                    'product_id', 'name', 'task_id', 'to_invoice', 'amount',
                    'unit_amount', 'product_uom_id', 'reported_hours'
                ]
            ]
        )
        return new_timesheet

    @staticmethod
    def convert_datetime(datetime_to_convert):
        """
        Converts date to JIRA datetime format
        """
        return datetime_to_convert.strftime('%Y-%m-%d')
