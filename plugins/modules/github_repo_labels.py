import ansible_collections.oddbit.github.plugins.module_utils.github_helper as github_helper
import ansible_collections.oddbit.github.plugins.module_utils.github_models as github_models


class Module(github_helper.GithubModule):
    def module_args(self):
        return dict(
            repo=dict(type="str", required=True),
            state=dict(type="str"),
            exclusive=dict(type="bool"),
            labels=dict(
                type="list",
                options=dict(
                    name=dict(type="str"),
                    description=dict(type="str"),
                    color=dict(type="str"),
                ),
            ),
        )

    def list_labels(self, reponame):
        return list(
            github_helper.flatten(
                self.api.issues.list_labels_for_repo,
                owner=reponame.owner,
                repo=reponame.name,
            )
        )

    def run(self):
        reponame = self.parse_repo_name(self.params["repo"])

        try:
            havelabels = github_models.LabelList.parse_obj(self.list_labels(reponame))
        except github_helper.HTTPError as err:
            self.fail_json(
                msg=f"failed to get labels from repository {reponame.fqrn}: {err}"
            )

        wantlabels = github_models.LabelList.parse_obj(self.params["labels"])
        added: list[dict] = []
        updated: list[dict] = []
        deleted: list[dict] = []

        results = {
            "repo": reponame.dict(),
            "changed": False,
            "labels": havelabels.list(),
            "added": added,
            "updated": updated,
            "deleted": deleted,
        }

        if self.params["state"] == "present":
            for label in wantlabels.__root__:
                have = next(
                    (x for x in havelabels.__root__ if x.name == label.name), None
                )
                if have is None:
                    added.append(label.dict())
                    try:
                        self.api.issues.create_label(
                            owner=reponame.owner, repo=reponame.name, **label.dict()
                        )
                    except github_helper.HTTPError as err:
                        self.fail_json(msg=f"failed to add label {label.name}: {err}")
                else:
                    want = github_models.Label(**(have.dict() | label.dict()))
                    if have != want:
                        updated.append(label.dict())
                        try:
                            self.api.issues.update_label(
                                owner=reponame.owner, repo=reponame.name, **want.dict()
                            )
                        except github_helper.HTTPError as err:
                            self.fail_json(
                                msg=f"failed to update label {label.name}: {err}"
                            )
            if self.params["exclusive"]:
                for label in havelabels.__root__:
                    have = next(
                        (x for x in wantlabels.__root__ if x.name == label.name), None
                    )
                    if have is None:
                        try:
                            deleted.append(label.dict())
                            self.api.issues.delete_label(
                                owner=reponame.owner,
                                repo=reponame.name,
                                name=label.name,
                            )
                        except github_helper.HTTPError as err:
                            self.fail_json(
                                msg=f"failed to delete label {label.name}: {err}"
                            )
        if self.params["state"] == "absent":
            for label in wantlabels.__root__:
                have = next(
                    (x for x in havelabels.__root__ if x.name == label.name), None
                )
                if have is not None:
                    try:
                        deleted.append(label.dict())
                        self.api.issues.delete_label(
                            owner=reponame.owner,
                            repo=reponame.name,
                            name=label.name,
                        )
                    except github_helper.HTTPError as err:
                        self.fail_json(
                            msg=f"failed to delete label {label.name}: {err}"
                        )

        results["changed"] = bool(added or updated or deleted)
        if results["changed"]:
            havelabels = github_models.LabelList.parse_obj(self.list_labels(reponame))
            results["labels"] = havelabels.list()

        self.exit_json(**results)


def main():
    Module().run()


if __name__ == "__main__":
    main()
