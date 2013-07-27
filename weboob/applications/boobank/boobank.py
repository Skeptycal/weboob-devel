# -*- coding: utf-8 -*-

# Copyright(C) 2009-2011  Romain Bignon, Christophe Benz
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


from datetime import date
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse as parse_date
from decimal import Decimal, InvalidOperation
import sys

from weboob.capabilities.base import empty
from weboob.capabilities.bank import ICapBank, Account, Transaction
from weboob.tools.application.repl import ReplApplication, defaultcount
from weboob.tools.application.formatters.iformatter import IFormatter, PrettyFormatter


__all__ = ['Boobank']


class QifFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'date', 'raw', 'amount')

    def start_format(self, **kwargs):
        self.output(u'!Type:Bank')

    def format_obj(self, obj, alias):
        result = u'D%s\n' % obj.date.strftime('%d/%m/%y')
        result += u'T%s\n' % obj.amount
        if hasattr(obj, 'category') and not empty(obj.category):
            result += u'N%s\n' % obj.category
        result += u'M%s\n' % obj.raw
        result += u'^'
        return result


class PrettyQifFormatter(QifFormatter):
    MANDATORY_FIELDS = ('id', 'date', 'raw', 'amount', 'category')

    def start_format(self, **kwargs):
        self.output(u'!Type:Bank')

    def format_obj(self, obj, alias):
        if hasattr(obj, 'rdate') and not empty(obj.rdate):
            result = u'D%s\n' % obj.rdate.strftime('%d/%m/%y')
        else:
            result = u'D%s\n' % obj.date.strftime('%d/%m/%y')
        result += u'T%s\n' % obj.amount

        if hasattr(obj, 'category') and not empty(obj.category):
            result += u'N%s\n' % obj.category

        if hasattr(obj, 'label') and not empty(obj.label):
            result += u'M%s\n' % obj.label
        else:
            result += u'M%s\n' % obj.raw

        result += u'^'
        return result


class TransactionsFormatter(IFormatter):
    MANDATORY_FIELDS = ('date', 'label', 'amount')
    TYPES = ['', 'Transfer', 'Order', 'Check', 'Deposit', 'Payback', 'Withdrawal', 'Card', 'Loan', 'Bank']

    def start_format(self, **kwargs):
        self.output(' Date         Category     Label                                                  Amount ')
        self.output('------------+------------+---------------------------------------------------+-----------')

    def format_obj(self, obj, alias):
        if hasattr(obj, 'category') and obj.category:
            _type = obj.category
        else:
            try:
                _type = self.TYPES[obj.type]
            except (IndexError,AttributeError):
                _type = ''

        label = obj.label
        if not label and hasattr(obj, 'raw'):
            label = obj.raw
        date = obj.date.strftime('%Y-%m-%d') if not empty(obj.date) else ''
        amount = obj.amount or Decimal('0')
        return ' %s   %s %s %s' % (self.colored('%-10s' % date, 'blue'),
                                   self.colored('%-12s' % _type[:12], 'magenta'),
                                   self.colored('%-50s' % label[:50], 'yellow'),
                                   self.colored('%10.2f' % obj.amount, 'green' if amount >= 0 else 'red'))


class TransferFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'date', 'origin', 'recipient', 'amount')

    def format_obj(self, obj, alias):
        result = u'------- Transfer %s -------\n' % obj.fullid
        result += u'Date:       %s\n' % obj.date
        result += u'Origin:     %s\n' % obj.origin
        result += u'Recipient:  %s\n' % obj.recipient
        result += u'Amount:     %.2f\n' % obj.amount
        if obj.reason:
            result += u'Reason:     %s\n' % obj.reason
        return result

