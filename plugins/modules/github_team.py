from ansible.module_utils.basic import AnsibleModule

import ansible_collections.oddbit.github.plugins.module_utils.github_helper as github_helper
import ansible_collections.oddbit.github.plugins.module_utils.github_models as github_models


class Module(github_helper.GithubModule):
    class Model(github_models.ModuleCommonParameters):
        state: github_models.StateEnum = github_models.pydantic.Field(default="present")
        organization: str
        team: github_models.TeamRequest

    def module_args(self):
        return dict(
            state=dict(type="str"),
            organization=dict(type="str", required=True),
            team=dict(type="dict"),
        )

    def run(self):
        try:
            team = self.find_team_by_name(
                org=self.data.organization, name=self.data.team.name
            )
        except github_helper.HTTP404NotFoundError:
            exists = False
            team = {}
        except github_helper.HTTPError as err:
            self.fail_json(msg=f"failed to look up team {self.data.team.name}: {err}")
        else:
            exists = True

        results = {
            "changed": False,
            "exists": exists,
            "name": self.data.team.name,
            "organization": self.data.organization,
            "github": {"team": team},
        }

        if exists and self.data.state == "present":
            results["op"] = "update"

            have = github_models.Team(**team)
            want = github_models.Team.fromTeamRequest(self.data.team)
            patch = github_models.Team(
                **{
                    **have.dict(),
                    **want.dict(),
                }
            )
            if have != patch:
                results["changed"] = True
                try:
                    self.api.teams.update_in_org(
                        org=self.data.organization, **patch.dict()
                    )
                    results["github"]["team"] = self.api.teams.get_by_name(
                        org=self.data.organization,
                        team_slug=have.team_slug,
                    )
                except github_helper.HTTPError as err:
                    self.fail_json(
                        msg=f"failed to update team {self.data.team.name}: {err}"
                    )
        elif not exists and self.data.state == "present":
            results["op"] = "create"
            results["changed"] = True

            want = github_models.Team.fromTeamRequest(self.data.team)
            try:
                results["github"]["team"] = self.api.teams.create(
                    org=self.data.organization, **want.dict()
                )
            except github_helper.HTTPError as err:
                self.fail_json(
                    msg=f"failed to create team {self.data.team.name}: {err}"
                )
        elif exists and self.data.state == "absent":
            results["op"] = "delete"
            results["changed"] = True
            try:
                self.api.teams.delete_in_org(
                    org=self.data.organization, team_slug=team.slug
                )
            except github_helper.HTTPError as err:
                self.fail_json(
                    msg=f"failed to delete team {self.data.team.name}: {err}"
                )

        self.exit_json(**results)


def main():
    Module().run()


if __name__ == "__main__":
    main()
