"""UI panel for the Multi-Cam Sprite Renderer addon"""

import bpy


class MultiCamSpriteRendererPanel(bpy.types.Panel):
    bl_label = "Multi-Cam Sprite Renderer"
    bl_idname = "MCSR_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MultiCam"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        self._draw_camera_settings(layout, scene)
        self._draw_sprite_settings(layout, scene)
        self._draw_scene_configuration(layout, scene)
        self._draw_preview_settings(layout, scene)
        self._draw_debug_settings(layout, scene)
        self._draw_render_buttons(layout, scene)

    def _draw_camera_settings(self, layout, scene):
        """Draw camera settings section"""
        box = layout.box()
        box.label(text="Camera Settings", icon="CAMERA_DATA")
        box.prop(scene, "mcsr_camera_count")
        box.prop(scene, "mcsr_distance")

        box.separator()
        box.prop(scene, "mcsr_camera_type")
        if scene.mcsr_camera_type == "PERSP":
            box.prop(scene, "mcsr_focal_length")
        else:
            box.prop(scene, "mcsr_ortho_scale")

        box.prop(scene, "mcsr_clip_start")
        box.prop(scene, "mcsr_clip_end")

    def _draw_sprite_settings(self, layout, scene):
        """Draw sprite sheet settings section"""
        box = layout.box()
        box.label(text="Sprite Sheet Settings", icon="IMAGE_DATA")
        box.prop(scene, "mcsr_spacing")
        box.prop(scene, "mcsr_output_path")

    def _draw_scene_configuration(self, layout, scene):
        """Draw scene configuration section"""
        box = layout.box()
        box.label(text="Scene Configuration", icon="SCENE_DATA")
        box.prop(scene, "mcsr_pixel_art")
        box.operator(
            "mcsr.apply_recommended_settings", text="Apply Recommended Settings"
        )

        box.separator()
        box.label(text="Render Passes", icon="RENDERLAYERS")

        row = box.row()
        row.prop(scene, "mcsr_render_lit")
        row.prop(scene, "mcsr_render_diffuse")

        row = box.row()
        row.prop(scene, "mcsr_render_specular")

        box.prop(scene, "mcsr_render_normal")

    def _draw_preview_settings(self, layout, scene):
        """Draw preview settings section"""
        box = layout.box()
        box.label(text="Preview", icon="HIDE_OFF")
        if scene.mcsr_show_preview:
            box.operator("mcsr.toggle_preview", text="Hide Preview", icon="HIDE_OFF")
        else:
            box.operator("mcsr.toggle_preview", text="Show Preview", icon="HIDE_ON")

    def _draw_debug_settings(self, layout, scene):
        """Draw debug settings section"""
        box = layout.box()

        # Create a collapsible header
        row = box.row()
        row.prop(
            scene,
            "mcsr_show_debug",
            icon=(
                "TRIA_DOWN"
                if getattr(scene, "mcsr_show_debug", False)
                else "TRIA_RIGHT"
            ),
            icon_only=True,
            emboss=False,
        )
        row.label(text="Debug", icon="CONSOLE")

        # Only show contents if expanded
        if getattr(scene, "mcsr_show_debug", False):
            box.prop(scene, "mcsr_debug_preserve_compositor")

    def _draw_render_buttons(self, layout, scene):
        """Draw render buttons section"""
        box = layout.box()
        box.label(text="Render", icon="RENDER_STILL")
        box.operator("mcsr.render_still", text="Render Image", icon="RENDER_STILL")
        box.operator(
            "mcsr.render_animation", text="Render Animation", icon="RENDER_ANIMATION"
        )
