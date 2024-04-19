from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, TYPE_CHECKING

from ado_wrapper.state_managed_abc import StateManagedResource
from ado_wrapper.resources.users import Member
from ado_wrapper.utils import from_ado_date_string

if TYPE_CHECKING:
    from ado_wrapper.client import AdoClient

EnvironmentEditableAttribute = Literal["name", "description"]


# ====================================================================


@dataclass
class Environment(StateManagedResource):
    """https://learn.microsoft.com/en-us/rest/api/azure/devops/distributedtask/environments?view=azure-devops-rest-7.1"""

    environment_id: str = field(metadata={"is_id_field": True})
    name: str = field(metadata={"editable": True})
    description: str = field(metadata={"editable": True})
    resources: list[dict[str, Any]]  # This isn't used anywhere by ourselves, feel free to implement better logic.
    created_by: Member
    created_on: datetime
    modified_by: Member | None
    modified_on: datetime | None

    @classmethod
    def from_request_payload(cls, data: dict[str, Any]) -> Environment:
        return cls(
            str(data["id"]),
            data["name"],
            data["description"],
            data.get("resources", []),
            Member.from_request_payload(data["createdBy"]),
            from_ado_date_string(data["createdOn"]),
            Member.from_request_payload(data["modifiedOn"]) if data.get("modifiedBy") else None,
            from_ado_date_string(data.get("modifiedOn")),
        )

    @classmethod
    def get_by_id(cls, ado_client: AdoClient, environment_id: str) -> Environment:
        return super().get_by_url(
            ado_client,
            f"/{ado_client.ado_project}/_apis/distributedtask/environments/{environment_id}?api-version=7.1-preview.1",
        )  # type: ignore[return-value]

    @classmethod
    def create(cls, ado_client: AdoClient, name: str, description: str) -> Environment:  # type: ignore[override]
        return super().create(
            ado_client,
            f"/{ado_client.ado_project}/_apis/distributedtask/environments?api-version=7.1-preview.1",
            {"name": name, "description": description},
        )  # type: ignore[return-value]

    def update(self, ado_client: AdoClient, attribute_name: EnvironmentEditableAttribute, attribute_value: Any) -> None:  # type: ignore[override]
        return super().update(
            ado_client, "patch",
            f"/{ado_client.ado_project}/_apis/distributedtask/environments/{self.environment_id}?api-version=7.1-preview.1",
            attribute_name, attribute_value, {},  # fmt: skip
        )

    @classmethod
    def delete_by_id(cls, ado_client: AdoClient, environment_id: str) -> None:  # type: ignore[override]
        return super().delete_by_id(
            ado_client,
            f"/{ado_client.ado_project}/_apis/distributedtask/environments/{environment_id}?api-version=7.1-preview.1",
            environment_id,
        )

    @classmethod
    def get_all(cls, ado_client: AdoClient) -> list[Environment]:  # type: ignore[override]
        return super().get_all(
            ado_client,
            f"/{ado_client.ado_project}/_apis/distributedtask/environments?api-version=7.1-preview.1&$top=10000",
        )  # type: ignore[return-value]

    # # ============ End of requirement set by all state managed resources ================== #
    # # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
    # # =============== Start of additional methods included with class ===================== #

    @classmethod
    def get_by_name(cls, ado_client: AdoClient, name: str) -> Environment:
        return cls.get_by_abstract_filter(ado_client, lambda x: x.name == name)  # type: ignore[return-value, attr-defined]

    def get_pipeline_permissions(self, ado_client: AdoClient) -> dict[str, Any]:
        return PipelineAuthorisation.get_all_for_environment(ado_client, self.environment_id)  # type: ignore[return-value]

    def add_pipeline_permission(self, ado_client: AdoClient, pipeline_id: str) -> PipelineAuthorisation:
        return PipelineAuthorisation.create(ado_client, self.environment_id, pipeline_id)

@dataclass
class PipelineAuthorisation:
    pipeline_authorisation_id: str
    environment_id: str
    authorized: bool
    authorized_by: Member
    authorized_on: datetime

    @classmethod
    def from_request_payload(cls, data: dict[str, Any], environment_id: str) -> PipelineAuthorisation:
        return cls(
            str(data["id"]),
            environment_id,
            data["authorized"],
            Member.from_request_payload(data["authorizedBy"]),
            from_ado_date_string(data["authorizedOn"]),
        )

    @classmethod
    def get_all_for_environment(cls, ado_client: AdoClient, environment_id: str) -> list[PipelineAuthorisation]:  # type: ignore[override]
        request = ado_client.session.get(
            f"https://dev.azure.com/{ado_client.ado_org}/{ado_client.ado_project_id}/_apis/pipelines/pipelinePermissions/environment/{environment_id}",
        ).json()
        return [cls.from_request_payload(x, request["resource"]["id"]) for x in request["pipelines"]]

    @classmethod
    def create(cls, ado_client: AdoClient, environment_id: str, pipeline_id: str, authorized: bool=True) -> PipelineAuthorisation:
        all_existing = cls.get_all_for_environment(ado_client, environment_id)
        payload = {"pipelines": [{"id": x.pipeline_authorisation_id, "authorized": True} for x in all_existing]}
        payload["pipelines"] = [x for x in payload["pipelines"] if x["id"] != pipeline_id]  # Remove existing entry if it exists
        payload["pipelines"].append({"id": pipeline_id, "authorized": authorized})
        payload |= {"resource": {"type": "environment", "id": environment_id}}

        request = ado_client.session.patch(
            f"https://dev.azure.com/{ado_client.ado_org}/{ado_client.ado_project_id}/_apis/pipelines/pipelinePermissions/environment/{environment_id}?api-version=7.1-preview.1",
            json=payload,
        )
        if request.status_code == 404:
            raise ValueError(f"Pipeline {pipeline_id} not found.")
        created_pipeline_dict = max(request.json()["pipelines"], key=lambda x: x["authorizedOn"])
        return cls.from_request_payload(created_pipeline_dict, environment_id)

    def update(self, ado_client: AdoClient, authorized: bool) -> None:  # type: ignore[override]
        self.delete_by_id(ado_client, self.environment_id, self.pipeline_authorisation_id)
        new = self.create(ado_client, self.environment_id, self.pipeline_authorisation_id, authorized)
        self.__dict__.update(new.__dict__)

    @classmethod
    def delete_by_id(cls, ado_client: AdoClient, environment_id: str, pipeline_authorisation_id: str) -> None:
        cls.create(ado_client, environment_id, pipeline_authorisation_id, False)