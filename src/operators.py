"""Render operators for the Multi-Cam Sprite Renderer addon"""

import bpy
import os
from typing import Set, TYPE_CHECKING
from bpy.props import StringProperty

if TYPE_CHECKING:
    from .mcsr_types import McsrScene
    from bpy.stub_internal.rna_enums import OperatorReturnItems
else:
    OperatorReturnItems = str

from .mcsr_types import get_mcsr_scene
from .camera_utils import (
    clone_camera,
    calculate_camera_positions,
    create_preview_cameras,
)

from .utils import (
    create_sprite_sheet_from_temp_files,
    TempDirectoryManager,
    get_enabled_passes,
    cleanup_compositor_nodes,
    setup_compositor_nodes,
    update_compositor_file_paths,
    cleanup_preview_cameras,
)


class MultiCamSpriteRenderStillOperator(bpy.types.Operator):
    bl_idname = "mcsr.render_still"
    bl_label = "Render Multi-Cam Sprite Image"
    bl_description = "Renders current frame from multiple camera angles"

    def execute(self, context) -> Set[OperatorReturnItems]:
        scene = get_mcsr_scene(context.scene)
        wm = context.window_manager

        assert wm is not None, "Window manager is required for progress updates"

        if not scene.mcsr_active_object:
            self.report({"ERROR"}, "Please select a target object")
            return {"CANCELLED"}

        target_object = scene.mcsr_active_object
        if not target_object.mcsr.reference_camera:
            self.report({"ERROR"}, "Please select a reference camera")
            return {"CANCELLED"}

        output_path = bpy.path.abspath(target_object.mcsr.output_path)
        if not output_path:
            self.report({"ERROR"}, "Please set output path")
            return {"CANCELLED"}

        os.makedirs(output_path, exist_ok=True)
        original_camera = scene.camera

        camera_count = target_object.mcsr.camera_count
        center = target_object.location
        reference_camera = target_object.mcsr.reference_camera

        try:
            camera_positions = calculate_camera_positions(
                center, camera_count, reference_camera, include_reference=True
            )
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

        enabled_passes = get_enabled_passes(scene)
        if not enabled_passes:
            self.report({"ERROR"}, "No render passes enabled")
            return {"CANCELLED"}

        wm.progress_begin(0, camera_count + len(enabled_passes))
        temp_cameras = []

        with TempDirectoryManager() as temp_dir:
            try:
                setup_compositor_nodes(scene, temp_dir, enabled_passes)
                scene.render.use_compositing = True

                for i, (position, rotation) in enumerate(camera_positions):
                    wm.progress_update(i)

                    camera = clone_camera(reference_camera)
                    camera.location = position
                    camera.rotation_euler = rotation
                    temp_cameras.append(camera)

                    assert (
                        context.view_layer is not None
                    ), "View layer should not be None"
                    context.view_layer.update()  # needs to be called before the transformation matrix updates. This little line cost me 2 hours of debugging

                    if "normal" in enabled_passes:
                        update_normal_matrix(scene, camera)

                    scene.camera = camera
                    update_compositor_file_paths(scene, enabled_passes, i)
                    bpy.ops.render.render(write_still=False)

                    self.report({"INFO"}, f"Rendered view {i+1}/{camera_count}")

                wm.progress_update(camera_count)

                for i, pass_name in enumerate(enabled_passes):
                    wm.progress_update(camera_count + i)
                    sprite_sheet_path = os.path.join(
                        output_path, f"sprite_sheet_{pass_name}.png"
                    )
                    create_sprite_sheet_from_temp_files(
                        temp_dir,
                        camera_count,
                        scene.mcsr_spacing,
                        sprite_sheet_path,
                        pass_name,
                    )

            finally:
                if not scene.mcsr_debug_preserve_compositor:
                    cleanup_compositor_nodes(scene)

                wm.progress_end()
                for camera in temp_cameras:
                    bpy.data.objects.remove(camera, do_unlink=True)
                scene.camera = original_camera

        self.report(
            {"INFO"},
            f"Multi-view render complete! {camera_count} views saved to {output_path}",
        )
        return {"FINISHED"}


def update_normal_matrix(scene, cam):
    R = cam.matrix_world.inverted().to_3x3()
    R[2] *= -1
    for r in range(3):
        for c in range(3):
            node = scene.node_tree.nodes.get(f"MCSR_R{r}{c}")
            assert node, f"Missing node MCSR_R{r}{c}"
            node.outputs[0].default_value = R[r][c]


