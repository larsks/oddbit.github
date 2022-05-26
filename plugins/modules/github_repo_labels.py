from ansible.module_utils.basic import AnsibleModule

import ansible_collections.oddbit.github.plugins.module_utils.github_helper as github_helper


def list_labels(api):
    return {
        label["name"]: {k: label[k] for k in ["name", "color", "description"]}
        for label in github_helper.flatten(api.issues.list_labels_for_repo)
    }


def main():
    module_args = github_helper.common_args()
    module_args.update(
        dict(
            repo=dict(type="str", required=True),
            state=dict(type="str", default="present", choices=["present", "absent"]),
            labels=dict(type="list", default=[]),
            exclusive=dict(type="bool", default=False),
        )
    )

    module = AnsibleModule(argument_spec=module_args)

    try:
        owner, repo = module.params["repo"].split("/")
    except ValueError:
        module.fail_json(msg="repo must be specified as owner/repo")

    api = github_helper.login(module, owner=owner, repo=repo)
    added = []
    removed = []
    modified = []
    result = dict(
        changed=False,
        repo=module.params["repo"],
        added=added,
        removed=removed,
        modified=modified,
    )

    if module.params["exclusive"] and module.params["state"] == "absent":
        module.fail_json(msg="using exclusive with state=absent is not supported")

    try:
        api.repos.get()
    except github_helper.HTTPError as err:
        module.fail_json(msg=f"failed to lookup repository: {err}")

    try:
        labels = list_labels(api)

        for label in module.params["labels"]:
            if "color" in label and label["color"].startswith("#"):
                label["color"] = label["color"][1:]

            if label["name"] not in labels and module.params["state"] == "present":
                added.append(label)
                api.issues.create_label(**label)
            elif label["name"] in labels and module.params["state"] == "present":
                if any(label[k] != labels[label["name"]][k] for k in label.keys()):
                    modified.append(label)
                    api.issues.update_label(**label)
            elif label["name"] in labels and module.params["state"] == "absent":
                removed.append(label)
                api.issues.delete_label(name=label["name"])

        if module.params["exclusive"] and module.params["state"] == "present":
            labelmap = {label["name"]: label for label in module.params["labels"]}
            for name, label in labels.items():
                if name not in labelmap:
                    removed.append(label)
                    api.issues.delete_label(name=name)

        labels = list_labels(api)
        result["labels"] = labels
    except github_helper.HTTPError as err:
        module.fail_json(msg=f"failed to update repository: {err}")

    result["changed"] = bool(added or removed or modified)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
