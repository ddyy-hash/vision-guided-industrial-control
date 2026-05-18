#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from datetime import datetime, date, time
from decimal import Decimal

class CustomJSONEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, time):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)

def json_serialize(obj):
    return json.dumps(obj, cls=CustomJSONEncoder)

def json_response(data, status_code=200):
    from flask import jsonify
    return jsonify(json.loads(json_serialize(data))), status_code

def serialize_for_json(obj):
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(v) for v in obj]
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, time):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif hasattr(obj, '__dict__'):
        return serialize_for_json(obj.__dict__)
    else:
        return obj