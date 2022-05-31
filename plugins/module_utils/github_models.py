import pydantic

from enum import Enum


class StateEnum(str, Enum):
    present = "present"
    absent = "absent"


class TeamPrivacyEnum(str, Enum):
    closed = "closed"
    secret = "secret"


class CollaboratorPermissionsEnum(str, Enum):
    pull = "pull"
    traige = "traige"
    push = "push"
    maintain = "maintain"
    admin = "admin"
    read = "read"  # alias for pull
    write = "write"  # alias for push


class BaseModel(pydantic.BaseModel):
    class Config:
        use_enum_values = True
        allow_population_by_field_name = True

    def dict(self, **kwargs):
        kwargs = {"exclude_defaults": True, "exclude_unset": True} | kwargs
        return super().dict(**kwargs)  # type: ignore

    def json(self, **kwargs):
        kwargs = {"exclude_defaults": True, "exclude_unset": True} | kwargs
        return super().json(**kwargs)  # type: ignore


class Label(BaseModel):
    name: str
    description: str | None
    color: str | None

    @pydantic.validator("color")
    def validate_color(cls, v):
        if v.startswith("#"):
            v = v[1:]

        return v


class LabelList(BaseModel):
    __root__: list[Label]

    def has(self, name):
        return any(label.name == name for label in self.__root__)

    def get(self, name):
        try:
            return next(label for label in self.__root__ if label.name == name)
        except StopIteration:
            return None

    def list(self):
        return [label.dict() for label in self.__root__]


class User(BaseModel):
    login: str
    name: str | None
    email: str | None


class TeamRequest(BaseModel):
    name: str
    description: str | None
    privacy: TeamPrivacyEnum | None


class Team(BaseModel):
    name: str | None
    team_slug: str | None = pydantic.Field(alias="slug")
    description: str | None
    privacy: TeamPrivacyEnum

    @classmethod
    def fromTeamRequest(cls, tr):
        return cls(
            name=tr.name,
            description=tr.description,
            privacy=tr.privacy,
        )


class CollaboratorPermissionsMap(BaseModel):
    pull: bool = pydantic.Field(default=False)
    push: bool = pydantic.Field(default=False)
    triage: bool = pydantic.Field(default=False)
    maintain: bool = pydantic.Field(default=False)
    admin: bool = pydantic.Field(default=False)

    @classmethod
    def fromPerms(cls, *perms):
        return cls(**{k: True for k in perms})


class CollaboratorListResponse(BaseModel):
    login: str
    permissions: CollaboratorPermissionsMap
    role_name: CollaboratorPermissionsEnum


class CollaboratorList(BaseModel):
    __root__: list[CollaboratorListResponse]


permNameToMap = {
    "pull": CollaboratorPermissionsMap.fromPerms("pull"),
    "triage": CollaboratorPermissionsMap.fromPerms("pull", "triage"),
    "push": CollaboratorPermissionsMap.fromPerms("pull", "triage", "push"),
    "maintain": CollaboratorPermissionsMap.fromPerms(
        "pull", "triage", "push", "maintain"
    ),
    "admin": CollaboratorPermissionsMap.fromPerms(
        "pull", "triage", "push", "maintain", "admin"
    ),
}


class RepositoryName(BaseModel):
    owner: str
    name: str
    org: str | None

    @property
    def fqrn(self):
        return f"{self.owner}/{self.name}"


class RepositoryCreateRequest(BaseModel):
    private: bool | None
    description: str | None
    homepage: str | None
    has_issues: bool | None
    has_projects: bool | None
    has_wiki: bool | None
    auto_init: bool | None
    gitignore_template: str | None
    license_template: str | None
    allow_squash_merge: bool | None
    allow_merge_commit: bool | None
    allow_rebase_merge: bool | None
    allow_auto_merge: bool | None
    delete_branch_on_merge: bool | None


class ModuleCommonParameters(BaseModel):
    github_token: str
    github_url: str | None
