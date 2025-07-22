"""Utility functions shared across the Multi-Cam Sprite Renderer addon"""

import bpy
import math
import os
import tempfile
import shutil
import glob
from bpy.types import CompositorNodeOutputFile
from mathutils import Vector
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .mcsr_types import McsrScene

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
    temp_dir, camera_count, spacing, sprite_sheet_path, pass_name="lit"
):
    """Create a sprite sheet from temporary render files, then delete them"""
    cols = math.ceil(math.sqrt(camera_count))
    rows = math.ceil(camera_count / cols)

    assert bpy.context.scene is not None, "No active scene found in context"

    # Get actual rendered image dimensions from the first image file
    # instead of using scene settings (which don't account for render percentage)
    actual_img_width = None
    actual_img_height = None

    # Find the first existing image to get actual dimensions
    # Scan the temp directory for files matching the pass pattern
    pattern = os.path.join(temp_dir, f"*_{pass_name}*.png")
    matching_files = glob.glob(pattern)

    if matching_files:
        # Use the first matching file to get dimensions
        img_path = matching_files[0]
        img = bpy.data.images.load(img_path)
        actual_img_width, actual_img_height = img.size
        bpy.data.images.remove(img)
    else:
        actual_img_width = None
        actual_img_height = None

    assert (
        actual_img_width is not None and actual_img_height is not None
    ), "No rendered images found to determine dimensions."

    # Use actual image dimensions for sprite sheet layout
    sheet_width = cols * actual_img_width + (cols - 1) * spacing
    sheet_height = rows * actual_img_height + (rows - 1) * spacing

    sprite_sheet = bpy.data.images.new(
        "sprite_sheet", sheet_width, sheet_height, alpha=True
    )
    pixels = [0.0] * (sheet_width * sheet_height * 4)  # RGBA

    # Get all files for this pass and sort them
    pattern = os.path.join(temp_dir, f"*_{pass_name}*.png")
    temp_files = sorted(glob.glob(pattern))

    for i in range(camera_count):
        col = i % cols
        row = i // cols

        if i < len(temp_files):
            img_path = temp_files[i]

            if os.path.exists(img_path):
                img = bpy.data.images.load(img_path)
                img_pixels = list(img.pixels)  # type: ignore[arg-type]

                # Use actual image dimensions for pixel copying
                actual_width, actual_height = img.size
                copy_width = actual_width
                copy_height = actual_height

                # Calculate position in sprite sheet
                start_x = col * (actual_img_width + spacing)
                start_y = row * (actual_img_height + spacing)

                # Copy pixels to sprite sheet with Y-coordinate flipping for Blender
                for y in range(copy_height):
                    for x in range(copy_width):
                        src_y = actual_height - 1 - y
                        src_idx = (src_y * actual_width + x) * 4

                        dest_x = start_x + x
                        dest_y = sheet_height - 1 - (start_y + y)
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


def get_enabled_passes(scene) -> list[str]:
    """Get list of enabled render passes from scene properties"""
    passes = []
    if scene.mcsr_render_lit:
        passes.append("lit")
    if scene.mcsr_render_diffuse:
        passes.append("diffuse")
    if scene.mcsr_render_specular:
        passes.append("specular")
    if scene.mcsr_render_normal:
        passes.append("normal")
    return passes


def cleanup_compositor_nodes(scene: bpy.types.Scene) -> None:
    """Remove MCSR-created compositor nodes"""
    assert scene.node_tree is not None, "Scene node tree is None when cleaning up nodes"
    nodes_to_remove = []
    for node in scene.node_tree.nodes:
        if node.name.startswith("MCSR_"):
            nodes_to_remove.append(node)

    for node in nodes_to_remove:
        scene.node_tree.nodes.remove(node)


def update_compositor_file_paths(
    scene: bpy.types.Scene, passes: list[str], camera_index: int
) -> None:
    """Update compositor file output paths for a specific camera"""
    assert scene.node_tree is not None, "Scene node tree is None"

    for pass_name in passes:
        node_name = f"MCSR_Output_{pass_name}"
        assert (
            node_name in scene.node_tree.nodes
        ), f"Compositor node {node_name} not found"
        file_output = scene.node_tree.nodes[node_name]
        # Don't clear slots - just update the path of the existing slot
        assert file_output.file_slots, f"No file slots found in {node_name}"
        file_output.file_slots[0].path = f"temp_view_{camera_index:02d}_{pass_name}"


