import ghapi.all

from fastcore.net import HTTPError  # noqa: F401
from fastcore.net import HTTP404NotFoundError  # noqa: F401
from ansible.module_utils.basic import env_fallback

from ansible.module_utils.basic import AnsibleModule

import ansible_collections.oddbit.github.plugins.module_utils.github_models as models


class GithubModule(AnsibleModule):
    Model = models.ModuleCommonParameters

    def __init__(self, **kwargs):
        argspec = self.common_args() | self.module_args()
        super().__init__(argspec)

        try:
            self.data = self.Model(**self.params)
            self.login(**kwargs)
        except models.pydantic.ValidationError as err:
            self.fail_json(msg=f"Invalid module parameters: {err}", errors=err.errors())

    def parse_repo_name(self, fqrn):
        try:
            owner, reponame = fqrn.split("/")
        except ValueError:
            owner = self.user.login
            reponame = fqrn

        if owner != self.user.login:
            org = owner
        else:
            org = None

        return models.RepositoryName(
            owner=owner,
            name=reponame,
            org=org,
        )

    def common_args(self):
        return {
            "github_token": {
                "type": "str",
                "no_log": True,
                "required": True,
                "fallback": (env_fallback, ["GITHUB_TOKEN"]),
            },
            "github_url": {
                "type": "str",
            },
            "github_per_page": {
                "type": "int",
                "default": 30,
            },
        }

    def module_args(self):
        return {}

    def run(self):
        self.exit_json(changed=False, msg="This module does nothing")

    def login(self, **kwargs):
        token = self.data.github_token
        self.api = ghapi.all.GhApi(token=token, gh_host=self.data.github_url, **kwargs)
        self.user = self.api.users.get_authenticated()


def flatten(oper, *args, **kwargs):
    for page in ghapi.all.paged(oper, *args, **kwargs):
        for item in page:
            yield item
