import json
from enum import Enum
from flask import Response

from src.const import *

class ResponseType(Enum):
    JSON = "json"
    CSV = "csv"
    HTML = "html"

CONTENT_TYPE = {
    ResponseType.JSON: "application/json",
    ResponseType.CSV: "text/csv",
    ResponseType.HTML: "text/html"
}

def _format_response(resp, status, resp_type=ResponseType.HTML, **args):
    headers = {'Content-type': CONTENT_TYPE[resp_type]}
    if resp_type == ResponseType.JSON:
        resp = json.dumps(resp)
    elif resp_type == ResponseType.CSV:
        headers['Content-disposition'] = f"attachment; filename={args['filename']}"

    return Response(response=resp, status=status, mimetype=CONTENT_TYPE[resp_type], headers=headers)


def _format_error_data(code, message):
    return {
        'success': False, 
        'errorCode': code, 
        'errorMessage': message
    }


def success(data=None):
    resp = {'success': True}
    if data is not None:
        resp['data'] = data
    return _format_response(resp, 200, ResponseType.JSON)


def bad_request(errorMessage):
    return _format_response(_format_error_data(ERROR_CODE_BAD_REQUEST, errorMessage), 400, ResponseType.JSON)


def not_found(errorMessage):
    return _format_response(_format_error_data(ERROR_CODE_NOT_FOUND, errorMessage), 404, ResponseType.JSON)


def internal_error(errorMessage):
    return _format_response(_format_error_data(ERROR_CODE_INTERNAL_ERROR, errorMessage), 500, ResponseType.JSON)