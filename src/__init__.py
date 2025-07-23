"""Multi-Cam Sprite Renderer - Blender addon for creating sprite sheets from multiple camera angles"""

import sys

# Module cleanup disabled to prevent conflicts with Blender's extension system

import bpy
import importlib

from . import ui_panel, properties, utils, constants, mcsr_types, camera_utils, render_utils
from . import operators

classes = (
    ui_panel.MultiCamSpriteRendererPanel,
    operators.MultiCamSpriteRenderOperator,
    operators.RenderAllMcsrOperator,
    operators.TogglePreviewOperator,
    operators.UpdatePreviewOperator,
    operators.ApplyRecommendedSettingsOperator,
    operators.AddSelectedToMcsrOperator,
    operators.RemoveFromMcsrOperator,
    operators.SelectMcsrObjectOperator,
    operators.AddActionOperator,
    operators.RemoveActionOperator,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    properties.register_properties()


def unregister():
    properties.unregister_properties()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
