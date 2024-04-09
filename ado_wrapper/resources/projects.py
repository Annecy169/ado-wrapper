from __future__ import annotations

from typing import Any, TYPE_CHECKING
from datetime import datetime
from dataclasses import dataclass, field

from ado_wrapper.state_managed_abc import StateManagedResource

if TYPE_CHECKING:
    from ado_wrapper.client import AdoClient


@dataclass
class Project(StateManagedResource):
    "https://learn.microsoft.com/en-us/rest/api/azure/devops/core/projects?view=azure-devops-rest-7.1"
    project_id: str = field(metadata={"is_id_field": True})  # None are editable
    name: str
    description: str
    last_update_time: datetime | None = None

    @classmethod
    def from_request_payload(cls, data: dict[str, Any]) -> "Project":
        return cls(data["id"], data["name"], data.get("description", ""), data.get("lastUpdateTime"))

    @classmethod
    def get_by_id(cls, ado_client: AdoClient, project_id: str) -> "Project":
        return super().get_by_url(
            ado_client,
            f"/_apis/projects/{project_id}?api-version=7.1",
        )  # type: ignore[return-value]

    @classmethod
    def create(cls, ado_client: AdoClient, project_name: str, project_description: str) -> "Project":  # type: ignore[override]
        raise NotImplementedError

    @staticmethod
    def delete_by_id(ado_client: AdoClient, project_id: str) -> None:  # type: ignore[override]
        raise NotImplementedError

    @classmethod
    def get_all(cls, ado_client: AdoClient) -> list["Project"]:  # type: ignore[override]
        return super().get_all(
            ado_client,
            "/_apis/projects?api-version=7.1",
        )  # type: ignore[return-value]

    # ============ End of requirement set by all state managed resources ================== #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
    # =============== Start of additional methods included with class ===================== #

    @classmethod
    def get_by_name(cls, ado_client: AdoClient, project_name: str) -> "Project | None":
        return cls.get_by_abstract_filter(ado_client, lambda project: project.name == project_name)  # type: ignore[return-value, attr-defined]
