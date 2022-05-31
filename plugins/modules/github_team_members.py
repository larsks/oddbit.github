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
                    members=dict(type="list", default=[]),
                    maintainers=dict(type="list", default=[]),
                    exclusive=dict(type="bool"),
                ),
            ),
        )

    def list_members(self, org, name, role=None):
        return [
            member["login"]
            for member in github_helper.flatten(
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
                org=self.params["organization"], name=self.params["team"]["name"]
            )
        except github_helper.HTTP404NotFoundError:
            self.fail_json(msg=f"failed to lookup team {self.params['team']['name']}")

        added: list[str] = []
        removed: list[str] = []

        results = {
            "organization": self.params["organization"],
            "changed": False,
            "github": {
                "team": team,
            },
            "added": added,
            "removed": removed,
        }

        all_members = (
            self.params["team"]["members"] + self.params["team"]["maintainers"]
        )

        if self.params["state"] == "present":
            added.extend(
                self.add_members_to_role(
                    self.params["organization"],
                    team.slug,
                    "maintainer",
                    self.params["team"]["maintainers"],
                )
            )
            added.extend(
                self.add_members_to_role(
                    self.params["organization"],
                    team.slug,
                    "member",
                    self.params["team"]["members"],
                )
            )
            if self.params["team"]["exclusive"]:
                for member in self.list_members(
                    org=self.params["organization"], name=team.slug
                ):
                    if member not in all_members:
                        removed.append(member)
                        self.api.teams.remove_membership_for_user_in_org(
                            org=self.params["organization"],
                            team_slug=team.slug,
                            username=member,
                        )

        elif self.params["state"] == "absent":
            removed.extend(
                self.remove_members(self.params["organization"], team.slug, all_members)
            )

        results["changed"] = bool(added or removed)
        results["maintainers"] = self.list_members(
            org=self.params["organization"], name=team.slug, role="maintainer"
        )
        results["members"] = self.list_members(
            org=self.params["organization"], name=team.slug, role="member"
        )
        self.exit_json(**results)


def main():
    Module().run()


if __name__ == "__main__":
    main()
