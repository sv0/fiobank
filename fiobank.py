# -*- coding: utf-8 -*-
import datetime

from functools import wraps
import re
import time
import warnings

import requests


__all__ = ('Account', 'FioBank', 'ThrottlingError')


def decor(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f'Args: {args}')
        print(f'Kwargs: {kwargs}')

        return func(*args, **kwargs)

    print(f'"{func.__name__}" function was decorated.')
    return wrapper


def coerce_date(value):
    if isinstance(value, datetime.datetime):
        return value.date()
    elif isinstance(value, datetime.date):
        return value
    else:
        return datetime.datetime.strptime(value[:10], '%Y-%m-%d').date()


def sanitize_value(value, convert=None):
    if isinstance(value, str):
        value = value.strip() or None
    if convert and value is not None:
        return convert(value)
    return value


class ThrottlingError(Exception):
    """Throttling error raised when api is being used too fast."""

    def __str__(self):
        return 'Token should be used only once per 30s.'


class Query:
    """Base class representing a query to the FioBank API
        https://www.fio.cz/docs/cz/API_Bankovnictvi.pdf

    {'account_name': None,
    'account_number': None,
    'account_number_full': None,
    'amount': -173.4,
    'bank_code': None,
    'bank_name': None,
    'bic': None,
    'comment': u'N\xe1kup: ALBERT 0669, BRNO, dne 21.10.2016',
    'constant_symbol': None,
    'currency': u'CZK',
    'date': datetime.datetime.date(2016, 10, 23),
    'executor': u'Svyrydiuk, Viacheslav',
    'instruction_id': u'14863889098',
    'original_amount': None,
    'original_currency': None,
    'recipient_message': u'N\xe1kup: ALBERT BRNO, dne 21.12.2017',
    'specific_symbol': None,
    'specification': None,
    'transaction_id': u'13351406489',
    'type': u'Platba kartou',
    'user_identification': u'N\xe1kup: ALBERT, BRNO, dne 21.12.2017',
    'variable_symbol': u'9362'}
    """

    _cache = []

    def __init__(self, account):
        self.account = account

    def __getitem__(self, key):
        return key * 2

    def __iter__(self):
        print('__iter__')

    def filter(self, *args, **kwargs):
        print('filter')

    def all(self):
        today = datetime.datetime.today()
        from_date = today - datetime.timedelta(days=365*3)
        return self.account.period(from_date, today)

    def latest(self):
        """Return the latest transaction)"""
        self.account._request(
            'set-last-date',
            from_date=coerce_date(datetime.date.today() - datetime.timedelta(days=30))  # noqa
        )
        transactions = self.account._parse_transactions(
            self.account._request('last')
        )
        try:
            return list(transactions)[-1]
        except IndexError:
            return None


