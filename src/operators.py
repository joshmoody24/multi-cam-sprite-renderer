"""Render operators for the Multi-Cam Sprite Renderer addon"""

import bpy
import os
from typing import Set, TYPE_CHECKING

if TYPE_CHECKING:
    from .mcsr_types import McrsScene
    from bpy.stub_internal.rna_enums import OperatorReturnItems
else:
    OperatorReturnItems = str

from .mcsr_types import get_mcsr_scene

from .utils import (
    get_scene_center,
    calculate_camera_positions,
    apply_camera_settings,
    point_camera_at_target,
    create_sprite_sheet_from_temp_files,
    TempDirectoryManager,
)


class MultiCamSpriteRenderStillOperator(bpy.types.Operator):
    bl_idname = "mcsr.render_still"
    bl_label = "Render Multi-Cam Sprite Image"
    bl_description = "Renders current frame from multiple camera angles"

    def execute(self, context) -> Set[OperatorReturnItems]:
        scene = get_mcsr_scene(context.scene)
        wm = context.window_manager

        assert wm is not None, "Window manager is required for progress updates"

        output_path = bpy.path.abspath(scene.mcsr_output_path)
        if not output_path:
            self.report({"ERROR"}, "Please set output path")
            return {"CANCELLED"}

        os.makedirs(output_path, exist_ok=True)
        original_camera = scene.camera

        camera_count = scene.mcsr_camera_count
        center = get_scene_center(scene)
        camera_positions = calculate_camera_positions(
            center, scene.mcsr_distance, camera_count
        )

        wm.progress_begin(0, camera_count + 1)
        temp_cameras = []

        with TempDirectoryManager() as temp_dir:
            try:
                for i, cam_location in enumerate(camera_positions):
                    wm.progress_update(i)

                    bpy.ops.object.camera_add(location=cam_location)
                    camera = context.active_object
                    temp_cameras.append(camera)

                    apply_camera_settings(camera, scene)
                    point_camera_at_target(camera, center)

                    scene.camera = camera
                    temp_filepath = os.path.join(temp_dir, f"temp_view_{i:02d}.png")
                    scene.render.filepath = temp_filepath
                    bpy.ops.render.render(write_still=True)

                    self.report({"INFO"}, f"Rendered view {i+1}/{camera_count}")

                wm.progress_update(camera_count)
                sprite_sheet_path = os.path.join(output_path, "sprite_sheet.png")
                create_sprite_sheet_from_temp_files(
                    temp_dir, camera_count, scene.mcsr_spacing, sprite_sheet_path
                )

            finally:
                wm.progress_end()
                for camera in temp_cameras:
                    bpy.data.objects.remove(camera, do_unlink=True)
                scene.camera = original_camera

        self.report(
            {"INFO"},
            f"Multi-view render complete! {camera_count} views saved to {output_path}",
        )
        return {"FINISHED"}


class MultiCamSpriteRenderAnimationOperator(bpy.types.Operator):
    bl_idname = "mcsr.render_animation"
    bl_label = "Render Multi-Cam Sprite Animation"
    bl_description = "Renders animation frames from multiple camera angles"

    def execute(self, context) -> Set[OperatorReturnItems]:
        scene = get_mcsr_scene(context.scene)
        wm = context.window_manager

        assert wm is not None, "Window manager is required for progress updates"

        output_path = bpy.path.abspath(scene.mcsr_output_path)
        if not output_path:
            self.report({"ERROR"}, "Please set output path")
            return {"CANCELLED"}

        os.makedirs(output_path, exist_ok=True)
        original_camera = scene.camera
        original_frame = scene.frame_current

        camera_count = scene.mcsr_camera_count
        frame_start = scene.frame_start
        frame_end = scene.frame_end
        frame_count = frame_end - frame_start + 1
        total_operations = frame_count * (camera_count + 1)

        wm.progress_begin(0, total_operations)
        operation_count = 0
        temp_cameras = []

        with TempDirectoryManager() as temp_dir:
            try:
                for frame in range(frame_start, frame_end + 1):
                    scene.frame_set(frame)

                    # Clear existing cameras for this frame
                    for camera in temp_cameras:
                        bpy.data.objects.remove(camera, do_unlink=True)
                    temp_cameras = []

                    center = get_scene_center(scene)
                    camera_positions = calculate_camera_positions(
                        center, scene.mcsr_distance, camera_count
                    )

                    for i, cam_location in enumerate(camera_positions):
                        wm.progress_update(operation_count)
                        operation_count += 1

                        bpy.ops.object.camera_add(location=cam_location)
                        camera = context.active_object
                        temp_cameras.append(camera)

                        apply_camera_settings(camera, scene)
                        point_camera_at_target(camera, center)

                        scene.camera = camera
                        temp_filepath = os.path.join(temp_dir, f"temp_view_{i:02d}.png")
                        scene.render.filepath = temp_filepath
                        bpy.ops.render.render(write_still=True)

                        self.report(
                            {"INFO"},
                            f"Frame {frame}: Rendered view {i+1}/{camera_count}",
                        )

                    wm.progress_update(operation_count)
                    operation_count += 1

                    sprite_sheet_path = os.path.join(
                        output_path, f"sprite_sheet_frame_{frame:04d}.png"
                    )
                    create_sprite_sheet_from_temp_files(
                        temp_dir, camera_count, scene.mcsr_spacing, sprite_sheet_path
                    )

            finally:
                wm.progress_end()
                for camera in temp_cameras:
                    bpy.data.objects.remove(camera, do_unlink=True)
                scene.camera = original_camera
                scene.frame_set(original_frame)

        self.report(
            {"INFO"},
            f"Multi-view animation complete! {frame_count} frames × {camera_count} views saved to {output_path}",
        )
        return {"FINISHED"}


class TogglePreviewOperator(bpy.types.Operator):
    bl_idname = "mcsr.toggle_preview"
    bl_label = "Toggle Preview"
    bl_description = "Toggle camera preview in viewport"

    def execute(self, context) -> Set[OperatorReturnItems]:
        scene = get_mcsr_scene(context.scene)
        scene.mcsr_show_preview = not scene.mcsr_show_preview

        # Toggle preview directly
        self.toggle_preview(context)

        return {"FINISHED"}

    def toggle_preview(self, context):
        """Toggle preview on/off using temporary camera objects"""
        from .utils import cleanup_preview_cameras, create_preview_cameras

        cleanup_preview_cameras()
        scene = get_mcsr_scene(context.scene)
        if scene.mcsr_show_preview:
            create_preview_cameras(context)

        # Force viewport update
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
