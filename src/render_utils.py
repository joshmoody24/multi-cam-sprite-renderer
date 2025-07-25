"""Pure functions for rendering operations"""

import os
import json
import math
import bpy
from typing import List, Dict, Any, Optional, Tuple

from .constants import MAX_TEXTURE_SIZE


def validate_render_dimensions(
    scene_render_x: int,
    scene_render_y: int,
    resolution_percentage: float,
    actions_to_render: List[Optional[Any]],
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate render dimensions and calculate optimal grid layout for animation frames.

    Calculates the actual render dimensions accounting for resolution percentage,
    determines the maximum frame count across all actions, computes an optimal
    square-ish grid layout, and validates against GPU texture size limits.

    Args:
        scene_render_x: Base render width from scene settings
        scene_render_y: Base render height from scene settings
        resolution_percentage: Render resolution percentage (0-100)
        actions_to_render: List of actions to render (None = current frame)

    Returns:
        Tuple of (is_valid, params_dict) where params_dict contains:
        - actual_render_x/y: Final render dimensions
        - total_frames: Maximum frames across all actions
        - grid_cols/rows: Optimal grid layout
        - error_message: User-friendly error if validation fails
    """
    actual_render_x = int(scene_render_x * resolution_percentage / 100.0)
    actual_render_y = int(scene_render_y * resolution_percentage / 100.0)

    # Calculate maximum frame count across all actions
    total_frames = 0
    for action in actions_to_render:
        if action:
            frame_count = action.frame_range[1] - action.frame_range[0] + 1
            total_frames = max(total_frames, frame_count)
        else:
            total_frames = max(total_frames, 1)

    # Calculate optimal grid layout (as square as possible)
    grid_cols = math.ceil(math.sqrt(total_frames))
    grid_rows = math.ceil(total_frames / grid_cols)

    final_width = actual_render_x * grid_cols
    final_height = actual_render_y * grid_rows

    # Check size limits
    is_valid = final_width <= MAX_TEXTURE_SIZE and final_height <= MAX_TEXTURE_SIZE

    error_msg = ""
    if not is_valid:
        error_msg = (
            f"Animation too large: {final_width}x{final_height} exceeds {MAX_TEXTURE_SIZE} limit. "
            f"Current: {actual_render_x}x{actual_render_y} per frame ({resolution_percentage:.0f}%), "
            f"{total_frames} frames in {grid_cols}x{grid_rows} grid. "
            f"Reduce render resolution, resolution percentage, or frame count."
        )

    render_params = {
        "actual_render_x": actual_render_x,
        "actual_render_y": actual_render_y,
        "total_frames": total_frames,
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
        "error_message": error_msg,
    }

    return is_valid, render_params


def generate_metadata_dict(
    actions_to_render: List[Optional[Any]],
    fps: float,
    frame_width: int,
    frame_height: int,
    grid_cols: int,
    enabled_passes: List[str],
    frame_durations: Optional[Dict[str, List[List[int]]]] = None,
) -> Dict[str, Any]:
    """
    Generate metadata dictionary according to roadmap specification.

    Creates a metadata structure with FPS, frame dimensions, and per-action
    sprite data, including position and frame durations.

    Args:
        actions_to_render: List of Blender actions (None = single frame)
        fps: Frames per second for animations
        frame_width: Width of individual frames in pixels
        frame_height: Height of individual frames in pixels
        grid_cols: Number of columns in the sprite sheet grid
        enabled_passes: List of enabled render passes
        frame_durations: Dict mapping pass names to lists of frame durations per action

    Returns:
        Dictionary with metadata structure ready for JSON serialization
    """
    actions_list = []
    for action_idx, action in enumerate(actions_to_render):
        action_name = action.name if action else "_default"

        sprites_data = []
        # If skipping duplicates, use the duration data.
        if frame_durations and frame_durations.keys():
            # Assume all passes have the same frame structure, use the first pass's durations.
            first_pass = next(iter(frame_durations.keys()))

            if action_idx < len(frame_durations[first_pass]):
                action_specific_durations = frame_durations[first_pass][action_idx]

                for sprite_idx, duration in enumerate(action_specific_durations):
                    sprite_data = {
                        "x": (sprite_idx % grid_cols) * frame_width,
                        "y": (sprite_idx // grid_cols) * frame_height,
                        "frames": duration,
                    }
                    sprites_data.append(sprite_data)
        else:  # Not skipping duplicates, so each frame has a duration of 1.
            if action:
                frame_count = int(action.frame_range[1] - action.frame_range[0] + 1)
            else:
                frame_count = 1

            for sprite_idx in range(frame_count):
                sprite_data = {
                    "x": (sprite_idx % grid_cols) * frame_width,
                    "y": (sprite_idx // grid_cols) * frame_height,
                    "frames": 1,
                }
                sprites_data.append(sprite_data)

        actions_list.append(
            {
                "name": action_name,
                "sprites": sprites_data,
            }
        )

    return {
        "fps": fps,
        "frameDimensions": {"width": frame_width, "height": frame_height},
        "passes": enabled_passes,
        "actions": actions_list,
    }


def save_metadata_json(metadata_dict: Dict[str, Any], output_path: str) -> None:
    """Save metadata dictionary to JSON file"""
    metadata_path = os.path.join(output_path, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata_dict, f, indent=2)


def create_animation_from_frames(
    frame_paths: List[str],
    output_path: str,
    frame_width: int,
    frame_height: int,
    grid_cols: int,
    grid_rows: int,
) -> None:
    """Create a grid-based animation from individual frames"""
    frame_count = len(frame_paths)

    # Create a new image for the animation grid
    total_width = frame_width * grid_cols
    total_height = frame_height * grid_rows

    animation_image = bpy.data.images.new(
        name="temp_animation",
        width=total_width,
        height=total_height,
        alpha=True,  # Ensure alpha channel support
    )

    try:
        # Initialize with fully transparent pixels (RGBA: 0,0,0,0)
        animation_pixels = [0.0, 0.0, 0.0, 0.0] * (total_width * total_height)

        # Load and composite frames in grid layout
        for i, frame_path in enumerate(frame_paths):
            if i >= grid_cols * grid_rows:
                break  # Don't exceed grid capacity

            frame_image = bpy.data.images.load(frame_path)
            try:
                # Calculate grid position
                grid_x = i % grid_cols
                grid_y = i // grid_cols

                x_offset = grid_x * frame_width
                y_offset = grid_y * frame_height

                # Get pixel data
                frame_pixels = list(frame_image.pixels)

                # Copy pixels (RGBA format) to grid position
                for y in range(frame_height):
                    for x in range(frame_width):
                        src_idx = (y * frame_width + x) * 4
                        dst_x = x_offset + x
                        dst_y = y_offset + y
                        dst_idx = (dst_y * total_width + dst_x) * 4

                        if (
                            src_idx + 3 < len(frame_pixels)
                            and dst_idx + 3 < len(animation_pixels)
                            and dst_x < total_width
                            and dst_y < total_height
                        ):
                            # Copy RGBA values
                            animation_pixels[dst_idx] = frame_pixels[src_idx]  # R
                            animation_pixels[dst_idx + 1] = frame_pixels[
                                src_idx + 1
                            ]  # G
                            animation_pixels[dst_idx + 2] = frame_pixels[
                                src_idx + 2
                            ]  # B
                            animation_pixels[dst_idx + 3] = frame_pixels[
                                src_idx + 3
                            ]  # A

            finally:
                bpy.data.images.remove(frame_image, do_unlink=True)

        # Set pixels and save
        animation_image.pixels = animation_pixels
        animation_image.filepath_raw = output_path
        animation_image.file_format = "PNG"
        animation_image.save()

    finally:
        bpy.data.images.remove(animation_image, do_unlink=True)


def update_normal_matrix(scene: bpy.types.Scene, camera: bpy.types.Object) -> None:
    """Update normal transformation matrix for camera-space normals"""
    R = camera.matrix_world.inverted().to_3x3()
    R[2] *= -1
    for r in range(3):
        for c in range(3):
            node = scene.node_tree.nodes.get(f"MCSR_R{r}{c}")
            assert node, f"Missing node MCSR_R{r}{c}"
            node.outputs[0].default_value = R[r][c]


def are_images_very_similar(image_path1: str, image_path2: str) -> bool:
    """
    Compare two images to determine if they are visually very similar.
    Uses fuzzy comparison to handle noise and small rendering variations.

    Args:
        image_path1: Path to the first image
        image_path2: Path to the second image

    Returns:
        True if images are considered very similar (duplicates)
    """
    if not os.path.exists(image_path1) or not os.path.exists(image_path2):
        print(
            f"[MCSR DEBUG] Similarity: One or both files don't exist: {os.path.basename(image_path1)}, {os.path.basename(image_path2)}"
        )
        return False

    # Load both images using Blender
    temp_image1 = bpy.data.images.load(image_path1)
    temp_image2 = bpy.data.images.load(image_path2)

    try:
        # Basic dimension check - convert to tuples for proper comparison
        size1 = (temp_image1.size[0], temp_image1.size[1])
        size2 = (temp_image2.size[0], temp_image2.size[1])
        if size1 != size2:
            print(f"[MCSR DEBUG] Similarity: Different dimensions - {size1} vs {size2}")
            return False

        # Get pixel data
        pixels1 = list(temp_image1.pixels)
        pixels2 = list(temp_image2.pixels)

        if len(pixels1) != len(pixels2):
            print(
                f"[MCSR DEBUG] Similarity: Different pixel counts - {len(pixels1)} vs {len(pixels2)}"
            )
            return False

        width, height = size1[0], size1[1]

        # Sample pixels in a grid pattern for fuzzy comparison
        sample_size = 8  # 8x8 grid of samples
        step_x = max(1, width // sample_size)
        step_y = max(1, height // sample_size)

        total_diff = 0.0
        sample_count = 0

        for y in range(0, height, step_y):
            for x in range(0, width, step_x):
                if y < height and x < width:
                    pixel_idx = (y * width + x) * 4
                    if pixel_idx + 2 < len(pixels1):
                        # Compare RGB values (ignore alpha for now)
                        r1, g1, b1 = (
                            pixels1[pixel_idx],
                            pixels1[pixel_idx + 1],
                            pixels1[pixel_idx + 2],
                        )
                        r2, g2, b2 = (
                            pixels2[pixel_idx],
                            pixels2[pixel_idx + 1],
                            pixels2[pixel_idx + 2],
                        )

                        # Calculate luminance difference
                        lum1 = 0.299 * r1 + 0.587 * g1 + 0.114 * b1
                        lum2 = 0.299 * r2 + 0.587 * g2 + 0.114 * b2

                        total_diff += abs(lum1 - lum2)
                        sample_count += 1

        if sample_count == 0:
            print(f"[MCSR DEBUG] Similarity: No samples could be compared")
            return False

        avg_diff = total_diff / sample_count
        similarity_threshold = 0.00003  # average luminance difference threshold - only very small differences

        is_similar = avg_diff < similarity_threshold

        print(
            f"[MCSR DEBUG] Similarity: {os.path.basename(image_path1)} vs {os.path.basename(image_path2)} - avg_diff: {avg_diff:.4f}, similar: {is_similar}"
        )

        return is_similar

    finally:
        bpy.data.images.remove(temp_image1, do_unlink=True)
        bpy.data.images.remove(temp_image2, do_unlink=True)


def should_skip_duplicate_frame(
    current_image_path: str, previous_image_path: Optional[str]
) -> Tuple[bool, str]:
    """
    Check if current frame should be skipped due to being very similar to previous frame.

    Args:
        current_image_path: Path to the current rendered frame
        previous_image_path: Path to the previous frame (if any)

    Returns:
        Tuple of (should_skip, current_image_path)
        - should_skip: True if frame should be skipped
        - current_image_path: Path to current frame for next comparison
    """
    if previous_image_path is None:
        print(
            f"[MCSR DEBUG] Skip: First frame, never skip - {os.path.basename(current_image_path)}"
        )
        return False, current_image_path

    should_skip = are_images_very_similar(current_image_path, previous_image_path)

    if should_skip:
        print(
            f"[MCSR DEBUG] Skip: DUPLICATE DETECTED - {os.path.basename(current_image_path)} (very similar to previous)"
        )
    else:
        print(
            f"[MCSR DEBUG] Skip: Different frame - {os.path.basename(current_image_path)} (sufficiently different from previous)"
        )

    return should_skip, current_image_path
