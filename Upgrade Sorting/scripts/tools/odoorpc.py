#!/usr/bin/python3

import logging
import sys
import xmlrpc.client

from tools.password_manager import OePassword

_logger = logging.getLogger(__name__)


class OdooXR:
    _client = None

    _db = None
    _host = None
    _pm = None

    _uid = 0
    _common = False

    def __init__(self, db: str, host: str, pm: OePassword, local_port: int = None):
        self._client = xmlrpc.client.ServerProxy

        self._db = db
        self._host = host if not local_port else '{}:{}'.format(host, str(local_port))
        self._pm = pm

        url_xmlrpc = '{}/xmlrpc/2'.format(self._host)
        self._url_common = '{}/common'.format(url_xmlrpc)
        self._url_object = '{}/object'.format(url_xmlrpc)

        self._connect()

    def _connect(self):
        try:
            self._common = self._client(self._url_common)
        except Exception as e:
            _logger.error(str(e))
        try:
            self._common.version()
        except ConnectionRefusedError:
            _logger.error('Unable to reach the database. Check the url. ({})'.format(self._host))
            sys.exit(1)

        try:
            # First try with user/password
            self._uid = self._common.authenticate(self._db, self._pm.user, self._pm.password, {})
            self._password = self._pm.password

            # Second try with user/API KEY (in case 2FA is activated for that user)
            if not self._uid:
                pm_2fa = OePassword(self._pm.user + "-2FA", pm_type='odoo-2fa')
                self._uid = self._common.authenticate(self._db, self._pm.user, pm_2fa.password, {})
                self._password = pm_2fa.password

            # Last try with user/magic password
            if not self._uid:
                self._uid = self._common.authenticate(self._db, self._pm.user, self._pm.magic_password, {})
                self._password = self._pm.magic_password

            if not self._uid:
                raise ValueError('Wrong user and|or password.')
        except ValueError as e:
            _logger.error('Unable to log in the database. Check the username. ({})\n\n{}'.format(self._pm.user, str(e)))
            sys.exit(1)
        except Exception as e:
            _logger.error('Unable to log in the database. Check the database name. ({})\n\n{}'.format(self._db, str(e)))
            sys.exit(1)

    def _call(self, model, method, args, kwargs={}):
        models = self._client(self._url_object)
        return models.execute_kw(self._db, self._uid, self._password,
                                 model, method,
                                 args, kwargs)

    def call(self, model, method, args, kwargs):
        """ Generic call method"""
        return self._call(model, method, args, kwargs)

    def count(self, model: str, domain: list = []) -> int:
        """
        Count number of record for the model with the domain
        :param model: Name of the model
        :type model: str

        :param domain: Domain of the research
        :type domain: list

        :return int
        """
        method = 'search_count'
        args = [domain]
        return self._call(model, method, args)

    def fields_get(self, model: str, attributes_to_get: list = []) -> dict:
        """
        Get the technical fields detail for a given model
        :param model: Name of the model
        :type model: str

        :param attributes_to_get: List of the attributes of the fields to retrieve
        :type attributes_to_get: list

        :return dict with definition of each field
        """
        method = 'fields_get'
        args = []
        kwargs = {'attributes': attributes_to_get}
        return self._call(model, method, args, kwargs)

    def list(self, model: str, domain: list = [], offset: int = None, limit: int = None) -> list:
        """
        Get the record_ids of a given model
        :param model: Name of the model
        :type model: str

        :param domain: Domain of the research
        :type domain: list

        :param offset: Used to retrieve a subset of the records
        :type offset: int
        :param limit: Used to retrieve a subset of the records
        :type limit: int

        :return list of ids
        """
        method = 'search'
        args = [domain]
        kwargs = {}
        if offset:
            kwargs.update({'offset': offset})
        if limit:
            kwargs.update({'limit': limit})
        return self._call(model, method, args)

    def read(self, model: str, ids: list, fields_to_get: list = []) -> dict:
        """
        Read the values of given records for given model
        :param model: Name of the model
        :type model: str

        :param ids: List of ids to search for
        :type ids: list

        :param fields_to_get: List of the fields to read on the records
        :type fields_to_get: list

        :return dict with value of each field
        """
        method = 'read'
        kwargs = {'fields': fields_to_get}
        return self._call(model, method, ids, kwargs)

    def search(self, model: str, domain: list,  offset: int = None, limit: int = None) -> dict:

        method = 'search'
        kwargs = {}
        args = [domain]
        if offset:
            kwargs.update({'offset': offset})
        if limit:
            kwargs.update({'limit': limit})
        return self._call(model, method, args, kwargs)

    def write(self, model: str, ids: list, fields_to_set: dict = {}):

        method = 'write'
        kwargs = {'vals': fields_to_set}
        return self._call(model, method, ids, kwargs)

    def create(self, model: str, fields_to_set: dict = {}):

        method = 'create'
        kwargs = {'vals': fields_to_set}
        return self._call(model, method, kwargs)

    def search_read(self, model: str, domain: list, fields_to_get: list = []) -> dict:
        """
        Read the values of corresponding domain search for given model
        :param model: Name of the model
        :type model: str

        :param domain: Domain of the research
        :type domain: list

        :param fields_to_get: List of the fields to read on the records
        :type fields_to_get: list

        :return dict with value of each field
        """
        method = 'search_read'
        args = [domain]
        kwargs = {}
        if fields_to_get:
            kwargs.update({'fields': fields_to_get})
        return self._call(model, method, args, kwargs)
