from ansible.module_utils.basic import AnsibleModule

import ansible_collections.oddbit.github.plugins.module_utils.github_helper as github_helper


def list_members(api, name, role):
    return [
        m["login"]
        for m in github_helper.flatten(
            api.teams.list_members_in_org, team_slug=name, role=role
        )
    ]


def main():
    module_args = github_helper.common_args()
    module_args.update(
        dict(
            name=dict(type="str", required=True),
            organization=dict(type="str", required=True),
            state=dict(type="str", default="present", choices=["present", "absent"]),
            members=dict(type="list", default=[]),
            maintainers=dict(type="list", default=[]),
            exclusive=dict(type="bool", default=False),
        )
    )

    module = AnsibleModule(argument_spec=module_args)
    api = github_helper.login(module, org=module.params["organization"])
    added_members = []
    added_maintainers = []
    removed = []
    result = dict(
        changed=False,
        name=module.params["name"],
        organization=module.params["organization"],
        added_members=added_members,
        added_maintainers=added_maintainers,
        removed=removed,
    )

    if module.params["exclusive"] and module.params["state"] == "absent":
        module.fail_json(msg="using exclusive with state=absent is not supported")

    try:
        team = api.teams.get_by_name(module.params["name"])
    except github_helper.HTTPError as err:
        module.fail_json(msg=f"failed to look up team: {err}")

    try:
        members = list_members(api, team["slug"], "member")
        maintainers = list_members(api, team["slug"], "maintainer")

        for member in module.params["maintainers"]:
            if member not in maintainers and module.params["state"] == "present":
                added_maintainers.append(member)
                api.teams.add_or_update_membership_for_user_in_org(
                    team["slug"], member, "maintainer"
                )
            elif member in maintainers and module.params["state"] == "absent":
                removed.append(member)
                api.teams.remove_membership_for_user_in_org(team["slug"], member)
        for member in module.params["members"]:
            if member not in members and module.params["state"] == "present":
                added_members.append(member)
                api.teams.add_or_update_membership_for_user_in_org(
                    team["slug"], member, "member"
                )
            elif member in members and module.params["state"] == "absent":
                removed.append(member)
                api.teams.remove_membership_for_user_in_org(team["slug"], member)

        if module.params["exclusive"] and module.params["state"] == "present":
            for member in members:
                if member not in module.params["members"]:
                    removed.append(member)
                    api.teams.remove_membership_for_user_in_org(team["slug"], member)
            for member in maintainers:
                if member not in module.params["maintainers"]:
                    removed.append(member)
                    api.teams.remove_membership_for_user_in_org(team["slug"], member)

        # Update lists after changes

        members = list_members(api, team["slug"], "member")
        maintainers = list_members(api, team["slug"], "maintainer")

        result["members"] = members
        result["maintainers"] = maintainers
    except github_helper.HTTPError as err:
        module.fail_json(msg=f"failed to update team: {err}")

    result["changed"] = bool(removed or added_members or added_maintainers)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
