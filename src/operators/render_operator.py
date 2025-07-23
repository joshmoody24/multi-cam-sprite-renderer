"""Main rendering operators for the Multi-Cam Sprite Renderer addon"""

import bpy
import os
import tempfile
import shutil
from typing import Set, TYPE_CHECKING

if TYPE_CHECKING:
    from bpy.stub_internal.rna_enums import OperatorReturnItems
else:
    OperatorReturnItems = str

from ..mcsr_types import McsrOperator, get_mcsr_scene, get_mcsr_object
from ..camera_utils import clone_camera, calculate_camera_positions
from ..utils import get_enabled_passes, cleanup_compositor_nodes, setup_compositor_nodes
from ..render_utils import (
    validate_render_dimensions,
    generate_metadata_dict,
    save_metadata_json,
    create_animation_from_frames,
    update_normal_matrix,
    should_skip_duplicate_frame,
)


def collect_frame_paths(
    temp_dir: str, current_frame: int, enabled_passes: list
) -> dict:
    """Collect all frame paths for a rendered frame"""
    frame_paths = {}
    for pass_name in enabled_passes:
        frame_filename = f"{pass_name}{current_frame:04d}.png"
        frame_path = os.path.join(temp_dir, frame_filename)
        assert os.path.exists(frame_path), f"Rendered frame not found: {frame_path}"
        frame_paths[pass_name] = frame_path
    return frame_paths


def setup_duplicate_detection(scene, enabled_passes: list, frame_count: int) -> dict:
    """Setup duplicate detection tracking and return tracker state"""
    tracker = {
        "enabled": scene.mcsr_skip_duplicate_frames,
        "first_pass": enabled_passes[0] if enabled_passes else None,
        "previous_frame_path": None,
    }

    if tracker["enabled"]:
        print(
            f"[MCSR DEBUG] Render: Duplicate frame skipping ENABLED for {frame_count} frames across {len(enabled_passes)} passes: {enabled_passes}"
        )
        print(
            f"[MCSR DEBUG] Render: Using '{tracker['first_pass']}' pass as reference for duplicate detection"
        )
    else:
        print(f"[MCSR DEBUG] Render: Duplicate frame skipping DISABLED")

    return tracker


def process_duplicate_detection(
    frame_paths: dict, frame_offset: int, duplicate_tracker: dict
) -> tuple:
    """Process duplicate detection and return (should_skip, updated_tracker)"""
    should_skip_frame = False

    if duplicate_tracker["enabled"]:
        print(
            f"[MCSR DEBUG] Render: Checking frame {frame_offset+1} using '{duplicate_tracker['first_pass']}' pass for duplicate detection"
        )
        should_skip_frame, current_frame_path = should_skip_duplicate_frame(
            frame_paths[duplicate_tracker["first_pass"]],
            duplicate_tracker["previous_frame_path"],
        )
        duplicate_tracker["previous_frame_path"] = current_frame_path

    return should_skip_frame, duplicate_tracker


def extend_frame_durations(
    frame_offset: int, frame_durations: dict, enabled_passes: list
) -> None:
    """Extend the duration of the previous frame for all passes"""
    print(
        f"[MCSR DEBUG] Render: Frame {frame_offset+1} skipped for ALL passes - extending previous frame durations"
    )
    for pass_name in enabled_passes:
        if frame_durations[pass_name]:
            old_duration = frame_durations[pass_name][-1]
            frame_durations[pass_name][-1] += 1
            print(
                f"[MCSR DEBUG] Render: Pass '{pass_name}' - extending previous frame duration from {old_duration} to {frame_durations[pass_name][-1]}"
            )


def add_frame_to_passes(
    frame_offset: int,
    frame_paths: dict,
    all_pass_frames: dict,
    frame_durations: dict,
    enabled_passes: list,
) -> None:
    """Add new frame to all passes with duration of 1"""
    print(f"[MCSR DEBUG] Render: Frame {frame_offset+1} added for ALL passes")
    for pass_name in enabled_passes:
        all_pass_frames[pass_name].append(frame_paths[pass_name])
        frame_durations[pass_name].append(1)
        print(
            f"[MCSR DEBUG] Render: Pass '{pass_name}' - frame added (total frames: {len(all_pass_frames[pass_name])})"
        )


