"""Base connector class"""
import iso8601


class ExportException(Exception):
    """
    Custom exception class to handle errors when import or export from
    different connectors
    """
    def __init__(self, index, message=None):
        self.index = index
        self.message = message


class WrongIssueIDException(Exception):
    """
    Custom exception class to handle errors related to wrong issue ID
    """
    pass


class BaseConnector(object):
    NAME = None
    ExportException = ExportException

    def __init__(self, **kwargs):
        pass

    def import_worklogs(self, start_date, end_date):
        raise NotImplementedError()

    def export_worklogs(self, worklogs):
        """
        Parameters:
        worklogs -- list of Worklog objects to process
        """
        raise NotImplementedError()

    @staticmethod
    def parse_iso_str(date_iso_str):
        """
        Parses an ISO 8601 datetime string and returns a datetime object.
        """
        if isinstance(date_iso_str, str):
            return iso8601.parse_date(date_iso_str)
        return date_iso_str
