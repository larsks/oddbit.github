import os

from fastcore.net import (
    HTTPError,
    HTTP4xxClientError,
    HTTP404NotFoundError,
)  # noqa: F401

try:
    from ghapi.all import GhApi
except ImportError:
    GhApi = None


def common_args():
    return {
        "github_auth_token": {
            "type": "str",
            "default": os.getenv("GITHUB_AUTH_TOKEN"),
            "no_log": True,
        },
        "github_url": {
            "type": "str",
        },
        "github_per_page": {
            "type": "int",
            "default": 30,
        },
    }


def login(module, **kwargs):
    token = module.params["github_auth_token"]
    api = GhApi(token=token, gh_host=module.params.get("github_url"), **kwargs)
    return api