"""Type definitions for the Multi-Cam Sprite Renderer addon"""

from typing import TYPE_CHECKING, cast
import bpy

if TYPE_CHECKING:
    from typing import Literal

    class McsrScene(bpy.types.Scene):
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

        # Scene configuration
        mcsr_pixel_art: bool

        # Render passes
        mcsr_render_lit: bool
        mcsr_render_diffuse: bool
        mcsr_render_specular: bool
        mcsr_render_normal: bool

        # Debug settings
        mcsr_show_debug: bool
        mcsr_debug_preserve_compositor: bool


def get_mcsr_scene(scene: bpy.types.Scene | None) -> "McsrScene":
    """Cast a bpy.types.Scene to McsrScene with MCSR properties"""
    assert scene is not None, "Cannot cast scene to McsrScene: Scene is None"
    return cast("McsrScene", scene)
