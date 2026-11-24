from .core import Ref


def required(data, key):
    value = data.get(key, "")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Please complete {key.replace('_', ' ')}")
    if len(value) > 20000:
        raise ValueError("Each field must be under 20,000 characters")
    return value.strip()


def optional(data, key):
    value = data.get(key, "")
    if not isinstance(value, str) or len(value) > 20000:
        raise ValueError("Invalid text field")
    return value.strip()


def reference(value):
    if not isinstance(value, dict) or not isinstance(value.get("id"), str) or type(value.get("revision")) is not int or value["revision"] < 1:
        raise ValueError("An exact record version is required; refresh the page")
    return Ref(value["id"], value["revision"])
