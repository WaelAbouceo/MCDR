from enum import StrEnum


class Resource(StrEnum):
    CASE = "case"
    CALL = "call"
    CUSTOMER = "customer"
    USER = "user"
    SLA = "sla"
    ESCALATION = "escalation"
    QA = "qa"
    AUDIT = "audit"
    REPORT = "report"
    APPROVAL = "approval"


class Action(StrEnum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    ESCALATE = "escalate"
    EVALUATE = "evaluate"
    EXPORT = "export"


ROLE_PERMISSIONS: dict[str, set[tuple[Resource, Action]]] = {
    "agent": {
        (Resource.CASE, Action.CREATE),
        (Resource.CASE, Action.READ),
        (Resource.CASE, Action.UPDATE),
        (Resource.CALL, Action.READ),
        (Resource.CUSTOMER, Action.READ),
        (Resource.ESCALATION, Action.ESCALATE),
        (Resource.QA, Action.READ),
        (Resource.APPROVAL, Action.CREATE),
        (Resource.APPROVAL, Action.READ),
    },
    "senior_agent": {
        (Resource.CASE, Action.CREATE),
        (Resource.CASE, Action.READ),
        (Resource.CASE, Action.UPDATE),
        (Resource.CALL, Action.READ),
        (Resource.CUSTOMER, Action.READ),
        (Resource.ESCALATION, Action.ESCALATE),
        (Resource.ESCALATION, Action.READ),
        (Resource.SLA, Action.READ),
        (Resource.REPORT, Action.READ),
        (Resource.QA, Action.READ),
        (Resource.APPROVAL, Action.CREATE),
        (Resource.APPROVAL, Action.READ),
    },
    "team_lead": {
        (Resource.CASE, Action.CREATE),
        (Resource.CASE, Action.READ),
        (Resource.CASE, Action.UPDATE),
        (Resource.CALL, Action.READ),
        (Resource.CUSTOMER, Action.READ),
        (Resource.ESCALATION, Action.ESCALATE),
        (Resource.ESCALATION, Action.READ),
        (Resource.REPORT, Action.READ),
        (Resource.USER, Action.READ),
        (Resource.SLA, Action.READ),
        (Resource.QA, Action.READ),
        (Resource.APPROVAL, Action.CREATE),
        (Resource.APPROVAL, Action.READ),
        (Resource.APPROVAL, Action.UPDATE),
    },
    "supervisor": {
        (Resource.CASE, Action.CREATE),
        (Resource.CASE, Action.READ),
        (Resource.CASE, Action.UPDATE),
        (Resource.CALL, Action.READ),
        (Resource.CUSTOMER, Action.READ),
        (Resource.ESCALATION, Action.ESCALATE),
        (Resource.ESCALATION, Action.READ),
        (Resource.REPORT, Action.READ),
        (Resource.REPORT, Action.EXPORT),
        (Resource.USER, Action.READ),
        (Resource.SLA, Action.READ),
        (Resource.QA, Action.READ),
        (Resource.APPROVAL, Action.READ),
        (Resource.APPROVAL, Action.UPDATE),
    },
    "qa_analyst": {
        (Resource.CASE, Action.READ),
        (Resource.CASE, Action.UPDATE),
        (Resource.CALL, Action.READ),
        (Resource.CUSTOMER, Action.READ),
        (Resource.ESCALATION, Action.READ),
        (Resource.SLA, Action.READ),
        (Resource.QA, Action.READ),
        (Resource.QA, Action.EVALUATE),
        (Resource.REPORT, Action.READ),
    },
    "admin": {
        (r, a) for r in Resource for a in Action
    },
}

FIELD_MASKS: dict[str, dict[str, list[str]]] = {
    "agent": {
        "customer": ["id", "name", "phone_number", "account_tier"],
    },
    "senior_agent": {
        "customer": ["id", "name", "phone_number", "account_tier"],
    },
    "team_lead": {
        "customer": ["id", "name", "phone_number", "account_number", "account_tier"],
    },
    "supervisor": {
        "customer": ["id", "name", "phone_number", "account_number", "account_tier"],
    },
    "qa_analyst": {
        "customer": ["id", "name", "phone_number", "account_tier"],
    },
    "admin": {},
}
