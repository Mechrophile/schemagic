import json
from functools import partial, wraps, update_wrapper

import collections

import flask
from flask.app import Flask
from flask.globals import request

from schemagic.core import validate_against_schema, validator
from schemagic.utils import multiple_dispatch_fn

ALWAYS = lambda: True
WHEN_DEBUGGING = lambda: __debug__
IDENTITY = lambda x: x

dispatch_to_fn = multiple_dispatch_fn("dispatch_to_fn",{
    lambda fn, args: isinstance(args, collections.Sequence): lambda fn, arg_list: fn(*arg_list),
    lambda fn, args: isinstance(args, collections.MutableMapping): lambda fn, arg_list: fn(**arg_list)
})


def webservice_fn(fn, validation_predicate, input_validator, output_validator):
    validate = validation_predicate()
    return reduce(lambda x, y: y(x),[
        json.loads,
        partial(validate_against_schema, input_validator) if validate else IDENTITY,
        partial(dispatch_to_fn, fn),
        partial(validate_against_schema, output_validator) if validate else IDENTITY,
        json.dumps
    ], request.data)

def service_route(service, validation_pred=None, coerce_data=True, rule=None, input_schema=None, output_schema=None, fn=None):
    if not rule:
        return partial(service_route, service, validation_pred, coerce_data)
    if fn is None:
        return partial(service_route, service, validation_pred, coerce_data, rule, input_schema, output_schema)

    validation_pred = validation_pred or WHEN_DEBUGGING
    input_validator = validator(input_schema or IDENTITY, "input to endpoint {0}".format(rule), coerce_data)
    output_validator = validator(output_schema or IDENTITY, "output from endpoint {0}".format(rule), coerce_data)

    service.add_url_rule(
        rule=rule,
        endpoint=fn.__name__ if hasattr(fn, "__name__") else rule,
        view_func=update_wrapper(lambda: webservice_fn(fn, validation_pred, input_validator, output_validator), fn),
        methods=['POST']
    )
    return fn


