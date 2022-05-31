from ansible.module_utils.basic import AnsibleModule

import ansible_collections.oddbit.github.plugins.module_utils.github_helper as github_helper
import ansible_collections.oddbit.github.plugins.module_utils.github_models as github_models


class Module(github_helper.GithubModule):
    def module_args(self):
        return dict(
            state=dict(
                type="str", choices=github_models.StateEnum.values(), default="present"
            ),
            organization=dict(type="str", required=True),
            team=dict(
                type="dict",
                options=dict(
                    name=dict(type="str", required=True),
                    description=dict(type="str"),
                    privacy=dict(
                        type="str", choices=github_models.TeamPrivacyEnum.values()
                    ),
                ),
            ),
        )

    def run(self):
        try:
            team = self.find_team_by_name(
                org=self.params["organization"], name=self.params["team"]["name"]
            )
        except github_helper.HTTP404NotFoundError:
            exists = False
            team = {}
        except github_helper.HTTPError as err:
            self.fail_json(
                msg=f"failed to look up team {self.params['team']['name']}: {err}"
            )
        else:
            exists = True

        results = {
            "changed": False,
            "team": team,
        }

        if exists and self.params["state"] == "present":
            results["op"] = "update"

            have = github_models.Team(**team)
            want = github_models.Team(**self.params["team"])
            patch = github_models.Team(**(have.dict() | want.dict()))
            if have != patch:
                results["changed"] = True
                try:
                    self.api.teams.update_in_org(
                        org=self.params["organization"], **patch.dict()
                    )
                    results["team"] = self.api.teams.get_by_name(
                        org=self.params["organization"],
                        team_slug=have.team_slug,
                    )
                except github_helper.HTTPError as err:
                    self.fail_json(
                        msg=f"failed to update team {self.params['team']['name']}: {err}"
                    )
        elif not exists and self.params["state"] == "present":
            results["op"] = "create"
            results["changed"] = True

            want = github_models.Team(**self.params["team"])
            try:
                results["team"] = self.api.teams.create(
                    org=self.params["organization"], **want.dict()
                )
            except github_helper.HTTPError as err:
                self.fail_json(
                    msg=f"failed to create team {self.params['team']['name']}: {err}"
                )
        elif exists and self.params["state"] == "absent":
            results["op"] = "delete"
            results["changed"] = True
            try:
                self.api.teams.delete_in_org(
                    org=self.params["organization"], team_slug=team.slug
                )
            except github_helper.HTTPError as err:
                self.fail_json(
                    msg=f"failed to delete team {self.params['team']['name']}: {err}"
                )

        self.exit_json(**results)


def main():
    Module().run()


if __name__ == "__main__":
    main()
