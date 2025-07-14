"""Multi-Cam Sprite Renderer - Blender addon for creating sprite sheets from multiple camera angles"""

import bpy
import importlib

from . import ui_panel, operators, properties, utils, constants

# Reload modules when addon is reloaded
if "bpy" in locals():
    importlib.reload(ui_panel)
    importlib.reload(operators)
    importlib.reload(properties)
    importlib.reload(utils)
    importlib.reload(constants)

classes = (
    ui_panel.MultiCamSpriteRendererPanel,
    operators.MultiCamSpriteRenderStillOperator,
    operators.MultiCamSpriteRenderAnimationOperator,
    operators.TogglePreviewOperator,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    properties.register_properties()


def unregister():
    properties.unregister_properties()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