class TogglePreviewOperator(bpy.types.Operator):
    bl_idname = "mcsr.toggle_preview"
    bl_label = "Toggle Preview"
    bl_description = "Toggle camera preview in viewport"

    def execute(self, context) -> Set[OperatorReturnItems]:
        scene = get_mcsr_scene(context.scene)

        if not scene.mcsr_active_object:
            self.report({"ERROR"}, "Please select a target object")
            return {"CANCELLED"}

        if not scene.mcsr_active_object.mcsr.reference_camera:
            self.report({"ERROR"}, "Please select a reference camera")
            return {"CANCELLED"}

        scene.mcsr_show_preview = not scene.mcsr_show_preview
        self.toggle_preview(context)
        return {"FINISHED"}

    def toggle_preview(self, context):
        cleanup_preview_cameras()
        scene = get_mcsr_scene(context.scene)
        if scene.mcsr_show_preview:
            create_preview_cameras(context)

        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


class UpdatePreviewOperator(bpy.types.Operator):
    bl_idname = "mcsr.update_preview"
    bl_label = "Update Preview"
    bl_description = "Update preview camera positions"

    def execute(self, context) -> Set[OperatorReturnItems]:
        scene = get_mcsr_scene(context.scene)

        if not scene.mcsr_active_object:
            self.report({"ERROR"}, "Please select a target object")
            return {"CANCELLED"}

        if not scene.mcsr_active_object.mcsr.reference_camera:
            self.report({"ERROR"}, "Please select a reference camera")
            return {"CANCELLED"}

        if not scene.mcsr_show_preview:
            return {"FINISHED"}

        cleanup_preview_cameras()
        create_preview_cameras(context)

        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()

        return {"FINISHED"}


class ApplyRecommendedSettingsOperator(bpy.types.Operator):
    bl_idname = "mcsr.apply_recommended_settings"
    bl_label = "Apply Recommended Settings"
    bl_description = "Makes renders transparent, sets view transform to Raw, and sets filter size to 0 if pixel art is enabled"

    def execute(self, context) -> Set[OperatorReturnItems]:
        scene = get_mcsr_scene(context.scene)
        scene.render.film_transparent = True

        if scene.mcsr_pixel_art:
            scene.render.filter_size = 0.0

        assert scene.view_settings is not None, "Scene view settings should not be None"
        scene.view_settings.view_transform = "Raw"  # type: ignore[attr-defined]

        self.report({"INFO"}, "Applied recommended settings")
        return {"FINISHED"}


class AddSelectedToMcsrOperator(bpy.types.Operator):
    bl_idname = "mcsr.add_selected"
    bl_label = "Add Selected to MCSR"
    bl_description = "Add selected object to MCSR objects list"

    def execute(self, context) -> Set[OperatorReturnItems]:
        scene = get_mcsr_scene(context.scene)
        active_obj = context.active_object

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
        scene.mcsr_active_object = active_obj

        return {"FINISHED"}


class RemoveFromMcsrOperator(bpy.types.Operator):
    bl_idname = "mcsr.remove_active"
    bl_label = "Remove from MCSR"
    bl_description = "Remove active object from MCSR objects list"

    def execute(self, context) -> Set[OperatorReturnItems]:
        scene = get_mcsr_scene(context.scene)
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


class SelectMcsrObjectOperator(bpy.types.Operator):
    bl_idname = "mcsr.select_object"
    bl_label = "Select MCSR Object"
    bl_description = "Set active MCSR object"

    object_name: StringProperty()

    def execute(self, context) -> Set[OperatorReturnItems]:
        scene = get_mcsr_scene(context.scene)
        obj = bpy.data.objects.get(self.object_name)

        if not obj:
            self.report({"ERROR"}, "Object not found")
            return {"CANCELLED"}

        scene.mcsr_active_object = obj
        return {"FINISHED"}


class RenderAllMcsrOperator(bpy.types.Operator):
    bl_idname = "mcsr.render_all"
    bl_label = "Render All MCSR Objects"
    bl_description = "Renders all objects in the MCSR list"

    def execute(self, context) -> Set[OperatorReturnItems]:
        scene = get_mcsr_scene(context.scene)

        if not scene.mcsr_objects:
            self.report({"ERROR"}, "No MCSR objects to render")
            return {"CANCELLED"}

        # Store original active object
        original_active = scene.mcsr_active_object

        # Render each object
        for item in scene.mcsr_objects:
            if not item.object:
                continue

            scene.mcsr_active_object = item.object
            bpy.ops.mcsr.render_still()

        # Restore original active object
        scene.mcsr_active_object = original_active

        return {"FINISHED"}
