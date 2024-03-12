import requests

from main import AdoClient


class Branch:
    def __init__(self, branch_id: str, name: str, is_main: bool, is_protected: bool, is_deleted: bool) -> None:
        self.branch_id = branch_id
        self.name = name
        self.is_main = is_main
        self.is_protected = is_protected
        self.is_deleted = is_deleted

    def __repr__(self) -> str:
        return f"Branch(name={self.name}, id={self.branch_id}, is_main={self.is_main}, is_protected={self.is_protected}, is_deleted={self.is_deleted})"

    def __str__(self) -> str:
        return f"Branch(name={self.name}, id={self.branch_id}, is_main={self.is_main}, is_protected={self.is_protected}, is_deleted={self.is_deleted})"

    @classmethod
    def from_json(cls, branch_response: dict[str, str]) -> "Branch":
        return cls(branch_response["objectId"], branch_response["name"], bool(branch_response.get("isMain", False)),
                   bool(branch_response.get("isProtected", False)), bool(branch_response.get("isDeleted")))  # fmt: skip

    @classmethod
    def get_all(cls, ado_client: AdoClient, repo_id: str) -> list["Branch"]:
        request = requests.get(
            f"https://dev.azure.com/{ado_client.ado_org}/{ado_client.ado_project}/_apis/git/repositories/{repo_id}/refs?filter=heads&api-version=7.1",
            auth=ado_client.auth,
        ).json()
        return [cls.from_json(branch) for branch in request["value"]]

    @classmethod
    def get_by_id(cls, ado_client: AdoClient, repo_id: str, branch_id: str) -> "Branch":
        for branch in cls.get_all(ado_client, repo_id):
            if branch.branch_id == branch_id:
                return branch
        raise ValueError(f"Branch {branch_id} not found")

    @classmethod
    def get_by_name(cls, ado_client: AdoClient, repo_id: str, branch_name: str) -> "Branch":
        for branch in cls.get_all(ado_client, repo_id):
            if branch.name == branch_name:
                return branch
        raise ValueError(f"Branch {branch_name} not found")

    @classmethod
    def get_main_branch(cls, ado_client: AdoClient, repo_id: str) -> "Branch":  # type: ignore[return]
        for branch in cls.get_all(ado_client, repo_id):
            if branch.is_main:
                return branch

    @classmethod
    def get_protected_branches(cls, ado_client: AdoClient, repo_id: str) -> list["Branch"]:
        return [branch for branch in cls.get_all(ado_client, repo_id) if branch.is_protected]

    @classmethod
    def get_deleted_branches(cls, ado_client: AdoClient, repo_id: str) -> list["Branch"]:
        return [branch for branch in cls.get_all(ado_client, repo_id) if branch.is_deleted]

    @classmethod
    def get_unprotected_branches(cls, ado_client: AdoClient, repo_id: str) -> list["Branch"]:
        return [branch for branch in cls.get_all(ado_client, repo_id) if not branch.is_protected]

    @classmethod
    def get_active_branches(cls, ado_client: AdoClient, repo_id: str) -> list["Branch"]:
        return [branch for branch in cls.get_all(ado_client, repo_id) if not branch.is_deleted]

    @classmethod
    def create(cls, ado_client: AdoClient, repo_id: str, branch_name: str, source_branch: str) -> "Branch":
        data = {
            "name": branch_name,
            "ref": f"refs/heads/{source_branch}",
        }
        request = requests.post(
            f"https://dev.azure.com/{ado_client.ado_org}/{ado_client.ado_project}/_apis/git/repositories/{repo_id}/refs?api-version=7.1",
            json=data,
            auth=ado_client.auth,
        ).json()
        return cls.from_json(request)

    def delete(self, ado_client: AdoClient, repo_id: str) -> None:
        request = requests.delete(
            f"https://dev.azure.com/{ado_client.ado_org}/{ado_client.ado_project}/_apis/git/repositories/{repo_id}/refs/{self.branch_id}?api-version=7.1",
            auth=ado_client.auth,
        )
        assert request.status_code < 300

if __name__ == "__main__":
    from secret import email, ado_access_token, ado_org, ado_project, ALTERNATIVE_EXISTING_REPO_NAME
    from repository import Repo

    ado_client = AdoClient(email, ado_access_token, ado_org, ado_project)
    repo = Repo.get_by_name(ado_client, ALTERNATIVE_EXISTING_REPO_NAME)
    # branches = Branch.get_all(ado_client, repo.repo_id)
