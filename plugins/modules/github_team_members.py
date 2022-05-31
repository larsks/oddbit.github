import ansible_collections.oddbit.github.plugins.module_utils.github_helper as github_helper
import ansible_collections.oddbit.github.plugins.module_utils.github_models as github_models


class Module(github_helper.GithubModule):
    class Model(github_models.ModuleCommonParameters):
        state: github_models.StateEnum = github_models.pydantic.Field(default="present")
        organization: str
        team: github_models.TeamMembersRequest

    def module_args(self):
        return dict(
            organization=dict(type="str", required=True),
            state=dict(type="str"),
            team=dict(type="dict"),
        )

    def list_members(self, org, name, role=None):
        return [
            m["login"]
            for m in github_helper.flatten(
                self.api.teams.list_members_in_org, org=org, team_slug=name, role=role
            )
        ]

    def add_members_to_role(self, org, name, role, members):
        if not members:
            return []

        added = []
        have = self.list_members(org=org, name=name, role=role)

        for member in members:
            if member not in have:
                added.append(member)
                try:
                    self.api.teams.add_or_update_membership_for_user_in_org(
                        org=org, team_slug=name, username=member, role=role
                    )
                except github_helper.HTTPError as err:
                    self.fail_json(
                        msg=f"failed to add {member} as {role} to team {name}: {err}"
                    )

        return added

    def remove_members(self, org, name, members):
        if not members:
            return []

        removed = []
        have = self.list_members(org=org, name=name)

        for member in members:
            if member in have:
                removed.append(member)
                try:
                    self.api.teams.remove_membership_for_user_in_org(
                        org=org, team_slug=name, username=member
                    )
                except github_helper.HTTPError as err:
                    self.fail_json(
                        msg=f"failed to remove {member} from team {name}: {err}"
                    )

        return removed

    def run(self):
        try:
            team = self.find_team_by_name(
                org=self.data.organization, name=self.data.team.name
            )
        except github_helper.HTTP404NotFoundError:
            self.fail_json(msg=f"failed to lookup team {self.data.team.name}")

        added: list[str] = []
        removed: list[str] = []

        results = {
            "organization": self.data.organization,
            "changed": False,
            "github": {
                "team": team,
            },
            "added": added,
            "removed": removed,
        }

        if self.data.state == "present":
            added.extend(
                self.add_members_to_role(
                    self.data.organization,
                    team.slug,
                    "maintainer",
                    self.data.team.maintainers,
                )
            )
            added.extend(
                self.add_members_to_role(
                    self.data.organization,
                    team.slug,
                    "member",
                    self.data.team.members,
                )
            )
        elif self.data.state == "absent":
            removed.extend(
                self.remove_members(
                    self.data.organization,
                    team.slug,
                    (self.data.team.maintainers or []) + (self.data.team.members or []),
                )
            )

        results["changed"] = bool(added or removed)
        self.exit_json(**results)


def main():
    Module().run()


if __name__ == "__main__":
    main()
