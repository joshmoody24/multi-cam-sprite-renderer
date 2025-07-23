"""Object management operators for the Multi-Cam Sprite Renderer addon"""

import bpy
from typing import Set, TYPE_CHECKING
from bpy.props import StringProperty
from ..mcsr_types import McsrOperator, get_mcsr_object

if TYPE_CHECKING:
    from bpy.stub_internal.rna_enums import OperatorReturnItems
else:
    OperatorReturnItems = str


class AddSelectedToMcsrOperator(McsrOperator):
    bl_idname = "mcsr.add_selected"
    bl_label = "Add Selected to MCSR"
    bl_description = "Add selected object to MCSR objects list"

    def execute_mcsr(self, scene) -> Set[OperatorReturnItems]:
        active_obj = bpy.context.active_object

        if not active_obj:
            self.report({"ERROR"}, "No active object")
            return {"CANCELLED"}

        if active_obj.type != "MESH":
            self.report({"ERROR"}, "Selected object must be a mesh")
            return {"CANCELLED"}

        # Check if object is already in list
        for item in scene.mcsr_objects:
            if item.object == active_obj:
                self.report({"INFO"}, "Object already in MCSR list")
                return {"CANCELLED"}

        # Add to list
        item = scene.mcsr_objects.add()
        item.object = active_obj
        scene.mcsr_active_object = get_mcsr_object(active_obj)

        return {"FINISHED"}


class RemoveFromMcsrOperator(McsrOperator):
    bl_idname = "mcsr.remove_active"
    bl_label = "Remove from MCSR"
    bl_description = "Remove active object from MCSR objects list"

    def execute_mcsr(self, scene) -> Set[OperatorReturnItems]:
        active_obj = scene.mcsr_active_object

        if not active_obj:
            self.report({"ERROR"}, "No active MCSR object")
            return {"CANCELLED"}

        # Find and remove from list
        for i, item in enumerate(scene.mcsr_objects):
            if item.object == active_obj:
                scene.mcsr_objects.remove(i)
                scene.mcsr_active_object = None
                break

        return {"FINISHED"}


class SelectMcsrObjectOperator(McsrOperator):
    bl_idname = "mcsr.select_object"
    bl_label = "Select MCSR Object"
    bl_description = "Set active MCSR object"

    object_name: StringProperty()  # type: ignore

    def execute_mcsr(self, scene) -> Set[OperatorReturnItems]:
        obj = bpy.data.objects.get(self.object_name)

        if not obj:
            self.report({"ERROR"}, "Object not found")
            return {"CANCELLED"}

        scene.mcsr_active_object = get_mcsr_object(obj)
        return {"FINISHED"}
