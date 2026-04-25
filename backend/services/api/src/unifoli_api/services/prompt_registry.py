from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from unifoli_api.core.config import get_settings
from unifoli_shared.paths import find_project_root


_PROMPT_BODY_PATTERN = re.compile(r"^## Prompt Body\s*$", re.MULTILINE)


class PromptRegistryError(RuntimeError):
    """Base error for prompt registry loading problems."""


class PromptAssetNotFoundError(PromptRegistryError):
    """Raised when a named prompt asset is missing from the registry."""


@dataclass(frozen=True, slots=True)
class PromptAssetMeta:
    name: str
    category: str
    version: str
    relative_path: str
    description: str
    output_mode: str
    wiring_status: str
    dependencies: tuple[str, ...]
    runtime_targets: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PromptAsset:
    meta: PromptAssetMeta
    full_path: Path
    markdown: str
    body: str


class PromptRegistry:
    def __init__(
        self,
        *,
        prompt_root: Path | None = None,
        registry_path: Path | None = None,
    ) -> None:
        settings = get_settings()
        self.prompt_root = self._resolve_prompt_root(
            explicit=prompt_root,
            configured=settings.prompt_asset_root,
        )
        self.registry_path = self._resolve_registry_path(
            explicit=registry_path,
            configured=settings.prompt_registry_path,
            prompt_root=self.prompt_root,
        )
        self._manifest: dict[str, object] | None = None
        self._asset_roots: dict[str, Path] = {}
        self._fallback_prompt_roots = (
            self._build_fallback_prompt_roots(self.prompt_root)
            if prompt_root is None and registry_path is None
            else ()
        )

    def list_asset_metadata(self) -> tuple[PromptAssetMeta, ...]:
        registry = self._load_manifest()
        return tuple(
            self._parse_meta(name=name, payload=payload)
            for name, payload in registry.items()
        )

    def get_asset(self, name: str) -> PromptAsset:
        registry = self._load_manifest()
        payload = registry.get(name)
        if payload is None:
            raise PromptAssetNotFoundError(
                f"Prompt asset '{name}' was not found in registry '{self.registry_path}'."
            )
        meta = self._parse_meta(name=name, payload=payload)
        full_path = self._resolve_asset_path(meta)
        if not full_path.exists():
            raise PromptRegistryError(
                f"Prompt file for '{name}' is missing: '{full_path}'."
            )
        markdown = full_path.read_text(encoding="utf-8")
        return PromptAsset(
            meta=meta,
            full_path=full_path,
            markdown=markdown,
            body=self._extract_prompt_body(markdown=markdown, name=name),
        )

    def compose_prompt(self, name: str) -> str:
        parts: list[str] = []
        visited: set[str] = set()

        def visit(prompt_name: str) -> None:
            if prompt_name in visited:
                return
            asset = self.get_asset(prompt_name)
            for dependency in asset.meta.dependencies:
                visit(dependency)
            visited.add(prompt_name)
            parts.append(asset.body)

        visit(name)
        return "\n\n".join(part.strip() for part in parts if part.strip()).strip()

    def _load_manifest(self) -> dict[str, object]:
        if self._manifest is not None:
            prompts = self._manifest.get("prompts")
            if isinstance(prompts, dict):
                return prompts
            raise PromptRegistryError(
                f"Registry '{self.registry_path}' is missing a top-level 'prompts' object."
            )

        prompts = dict(self._read_manifest_prompts(self.registry_path))
        self._asset_roots = {name: self.prompt_root for name in prompts}

        for fallback_root in self._fallback_prompt_roots:
            fallback_registry_path = (fallback_root / "registry.v1.json").resolve()
            if fallback_registry_path == self.registry_path.resolve() or not fallback_registry_path.exists():
                continue
            fallback_prompts = self._read_manifest_prompts(fallback_registry_path)
            for name, payload in fallback_prompts.items():
                if name in prompts:
                    continue
                prompts[name] = payload
                self._asset_roots[name] = fallback_root

        self._manifest = {"prompts": prompts}
        return prompts

    @staticmethod
    def _read_manifest_prompts(registry_path: Path) -> dict[str, object]:
        if not registry_path.exists():
            raise PromptRegistryError(
                f"Prompt registry file is missing: '{registry_path}'."
            )
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise PromptRegistryError(
                f"Prompt registry '{registry_path}' must contain a JSON object."
            )
        prompts = raw.get("prompts")
        if not isinstance(prompts, dict):
            raise PromptRegistryError(
                f"Registry '{registry_path}' is missing a top-level 'prompts' object."
            )
        return prompts

    def _resolve_asset_path(self, meta: PromptAssetMeta) -> Path:
        roots: list[Path] = []
        preferred_root = self._asset_roots.get(meta.name)
        if preferred_root is not None:
            roots.append(preferred_root)
        roots.append(self.prompt_root)
        roots.extend(self._fallback_prompt_roots)

        seen: set[Path] = set()
        for root in roots:
            resolved_root = root.resolve()
            if resolved_root in seen:
                continue
            seen.add(resolved_root)
            candidate = (resolved_root / meta.relative_path).resolve()
            if candidate.exists():
                return candidate
        first_root = roots[0] if roots else self.prompt_root
        return (first_root / meta.relative_path).resolve()

    @staticmethod
    def _resolve_prompt_root(*, explicit: Path | None, configured: str | None) -> Path:
        if explicit is not None:
            return explicit.resolve()
        if configured:
            return PromptRegistry._resolve_path(configured).resolve()
        return (PromptRegistry._repo_root() / "prompts").resolve()

    @staticmethod
    def _resolve_registry_path(
        *,
        explicit: Path | None,
        configured: str | None,
        prompt_root: Path,
    ) -> Path:
        if explicit is not None:
            return explicit.resolve()
        if configured:
            return PromptRegistry._resolve_path(configured).resolve()
        return (prompt_root / "registry.v1.json").resolve()

    @staticmethod
    def _resolve_path(value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return PromptRegistry._repo_root() / path

    @staticmethod
    def _repo_root() -> Path:
        return find_project_root().parent

    @staticmethod
    def _backend_root() -> Path:
        return find_project_root()

    @staticmethod
    def _build_fallback_prompt_roots(primary_root: Path) -> tuple[Path, ...]:
        candidates = [
            PromptRegistry._repo_root() / "prompts",
            PromptRegistry._backend_root() / "prompts",
        ]
        roots: list[Path] = []
        seen: set[Path] = {primary_root.resolve()}
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen or not resolved.exists():
                continue
            seen.add(resolved)
            roots.append(resolved)
        return tuple(roots)

    @staticmethod
    def _parse_meta(*, name: str, payload: object) -> PromptAssetMeta:
        if not isinstance(payload, dict):
            raise PromptRegistryError(f"Registry entry for '{name}' must be a JSON object.")

        dependencies = payload.get("dependencies") or []
        runtime_targets = payload.get("runtime_targets") or []
        if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
            raise PromptRegistryError(f"Registry entry for '{name}' has invalid 'dependencies'.")
        if not isinstance(runtime_targets, list) or not all(isinstance(item, str) for item in runtime_targets):
            raise PromptRegistryError(f"Registry entry for '{name}' has invalid 'runtime_targets'.")

        try:
            return PromptAssetMeta(
                name=name,
                category=str(payload["category"]),
                version=str(payload["version"]),
                relative_path=str(payload["relative_path"]),
                description=str(payload["description"]),
                output_mode=str(payload["output_mode"]),
                wiring_status=str(payload["wiring_status"]),
                dependencies=tuple(dependencies),
                runtime_targets=tuple(runtime_targets),
            )
        except KeyError as exc:
            raise PromptRegistryError(
                f"Registry entry for '{name}' is missing required field '{exc.args[0]}'."
            ) from exc

    @staticmethod
    def _extract_prompt_body(*, markdown: str, name: str) -> str:
        match = _PROMPT_BODY_PATTERN.search(markdown)
        if match is None:
            raise PromptRegistryError(
                f"Prompt asset '{name}' is missing the '## Prompt Body' section."
            )
        body = markdown[match.end() :].strip()
        if not body:
            raise PromptRegistryError(
                f"Prompt asset '{name}' has an empty prompt body."
            )
        return body


@lru_cache(maxsize=1)
def get_prompt_registry() -> PromptRegistry:
    return PromptRegistry()
