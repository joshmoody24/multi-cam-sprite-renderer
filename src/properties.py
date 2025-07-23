"""Property definitions for the Multi-Cam Sprite Renderer addon"""

import bpy
from bpy.props import (
    IntProperty,
    FloatProperty,
    StringProperty,
    BoolProperty,
    EnumProperty,
    PointerProperty,
    CollectionProperty,
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
    if not context.scene.mcsr_show_preview:
        return

    from .utils import cleanup_preview_cameras
    from .camera_utils import create_preview_cameras

    cleanup_preview_cameras()
    create_preview_cameras(context)


class McsrActionSetting(bpy.types.PropertyGroup):
    """Reference to an Action"""

    action: PointerProperty(  # type: ignore[misc]
        name="Action", description="Action to render", type=bpy.types.Action
    )


class McsrObjectSettings(bpy.types.PropertyGroup):
    """Per-object settings for Multi-Cam Sprite Renderer"""

    reference_camera: PointerProperty(  # type: ignore[misc]
        name="Reference Camera",
        description="Camera to use as reference for position and settings",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == "CAMERA",
    )

    camera_count: IntProperty(  # type: ignore[misc]
        name="Camera Count",
        description="Number of cameras to render from",
        default=DEFAULT_CAMERA_COUNT,
        min=3,
        max=24,
        update=update_preview,
    )

    output_path: StringProperty(  # type: ignore[misc]
        name="Output Path",
        description="Directory to save rendered images",
        default=DEFAULT_OUTPUT_PATH,
        subtype="DIR_PATH",
    )

    actions: CollectionProperty(  # type: ignore[misc]
        name="Actions",
        description="Actions to render for this object",
        type=McsrActionSetting,
    )


class McsrObjectPointer(bpy.types.PropertyGroup):
    """Reference to an object with MCSR settings"""

    object: PointerProperty(  # type: ignore[misc]
        name="Object", description="Object with MCSR settings", type=bpy.types.Object
    )


def register_properties():
    """Register all properties for the addon"""
    bpy.utils.register_class(McsrActionSetting)
    bpy.utils.register_class(McsrObjectSettings)
    bpy.utils.register_class(McsrObjectPointer)

    # Add object settings
    bpy.types.Object.mcsr = PointerProperty(type=McsrObjectSettings)  # type: ignore[misc]

    # Add active object selection and list to scene
    bpy.types.Scene.mcsr_active_object = PointerProperty(  # type: ignore[misc]
        name="Active MCSR Object",
        description="Currently selected object for MCSR settings",
        type=bpy.types.Object,
    )

    bpy.types.Scene.mcsr_objects = CollectionProperty(  # type: ignore[misc]
        name="MCSR Objects",
        description="Objects with MCSR settings",
        type=McsrObjectPointer,
    )

    bpy.types.Scene.mcsr_distance = FloatProperty(  # type: ignore[misc]
        name="Distance",
        description="Distance from center to cameras",
        default=DEFAULT_DISTANCE,
        min=0.1,
        max=100.0,
    )

    bpy.types.Scene.mcsr_camera_type = EnumProperty(  # type: ignore[misc]
        name="Camera Type",
        description="Type of camera projection",
        items=[
            ("PERSP", "Perspective", "Perspective projection"),
            ("ORTHO", "Orthographic", "Orthographic projection"),
        ],
        default="PERSP",
    )

    bpy.types.Scene.mcsr_focal_length = FloatProperty(  # type: ignore[misc]
        name="Focal Length",
        description="Camera focal length in mm",
        default=DEFAULT_FOCAL_LENGTH,
        min=1.0,
        max=5000.0,
    )

    bpy.types.Scene.mcsr_ortho_scale = FloatProperty(  # type: ignore[misc]
        name="Orthographic Scale",
        description="Orthographic scale",
        default=DEFAULT_ORTHO_SCALE,
        min=0.001,
        max=10000.0,
    )

    bpy.types.Scene.mcsr_clip_start = FloatProperty(  # type: ignore[misc]
        name="Clip Start",
        description="Camera near clipping distance",
        default=DEFAULT_CLIP_START,
        min=0.001,
        max=1000.0,
    )

    bpy.types.Scene.mcsr_clip_end = FloatProperty(  # type: ignore[misc]
        name="Clip End",
        description="Camera far clipping distance",
        default=DEFAULT_CLIP_END,
        min=0.001,
        max=100000.0,
    )

    bpy.types.Scene.mcsr_spacing = IntProperty(  # type: ignore[misc]
        name="Sprite Spacing",
        description="Pixels between each sprite in the sheet",
        default=DEFAULT_SPACING,
        min=0,
        max=50,
    )

    bpy.types.Scene.mcsr_show_preview = BoolProperty(  # type: ignore[misc]
        name="Show Preview",
        description="Show camera positions in viewport",
        default=False,
    )

    bpy.types.Scene.mcsr_pixel_art = BoolProperty(  # type: ignore[misc]
        name="Pixel Art",
        description="Enable pixel art mode (affects filtering)",
        default=False,
    )

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

    # Remove object settings
    bpy.utils.unregister_class(McsrActionSetting)
    bpy.utils.unregister_class(McsrObjectSettings)
    bpy.utils.unregister_class(McsrObjectPointer)
    del bpy.types.Object.mcsr

    # Remove all scene properties
    for prop in dir(bpy.types.Scene):
        if prop.startswith("mcsr_"):
            delattr(bpy.types.Scene, prop)
