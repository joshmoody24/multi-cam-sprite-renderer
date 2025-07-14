"""Utility functions shared across the Multi-Cam Sprite Renderer addon"""

import bpy
import math
import os
import tempfile
import shutil
from mathutils import Vector

from .constants import (
    PREVIEW_COLLECTION_NAME,
    PREVIEW_PARENT_NAME,
    PREVIEW_CAMERA_PREFIX,
    PREVIEW_COLOR,
)


def get_scene_center(scene):
    """Calculate the center point of all mesh objects in the scene"""
    mesh_objects = [obj for obj in scene.objects if obj.type == "MESH"]
    if not mesh_objects:
        return Vector((0, 0, 0))

    return sum([obj.location for obj in mesh_objects], Vector()) / len(mesh_objects)


def calculate_camera_positions(center, distance, camera_count):
    """Generate camera positions in a circle around the center point"""
    positions = []
    for i in range(camera_count):
        angle = (i / camera_count) * 2 * math.pi
        position = Vector(
            (
                center.x + distance * math.cos(angle),
                center.y + distance * math.sin(angle),
                center.z,
            )
        )
        positions.append(position)
    return positions


def apply_camera_settings(camera, scene):
    """Apply scene camera properties to a camera object"""
    cam_data = camera.data
    cam_data.type = scene.mcsr_camera_type
    cam_data.lens = scene.mcsr_focal_length
    cam_data.ortho_scale = scene.mcsr_ortho_scale
    cam_data.clip_start = scene.mcsr_clip_start
    cam_data.clip_end = scene.mcsr_clip_end

    # Apply depth of field settings
    if scene.mcsr_use_dof:
        cam_data.dof.use_dof = True
        cam_data.dof.aperture_fstop = scene.mcsr_dof_aperture

        if scene.mcsr_dof_object:
            cam_data.dof.focus_object = scene.mcsr_dof_object
        else:
            cam_data.dof.focus_distance = scene.mcsr_dof_distance
    else:
        cam_data.dof.use_dof = False


def point_camera_at_target(camera, target_location):
    """Point a camera at a target location"""
    direction = target_location - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def cleanup_preview_cameras():
    """Remove any existing preview cameras and parent object"""
    preview_collection = bpy.data.collections.get(PREVIEW_COLLECTION_NAME)
    if preview_collection:
        bpy.data.collections.remove(preview_collection)

    # Clean up any remaining objects with our naming pattern
    cameras_to_remove = [
        obj for obj in bpy.data.objects if obj.name.startswith(PREVIEW_CAMERA_PREFIX)
    ]
    for cam in cameras_to_remove:
        bpy.data.objects.remove(cam, do_unlink=True)

    parent_objects = [
        obj for obj in bpy.data.objects if obj.name == PREVIEW_PARENT_NAME
    ]
    for parent in parent_objects:
        bpy.data.objects.remove(parent, do_unlink=True)


def create_preview_cameras(context):
    """Create temporary camera objects for preview"""
    scene = context.scene
    center = get_scene_center(scene)
    camera_positions = calculate_camera_positions(
        center, scene.mcsr_distance, scene.mcsr_camera_count
    )

    # Create or get preview collection
    preview_collection = bpy.data.collections.get(PREVIEW_COLLECTION_NAME)
    if not preview_collection:
        preview_collection = bpy.data.collections.new(PREVIEW_COLLECTION_NAME)
        context.scene.collection.children.link(preview_collection)

    # Create parent empty object
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=center)
    parent_empty = context.active_object
    parent_empty.name = PREVIEW_PARENT_NAME
    parent_empty.empty_display_size = 0.5
    parent_empty.hide_render = True
    parent_empty.hide_select = True
    parent_empty.color = PREVIEW_COLOR

    # Move parent to preview collection
    if parent_empty.name in context.scene.collection.objects:
        context.scene.collection.objects.unlink(parent_empty)
    preview_collection.objects.link(parent_empty)

    # Create preview cameras
    for i, cam_location in enumerate(camera_positions):
        bpy.ops.object.camera_add(location=cam_location)
        camera = context.active_object
        camera.name = f"{PREVIEW_CAMERA_PREFIX}{i:02d}"

        camera.hide_render = True
        camera.hide_select = True
        camera.color = PREVIEW_COLOR

        apply_camera_settings(camera, scene)
        point_camera_at_target(camera, center)

        # Parent camera to the empty object and move to collection
        camera.parent = parent_empty
        if camera.name in context.scene.collection.objects:
            context.scene.collection.objects.unlink(camera)
        preview_collection.objects.link(camera)


def create_sprite_sheet_from_temp_files(
    temp_dir, camera_count, spacing, sprite_sheet_path
):
    """Create a sprite sheet from temporary render files, then delete them"""
    cols = math.ceil(math.sqrt(camera_count))
    rows = math.ceil(camera_count / cols)

    render_width = bpy.context.scene.render.resolution_x
    render_height = bpy.context.scene.render.resolution_y

    sheet_width = cols * render_width + (cols - 1) * spacing
    sheet_height = rows * render_height + (rows - 1) * spacing

    sprite_sheet = bpy.data.images.new(
        "sprite_sheet", sheet_width, sheet_height, alpha=True
    )
    pixels = [0.0] * (sheet_width * sheet_height * 4)  # RGBA

    temp_files = []
    for i in range(camera_count):
        col = i % cols
        row = i // cols

        img_path = os.path.join(temp_dir, f"temp_view_{i:02d}.png")
        temp_files.append(img_path)

        if os.path.exists(img_path):
            img = bpy.data.images.load(img_path)
            img_pixels = list(img.pixels)

            # Copy pixels to sprite sheet with Y-coordinate flipping for Blender
            for y in range(render_height):
                for x in range(render_width):
                    src_y = render_height - 1 - y
                    src_idx = (src_y * render_width + x) * 4

                    dest_x = col * (render_width + spacing) + x
                    dest_y = sheet_height - 1 - (row * (render_height + spacing) + y)
                    dest_idx = (dest_y * sheet_width + dest_x) * 4

                    if src_idx < len(img_pixels) and dest_idx < len(pixels):
                        pixels[dest_idx : dest_idx + 4] = img_pixels[
                            src_idx : src_idx + 4
                        ]

            bpy.data.images.remove(img)

    sprite_sheet.pixels = pixels
    sprite_sheet.filepath_raw = sprite_sheet_path
    sprite_sheet.file_format = "PNG"
    sprite_sheet.save()
    bpy.data.images.remove(sprite_sheet)

    # Clean up temporary files
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)


class TempDirectoryManager:
    """Context manager for creating and cleaning up temporary directories"""

    def __init__(self):
        self.temp_dir = None

    def __enter__(self):
        self.temp_dir = tempfile.mkdtemp()
        return self.temp_dir

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

