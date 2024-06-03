from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal

from ado_wrapper.utils import from_ado_date_string, to_iso, InvalidPermissionError

if TYPE_CHECKING:
    from ado_wrapper.client import AdoClient


AuthenticationMechanismType = None | Literal["", "AAD", "AAD_Cookie", "SSH", "S2S_ServicePrincipal"
                                             "SessionToken_Unscoped authorizationId: <id>", "PAT_Unscoped authorizationId: <id>"]
AreaType = Literal['Auditing', 'Checks', 'Git', 'Group', 'Library', 'Licensing', 'Permissions',
                   'Pipelines', 'Policy', 'Process', 'Project', 'Release']
CategoryType = Literal["access", "create", "execute", "modify", "remove", "unknown"]
CategoryDisplayNameType = Literal['Access', 'Create', 'Execute', 'Modify', "Remove", "Unknown"]
ScopeTypeType = Literal["deployment", "enterprise", "organization", "project", "unknown"]


@dataclass
class AuditLog:
    """https://learn.microsoft.com/en-us/rest/api/azure/devops/audit/audit-log/query?view=azure-devops-rest-7.1&tabs=HTTP"""
    audit_log_id: str = field(repr=False)
    correlation_id: str = field(repr=False)  # For grouping logs, e.g. if one action creates 5 logs
    activity_id: str = field(repr=False)  # List of 32 char UUIDs
    actor_user_id: str = field(repr=False)
    actor_client_id: str = field(repr=False)
    actor_UPN: str = field(repr=False)  # User Principal Name (most likely email)
    authentication_mechanism: AuthenticationMechanismType = field(repr=False)
    created_on: datetime
    scope_type: ScopeTypeType
    scope_display_name: str = field(repr=False)  # E.g. `<org_name> (Organisation)`
    scope_id: str = field(repr=False)  # E.g. `<org_id>`
    project_id: str = field(repr=False)
    project_name: str = field(repr=False)
    ip_address: str | None = field(repr=False)  # octed.octed.octed.octed or MAC addresses
    user_agent: str = field(repr=False)
    action_id: str  # The action id for the event, i.e Git.CreateRepo, Project.RenameProject, Library.AgentAdded
    details: str = field(repr=False)
    area: AreaType
    category: CategoryType
    category_display_name: CategoryDisplayNameType
    actor_display_name: str  # E.g. First Last
    data: dict[str, str]  # External data such as CUIDs, item names, etc.

    @classmethod
    def from_request_payload(cls, data: dict[str, Any]) -> AuditLog:
        return cls(
            data["id"], data["correlationId"], data["activityId"], data["actorUserId"],
            data["actorClientId"], data["actorUPN"], data["authenticationMechanism"],
            from_ado_date_string(data["timestamp"]), data["scopeType"], data["scopeDisplayName"],
            data["scopeId"], data["projectId"], data["projectName"], data["ipAddress"], data["userAgent"],
            data["actionId"], data["details"], data["area"], data["category"], data["categoryDisplayName"],
            data["actorDisplayName"], data["data"]
        )

    @classmethod
    def get_all(cls, ado_client: AdoClient, start_time: datetime | None = None, end_time: datetime = datetime.now()) -> list[AuditLog]:
        """ https://learn.microsoft.com/en-us/rest/api/azure/devops/audit/audit-log/query?view=azure-devops-rest-7.1&tabs=HTTP#auditlogqueryresult """
        if start_time is None:
            start_time = datetime.now() - timedelta(days=1)
        assert start_time <= end_time, "Start time must be before end time!"
        combined_entries = []
        has_more = True
        continuation_token = None
        while has_more:
            data = ado_client.session.get(
                f"https://auditservice.dev.azure.com/{ado_client.ado_org}/_apis/audit/auditlog?batchSize=100000&startTime={to_iso(start_time)}&endTime={to_iso(end_time)}{f'&continuationToken={continuation_token}' if continuation_token else ''}&api-version=7.1-preview.1",
            )
            if data.status_code == 403:
                raise InvalidPermissionError("You have insufficient perms to use this function, it requires 'View audit log'")
            json_data = data.json()
            has_more = json_data["hasMore"]
            continuation_token = json_data["continuationToken"]
            combined_entries.extend(json_data["decoratedAuditLogEntries"])
        return [cls.from_request_payload(x) for x in combined_entries]

    @classmethod
    def get_all_by_area(cls, ado_client: AdoClient, area_type: AreaType, start_time: datetime | None = None, end_time: datetime = datetime.now()) -> list[AuditLog]:
        return [x for x in cls.get_all(ado_client, start_time, end_time) if x.area == area_type]

    @classmethod
    def get_all_by_category(cls, ado_client: AdoClient, category: CategoryType, start_time: datetime | None = None, end_time: datetime = datetime.now()) -> list[AuditLog]:
        return [x for x in cls.get_all(ado_client, start_time, end_time) if x.category == category]

    @classmethod
    def get_all_by_scope_type(cls, ado_client: AdoClient, scope_type: ScopeTypeType, start_time: datetime | None = None, end_time: datetime = datetime.now()) -> list[AuditLog]:
        return [x for x in cls.get_all(ado_client, start_time, end_time) if x.scope_type == scope_type]
