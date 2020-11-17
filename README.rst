fiobank
=======

|PyPI version| |Build Status| |Test Coverage|

`Fio Bank API <http://www.fio.cz/bank-services/internetbanking-api>`__
in Python.

Installation
------------

.. code:: sh

    $ pip install fiobank

Usage
-----

First, `get your API token <https://ib.fio.cz/ib/wicket/page/NastaveniPage?3>`__.
Initialization of the client:

.. code:: python

    >>> import fiobank
    >>> account = fiobank.Account(token='...')

Account information:

.. code:: python

    >>> account.info()
    {
      'currency': 'CZK',
      'account_number_full': 'XXXXXXXXXX/2010',
      'balance': 42.00,
      'account_number': 'XXXXXXXXXX',
      'bank_code': '2010'
    }

Listing transactions within a time period:

.. code:: python

    >>> gen = account.period('2013-01-20', '2013-03-20')
    >>> list(gen)[0]
    {
      'comment': 'N\xe1kup: IKEA CR, BRNO, CZ, dne 17.1.2013, \u010d\xe1stka  2769.00 CZK',
      'recipient_message': 'N\xe1kup: IKEA CR, BRNO, CZ, dne 17.1.2013, \u010d\xe1stka  2769.00 CZK',
      'user_identifiaction': 'N\xe1kup: IKEA CR, BRNO, CZ, dne 17.1.2013, \u010d\xe1stka  2769.00 CZK',
      'currency': 'CZK',
      'amount': -2769.0,
      'instruction_id': 'XXXXXXXXXX',
      'executor': 'Vilém Fusek',
      'date': datetime.date(2013, 1, 20),
      'type': 'Platba kartou',
      'transaction_id': 'XXXXXXXXXX'
    }

Listing transactions from a single account statement:

.. code:: python

    >>> account.statement(2013, 1)  # 1 is January only by coincidence - arguments mean 'first statement of 2013'

Listing latest transactions:

.. code:: python

    >>> account.last()  # return transactions added from last listing
    >>> account.last(from_id='...')  # sets cursor to given transaction_id and returns following transactions
    >>> account.last(from_date='2013-03-01')  # sets cursor to given date and returns following transactions

Conflict Error
--------------

`Fio API documentation <http://www.fio.cz/docs/cz/API_Bankovnictvi.pdf>`__
(Section 8.2) states that a single token should be used only once per
30s. Otherwise a HTTP 409 Conflict will be returned and
``fiobank.ThrottlingError`` will be raised.

Contributing
------------

.. code:: shell

    $ pip install -e .[tests]
    $ pytest

Changelog
---------

See `GitHub Releases <https://github.com/honzajavorek/fiobank/releases>`_.

License: ISC
------------

© 2013-? Honza Javorek mail@honzajavorek.cz

This work is licensed under `ISC
license <https://en.wikipedia.org/wiki/ISC_license>`__.

.. |PyPI version| image:: https://badge.fury.io/py/fiobank.svg
   :target: https://badge.fury.io/py/fiobank
.. |Build Status| image:: https://travis-ci.org/honzajavorek/fiobank.svg?branch=master
   :target: https://travis-ci.org/honzajavorek/fiobank
.. |Test Coverage| image:: https://coveralls.io/repos/github/honzajavorek/fiobank/badge.svg?branch=master
   :target: https://coveralls.io/github/honzajavorek/fiobank?branch=master
