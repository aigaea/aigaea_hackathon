
import json


def is_json(data):
    try:
        if data is None:
            return False
        json.loads(data)
    except ValueError:
        return False
    return True


def get_dict_target_value(data: dict, key: str):
    if not isinstance(data, dict):
        raise TypeError(f"{data} is not dict!")
    if not data:
        return None
    if not key:
        raise TypeError("key is None!")
    keys = key.split(".")
    count = 0
    for k in keys:
        count += 1
        if k in data:
            data = data[k]
            if count == len(keys):
                return data
        else:
            return None