def create_final_pass_animations(
    all_pass_frames: dict, camera_folder: str, enabled_passes: list, render_params: dict
) -> None:
    """Create final animation files for each pass"""
    for pass_name in enabled_passes:
        frames = all_pass_frames[pass_name]
        final_path = os.path.join(camera_folder, f"{pass_name}.png")

        if len(frames) > 1:
            create_animation_from_frames(
                frames,
                final_path,
                render_params["actual_render_x"],
                render_params["actual_render_y"],
                render_params["grid_cols"],
                render_params["grid_rows"],
            )
        elif len(frames) == 1:
            shutil.copy2(frames[0], final_path)


class MultiCamSpriteRenderOperator(McsrOperator):
    bl_idname = "mcsr.render"
    bl_label = "Render Multi-Cam Sprite"
    bl_description = "Renders animations from multiple camera angles"

    def execute_mcsr(self, scene) -> Set[OperatorReturnItems]:
        """Main execution method - orchestrates the entire rendering process"""
        context = bpy.context
        try:
            # Validate prerequisites and get render parameters
            render_params = self._validate_prerequisites(context)
            if render_params is None:
                return {"CANCELLED"}

            # Calculate render dimensions and validate size limits
            if not self._validate_render_dimensions(render_params):
                return {"CANCELLED"}

            # Setup rendering context and begin progress tracking
            render_context = self._setup_render_context(context, render_params)

            # Store render_params for access in other methods
            self._render_params = render_params

            # Initialize frame durations tracking for metadata
            self._frame_durations = {
                pass_name: [] for pass_name in render_params["enabled_passes"]
            }

            # Execute the main rendering pipeline
            self._render_all_actions(context, render_context)

            # Generate metadata file
            metadata_dict = generate_metadata_dict(
                render_params["actions_to_render"],
                scene.render.fps,
                render_params["actual_render_x"],
                render_params["actual_render_y"],
                self._frame_durations if scene.mcsr_skip_duplicate_frames else None,
            )
            save_metadata_json(metadata_dict, render_params["output_path"])

            self.report(
                {"INFO"},
                f"Multi-camera animation render complete! Saved to {render_params['output_path']}",
            )
            return {"FINISHED"}

        except Exception as e:
            self.report({"ERROR"}, f"Render failed: {str(e)}")
            return {"CANCELLED"}
        finally:
            # Always cleanup, even if errors occurred
            if hasattr(self, "_render_context"):
                self._cleanup_render_context(context, self._render_context)

    def _validate_prerequisites(self, context):
        """Validate all prerequisites and return render parameters"""
        scene = get_mcsr_scene(context.scene)

        if not scene.mcsr_active_object:
            self.report({"ERROR"}, "Please select a target object")
            return None

        target_object = get_mcsr_object(scene.mcsr_active_object)
        assert target_object is not None, "Target object should not be None"
        if not target_object.mcsr.reference_camera:
            self.report({"ERROR"}, "Please select a reference camera")
            return None

        output_path = bpy.path.abspath(target_object.mcsr.output_path)
        if not output_path:
            self.report({"ERROR"}, "Please set output path")
            return None

        # Get actions to render
        actions_to_render = []
        if len(target_object.mcsr.actions) > 0:
            for action_item in target_object.mcsr.actions:
                if action_item.action:
                    actions_to_render.append(action_item.action)
        else:
            actions_to_render.append(None)  # Use current frame

        if not actions_to_render:
            self.report({"ERROR"}, "No valid actions to render")
            return None

        # Validate camera positions
        try:
            camera_positions = calculate_camera_positions(
                target_object.location,
                target_object.mcsr.camera_count,
                target_object.mcsr.reference_camera,
                include_reference=True,
            )
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return None

        # Validate render passes
        enabled_passes = get_enabled_passes(scene)
        if not enabled_passes:
            self.report({"ERROR"}, "No render passes enabled")
            return None

        return {
            "scene": scene,
            "target_object": target_object,
            "output_path": output_path,
            "actions_to_render": actions_to_render,
            "camera_positions": camera_positions,
            "enabled_passes": enabled_passes,
        }

    def _validate_render_dimensions(self, render_params):
        """Validate render dimensions and calculate grid layout"""
        scene = render_params["scene"]
        actions_to_render = render_params["actions_to_render"]

        is_valid, dimension_params = validate_render_dimensions(
            scene.render.resolution_x,
            scene.render.resolution_y,
            scene.render.resolution_percentage,
            actions_to_render,
        )

        if not is_valid:
            self.report({"ERROR"}, dimension_params["error_message"])
            return False

        # Store calculated values in render_params
        render_params.update(dimension_params)
        return True

    def _setup_render_context(self, context, render_params):
        """Setup rendering context and begin progress tracking"""
        scene = render_params["scene"]
        target_object = render_params["target_object"]
        wm = context.window_manager

        assert wm is not None, "Window manager is required for progress updates"

        # Calculate total progress steps
        camera_count = len(render_params["camera_positions"])
        actions_count = len(render_params["actions_to_render"])
        passes_count = len(render_params["enabled_passes"])
        total_frames = render_params["total_frames"]

        # Since we render all passes simultaneously, count is frames * cameras * actions * passes
        total_steps = camera_count * actions_count * total_frames * passes_count
        wm.progress_begin(0, total_steps)

        # Store original state for restoration
        render_context = {
            "original_camera": scene.camera,
            "original_frame": scene.frame_current,
            "original_action": (
                target_object.animation_data.action
                if target_object.animation_data
                else None
            ),
            "wm": wm,
            "step": 0,
        }

        # Create output directory
        os.makedirs(render_params["output_path"], exist_ok=True)

        # Store context for cleanup
        self._render_context = render_context

        return render_context

    def _render_all_actions(self, context, render_context):
        """Render all actions for all cameras"""
        render_params = self._render_params if hasattr(self, "_render_params") else {}

        # Extract from stored params in context
        actions_to_render = render_params.get("actions_to_render", [])

        for action_idx, action in enumerate(actions_to_render):
            self._render_single_action(context, render_context, action_idx, action)

    def _render_single_action(self, context, render_context, action_idx, action):
        """Render a single action across all cameras"""
        render_params = self._render_params
        scene = render_params["scene"]
        target_object = render_params["target_object"]
        camera_positions = render_params["camera_positions"]
        output_path = render_params["output_path"]

        action_name = action.name if action else "_default"
        action_folder = os.path.join(output_path, action_name)
        os.makedirs(action_folder, exist_ok=True)

        # Set up action animation
        if action:
            if not target_object.animation_data:
                target_object.animation_data_create()
            target_object.animation_data.action = action
            start_frame = int(action.frame_range[0])
            end_frame = int(action.frame_range[1])
            frame_count = end_frame - start_frame + 1
        else:
            start_frame = scene.frame_current
            end_frame = scene.frame_current
            frame_count = 1

        # Render each camera for this action
        for camera_idx, (position, rotation) in enumerate(camera_positions):
            self._render_single_camera(
                context,
                render_context,
                action_idx,
                camera_idx,
                position,
                rotation,
                action_folder,
                start_frame,
                frame_count,
            )

    def _render_single_camera(
        self,
        context,
        render_context,
        action_idx,
        camera_idx,
        position,
        rotation,
        action_folder,
        start_frame,
        frame_count,
    ):
        """Render a single camera for a specific action"""
        render_params = self._render_params
        scene = render_params["scene"]
        enabled_passes = render_params["enabled_passes"]

        camera_folder = os.path.join(action_folder, f"camera_{camera_idx:02d}")
        os.makedirs(camera_folder, exist_ok=True)

        # Create and position camera
        reference_camera = get_mcsr_object(
            render_params["target_object"]
        ).mcsr.reference_camera
        assert reference_camera is not None, "Reference camera should not be None"

        camera = clone_camera(reference_camera)
        assert camera is not None, "Cloned camera should not be None"

        camera.location = position
        camera.rotation_euler = rotation
        scene.camera = camera

        assert context.view_layer is not None, "View layer should not be None"
        context.view_layer.update()

        try:
            # Render all passes for this camera/action combo
            self._render_all_passes(
                context,
                render_context,
                action_idx,
                camera_idx,
                camera,
                camera_folder,
                start_frame,
                frame_count,
            )
        finally:
            # Clean up camera
            bpy.data.objects.remove(camera, do_unlink=True)

    def _render_all_passes(
        self,
        context,
        render_context,
        action_idx,
        camera_idx,
        camera,
        camera_folder,
        start_frame,
        frame_count,
    ):
        """Render all enabled passes for a camera/action"""
        render_params = self._render_params
        scene = render_params["scene"]
        actions_to_render = render_params["actions_to_render"]
        camera_count = len(render_params["camera_positions"])
        enabled_passes = render_params["enabled_passes"]

        # Use temp directory for individual frames
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_compositor_nodes(scene, temp_dir, enabled_passes)
            scene.render.use_compositing = True

            all_pass_frames = {pass_name: [] for pass_name in enabled_passes}
            frame_durations = {pass_name: [] for pass_name in enabled_passes}
            duplicate_tracker = setup_duplicate_detection(
                scene, enabled_passes, frame_count
            )

            for frame_offset in range(frame_count):
                current_frame = start_frame + frame_offset

                # Set frame and update progress
                scene.frame_set(current_frame)
                render_context["wm"].progress_update(render_context["step"])
                render_context["step"] += len(enabled_passes)
                progress_msg = f"Action {action_idx+1}/{len(actions_to_render)}, Camera {camera_idx+1}/{camera_count}, Frame {frame_offset+1}/{frame_count}"
                self.report({"INFO"}, progress_msg)

                if "normal" in enabled_passes:
                    update_normal_matrix(scene, camera)

                self._update_all_pass_outputs(
                    scene, enabled_passes, temp_dir, frame_offset
                )
                bpy.ops.render.render(write_still=True)

                frame_paths = collect_frame_paths(
                    temp_dir, current_frame, enabled_passes
                )

                should_skip_frame, duplicate_tracker = process_duplicate_detection(
                    frame_paths, frame_offset, duplicate_tracker
                )

                if should_skip_frame:
                    extend_frame_durations(
                        frame_offset, frame_durations, enabled_passes
                    )
                else:
                    add_frame_to_passes(
                        frame_offset,
                        frame_paths,
                        all_pass_frames,
                        frame_durations,
                        enabled_passes,
                    )

            for pass_name in enabled_passes:
                self._frame_durations[pass_name].append(frame_durations[pass_name])

            create_final_pass_animations(
                all_pass_frames, camera_folder, enabled_passes, render_params
            )

    def _update_all_pass_outputs(self, scene, enabled_passes, temp_dir, frame_offset):
        """Update file output paths for all passes"""
        for pass_name in enabled_passes:
            node_name = f"MCSR_Output_{pass_name}"
            if node_name in scene.node_tree.nodes:
                file_output = scene.node_tree.nodes[node_name]
                if file_output.file_slots:
                    # Blender automatically appends frame numbers, so just use pass name
                    file_output.file_slots[0].path = pass_name

    def _cleanup_render_context(self, context, render_context):
        """Cleanup rendering context and restore original state"""
        scene = get_mcsr_scene(context.scene)

        # Restore original state
        if "original_camera" in render_context:
            scene.camera = render_context["original_camera"]
        if "original_frame" in render_context:
            scene.frame_set(render_context["original_frame"])
        if "original_action" in render_context:
            target_object = get_mcsr_object(scene.mcsr_active_object)
            if target_object and target_object.animation_data:
                target_object.animation_data.action = render_context["original_action"]

        # Cleanup compositor if needed
        if not scene.mcsr_debug_preserve_compositor:
            cleanup_compositor_nodes(scene)

        # End progress tracking
        if "wm" in render_context:
            render_context["wm"].progress_end()


class RenderAllMcsrOperator(McsrOperator):
    bl_idname = "mcsr.render_all"
    bl_label = "Render All MCSR Objects"
    bl_description = "Renders all objects in the MCSR list"

    def execute_mcsr(self, scene) -> Set[OperatorReturnItems]:
        if not scene.mcsr_objects:
            self.report({"ERROR"}, "No MCSR objects to render")
            return {"CANCELLED"}

        # Store original active object
        original_active = scene.mcsr_active_object

        # Render each object
        for item in scene.mcsr_objects:
            if not item.object:
                continue

            scene.mcsr_active_object = get_mcsr_object(item.object)
            bpy.ops.mcsr.render()  # type: ignore

        # Restore original active object
        scene.mcsr_active_object = original_active

        return {"FINISHED"}
