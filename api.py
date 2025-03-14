#!/usr/bin/env python
# -*- coding: utf-8 -*-

from scoring import get_interests, get_score

import abc
import json
import datetime
from typing import Optional
import logging
import hashlib
import uuid
from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler, HTTPServer

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}
BIRTHDAY_LIMIT = 70


class Field:
    """ Base class for all Fields. Every field needs an initial value """
    def __init__(self, required: Optional[bool] = False, nullable: Optional[bool] = False) -> None:
        self.required = required
        self.nullable = nullable

    def validate(self, value):
        if self.required and value is None:
            raise ValueError(f'The value {type(self).__name__} is required')
        if not self.nullable and value in ('', [], (), {}):
            raise ValueError('The value should not be empty')
        return value


class CharField(Field):
    def validate(self, value):
        super().validate(value)
        if not isinstance(value, str):
            raise ValueError('The value should be string')
        return value


class ArgumentsField(Field):
    def validate(self, value):
        super().validate(value)
        if not isinstance(value, dict):
            raise ValueError('The value should be dict')
        return value


class EmailField(CharField):
    def validate(self, value):
        super().validate(value)
        if '@' not in value:
            raise ValueError('The value should be correct email')
        return value


class PhoneField(Field):
    def validate(self, value):
        super().validate(value)
        if not isinstance(value, (str, int)):
            raise ValueError('The value should be string or integer')
        if not str(value)[0] == '7':
            raise ValueError('The first digit of number should be 7')
        if len(str(value)) != 11:
            raise ValueError('The phone number must consist of 11 digits')
        return value


class DateField(CharField):
    def validate(self, value):
        super().validate(value)
        try:
            datetime.datetime.strptime(value, '%d.%m.%Y')
        except ValueError:
            raise ValueError('The value is not in date format DD.MM.YYYY')
        return value


class BirthDayField(DateField):
    def validate(self, value):
        super().validate(value)
        birthday = datetime.datetime.strptime(value, '%d.%m.%Y')
        today = datetime.datetime.now()
        year_difference = today.year - birthday.year
        if (today.month, today.day) < (birthday.month, birthday.day):
            year_difference -= 1  # Hasn't been a birthday in this year
        if year_difference > BIRTHDAY_LIMIT:
            raise ValueError(f'The birthday should be no older than {BIRTHDAY_LIMIT} years')
        return value


class GenderField(Field):
    def validate(self, value):
        super().validate(value)
        if not isinstance(value, int) or value not in GENDERS:
            raise ValueError('Gender takes the values 0, 1 or 2')
        return value


class ClientIDsField(Field):
    def validate(self, value):
        super().validate(value)
        if not isinstance(value, list):
            raise ValueError('Data of Client should be list')
        for item in value:
            if not isinstance(item, int):
                raise ValueError('The Clients_IDs should be a list of digits')
        return value


class MetaRequest(type):
    def __new__(meta, name, bases, attrs):
        fields = {}
        for key, value in attrs.items():
            if isinstance(value, Field):
                fields[key] = value
        attrs['_fields'] = fields
        return type.__new__(meta, name, bases, attrs)


class Request(metaclass=MetaRequest):
    def __init__(self, **kwargs):
        for attribute in self._fields:
            value = kwargs.get(attribute)
            setattr(self, attribute, value)

    def validate(self):
        for attribute, field in self._fields.items():
            value = getattr(self, attribute)
            if value is not None or field.required:
                field.validate(value)

    def __repr__(self):
        attributes = {
            name: getattr(self, name)
            for name in self.__dict__
            if name[0:2] != '__'
        }
        return f'<Class {self.__class__.__name__}: {attributes}>'


class MethodRequest(Request):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


class ClientsInterestsRequest(MethodRequest):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(MethodRequest):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    @property
    def enough_fields(self):
        if (
            (self.phone and self.email)
            or (self.first_name and self.last_name)
            or (self.birthday and self.gender in GENDERS)
        ):
            return True
        else:
            return False


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512(
            (datetime.datetime.now().strftime("%Y%m%d%H")
                + ADMIN_SALT).encode('utf-8')
        ).hexdigest()
    else:
        digest = hashlib.sha512(
            (request.account + request.login + SALT).encode('utf-8')
        ).hexdigest()
    if digest == request.token:
        return True
    return False


def clients_interests_handler(request, ctx, store):
    try:
        r = ClientsInterestsRequest(**request.arguments)
        r.validate()
    except ValueError as err:
        return {
            'code': INVALID_REQUEST,
            'error': str(err)
        }, INVALID_REQUEST

    clients_interests = {}
    for client_id in r.client_ids:
        clients_interests[f'client_id{client_id}'] = get_interests(
            'nowhere_store', client_id)
    return clients_interests, OK


def online_score_handler(request, ctx, store):
    if request.is_admin:
        score = 42
        return {'score': score}, OK
    try:
        r = OnlineScoreRequest(**request.arguments)
        r.validate()
    except ValueError as err:
        return {
            'code': INVALID_REQUEST,
            'error': str(err)
        }, INVALID_REQUEST

    if not r.enough_fields:
        return {
           'code': INVALID_REQUEST,
           'error': 'INVALID_REQUEST: not enough fields'
        }, INVALID_REQUEST

    score = get_score(store, r)
    return {'score': score}, OK


def method_handler(request, ctx, store):
    response, code = None, None
    method = {'clients_interests': clients_interests_handler,
              'online_score': online_score_handler}
    try:
        r = MethodRequest(**request.get('body'))
        r.validate()
    except ValueError as err:
        return {
            'code': INVALID_REQUEST,
            'error': str(err)
        }, INVALID_REQUEST

    if not r.method:
        return {
            'code': INVALID_REQUEST,
            'error': 'INVALID_REQUEST'
        }, INVALID_REQUEST

    if not check_auth(r):
        return None, FORBIDDEN

    response, code = method[r.method](r, ctx, store)
    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:  # noqa E722
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info('%s: %s %s' % (
                self.path,
                data_string.decode('utf8'),
                context["request_id"])
            )
            if path in self.router:
                try:
                    response, code = self.router[path](
                        {"body": request, "headers": self.headers},
                        context,
                        self.store
                    )
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {
                "error": response or ERRORS.get(code, "Unknown Error"),
                "code": code
            }
        context.update(r)
        logging.info(str(context))
        self.wfile.write(json.dumps(r).encode())
        return


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", action="store", type=int, default=8080)
    parser.add_argument("-l", "--log", action="store", default=None)
    args = parser.parse_args()
    logging.basicConfig(filename=args.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", args.port), MainHTTPHandler)
    logging.info("Starting server at %s" % args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()