class Account:

    cache = {}
    last_request_timestamp = 0

    base_url = 'https://fioapi.fio.cz/v1/rest/'

    actions = {
        'periods': 'periods/{token}/{from_date}/{to_date}/transactions.json',
        'by-id': 'by-id/{token}/{year}/{number}/transactions.json',
        'last': 'last/{token}/transactions.json',
        'set-last-id': 'set-last-id/{token}/{from_id}/',
        'set-last-date': 'set-last-date/{token}/{from_date}/',
    }

    # http://www.fio.cz/xsd/IBSchema.xsd
    transaction_schema = {
        'column0': ('date', coerce_date),
        'column1': ('amount', float),
        'column2': ('account_number', str),
        'column3': ('bank_code', str),
        'column4': ('constant_symbol', str),
        'column5': ('variable_symbol', str),
        'column6': ('specific_symbol', str),
        'column7': ('user_identification', str),
        'column8': ('type', str),
        'column9': ('executor', str),
        'column10': ('account_name', str),
        'column12': ('bank_name', str),
        'column14': ('currency', str),
        'column16': ('recipient_message', str),
        'column17': ('instruction_id', str),
        'column18': ('specification', str),
        'column22': ('transaction_id', str),
        'column25': ('comment', str),
        'column26': ('bic', str),
        'column27': ('reference', str),
    }

    info_schema = {
        'accountid': ('account_number', str),
        'bankid': ('bank_code', str),
        'currency': ('currency', str),
        'iban': ('iban', str),
        'bic': ('bic', str),
        'closingbalance': ('balance', float),
    }

    _amount_re = re.compile(r'\-?\d+(\.\d+)? [A-Z]{3}')

    def __init__(self, token):
        self.token = token
        self.transactions = Query(self)

    def __repr__(self):
        return f'{self.__class__.__name__}(token="{self.token}")'

    def _get_cached_response_json(self, url: str) -> dict:
        # last request was performed less than 30 sec ago
        return self.cache.get(url) \
            if time.time() - self.last_request_timestamp < 30 \
            else None

    def _request(self, action, **params):
        # import ipdb
        # ipdb.set_trace()

        template = self.base_url + self.actions[action]
        url = template.format(token=self.token, **params)
        cached_response_json = self._get_cached_response_json(url)
        if cached_response_json:
            # print(f'There is cached response for {url}')
            return cached_response_json
        response = requests.get(url)

        if response.status_code == requests.codes['conflict']:
            raise ThrottlingError()

        response.raise_for_status()

        if response.content:
            self.cache[url] = response.json()
            self.last_request_timestamp = time.time()
            return response.json()
        return None

    def _parse_info(self, data):
        warnings.warn(
            '_parse_info was renamed to _parse_account_info',
            DeprecationWarning
        )
        return self._get_account_info(data)

    def _get_account_info(self, data: dict) -> dict:
        """Get FioBank account information.

        Args:
            data (dict): data obtained from
            https://www.fio.cz/ib_api/rest/last/<token>/transactions.json

        Returns:
            dict: The dictionary which contains Fiobank account information.
                Example:

                {'account_number': '2400111111',
                 'account_number_full': '2400111111/2010',
                 'balance': 1573237.52,
                 'bank_code': '2010',
                 'bic': 'FIOBCZPPXXX',
                 'currency': 'CZK',
                 'iban': 'CZ1120100000002400111111'}
        """
        info = {}
        for key, value in data['accountStatement']['info'].items():
            key = key.lower()
            if key in self.info_schema:
                field_name, convert = self.info_schema[key]
                value = sanitize_value(value, convert)
                info[field_name] = value

        # make some refinements
        self._add_account_number_full(info)

        # return data
        return info

    def _parse_transactions(self, data):
        schema = self.transaction_schema
        try:
            entries = data['accountStatement']['transactionList']['transaction']  # NOQA
        except TypeError:
            entries = []

        for entry in entries:
            # parse entry from API
            trans = {}
            for column_name, column_data in entry.items():
                if not column_data:
                    continue
                field_name, convert = schema[column_name.lower()]
                value = sanitize_value(column_data['value'], convert)
                trans[field_name] = value

            # add missing fileds with None values
            for column_data_name, (field_name, convert) in schema.items():
                trans.setdefault(field_name, None)

            # make some refinements
            specification = trans.get('specification')
            is_amount = self._amount_re.match
            if specification is not None and is_amount(specification):
                amount, currency = trans['specification'].split(' ')
                trans['original_amount'] = float(amount)
                trans['original_currency'] = currency
            else:
                trans['original_amount'] = None
                trans['original_currency'] = None

            self._add_account_number_full(trans)

            # generate transaction data
            yield trans

    def _add_account_number_full(self, obj):
        account_number = obj.get('account_number')
        bank_code = obj.get('bank_code')

        if account_number is not None and bank_code is not None:
            account_number_full = '{}/{}'.format(account_number, bank_code)
        else:
            account_number_full = None

        obj['account_number_full'] = account_number_full

    @property
    def info(self) -> dict:
        data = self._request('last')
        return self._get_account_info(data)

    def period(self, from_date, to_date):
        data = self._request('periods',
                             from_date=coerce_date(from_date),
                             to_date=coerce_date(to_date))
        return self._parse_transactions(data)

    def statement(self, year, number):
        data = self._request('by-id', year=year, number=number)
        return self._parse_transactions(data)

    def last(self, from_id=None, from_date=None):
        if from_id and from_date:
            raise ValueError('Only one constraint is allowed.')

        if from_id:
            self._request('set-last-id', from_id=from_id)
        elif from_date:
            self._request('set-last-date', from_date=coerce_date(from_date))

        return self._parse_transactions(self._request('last'))


class FioBank(Account):

    def __init__(self, token):
        warnings.warn(
            'fiobank.FioBank class was renamed to fiobank.Account',
            DeprecationWarning
        )
        super().__init__(token)
