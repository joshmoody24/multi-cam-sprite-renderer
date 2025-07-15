"""Property definitions for the Multi-Cam Sprite Renderer addon"""

import bpy
from bpy.props import (
    IntProperty,
    FloatProperty,
    StringProperty,
    BoolProperty,
    EnumProperty,
)

from .constants import (
    DEFAULT_CAMERA_COUNT,
    DEFAULT_DISTANCE,
    DEFAULT_FOCAL_LENGTH,
    DEFAULT_ORTHO_SCALE,
    DEFAULT_CLIP_START,
    DEFAULT_CLIP_END,
    DEFAULT_SPACING,
    DEFAULT_OUTPUT_PATH,
)


def update_preview(self, context):
    """Refresh preview when camera settings change"""
    if (
        not hasattr(context.scene, "mcsr_show_preview")
        or not context.scene.mcsr_show_preview
    ):
        return

    from .utils import cleanup_preview_cameras, create_preview_cameras

    cleanup_preview_cameras()
    create_preview_cameras(context)


def register_properties():
    """Register all scene properties for the addon"""

    # Camera positioning
    bpy.types.Scene.mcsr_camera_count = IntProperty(  # type: ignore[misc]
        name="Camera Count",
        description="Number of cameras to render from",
        default=DEFAULT_CAMERA_COUNT,
        min=3,
        max=24,
        update=update_preview,
    )

    bpy.types.Scene.mcsr_distance = FloatProperty(  # type: ignore[misc]
        name="Distance",
        description="Distance from center to cameras",
        default=DEFAULT_DISTANCE,
        min=0.1,
        max=100.0,
        update=update_preview,
    )

    # Camera properties
    bpy.types.Scene.mcsr_camera_type = EnumProperty(  # type: ignore[misc]
        name="Camera Type",
        description="Type of camera projection",
        items=[
            ("PERSP", "Perspective", "Perspective projection"),
            ("ORTHO", "Orthographic", "Orthographic projection"),
        ],
        default="PERSP",
        update=update_preview,
    )

    bpy.types.Scene.mcsr_focal_length = FloatProperty(  # type: ignore[misc]
        name="Focal Length",
        description="Camera focal length in mm",
        default=DEFAULT_FOCAL_LENGTH,
        min=1.0,
        max=5000.0,
        update=update_preview,
    )

    bpy.types.Scene.mcsr_ortho_scale = FloatProperty(  # type: ignore[misc]
        name="Orthographic Scale",
        description="Orthographic scale",
        default=DEFAULT_ORTHO_SCALE,
        min=0.001,
        max=10000.0,
        update=update_preview,
    )

    bpy.types.Scene.mcsr_clip_start = FloatProperty(  # type: ignore[misc]
        name="Clip Start",
        description="Camera near clipping distance",
        default=DEFAULT_CLIP_START,
        min=0.001,
        max=1000.0,
        update=update_preview,
    )

    bpy.types.Scene.mcsr_clip_end = FloatProperty(  # type: ignore[misc]
        name="Clip End",
        description="Camera far clipping distance",
        default=DEFAULT_CLIP_END,
        min=0.001,
        max=100000.0,
        update=update_preview,
    )

    # Output settings
    bpy.types.Scene.mcsr_output_path = StringProperty(  # type: ignore[misc]
        name="Output Path",
        description="Directory to save rendered images",
        default=DEFAULT_OUTPUT_PATH,
        subtype="DIR_PATH",
    )

    bpy.types.Scene.mcsr_spacing = IntProperty(  # type: ignore[misc]
        name="Sprite Spacing",
        description="Pixels between each sprite in the sheet",
        default=DEFAULT_SPACING,
        min=0,
        max=50,
    )

    # Preview settings
    bpy.types.Scene.mcsr_show_preview = BoolProperty(  # type: ignore[misc]
        name="Show Preview",
        description="Show camera positions in viewport",
        default=False,
    )

    # Future preview features (not currently used)
    bpy.types.Scene.mcsr_preview_mode = bpy.props.EnumProperty(  # type: ignore[misc]
        name="Preview Mode",
        description="How to preview camera views",
        items=[
            ("NONE", "None", "No camera preview"),
            ("SINGLE", "Single Camera", "Preview one camera at a time"),
            ("GRID", "Grid View", "Preview all cameras in grid layout"),
        ],
        default="NONE",
    )

    bpy.types.Scene.mcsr_preview_camera_index = IntProperty(  # type: ignore[misc]
        name="Camera Index",
        description="Which camera to preview (0-based)",
        default=0,
        min=0,
    )

    # Scene configuration
    bpy.types.Scene.mcsr_pixel_art = BoolProperty(  # type: ignore[misc]
        name="Pixel Art",
        description="Enable pixel art mode (affects filtering)",
        default=False,
    )

    # Render passes
    bpy.types.Scene.mcsr_render_lit = BoolProperty(  # type: ignore[misc]
        name="Lit",
        description="Render standard lit pass",
        default=True,
    )

    bpy.types.Scene.mcsr_render_diffuse = BoolProperty(  # type: ignore[misc]
        name="Diffuse",
        description="Render diffuse color pass",
        default=False,
    )

    bpy.types.Scene.mcsr_render_specular = BoolProperty(  # type: ignore[misc]
        name="Specular",
        description="Render specular pass",
        default=False,
    )

    bpy.types.Scene.mcsr_render_normal = BoolProperty(  # type: ignore[misc]
        name="Normal",
        description="Render normal pass",
        default=False,
    )

    # Debug settings
    bpy.types.Scene.mcsr_show_debug = BoolProperty(  # type: ignore[misc]
        name="Show Debug",
        description="Show debug options",
        default=False,
    )

    bpy.types.Scene.mcsr_debug_preserve_compositor = BoolProperty(  # type: ignore[misc]
        name="Preserve Compositor",
        description="Keep compositor nodes after render for debugging",
        default=False,
    )


def unregister_properties():
    """Unregister all properties and clean up preview objects"""
    from .utils import cleanup_preview_cameras

    cleanup_preview_cameras()

    # Remove all registered properties
    props_to_remove = [
        "mcsr_camera_count",
        "mcsr_distance",
        "mcsr_camera_type",
        "mcsr_focal_length",
        "mcsr_ortho_scale",
        "mcsr_clip_start",
        "mcsr_clip_end",
        "mcsr_output_path",
        "mcsr_spacing",
        "mcsr_show_preview",
        "mcsr_preview_mode",
        "mcsr_preview_camera_index",
        "mcsr_pixel_art",
        "mcsr_render_lit",
        "mcsr_render_diffuse",
        "mcsr_render_specular",
        "mcsr_render_normal",
        "mcsr_show_debug",
        "mcsr_debug_preserve_compositor",
    ]

    for prop in props_to_remove:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)
