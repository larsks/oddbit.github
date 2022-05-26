from ansible.module_utils.basic import AnsibleModule

import ansible_collections.oddbit.github.plugins.module_utils.github_helper as github_helper


def main():
    module_args = github_helper.common_args()
    module_args.update(
        dict(
            description=dict(type="str"),
            name=dict(type="str", required=True),
            organization=dict(type="str", required=True),
            privacy=dict(type="str", default="closed", choices=["closed", "secret"]),
            state=dict(type="str", default="present", choices=["present", "absent"]),
            parent_team=dict(type="str"),
        )
    )

    module = AnsibleModule(argument_spec=module_args)
    api = github_helper.login(module, org=module.params["organization"])
    result = dict(
        changed=False,
        name=module.params["name"],
        organization=module.params["organization"],
    )

    try:
        team = api.teams.get_by_name(module.params["name"])
    except github_helper.HTTP404NotFoundError:
        team_exists = False
    except github_helper.HTTPError as err:
        module.fail_json(msg=str(err))
    else:
        team_exists = True

    try:
        if module.params["state"] == "present" and not team_exists:
            team = api.teams.create(
                module.params["name"],
                privacy=module.params.get("privacy"),
                description=module.params.get("description"),
            )
            result["changed"] = True
            result["team"] = team
        elif module.params["state"] == "present" and team_exists:
            team = api.teams.get_by_name(module.params["name"])
            result["team"] = team
            patch = {}
            for attr in ["privacy", "description"]:
                if team[attr] != module.params[attr]:
                    patch[attr] = module.params[attr]

            if patch:
                result["changed"] = True
                team = api.teams.update_in_org(module.params["name"], **patch)
        elif module.params["state"] == "absent" and team_exists:
            api.teams.delete_in_org(module.params["name"])
            result["team"] = team
            result["changed"] = True
    except github_helper.HTTPError as err:
        module.fail_json(msg=str(err))

    module.exit_json(**result)


if __name__ == "__main__":
    main()