class InvestmentFormatter(IFormatter):
    MANDATORY_FIELDS = ('label', 'quantity', 'unitvalue')

    tot_valuation = Decimal(0)
    tot_diff = Decimal(0)

    def start_format(self, **kwargs):
        self.output(' Label                           Code     Quantity   Unit Value  Valuation   diff   ')
        self.output('-------------------------------+--------+----------+-----------+-----------+--------')

    def format_obj(self, obj, alias):
        label = obj.label
        if not empty(obj.diff):
            diff = obj.diff
        else:
            diff = obj.valuation - (obj.quantity * obj.unitprice)
        self.tot_diff += diff
        self.tot_valuation += obj.valuation

        return u' %-30s %-10s %6d %11.2f %11.2f   %8.2f' %\
                (label[:30], obj.code[:8] if not empty(obj.code) else '', obj.quantity, obj.unitvalue, obj.valuation, diff)

    def flush(self):
        self.output('-------------------------------+--------+----------+-----------+-----------+--------')
        self.output(u'                                        Total                    %8.2f   %8.2f' %
                     (self.tot_valuation, self.tot_diff))
        self.tot_valuation = Decimal(0)
        self.tot_diff = Decimal(0)


class RecipientListFormatter(PrettyFormatter):
    MANDATORY_FIELDS = ('id', 'label')

    def start_format(self, **kwargs):
        self.output('Available recipients:')

    def get_title(self, obj):
        return obj.label


class AccountListFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'label', 'balance', 'coming')

    tot_balance = Decimal(0)
    tot_coming = Decimal(0)

    def start_format(self, **kwargs):
        self.output('               %s  Account                     Balance    Coming ' % ((' ' * 15) if not self.interactive else ''))
        self.output('------------------------------------------%s+----------+----------' % (('-' * 15) if not self.interactive else ''))

    def format_obj(self, obj, alias):
        if alias is not None:
            id = '%s (%s)' % (self.colored('%3s' % ('#' + alias), 'red', 'bold'),
                              self.colored(obj.backend, 'blue', 'bold'))
            clean = '#%s (%s)' % (alias, obj.backend)
            if len(clean) < 15:
                id += (' ' * (15 - len(clean)))
        else:
            id = self.colored('%30s' % obj.fullid, 'red', 'bold')

        balance = obj.balance or Decimal('0')
        coming = obj.coming or Decimal('0')
        result = u'%s %s %s  %s' % (id,
                                    self.colored('%-25s' % obj.label, 'yellow'),
                                    self.colored('%9.2f' % obj.balance, 'green' if balance >= 0 else 'red'),
                                    self.colored('%9.2f' % obj.coming, 'green' if coming >= 0 else 'red'))

        self.tot_balance += balance
        self.tot_coming += coming
        return result

    def flush(self):
        self.output(u'------------------------------------------%s+----------+----------' % (('-' * 15) if not self.interactive else ''))
        self.output(u'%s                                    Total   %s   %s' % (
                        (' ' * 15) if not self.interactive else '',
                        self.colored('%8.2f' % self.tot_balance, 'green' if self.tot_balance >= 0 else 'red'),
                        self.colored('%8.2f' % self.tot_coming, 'green' if self.tot_coming >= 0 else 'red'))
                   )
        self.tot_balance = Decimal(0)
        self.tot_coming = Decimal(0)


