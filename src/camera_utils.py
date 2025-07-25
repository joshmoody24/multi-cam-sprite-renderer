"""Camera reference system utilities for Multi-Cam Sprite Renderer"""

import bpy
from mathutils import Matrix
import math
from .constants import (
    PREVIEW_COLLECTION_NAME,
    PREVIEW_PARENT_NAME,
    PREVIEW_CAMERA_PREFIX,
    PREVIEW_COLOR,
)
from .mcsr_types import get_mcsr_object


def clone_camera(reference_camera):
    """Create a new camera with the same settings as the reference camera"""
    if not reference_camera:
        raise ValueError("Reference camera is required")

    new_camera = bpy.data.objects.new(
        name="MCSR_Temp_Camera", object_data=reference_camera.data.copy()
    )
    new_camera.rotation_euler = reference_camera.rotation_euler.copy()
    assert bpy.context.scene is not None, "Scene context is required"
    bpy.context.scene.collection.objects.link(new_camera)
    return new_camera


def calculate_camera_positions(
    center,
    camera_angles,
    reference_camera,
    include_reference=True,
):
    """Generate camera positions around center point, preserving reference camera orientation

    Args:
        center: Center point to rotate around
        camera_angles: List of angles in radians
        reference_camera: Camera to use as reference for position and orientation
        include_reference: If True, includes reference position and spaces remaining positions.

    Returns:
        List of tuples (position, rotation), where rotation is a euler rotation
    """
    if not reference_camera:
        raise ValueError("Reference camera is required")

    positions = []
    ref_to_center = center - reference_camera.location
    ref_rotation = reference_camera.rotation_euler.copy()

    # The first angle is always the reference position
    if include_reference:
        positions.append((reference_camera.location.copy(), ref_rotation.copy()))

    # Start from the second angle if including the reference
    start_index = 1 if include_reference else 0
    for i in range(start_index, len(camera_angles)):
        angle_rad = camera_angles[i].angle
        rotation_matrix = Matrix.Rotation(angle_rad, 4, "Z")

        # Calculate position
        offset = rotation_matrix @ ref_to_center
        position = center - offset

        # Calculate rotation by applying the same angle to reference rotation
        rotation = ref_rotation.copy()
        rotation.rotate(rotation_matrix)

        positions.append((position, rotation))

    return positions


def create_preview_cameras(context):
    """Create preview cameras using object settings"""
    scene = context.scene
    target_object = get_mcsr_object(scene.mcsr_active_object)

    if not target_object or not target_object.mcsr.reference_camera:
        return

    # Create preview collection if it doesn't exist
    preview_collection = bpy.data.collections.get(PREVIEW_COLLECTION_NAME)
    if not preview_collection:
        preview_collection = bpy.data.collections.new(PREVIEW_COLLECTION_NAME)
        context.scene.collection.children.link(preview_collection)

    # Create parent empty object
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=target_object.location)
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

    # Calculate camera positions
    center = target_object.location
    camera_angles = target_object.mcsr.camera_angles
    reference_camera = target_object.mcsr.reference_camera
    camera_positions = calculate_camera_positions(
        center, camera_angles, reference_camera, include_reference=False
    )

    # Create preview cameras
    for i, (position, rotation) in enumerate(camera_positions):
        camera = clone_camera(reference_camera)
        camera.name = f"{PREVIEW_CAMERA_PREFIX}{i:02d}"

        camera.hide_render = True
        camera.hide_select = True
        camera.color = PREVIEW_COLOR

        # Parent camera to the empty object and move to collection
        camera.parent = parent_empty
        if camera.name in context.scene.collection.objects:
            context.scene.collection.objects.unlink(camera)
        preview_collection.objects.link(camera)

        # Construct and set the world matrix AFTER parenting
        # This ensures the camera is positioned correctly in world space
        world_matrix = Matrix.Translation(position) @ rotation.to_matrix().to_4x4()
        camera.matrix_world = world_matrix
