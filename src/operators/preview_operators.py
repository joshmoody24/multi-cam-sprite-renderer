"""Preview operators for the Multi-Cam Sprite Renderer addon"""

import bpy
from typing import Set, TYPE_CHECKING

if TYPE_CHECKING:
    from bpy.stub_internal.rna_enums import OperatorReturnItems
else:
    OperatorReturnItems = str

from ..mcsr_types import McsrOperator, get_mcsr_scene, get_mcsr_object
from ..camera_utils import create_preview_cameras
from ..utils import cleanup_preview_cameras


class TogglePreviewOperator(McsrOperator):
    bl_idname = "mcsr.toggle_preview"
    bl_label = "Toggle Preview"
    bl_description = "Toggle camera preview in viewport"

    def execute_mcsr(self, scene) -> Set[OperatorReturnItems]:
        if not self.active_object:
            self.report({"ERROR"}, "Please select a target object")
            return {"CANCELLED"}

        if not self.active_object.mcsr.reference_camera:
            self.report({"ERROR"}, "Please select a reference camera")
            return {"CANCELLED"}

        scene.mcsr_show_preview = not scene.mcsr_show_preview
        self.toggle_preview(bpy.context)
        return {"FINISHED"}

    def toggle_preview(self, context):
        cleanup_preview_cameras()
        scene = get_mcsr_scene(context.scene)
        if scene.mcsr_show_preview:
            create_preview_cameras(context)

        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


class UpdatePreviewOperator(McsrOperator):
    bl_idname = "mcsr.update_preview"
    bl_label = "Update Preview"
    bl_description = "Update preview camera positions"

    def execute_mcsr(self, scene) -> Set[OperatorReturnItems]:
        if not self.active_object:
            self.report({"ERROR"}, "Please select a target object")
            return {"CANCELLED"}

        if not self.active_object.mcsr.reference_camera:
            self.report({"ERROR"}, "Please select a reference camera")
            return {"CANCELLED"}

        if not scene.mcsr_show_preview:
            return {"FINISHED"}

        cleanup_preview_cameras()
        create_preview_cameras(bpy.context)

        assert bpy.context.screen, "Context screen is not available"
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()

        return {"FINISHED"}
