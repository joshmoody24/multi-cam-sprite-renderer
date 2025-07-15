"""Type definitions for the Multi-Cam Sprite Renderer addon"""

from typing import TYPE_CHECKING, cast
import bpy

if TYPE_CHECKING:
    from typing import Literal

    class McrsScene(bpy.types.Scene):
        """Extended Scene type with MCSR properties"""

        # Camera positioning
        mcsr_camera_count: int
        mcsr_distance: float

        # Camera properties
        mcsr_camera_type: Literal["PERSP", "ORTHO"]
        mcsr_focal_length: float
        mcsr_ortho_scale: float
        mcsr_clip_start: float
        mcsr_clip_end: float

        # Output settings
        mcsr_output_path: str
        mcsr_spacing: int

        # Preview settings
        mcsr_show_preview: bool
        mcsr_preview_mode: Literal["NONE", "SINGLE", "GRID"]
        mcsr_preview_camera_index: int


def get_mcsr_scene(scene: bpy.types.Scene | None) -> "McrsScene":
    """Cast a bpy.types.Scene to McrsScene with MCSR properties"""
    assert scene is not None, "Cannot cast scene to McrsScene: Scene is None"
    return cast("McrsScene", scene)

