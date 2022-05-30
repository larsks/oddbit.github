import ansible_collections.oddbit.github.plugins.module_utils.github_helper as github_helper
import ansible_collections.oddbit.github.plugins.module_utils.github_models as github_models


class Module(github_helper.GithubModule):
    class Model(github_models.ModuleCommonParameters):
        state: github_models.StateEnum
        name: str
        repository: github_models.RepositoryCreateRequest

    def module_args(self):
        return dict(
            state=dict(type="str"),
            name=dict(type="str"),
            repository=dict(type="dict"),
        )

    def run(self):
        reponame = self.parse_repo_name(self.data.name)

        # check if repository exists
        try:
            repo = self.api.repos.get(owner=reponame.owner, repo=reponame.name)
        except github_helper.HTTP404NotFoundError:
            repo = {}
            exists = False
        except github_helper.HTTPError as err:
            self.fail_json(msg=f"failed to access repository {reponame.fqrn}: {err}")
        else:
            exists = True

        results = {"changed": False, "exists": exists, "name": reponame.dict()}

        if exists and self.data.state == "present":
            results["op"] = "update"
            have = github_models.RepositoryCreateRequest(**repo)
            patch = github_models.RepositoryCreateRequest(
                **{**have.dict(), **self.data.repository.dict()}
            )
            if patch != have:
                results["changed"] = True
                try:
                    repo = self.api.repos.update(
                        owner=reponame.owner, repo=reponame.name, **patch.dict()
                    )
                except github_helper.HTTPError as err:
                    self.fail_json(
                        msg=f"failed to update repository {reponame.fqrn}: {err}"
                    )
        elif not exists and self.data.state == "present":
            results["op"] = "create"
            results["changed"] = True

            if reponame.org:
                createfunc = self.api.repos.create_in_org
            else:
                createfunc = self.api.repos.create_for_authenticated_user
            try:
                repo = createfunc(
                    owner=reponame.owner,
                    name=reponame.name,
                    org=reponame.org,
                    **self.data.repository.dict(),
                )
            except github_helper.HTTPError as err:
                self.fail_json(
                    msg=f"failed to create repository {reponame.fqrn}: {err}"
                )
        elif exists and self.data.state == "absent":
            results["op"] = "delete"
            results["changed"] = True
            try:
                self.api.repos.delete(owner=reponame.owner, repo=reponame.name)
            except github_helper.HTTPError as err:
                self.fail_json(
                    msg=f"failed to delete repository {reponame.fqrn}: {err}"
                )

        results["github"] = {"repo": repo}
        self.exit_json(**results)


def main():
    Module().run()


if __name__ == "__main__":
    main()
