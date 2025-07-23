"""UI panel for the Multi-Cam Sprite Renderer addon"""

import bpy
from .mcsr_types import get_mcsr_scene, get_mcsr_object


class MultiCamSpriteRendererPanel(bpy.types.Panel):
    bl_label = "Multi-Cam Sprite Renderer"
    bl_idname = "MCSR_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MultiCam"

    def draw(self, context):
        layout = self.layout
        scene = get_mcsr_scene(context.scene)

        assert scene is not None, "Scene context is required"
        assert layout is not None, "Layout context is required"

        # Object management
        box = layout.box()
        box.label(text="MCSR Objects", icon="OUTLINER_OB_MESH")

        row = box.row()
        row.operator("mcsr.add_selected", text="Add Selected", icon="ADD")
        row.operator("mcsr.remove_active", text="Remove Active", icon="REMOVE")

        # Object list
        if len(scene.mcsr_objects) > 0:
            box.separator()
            for item in scene.mcsr_objects:
                obj = item.object
                if not obj:
                    continue

                row = box.row()
                op = row.operator(
                    "mcsr.select_object",
                    text=obj.name,
                    depress=(obj == scene.mcsr_active_object),
                    icon=(
                        "RADIOBUT_ON"
                        if obj == scene.mcsr_active_object
                        else "RADIOBUT_OFF"
                    ),
                )
                op.object_name = obj.name

        # Settings for active object
        active_object = get_mcsr_object(scene.mcsr_active_object)
        if active_object:
            box = layout.box()
            box.label(text=f"Settings for {active_object.name}", icon="SETTINGS")
            box.prop_search(
                active_object.mcsr,
                "reference_camera",
                context.scene,
                "objects",
                text="Camera",
            )
            if active_object.mcsr.reference_camera:
                box.prop(active_object.mcsr, "camera_count")
                box.prop(active_object.mcsr, "output_path")

            self._draw_action_settings(layout, active_object.mcsr)
            self._draw_sprite_settings(layout, scene)
            self._draw_scene_configuration(layout, scene)
            self._draw_preview_settings(layout, scene)
            self._draw_debug_settings(layout, scene)
            self._draw_render_buttons(layout, scene, active_object)
        else:
            layout.label(text="Select an MCSR object to configure", icon="INFO")

    def _draw_sprite_settings(self, layout, scene):
        """Draw sprite sheet settings section"""
        box = layout.box()
        box.label(text="Sprite Sheet Settings", icon="IMAGE_DATA")
        box.prop(scene, "mcsr_spacing")

    def _draw_action_settings(self, layout, mcsr_settings):
        """Draw action settings section"""
        box = layout.box()
        box.label(text="Action Settings", icon="ACTION")

        row = box.row()
        row.operator("mcsr.add_action", text="Add Action", icon="ADD")
        row.operator("mcsr.remove_action", text="Remove Action", icon="REMOVE")

        for i, action_item in enumerate(mcsr_settings.actions):
            row = box.row()
            row.prop_search(action_item, "action", bpy.data, "actions", text="")

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
        row = box.row()
        if scene.mcsr_show_preview:
            row.operator("mcsr.toggle_preview", text="Hide Preview", icon="HIDE_OFF")
            row.operator(
                "mcsr.update_preview", text="Update Preview", icon="FILE_REFRESH"
            )
        else:
            row.operator("mcsr.toggle_preview", text="Show Preview", icon="HIDE_ON")

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

    def _draw_render_buttons(self, layout, scene, active_object):
        """Draw render buttons section"""
        box = layout.box()
        box.label(text="Render", icon="RENDER_STILL")
        box.operator(
            "mcsr.render",
            text=f"Render {active_object.name}",
            icon="RENDER_STILL",
        )
        box.operator(
            "mcsr.render_all", text="Render All MCSR Objects", icon="RENDER_STILL"
        )
