import ghapi.all

from fastcore.net import HTTPError  # noqa: F401
from fastcore.net import HTTP404NotFoundError  # noqa: F401
from ansible.module_utils.basic import env_fallback

from ansible.module_utils.basic import AnsibleModule

import ansible_collections.oddbit.github.plugins.module_utils.github_models as models


class GithubModule(AnsibleModule):
    def __init__(self, **kwargs):
        argspec = self.common_args() | self.module_args()
        super().__init__(argspec)

        self.login(**kwargs)

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
        token = self.params["github_token"]
        self.api = ghapi.all.GhApi(
            token=token, gh_host=self.params["github_url"], **kwargs
        )
        self.user = self.api.users.get_authenticated()

    def list_teams(self):
        return flatten(self.api.teams.list, org=self.params["organization"])

    def find_team_by_name(self, org, name):
        """Github creates teams by name but searches by slug.

        Rather than try to reproduce the slugify algorithm, we first
        treat the team name as a slug, and if we find it, we're all done.
        If we don't find it, then we get a list of all organization teams
        and look for one with a matching name.
        """

        try:
            return self.api.teams.get_by_name(
                org=self.params["organization"], team_slug=name
            )
        except HTTP404NotFoundError:
            for team in self.list_teams():
                if team["name"] == name:
                    found = team
                    break
            else:
                raise

            return self.api.teams.get_by_name(
                org=self.params["organization"], team_slug=found["slug"]
            )


def flatten(oper, *args, **kwargs):
    for page in ghapi.all.paged(oper, *args, **kwargs):
        for item in page:
            yield item
