"""Type definitions for the Multi-Cam Sprite Renderer addon"""

from typing import TYPE_CHECKING, cast
import bpy

if TYPE_CHECKING:
    from typing import Literal, Protocol, Iterator

    class McsrObjectCollection(Protocol):
        """Type interface for Blender CollectionProperty of McsrObjectPointer"""

        def add(self) -> "McsrObjectPointer": ...
        def remove(self, index: int) -> None: ...
        def __iter__(self) -> Iterator["McsrObjectPointer"]: ...
        def __len__(self) -> int: ...

    class McsrActionSetting(Protocol):
        """Type interface for action setting property group"""

        name: str
        action: bpy.types.Action | None

    class McsrActionCollection(Protocol):
        """Type interface for Blender CollectionProperty of action settings"""

        def add(self) -> "McsrActionSetting": ...
        def remove(self, index: int) -> None: ...
        def __iter__(self) -> Iterator["McsrActionSetting"]: ...
        def __len__(self) -> int: ...

    class McsrObjectPointer(Protocol):
        """Type interface for McsrObjectPointer property group"""

        object: bpy.types.Object | None

    class McsrObject(bpy.types.Object):
        """Extended Object type with MCSR properties"""

        class mcsr:
            """Object MCSR settings"""

            reference_camera: bpy.types.Object | None
            camera_count: int
            output_path: str
            actions: "McsrActionCollection"

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

        # Object management
        mcsr_active_object: McsrObject | None
        mcsr_objects: McsrObjectCollection


def get_mcsr_scene(scene: bpy.types.Scene | None) -> "McsrScene":
    """Cast a bpy.types.Scene to McsrScene with MCSR properties"""
    assert scene is not None, "Cannot cast scene to McsrScene: Scene is None"
    return cast("McsrScene", scene)


def get_mcsr_object(obj: bpy.types.Object | None) -> "McsrObject | None":
    """Cast a bpy.types.Object to McsrObject with MCSR properties"""
    if obj is None:
        return None
    return cast("McsrObject", obj)


class McsrOperator(bpy.types.Operator):
    """Base operator class that provides typed MCSR scene and object access"""

    def execute(self, context):
        """Override this method in subclasses with proper typing"""
        # Cast the context to provide typed scene
        mcsr_scene = get_mcsr_scene(context.scene)
        return self.execute_mcsr(mcsr_scene)

    def execute_mcsr(self, scene: "McsrScene"):
        """Override this method in subclasses instead of execute()"""
        raise NotImplementedError("Subclasses must implement execute_mcsr()")

    @property
    def scene(self) -> "McsrScene":
        """Get the typed MCSR scene"""
        return get_mcsr_scene(bpy.context.scene)

    @property
    def active_object(self) -> "McsrObject | None":
        """Get the typed active MCSR object"""
        return get_mcsr_object(self.scene.mcsr_active_object)
