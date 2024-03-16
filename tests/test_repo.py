from client import AdoClient
from resources.repo import Repo
from resources.pull_requests import PullRequest
from resources.commits import Commit

import pytest

with open("tests/test_data.txt", "r", encoding="utf-8") as test_data:
    ado_org, ado_project, email, pat_token, *_ = test_data.read().splitlines()


class TestRepo:
    def setup_method(self) -> None:
        self.ado_client = AdoClient(email, pat_token, ado_org, ado_project)

    def test_from_request_payload(self) -> None:
        repo = Repo.from_request_payload({"id": "123", "name": "test-repo", "defaultBranch": "master"})
        assert isinstance(repo, Repo)
        assert repo.repo_id == "123"
        assert repo.name == "test-repo"
        assert repo.default_branch == "master"
        assert not repo.is_disabled
        assert repo.to_json() == Repo.from_json(repo.to_json()).to_json()

    def test_create_delete(self) -> None:
        repo = Repo.create(self.ado_client, "ado-api-test-repo-for-create-delete")
        assert repo.name == "ado-api-test-repo-for-create-delete"
        repo.delete(self.ado_client)

    def test_get_by_id(self) -> None:
        repo_created = Repo.create(self.ado_client, "ado-api-test-repo-for-get-by-id")
        repo = Repo.get_by_id(self.ado_client, repo_created.repo_id)
        assert repo.repo_id == repo_created.repo_id
        repo_created.delete(self.ado_client)

    def test_get_all(self) -> None:
        repos = Repo.get_all(self.ado_client)
        assert len(repos) > 10
        assert all(isinstance(repo, Repo) for repo in repos)

    def test_get_by_name(self) -> None:
        repo_created = Repo.create(self.ado_client, "ado-api-test-repo-for-get-by-name")
        repo = Repo.get_by_name(self.ado_client, "ado-api-test-repo-for-get-by-name")
        assert repo.name == repo_created.name
        assert repo.repo_id == repo_created.repo_id
        repo_created.delete(self.ado_client)

    def test_get_file(self) -> None:
        repo = Repo.create(self.ado_client, "ado-api-test-repo-for-get-file")
        Commit.create(self.ado_client, repo.repo_id, "main", "test-branch", {"read-this.txt": "Delete me!"}, "add", "Test commit")
        file = repo.get_file(self.ado_client, "README.md", "test-branch")
        assert len(file) > 5
        repo.delete(self.ado_client)

    def test_get_repo_contents(self) -> None:
        repo = Repo.create(self.ado_client, "ado-api-test-repo-for-get-repo-contents")
        Commit.create(self.ado_client, repo.repo_id, "main", "test-branch", {"test.txt": "Delete me!"}, "add", "Test commit")
        contents = repo.get_repo_contents(self.ado_client)
        assert len(contents.keys()) == 1
        assert isinstance(contents, dict)
        repo.delete(self.ado_client)

    def test_get_pull_requests(self) -> None:
        repo = Repo.create(self.ado_client, "ado-api-test-repo-for-get-pull-requests")
        Commit.create(self.ado_client, repo.repo_id, "main", "test-branch", {"test.txt": "This should be on the branch"}, "add", "Test commit")
        repo.create_pull_request(self.ado_client, "test-branch", "Test PR", "Test PR description")
        pull_requests = repo.get_all_pull_requests(self.ado_client, "all")
        assert len(pull_requests) == 1
        assert all(isinstance(pr, PullRequest) for pr in pull_requests)
        pull_requests[0].close(self.ado_client)
        repo.delete(self.ado_client)
