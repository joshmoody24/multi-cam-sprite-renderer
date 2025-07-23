"""Action management operators for the Multi-Cam Sprite Renderer addon"""

import bpy
from typing import Set, TYPE_CHECKING
from ..mcsr_types import McsrOperator

if TYPE_CHECKING:
    from bpy.stub_internal.rna_enums import OperatorReturnItems
else:
    OperatorReturnItems = str


class AddActionOperator(McsrOperator):
    bl_idname = "mcsr.add_action"
    bl_label = "Add Action"
    bl_description = "Add an action to the list"

    def execute_mcsr(self, scene) -> Set[OperatorReturnItems]:
        if not self.active_object:
            self.report({"ERROR"}, "No active MCSR object")
            return {"CANCELLED"}

        self.active_object.mcsr.actions.add()
        return {"FINISHED"}


class RemoveActionOperator(McsrOperator):
    bl_idname = "mcsr.remove_action"
    bl_label = "Remove Action"
    bl_description = "Remove the last action from the list"

    def execute_mcsr(self, scene) -> Set[OperatorReturnItems]:
        if not self.active_object:
            self.report({"ERROR"}, "No active MCSR object")
            return {"CANCELLED"}

        if len(self.active_object.mcsr.actions) > 0:
            self.active_object.mcsr.actions.remove(
                len(self.active_object.mcsr.actions) - 1
            )

        return {"FINISHED"}
