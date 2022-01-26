def custom_to_json(python_object): # for dealing with bytes, borrowed from www.diveintopython3.net/serializing.html
    if isinstance(python_object, bytes):
        return {"__class__": "bytes", "__value__": list(python_object)}
    else:
        raise TypeError(repr(python_object) + " not JSON serializable or not bytes.")