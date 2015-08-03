import json, uuid
from portality.core import app
from flask import request

class Api(object):
    pass

class ModelJsonEncoder(json.JSONEncoder):
    def default(self, o):
        return o.data

def jsonify_models(models):
    data = json.dumps(models, cls=ModelJsonEncoder)
    return respond(data, 200)

def respond(data, status):
    callback = request.args.get('callback', False)
    if callback:
        content = str(callback) + '(' + str(data) + ')'
        return app.response_class(content, status, {'Access-Control-Allow-Origin': '*'}, mimetype='application/javascript')
    else:
        return app.response_class(data, status, {'Access-Control-Allow-Origin': '*'}, mimetype='application/json')

def bad_request(message=None, exception=None):
    # Note - no magic number here, as it will already be in the exception message
    if exception is not None:
        message = exception.message
    app.logger.info("Sending 400 Bad Request from client: {x}".format(x=message))
    data = json.dumps({"status" : "error", "error" : message})
    return respond(data, 400)

def not_found(message=None):
    magic = uuid.uuid1()
    app.logger.info("Sending 404 Not Found from client: {x} (ref: {y})".format(x=message, y=magic))
    data = json.dumps({"status" : "not_found", "error" : message + " (ref: {y})".format(y=magic)})
    return respond(data, 404)

def forbidden(message=None):
    magic = uuid.uuid1()
    app.logger.info("Sending 401 Forbidden from client: {x} (ref: {y})".format(x=message, y=magic))
    data = json.dumps({"status" : "forbidden", "error" : message + " (ref: {y})".format(y=magic)})
    return respond(data, 401)