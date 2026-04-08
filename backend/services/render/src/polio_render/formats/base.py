from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from polio_render.models import RenderArtifact, RenderBuildContext
from polio_shared.paths import get_export_root, slugify


class BaseRenderer(ABC):
    extension = ".bin"
    implementation_level = "stub"

    @abstractmethod
    def render(self, context: RenderBuildContext, output_path: Path) -> RenderArtifact:
        """
        Renders the content to the specified output_path.
        """
        raise NotImplementedError