class Boobank(ReplApplication):
    APPNAME = 'boobank'
    VERSION = '0.g'
    COPYRIGHT = 'Copyright(C) 2010-2011 Romain Bignon, Christophe Benz'
    CAPS = ICapBank
    DESCRIPTION = "Console application allowing to list your bank accounts and get their balance, " \
                  "display accounts history and coming bank operations, and transfer money from an account to " \
                  "another (if available)."
    SHORT_DESCRIPTION = "manage bank accounts"
    EXTRA_FORMATTERS = {'account_list':   AccountListFormatter,
                        'recipient_list': RecipientListFormatter,
                        'transfer':       TransferFormatter,
                        'qif':            QifFormatter,
                        'pretty_qif':     PrettyQifFormatter,
                        'ops_list':       TransactionsFormatter,
                        'investment_list': InvestmentFormatter,
                       }
    DEFAULT_FORMATTER = 'table'
    COMMANDS_FORMATTERS = {'ls':          'account_list',
                           'list':        'account_list',
                           'transfer':    'transfer',
                           'history':     'ops_list',
                           'coming':      'ops_list',
                           'investment':  'investment_list',
                          }
    COLLECTION_OBJECTS = (Account, Transaction, )

    def _complete_account(self, exclude=None):
        if exclude:
            exclude = '%s@%s' % self.parse_id(exclude)

        return [s for s in self._complete_object() if s != exclude]

    def do_list(self, line):
        """
        list

        List accounts.
        """
        return self.do_ls(line)

    def show_history(self, command, line):
        id, end_date = self.parse_command_args(line, 2, 1)

        account = self.get_object(id, 'get_account', [])
        if not account:
            print >>sys.stderr, 'Error: please give an account ID (hint: use list command)'
            return 2

        if end_date is not None:
            try:
                end_date = parse_date(end_date)
            except ValueError:
                print >>sys.stderr, '"%s" is an incorrect date format (for example %s)' % (end_date, (date.today() - relativedelta(months=1)).strftime('%Y-%m-%d'))
                return 3
            old_count = self.options.count
            self.options.count = None

        self.start_format()
        for backend, transaction in self.do(command, account, backends=account.backend):
            if end_date is not None and transaction.date < end_date:
                break
            self.format(transaction)

        if end_date is not None:
            self.options.count = old_count

    def complete_history(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_account()

    @defaultcount(10)
    def do_history(self, line):
        """
        history ID [END_DATE]

        Display history of transactions.

        If END_DATE is supplied, list all transactions until this date.
        """
        return self.show_history('iter_history', line)

    def complete_coming(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_account()

    @defaultcount(10)
    def do_coming(self, line):
        """
        coming ID [END_DATE]

        Display future transactions.

        If END_DATE is supplied, show all transactions list this date.
        """
        return self.show_history('iter_coming', line)

    def complete_transfer(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_account()
        if len(args) == 3:
            return self._complete_account(args[1])

    def do_transfer(self, line):
        """
        transfer ACCOUNT [RECIPIENT AMOUNT [REASON]]

        Make a transfer beetwen two account
        - ACCOUNT    the source account
        - RECIPIENT  the recipient
        - AMOUNT     amount to transfer
        - REASON     reason of transfer

        If you give only the ACCOUNT parameter, it lists all the
        available recipients for this account.
        """
        id_from, id_to, amount, reason = self.parse_command_args(line, 4, 1)

        id_from, backend_name_from = self.parse_id(id_from)
        if not id_to:
            self.objects = []
            self.set_formatter('recipient_list')
            self.set_formatter_header(u'Available recipients')
            names = (backend_name_from,) if backend_name_from is not None else None

            self.start_format()
            for backend, recipient in self.do('iter_transfer_recipients', id_from, backends=names):
                self.cached_format(recipient)
            self.flush()
            return 0

        id_to, backend_name_to = self.parse_id(id_to)

        try:
            amount = Decimal(amount)
        except (TypeError, ValueError, InvalidOperation):
            print >>sys.stderr, 'Error: please give a decimal amount to transfer'
            return 2

        if backend_name_from != backend_name_to:
            print >>sys.stderr, "Transfer between different backends is not implemented"
            return 4
        else:
            backend_name = backend_name_from

        names = (backend_name,) if backend_name is not None else None

        if self.interactive:
            origin = self.get_object(id_from, 'get_account', [])
            to = self.get_object(id_to, 'iter_transfer_recipients', [])

            print 'Amount: %s%s' % (amount, origin.currency_text)
            print 'From:   %s' % origin.label
            print 'To:     %s' % to.label
            if not self.ask('Are you sure to do this transfer?', default=True):
                return

        self.start_format()
        for backend, transfer in self.do('transfer', id_from, id_to, amount, reason, backends=names):
            self.format(transfer)
        self.flush()

    def do_investment(self, id):
        """
        investment ID

        Display investments of an account.
        """
        account = self.get_object(id, 'get_account', [])
        if not account:
            print >>sys.stderr, 'Error: please give an account ID (hint: use list command)'
            return 2

        self.start_format()
        for backend, investment in self.do('iter_investment', account, backends=account.backend):
            self.format(investment)
