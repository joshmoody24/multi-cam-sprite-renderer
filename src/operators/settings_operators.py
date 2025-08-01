"""Settings operators for the Multi-Cam Sprite Renderer addon"""

import bpy
from typing import Set, TYPE_CHECKING

if TYPE_CHECKING:
    from bpy.stub_internal.rna_enums import OperatorReturnItems
else:
    OperatorReturnItems = str

from ..mcsr_types import McsrOperator


class ApplyRecommendedSettingsOperator(McsrOperator):
    bl_idname = "mcsr.apply_recommended_settings"
    bl_label = "Apply Recommended Settings"
    bl_description = "Makes renders transparent, sets view transform to Raw, and sets filter size to 0 if pixel art is enabled"

    def execute_mcsr(self, scene) -> Set[OperatorReturnItems]:
        scene.render.film_transparent = True

        # Enable Freestyle for outlines
        scene.render.use_freestyle = scene.mcsr_outline
        if scene.mcsr_outline:
            # Set line thickness to 0.7px
            scene.render.line_thickness = 0.7

        if scene.mcsr_pixel_art:
            scene.render.filter_size = 0.0
            if scene.mcsr_outline:
                scene.eevee.taa_render_samples = 1

        assert scene.view_settings is not None, "Scene view settings should not be None"
        scene.view_settings.view_transform = "Raw"  # type: ignore[attr-defined]

        self.report({"INFO"}, "Applied recommended settings")
        return {"FINISHED"}
