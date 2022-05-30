from ansible.module_utils.basic import AnsibleModule

import ansible_collections.oddbit.github.plugins.module_utils.github_helper as github_helper


def main():
    module_args_attrs = dict(
        name=dict(type="str", required=True),
        description=dict(type="str"),
        private=dict(type="bool", default=False),
        visibility=dict(type="str", choices=["public", "private", "internal"]),
        has_issues=dict(type="bool", default=True),
        has_projects=dict(type="bool", default=True),
        has_wiki=dict(type="bool", default=True),
        allow_squash_merge=dict(type="bool", default=True),
        allow_merge_commit=dict(type="bool", default=True),
        allow_rebase_merge=dict(type="bool", default=True),
        allow_auto_merge=dict(type="bool", default=False),
        delete_branch_on_merge=dict(type="bool", default=False),
    )
    module_args = github_helper.common_args()
    module_args.update(
        dict(
            organization=dict(type="str"),
            state=dict(type="str", default="present", choices=["present", "absent"]),
        )
    )
    module_args.update(module_args_attrs)

    module = AnsibleModule(argument_spec=module_args)

    try:
        if module.params.get("organization"):
            org = module.params["organization"]
            api = github_helper.login(module, org=org, owner=org)
        else:
            api = github_helper.login(module)
            authuser = api.users.get_authenticated()

            # create a new api object with the username inserted in
            # useful places.
            api = github_helper.login(
                module, owner=authuser["login"], username=authuser["login"]
            )
    except github_helper.HTTPError as err:
        module.fail_json(msg=f"failed to connect to api: {err}")

    result = dict(
        changed=False,
        organization=module.params["organization"],
        name=module.params["name"],
    )

    try:
        result["repo"] = api.repos.get(module.params["name"])
    except github_helper.HTTP404NotFoundError:
        repo_exists = False
    except github_helper.HTTPError as err:
        module.fail_json(msg=f"failed to lookup repository: {err}")
    else:
        repo_exists = True

    result["repo_exists"] = repo_exists

    try:
        if not repo_exists and module.params["state"] == "present":
            if module.params.get("organization"):
                createfunc = api.repos.create_in_org
            else:
                createfunc = api.repos.create_for_authenticated_user

            result["repo"] = createfunc(
                **{
                    k: v
                    for k, v in module.params.items()
                    if k not in ["organization", "state"]
                },
            )
        elif repo_exists and module.params["state"] == "present":
            patch = github_helper.patch(result["repo"], module.params)
            if patch:
                result["changed"] = True
                api.repos.update(repo=module.params["name"], **patch)
        elif repo_exists and module.params["state"] == "absent":
            result["changed"] = True
            api.repos.delete(repo=module.params["name"])
    except github_helper.HTTPError as err:
        module.fail_json(msg=f"failed to update repository: {err}")

    module.exit_json(**result)


if __name__ == "__main__":
    main()
