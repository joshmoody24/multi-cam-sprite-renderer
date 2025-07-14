import bpy
import importlib

from . import ui_panel, operators

# Reload modules when addon is reloaded
if "bpy" in locals():
    importlib.reload(ui_panel)
    importlib.reload(operators)

classes = (ui_panel.MultiViewPanel, operators.MultiViewRenderStillOperator, operators.MultiViewRenderAnimationOperator, operators.TogglePreviewOperator)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    ui_panel.register_properties()


def unregister():
    ui_panel.unregister_properties()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)