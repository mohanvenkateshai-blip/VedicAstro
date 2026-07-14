"""Fail-closed source and evidence policies for research snapshots."""

from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

from pydantic import BaseModel, ConfigDict

from .models import LocatorKind, SourceManifest


class ResearchPolicyError(ValueError):
    pass


class SourceAllowlist(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    uri_prefixes: tuple[str, ...] = ()
    local_roots: tuple[str, ...] = ()
    accepted_rights_or_licenses: tuple[str, ...] = ()

    def require_allowed(self, source: SourceManifest) -> None:
        if not source.research_use_allowed:
            raise ResearchPolicyError(
                f"source {source.source_id!r} is not licensed for research use"
            )
        if source.rights_or_license not in self.accepted_rights_or_licenses:
            raise ResearchPolicyError(f"source {source.source_id!r} has an unapproved license")

        if source.locator_kind is LocatorKind.URI:
            parsed = urlparse(source.locator)
            if parsed.scheme not in {"https", "http"} or not parsed.netloc:
                raise ResearchPolicyError("source URI must be an absolute HTTP(S) URI")
            if parsed.username or parsed.password or parsed.fragment:
                raise ResearchPolicyError("source URI cannot contain credentials or a fragment")
            allowed = any(_uri_is_within(parsed, prefix) for prefix in self.uri_prefixes)
        else:
            path = PurePosixPath(source.locator)
            if not path.is_absolute() or ".." in path.parts:
                raise ResearchPolicyError("local source path must be absolute and traversal-free")
            allowed = any(path.is_relative_to(PurePosixPath(root)) for root in self.local_roots)
        if not allowed:
            raise ResearchPolicyError(f"source {source.source_id!r} is not allowlisted")


def _uri_is_within(source, prefix: str) -> bool:
    allowed = urlparse(prefix)
    if allowed.scheme not in {"https", "http"} or not allowed.hostname:
        return False
    if allowed.username or allowed.password or allowed.fragment:
        return False
    source_port = source.port or (443 if source.scheme == "https" else 80)
    allowed_port = allowed.port or (443 if allowed.scheme == "https" else 80)
    if (
        source.scheme != allowed.scheme
        or source.hostname != allowed.hostname
        or source_port != allowed_port
    ):
        return False
    source_path = PurePosixPath(unquote(source.path or "/"))
    allowed_path = PurePosixPath(unquote(allowed.path or "/"))
    if ".." in source_path.parts or ".." in allowed_path.parts:
        return False
    return source_path == allowed_path or source_path.is_relative_to(allowed_path)
