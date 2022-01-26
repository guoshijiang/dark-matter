import json


def custom_to_json(python_object):
    if isinstance(python_object, bytes):
        return {"__class__": "bytes", "__value__": list(python_object)}
    else:
        raise TypeError(repr(python_object) + " not JSON serializable or not bytes.")


def write_json(file_name, j):
    with open(file_name, 'w') as outfile:
        json.dump(j, outfile, default=custom_to_json, separators=(',', ':'))


def read_json(file_name):
    with open(file_name) as data_file:
        j = json.load(data_file)
    return j