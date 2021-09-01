import hashlib
from base64 import b64decode, b64encode
from datetime import date, datetime, time, timedelta

import iso8601
import pytz
import requests
from Crypto import Random
from Crypto.Cipher import AES


class AESCipher(object):
    def __init__(self, key):
        self.block_size = AES.block_size
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, plain_text):
        plain_text = self.__pad(plain_text)
        iv = Random.new().read(self.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        encrypted_text = cipher.encrypt(plain_text.encode())

        return b64encode(iv + encrypted_text).decode("utf-8")

    def decrypt(self, encrypted_text):
        encrypted_text = b64decode(encrypted_text)
        iv = encrypted_text[:self.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        plain_text = cipher.decrypt(encrypted_text[self.block_size:]).decode("utf-8")
        return self.__unpad(plain_text)

    def __pad(self, plain_text):
        number_of_bytes_to_pad = self.block_size - len(plain_text) % self.block_size
        ascii_string = chr(number_of_bytes_to_pad)
        padding_str = number_of_bytes_to_pad * ascii_string
        padded_plain_text = plain_text + padding_str
        return padded_plain_text

    @staticmethod
    def __unpad(plain_text):
        last_character = plain_text[len(plain_text) - 1:]
        return plain_text[:-ord(last_character)]


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