def setup_compositor_nodes(
    scene: bpy.types.Scene, temp_dir: str, passes: list[str]
) -> None:
    """Setup compositor nodes for multi-pass rendering"""

    # Enable compositor
    scene.use_nodes = True
    assert scene.node_tree is not None, "Scene node tree is None after enabling nodes"
    nodes = scene.node_tree.nodes
    links = scene.node_tree.links

    # Clean up existing MCSR nodes
    cleanup_compositor_nodes(scene)

    # Enable required render passes
    view_layer = scene.view_layers[0]
    if "diffuse" in passes:
        view_layer.use_pass_diffuse_color = True
    if "specular" in passes:
        view_layer.use_pass_glossy_color = True
    if "normal" in passes:
        view_layer.use_pass_normal = True

    # Create render layers node
    render_layers = nodes.new(type="CompositorNodeRLayers")
    render_layers.name = "MCSR_RenderLayers"
    render_layers.location = (0, 0)

    # If normal pass is enabled, create the nodes to transform the normals to camera-space
    if "normal" in passes:
        create_normal_transform_nodes(scene, render_layers, 400, 0)

    # Create file output node for each pass
    x_offset = 400
    y_offset = 0

    for pass_name in passes:
        file_output: CompositorNodeOutputFile = nodes.new(
            type="CompositorNodeOutputFile"
        )
        file_output.name = f"MCSR_Output_{pass_name}"
        file_output.label = f"MCSR {pass_name.title()}"
        file_output.location = (x_offset, y_offset)
        file_output.base_path = temp_dir
        file_output.format.file_format = "PNG"
        file_output.format.color_mode = "RGBA"
        file_output.format.color_depth = "8"

        # Clear default input and add named input
        file_output.file_slots.clear()
        slot = file_output.file_slots.new(f"temp_view_00_{pass_name}")

        # Connect appropriate output to file output
        if pass_name == "lit":
            links.new(render_layers.outputs["Image"], file_output.inputs[0])
        elif pass_name == "diffuse":
            # Use Set Alpha node to ensure proper alpha channel
            set_alpha = nodes.new(type="CompositorNodeSetAlpha")
            set_alpha.name = f"MCSR_SetAlpha_{pass_name}"
            set_alpha.location = (x_offset - 100, y_offset)

            links.new(render_layers.outputs["DiffCol"], set_alpha.inputs["Image"])
            links.new(render_layers.outputs["Alpha"], set_alpha.inputs["Alpha"])
            links.new(set_alpha.outputs["Image"], file_output.inputs[0])
        elif pass_name == "specular":
            # Use Set Alpha node to ensure proper alpha channel
            set_alpha = nodes.new(type="CompositorNodeSetAlpha")
            set_alpha.name = f"MCSR_SetAlpha_{pass_name}"
            set_alpha.location = (x_offset - 100, y_offset)

            links.new(render_layers.outputs["GlossCol"], set_alpha.inputs["Image"])
            links.new(render_layers.outputs["Alpha"], set_alpha.inputs["Alpha"])
            links.new(set_alpha.outputs["Image"], file_output.inputs[0])
        elif pass_name == "normal":
            # Connect to already created normal transform nodes
            normal_transform_output = scene.node_tree.nodes["MCSR_SetAlphaNorm"].outputs["Image"]
            links.new(normal_transform_output, file_output.inputs[0])

        y_offset -= 200


