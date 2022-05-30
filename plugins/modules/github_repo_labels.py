import ansible_collections.oddbit.github.plugins.module_utils.github_helper as github_helper
import ansible_collections.oddbit.github.plugins.module_utils.github_models as github_models


class Module(github_helper.GithubModule):
    class Model(github_models.ModuleCommonParameters):
        state: github_models.StateEnum
        repo: str
        exclusive: bool | None = github_models.pydantic.Field(default=False)
        labels: github_models.LabelList

    def module_args(self):
        return dict(
            repo=dict(type="str", required=True),
            state=dict(type="str"),
            exclusive=dict(type="bool"),
            labels=dict(type="list"),
        )

    def list_labels(self, reponame):
        repolabels = github_models.LabelList.parse_obj(
            list(
                github_helper.flatten(
                    self.api.issues.list_labels_for_repo,
                    owner=reponame.owner,
                    repo=reponame.name,
                )
            )
        )

        return repolabels

    def run(self):
        reponame = self.parse_repo_name(self.data.repo)

        try:
            repolabels = self.list_labels(reponame)
        except github_helper.HTTPError as err:
            self.fail_json(
                msg=f"failed to get labels from repository {reponame.fqrn}: {err}"
            )

        added: list[github_models.Label] = []
        updated: list[github_models.Label] = []
        deleted: list[github_models.Label] = []

        results = {
            "repo": reponame.dict(),
            "changed": False,
            "github": {"labels": repolabels.list()},
            "added": added,
            "updated": updated,
            "deleted": deleted,
        }

        if self.data.state == "present":
            for label in self.data.labels.__root__:
                have = repolabels.get(label.name)

                if have is None or have != label:
                    if have is None:
                        added.append(label.dict())
                    else:
                        updated.append(label.dict())

                    try:
                        self.api.issues.create_label(
                            owner=reponame.owner, repo=reponame.name, **label.dict()
                        )
                    except github_helper.HTTPError as err:
                        self.fail_json(
                            msg=f"failed to update label {label.name} in repository {reponame.fqrn}: {err}"
                        )
            if self.data.exclusive:
                for label in repolabels.__root__:
                    if not self.data.labels.has(label.name):
                        deleted.append(label.dict())
                        self.api.issues.delete_label(
                            owner=reponame.owner, repo=reponame.name, name=label.name
                        )
        elif self.data.state == "absent":
            for label in self.data.labels:
                if repolabels.has(label.name):
                    deleted.append(label.dict())
                    self.api.issues.delete_label(
                        owner=reponame.owner, repo=reponame.name, name=label.name
                    )

        results["changed"] = bool(added or updated or deleted)
        if results["changed"]:
            results["github"]["labels"] = self.list_labels(reponame).list()
        self.exit_json(**results)


def main():
    Module().run()


if __name__ == "__main__":
    main()
