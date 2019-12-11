import pytz
import iso8601

from datetime import date, time, datetime, timedelta


class DateAndTime(object):
    """
    Class with utility date and time functions
    """

    def __init__(self, timezone='UTC'):
        self.tz = pytz.timezone(timezone)

    def localize(self, date_to_localize):
        """
        Returns "now" as a localized datetime object.
        """
        return self.tz.localize(date_to_localize)

    def now(self):
        """
        Returns "now" as a localized datetime object.
        """
        return datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(self.tz)

    def start_of_today(self):
        """
        Returns 00:00:00 today as a localized datetime object.
        """
        return self.tz.localize(
            datetime.combine(
                date.today(),
                time.min
            )
        )

    def start_of_prev_day(self, number_of_days):
        """
        Returns 00:00:00 one of previous days as a localized datetime object.
        """
        return self.tz.localize(
            datetime.combine(
                date.today(),
                time.min
            )
            - timedelta(days=number_of_days)
        )

    def parse_iso_str(self, iso_str):
        """
        Parses an ISO 8601 datetime string and returns a localized datetime
        object.
        """
        return iso8601.parse_date(iso_str).astimezone(self.tz)

    def compare_iso_dates(self, date1, date2):
        """
        Compares two dates in ISO8601 format. Returns 0 if dates are equal,
        -1 if date1 < date2 and 1 if date1 > date2
        """
        if isinstance(date1, str):
            date1 = self.parse_iso_str(date1)

        if isinstance(date2, str):
            date2 = self.parse_iso_str(date2)

        if date1 > date2:
            return 1
        elif date1 < date2:
            return -1
        return 0

    def is_equal_dates(self, date1, date2):
        """
        Returns True if two dates in ISO8601 format are the same date
        """
        if isinstance(date1, str):
            date1 = self.parse_iso_str(date1)

        if isinstance(date2, str):
            date2 = self.parse_iso_str(date2)

        return date1.date() == date2.date()