def create_normal_transform_nodes(
    scene: bpy.types.Scene,
    render_layers: bpy.types.Node,
    x_offset: int,
    y_offset: int,
):
    """World‑space **Normal** → camera‑space compositor chain (matrix version).

    Of course Blender 4.5 adds a vector math node to the compositor
    the DAY AFTER I raw dogged all the math with scalars. But I'm
    keeping it this way for backwards compatibility.

    Blender’s *Normal* render‑pass is world‑space, so we must multiply each
    pixel’s normal by the camera’s rotation matrix **R = (world→camera)**.  A
    pure rotation keeps lengths, so the inverse‑transpose is just `R`.  The
    only tricky bit: **`Matrix[i]` in *mathutils* returns a *column*, not a row.**
    We therefore feed **`Rᵀ` (the transpose)** into the nine Value nodes so
    that each dot‑product uses the correct row.

    Pipeline
    ========
    1. **SeparateXYZ** → Nx, Ny, Nz
    2. For each camera axis (row of Rᵀ) build `dot(N, row)` via three *MULTIPLY*
       and two *ADD* nodes → Cx, Cy, Cz
    3. **Negate Cz** (Blender camera looks down −Z, but we want +Z = blue)
    4. Remap −1…1 → 0…1 (×0.5 + 0.5)
    5. **CombineXYZ** → **Set Alpha** (restore RenderLayers alpha)

    The caller should populate the nine **MCSR_Rij** Value nodes each render:

    ```python
    R = cam.matrix_world.inverted().to_3x3().transposed()  # NOTE: transpose!
    R[2] *= -1  # flip forward row so +Z faces camera
    for r in range(3):
        for c in range(3):
            nt.nodes[f"MCSR_R{r}{c}"].outputs[0].default_value = R[r][c]
    ```
    """

    nt = scene.node_tree
    nodes, links = nt.nodes, nt.links

    # ───────────────────────────── 0. Separate world normal
    sep = nodes.new("CompositorNodeSeparateXYZ")
    sep.name = "MCSR_SepWorldNormal"
    sep.location = (x_offset - 400, y_offset + 200)
    links.new(render_layers.outputs["Normal"], sep.inputs[0])

    # Helper to create spaced Math nodes
    def math_node(op, px, py, name=""):
        m = nodes.new("CompositorNodeMath")
        m.operation = op
        m.location = (px, py)
        m.name = name or f"MCSR_Math_{op}_{px}_{py}"
        return m

    # ───────────────────────────── 1. Matrix Value nodes (spaced in a 3×3 grid)
    rot_values = {}
    cell_w, cell_h = 120, 110  # spacing grid
    base_x, base_y = x_offset - 900, y_offset + 350
    for r in range(3):
        for c in range(3):
            v = nodes.new("CompositorNodeValue")
            v.name = f"MCSR_R{r}{c}"
            v.label = f"R{r}{c}"
            v.location = (base_x + c * cell_w, base_y - r * cell_h)
            rot_values[(r, c)] = v

    # ───────────────────────────── 2. Dot‑product builder
    def build_dot(axis, px, py):
        mul0 = math_node("MULTIPLY", px, py)
        mul1 = math_node("MULTIPLY", px, py - 60)
        mul2 = math_node("MULTIPLY", px, py - 120)
        add0 = math_node("ADD", px + 140, py - 30)
        add1 = math_node("ADD", px + 280, py - 30)

        links.new(sep.outputs["X"], mul0.inputs[0])
        links.new(rot_values[(axis, 0)].outputs[0], mul0.inputs[1])
        links.new(sep.outputs["Y"], mul1.inputs[0])
        links.new(rot_values[(axis, 1)].outputs[0], mul1.inputs[1])
        links.new(sep.outputs["Z"], mul2.inputs[0])
        links.new(rot_values[(axis, 2)].outputs[0], mul2.inputs[1])

        links.new(mul0.outputs[0], add0.inputs[0])
        links.new(mul1.outputs[0], add0.inputs[1])
        links.new(add0.outputs[0], add1.inputs[0])
        links.new(mul2.outputs[0], add1.inputs[1])
        return add1

    cam_x = build_dot(0, x_offset - 120, y_offset + 180)
    cam_y = build_dot(1, x_offset - 120, y_offset + 20)
    cam_z = build_dot(2, x_offset - 120, y_offset - 140)

    # ───────────────────────────── 3. Negate Cz then remap
    neg_z = math_node("MULTIPLY", x_offset + 200, y_offset - 100, "MCSR_NegZ")
    neg_z.inputs[1].default_value = -1.0
    links.new(cam_z.outputs[0], neg_z.inputs[0])

    def remap(src, px, py):
        mul = math_node("MULTIPLY", px, py)
        mul.inputs[1].default_value = 0.5
        add = math_node("ADD", px + 140, py)
        add.inputs[1].default_value = 0.5
        links.new(src.outputs[0], mul.inputs[0])
        links.new(mul.outputs[0], add.inputs[0])
        return add

    rem_x = remap(cam_x, x_offset + 420, y_offset + 180)
    rem_y = remap(cam_y, x_offset + 420, y_offset + 20)
    rem_z = remap(neg_z, x_offset + 420, y_offset - 100)

    # ───────────────────────────── 4. Combine & Alpha restore (spaced)
    comb = nodes.new("CompositorNodeCombineXYZ")
    comb.name = "MCSR_CombineCamNorm"
    comb.location = (x_offset + 680, y_offset + 60)
    links.new(rem_x.outputs[0], comb.inputs[0])
    links.new(rem_y.outputs[0], comb.inputs[1])
    links.new(rem_z.outputs[0], comb.inputs[2])

    set_alpha = nodes.new("CompositorNodeSetAlpha")
    set_alpha.name = "MCSR_SetAlphaNorm"
    set_alpha.location = (x_offset + 940, y_offset + 60)
    links.new(comb.outputs[0], set_alpha.inputs["Image"])
    links.new(render_layers.outputs["Alpha"], set_alpha.inputs["Alpha"])

    return set_alpha.outputs["Image"]


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
