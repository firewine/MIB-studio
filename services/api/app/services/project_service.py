from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, delete, select
from sqlalchemy.orm import Session

from services.api.app.core.errors import APIError
from services.api.app.schemas.project import ProjectCreate, ProjectPage, ProjectPatch, ProjectRead, RouteInput, RouteRead
from services.shared.db.models import AgentPackage, Benchmark, Dataset, EvalSet, Job, ModelRun, Preset, Project, ProjectRoute


def utc_now() -> str:
    return format_timestamp(datetime.now(UTC))


def format_timestamp(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def new_id() -> str:
    return uuid.uuid4().hex


class ProjectService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_project(self, data: ProjectCreate) -> ProjectRead:
        if self.session.get(Preset, data.preset_id) is None:
            raise APIError(
                "PRESET_NOT_FOUND",
                "Preset does not exist.",
                status_code=404,
                details={"preset_id": data.preset_id},
            )

        now_dt = datetime.now(UTC)
        now = format_timestamp(now_dt)
        project = Project(
            id=new_id(),
            name=data.name,
            preset_id=data.preset_id,
            created_at=now,
            updated_at=now,
        )
        self.session.add(project)
        self.session.flush()
        self._replace_routes(project.id, data.routes, start=now_dt)
        self.session.flush()
        return self._read_project(project)

    def list_projects(self, *, cursor: str | None = None, limit: int = 50, include_archived: bool = False) -> ProjectPage:
        statement: Select[tuple[Project]] = select(Project)
        if not include_archived:
            statement = statement.where(Project.archived_at.is_(None))
        if cursor:
            statement = statement.where(Project.id > cursor)
        statement = statement.order_by(Project.updated_at.desc(), Project.id).limit(limit + 1)
        projects = list(self.session.scalars(statement))
        next_cursor = projects[-1].id if len(projects) > limit else None
        return ProjectPage(items=[self._read_project(project) for project in projects[:limit]], next_cursor=next_cursor)

    def get_project(self, project_id: str) -> ProjectRead:
        return self._read_project(self._project_or_404(project_id))

    def patch_project(self, project_id: str, data: ProjectPatch) -> ProjectRead:
        project = self._project_or_404(project_id)
        self._raise_if_archived(project)
        now_dt = datetime.now(UTC)
        now = format_timestamp(now_dt)
        if data.name is not None:
            project.name = data.name
        if data.routes is not None:
            locked_by = self._route_locking_resource(project.id)
            if locked_by is not None:
                resource_type, resource_id = locked_by
                raise APIError(
                    "ROUTE_TAXONOMY_LOCKED",
                    "Project routes cannot be changed after dependent resources exist.",
                    status_code=409,
                    details={
                        "project_id": project.id,
                        "locked_by_resource_type": resource_type,
                        "locked_by_resource_id": resource_id,
                    },
                )
            self._replace_routes(project.id, data.routes, start=now_dt)
        project.updated_at = now
        self.session.flush()
        return self._read_project(project)

    def archive_project(self, project_id: str) -> None:
        project = self._project_or_404(project_id)
        self._raise_if_archived(project)
        now = utc_now()
        project.archived_at = now
        project.updated_at = now
        self.session.flush()

    def _project_or_404(self, project_id: str) -> Project:
        project = self.session.get(Project, project_id)
        if project is None:
            raise APIError("PROJECT_NOT_FOUND", "Project does not exist.", status_code=404, details={"project_id": project_id})
        return project

    def _raise_if_archived(self, project: Project) -> None:
        if project.archived_at is not None:
            raise APIError(
                "PROJECT_ARCHIVED",
                "Archived projects are read-only.",
                status_code=409,
                details={"project_id": project.id},
            )

    def _replace_routes(self, project_id: str, routes: list[RouteInput], *, start: datetime) -> None:
        self.session.execute(delete(ProjectRoute).where(ProjectRoute.project_id == project_id))
        for index, route in enumerate(routes):
            self.session.add(
                ProjectRoute(
                    id=new_id(),
                    project_id=project_id,
                    route_id=route.route_id,
                    description=route.description,
                    is_unsafe=1 if route.is_unsafe else 0,
                    created_at=format_timestamp(start + timedelta(milliseconds=index)),
                )
            )

    def _routes_for_project(self, project_id: str) -> list[ProjectRoute]:
        statement = (
            select(ProjectRoute)
            .where(ProjectRoute.project_id == project_id)
            .order_by(ProjectRoute.created_at.asc(), ProjectRoute.id.asc())
        )
        return list(self.session.scalars(statement))

    def _read_project(self, project: Project) -> ProjectRead:
        routes = [
            RouteRead(
                id=route.id,
                route_id=route.route_id,
                description=route.description,
                is_unsafe=bool(route.is_unsafe),
                created_at=route.created_at,
            )
            for route in self._routes_for_project(project.id)
        ]
        return ProjectRead(
            id=project.id,
            name=project.name,
            preset_id=project.preset_id,
            routes=routes,
            archived_at=project.archived_at,
            route_taxonomy_locked=self._route_locking_resource(project.id) is not None,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    def _route_locking_resource(self, project_id: str) -> tuple[str, str] | None:
        checks = [
            ("dataset", Dataset),
            ("eval_set", EvalSet),
            ("job", Job),
            ("model_run", ModelRun),
            ("benchmark", Benchmark),
            ("agent_package", AgentPackage),
        ]
        for resource_type, model in checks:
            row = self.session.execute(select(model.id).where(model.project_id == project_id).limit(1)).first()
            if row is not None:
                return resource_type, str(row[0])
        return None
