import bpy
import bmesh
import mathutils
import os
from mathutils import Vector
import math


class MultiViewRenderStillOperator(bpy.types.Operator):
    bl_idname = "mv.render_still"
    bl_label = "Render Multi-View Image"
    bl_description = "Renders current frame from multiple camera angles"

    def execute(self, context):
        scene = context.scene

        # Get properties
        camera_count = scene.mv_camera_count
        distance = scene.mv_distance
        spacing = scene.mv_spacing
        template_camera = scene.mv_template_camera
        output_path = bpy.path.abspath(scene.mv_output_path)

        if not output_path:
            self.report({"ERROR"}, "Please set output path")
            return {"CANCELLED"}

        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)

        # Store original camera
        original_camera = scene.camera

        # Get scene center (average of all object locations)
        center = Vector((0, 0, 0))
        if scene.objects:
            center = sum(
                [obj.location for obj in scene.objects if obj.type == "MESH"], Vector()
            ) / len([obj for obj in scene.objects if obj.type == "MESH"])

        # Create temporary cameras and render
        temp_cameras = []
        try:
            for i in range(camera_count):
                # Calculate angle for this camera
                angle = (i / camera_count) * 2 * 3.14159

                # Position camera in circle
                cam_location = Vector(
                    (
                        center.x + distance * math.cos(angle),
                        center.y + distance * math.sin(angle),
                        center.z,
                    )
                )

                # Create camera
                bpy.ops.object.camera_add(location=cam_location)
                camera = context.active_object
                temp_cameras.append(camera)
                
                # Copy settings from template camera if provided
                if template_camera and template_camera.data:
                    template_data = template_camera.data
                    camera_data = camera.data
                    
                    # Copy camera data properties
                    camera_data.type = template_data.type
                    camera_data.lens = template_data.lens
                    camera_data.ortho_scale = template_data.ortho_scale
                    camera_data.clip_start = template_data.clip_start
                    camera_data.clip_end = template_data.clip_end
                    camera_data.shift_x = template_data.shift_x
                    camera_data.shift_y = template_data.shift_y
                    camera_data.sensor_width = template_data.sensor_width
                    camera_data.sensor_height = template_data.sensor_height
                    camera_data.sensor_fit = template_data.sensor_fit

                # Point camera at center
                direction = center - cam_location
                camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

                # Set as active camera and render
                scene.camera = camera

                # Render
                filename = f"view_{i:02d}.png"
                filepath = os.path.join(output_path, filename)
                scene.render.filepath = filepath
                bpy.ops.render.render(write_still=True)

                self.report({"INFO"}, f"Rendered view {i+1}/{camera_count}")

        finally:
            # Cleanup: remove temporary cameras
            for camera in temp_cameras:
                bpy.data.objects.remove(camera, do_unlink=True)

            # Restore original camera
            scene.camera = original_camera

        # Create sprite sheet
        sprite_sheet_path = os.path.join(output_path, "sprite_sheet.png")
        self.create_sprite_sheet(output_path, camera_count, spacing, sprite_sheet_path)
        
        self.report(
            {"INFO"},
            f"Multi-view render complete! {camera_count} views saved to {output_path}",
        )
        return {"FINISHED"}


class MultiViewRenderAnimationOperator(bpy.types.Operator):
    bl_idname = "mv.render_animation"
    bl_label = "Render Multi-View Animation"
    bl_description = "Renders animation frames from multiple camera angles"

    def execute(self, context):
        scene = context.scene
        
        # Get properties
        camera_count = scene.mv_camera_count
        distance = scene.mv_distance
        spacing = scene.mv_spacing
        template_camera = scene.mv_template_camera
        frame_start = scene.frame_start
        frame_end = scene.frame_end
        output_path = bpy.path.abspath(scene.mv_output_path)
        
        if not output_path:
            self.report({"ERROR"}, "Please set output path")
            return {"CANCELLED"}
            
        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)
        
        # Store original camera and frame
        original_camera = scene.camera
        original_frame = scene.frame_current
        
        # Get scene center (average of all object locations)
        center = Vector((0, 0, 0))
        if scene.objects:
            center = sum(
                [obj.location for obj in scene.objects if obj.type == "MESH"], Vector()
            ) / len([obj for obj in scene.objects if obj.type == "MESH"])

        # Create temporary cameras and render
        temp_cameras = []
        try:
            # Render each frame
            for frame in range(frame_start, frame_end + 1):
                scene.frame_set(frame)
                
                # Create frame directory for animation
                frame_dir = os.path.join(output_path, f"frame_{frame:04d}")
                os.makedirs(frame_dir, exist_ok=True)
                
                # Clear existing cameras for this frame
                for camera in temp_cameras:
                    bpy.data.objects.remove(camera, do_unlink=True)
                temp_cameras = []
                
                for i in range(camera_count):
                    # Calculate angle for this camera
                    angle = (i / camera_count) * 2 * 3.14159

                    # Position camera in circle
                    cam_location = Vector(
                        (
                            center.x + distance * math.cos(angle),
                            center.y + distance * math.sin(angle),
                            center.z,
                        )
                    )

                    # Create camera
                    bpy.ops.object.camera_add(location=cam_location)
                    camera = context.active_object
                    temp_cameras.append(camera)
                    
                    # Copy settings from template camera if provided
                    if template_camera and template_camera.data:
                        # Copy all camera data properties automatically
                        camera.data.user_remap(template_camera.data)
                        camera.data = template_camera.data.copy()

                    # Point camera at center
                    direction = center - cam_location
                    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

                    # Set as active camera and render
                    scene.camera = camera

                    # Render
                    filename = f"view_{i:02d}.png"
                    filepath = os.path.join(frame_dir, filename)
                    scene.render.filepath = filepath
                    bpy.ops.render.render(write_still=True)

                    self.report({"INFO"}, f"Frame {frame}: Rendered view {i+1}/{camera_count}")

                # Create sprite sheet for this frame
                sprite_sheet_path = os.path.join(frame_dir, f"sprite_sheet_frame_{frame:04d}.png")
                self.create_sprite_sheet(frame_dir, camera_count, spacing, sprite_sheet_path)

        finally:
            # Cleanup: remove temporary cameras
            for camera in temp_cameras:
                bpy.data.objects.remove(camera, do_unlink=True)

            # Restore original camera and frame
            scene.camera = original_camera
            scene.frame_set(original_frame)

        frame_count = frame_end - frame_start + 1
        self.report(
            {"INFO"},
            f"Multi-view animation complete! {frame_count} frames × {camera_count} views saved to {output_path}",
        )
        return {"FINISHED"}
    
    def create_sprite_sheet(self, output_path, camera_count, spacing, sprite_sheet_path):
        """Create a sprite sheet from individual renders using direct pixel manipulation"""
        
        # Calculate grid dimensions (prefer square-ish layout)
        import math
        cols = math.ceil(math.sqrt(camera_count))
        rows = math.ceil(camera_count / cols)
        
        # Get render dimensions
        render_width = bpy.context.scene.render.resolution_x
        render_height = bpy.context.scene.render.resolution_y
        
        # Create sprite sheet dimensions with spacing
        sheet_width = cols * render_width + (cols - 1) * spacing
        sheet_height = rows * render_height + (rows - 1) * spacing
        
        # Create new image in Blender
        sprite_sheet = bpy.data.images.new("sprite_sheet", sheet_width, sheet_height, alpha=True)
        
        # Initialize with transparent pixels (RGBA = 0,0,0,0)
        pixels = [0.0] * (sheet_width * sheet_height * 4)  # RGBA
        
        # Load and position each rendered image
        for i in range(camera_count):
            # Calculate grid position
            col = i % cols
            row = i // cols
            
            # Load the rendered image
            img_path = os.path.join(output_path, f"view_{i:02d}.png")
            if os.path.exists(img_path):
                # Load image
                img = bpy.data.images.load(img_path)
                
                # Get pixel data
                img_pixels = list(img.pixels)
                
                # Copy pixels to sprite sheet (flip Y coordinate for Blender)
                for y in range(render_height):
                    for x in range(render_width):
                        # Source pixel index (Blender images are bottom-up)
                        src_y = render_height - 1 - y
                        src_idx = (src_y * render_width + x) * 4
                        
                        # Destination pixel index (also bottom-up) with spacing
                        dest_x = col * (render_width + spacing) + x
                        dest_y = sheet_height - 1 - (row * (render_height + spacing) + y)
                        dest_idx = (dest_y * sheet_width + dest_x) * 4
                        
                        # Copy RGBA values
                        if src_idx < len(img_pixels) and dest_idx < len(pixels):
                            pixels[dest_idx:dest_idx+4] = img_pixels[src_idx:src_idx+4]
                
                # Clean up loaded image
                bpy.data.images.remove(img)
        
        # Set pixel data to sprite sheet
        sprite_sheet.pixels = pixels
        
        # Save sprite sheet
        sprite_sheet.filepath_raw = sprite_sheet_path
        sprite_sheet.file_format = 'PNG'
        sprite_sheet.save()
        
        # Clean up sprite sheet from memory
        bpy.data.images.remove(sprite_sheet)
    
    def create_sprite_sheet(self, output_path, camera_count, spacing, sprite_sheet_path):
        """Create a sprite sheet from individual renders using direct pixel manipulation"""
        
        # Calculate grid dimensions (prefer square-ish layout)
        import math
        cols = math.ceil(math.sqrt(camera_count))
        rows = math.ceil(camera_count / cols)
        
        # Get render dimensions
        render_width = bpy.context.scene.render.resolution_x
        render_height = bpy.context.scene.render.resolution_y
        
        # Create sprite sheet dimensions with spacing
        sheet_width = cols * render_width + (cols - 1) * spacing
        sheet_height = rows * render_height + (rows - 1) * spacing
        
        # Create new image in Blender
        sprite_sheet = bpy.data.images.new("sprite_sheet", sheet_width, sheet_height, alpha=True)
        
        # Initialize with transparent pixels (RGBA = 0,0,0,0)
        pixels = [0.0] * (sheet_width * sheet_height * 4)  # RGBA
        
        # Load and position each rendered image
        for i in range(camera_count):
            # Calculate grid position
            col = i % cols
            row = i // cols
            
            # Load the rendered image
            img_path = os.path.join(output_path, f"view_{i:02d}.png")
            if os.path.exists(img_path):
                # Load image
                img = bpy.data.images.load(img_path)
                
                # Get pixel data
                img_pixels = list(img.pixels)
                
                # Copy pixels to sprite sheet (flip Y coordinate for Blender)
                for y in range(render_height):
                    for x in range(render_width):
                        # Source pixel index (Blender images are bottom-up)
                        src_y = render_height - 1 - y
                        src_idx = (src_y * render_width + x) * 4
                        
                        # Destination pixel index (also bottom-up) with spacing
                        dest_x = col * (render_width + spacing) + x
                        dest_y = sheet_height - 1 - (row * (render_height + spacing) + y)
                        dest_idx = (dest_y * sheet_width + dest_x) * 4
                        
                        # Copy RGBA values
                        if src_idx < len(img_pixels) and dest_idx < len(pixels):
                            pixels[dest_idx:dest_idx+4] = img_pixels[src_idx:src_idx+4]
                
                # Clean up loaded image
                bpy.data.images.remove(img)
        
        # Set pixel data to sprite sheet
        sprite_sheet.pixels = pixels
        
        # Save sprite sheet
        sprite_sheet.filepath_raw = sprite_sheet_path
        sprite_sheet.file_format = 'PNG'
        sprite_sheet.save()
        
        # Clean up sprite sheet from memory
        bpy.data.images.remove(sprite_sheet)


class TogglePreviewOperator(bpy.types.Operator):
    bl_idname = "mv.toggle_preview"
    bl_label = "Toggle Preview"
    bl_description = "Toggle camera preview in viewport"

    def execute(self, context):
        scene = context.scene
        scene.mv_show_preview = not scene.mv_show_preview
        
        print(f"Preview toggled to: {scene.mv_show_preview}")
        
        # Toggle preview directly
        self.toggle_preview(context)
        
        return {"FINISHED"}
    
    def toggle_preview(self, context):
        """Toggle preview on/off using temporary camera objects"""
        import bpy
        
        # Clean up existing preview cameras
        self.cleanup_preview_cameras()
        
        if context.scene.mv_show_preview:
            # Create preview cameras
            self.create_preview_cameras(context)
        
        # Force viewport update
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    
    def cleanup_preview_cameras(self):
        """Remove any existing preview cameras"""
        import bpy
        
        # Remove cameras with our special naming
        cameras_to_remove = [obj for obj in bpy.data.objects if obj.name.startswith("MV_Preview_Camera_")]
        
        for cam in cameras_to_remove:
            bpy.data.objects.remove(cam, do_unlink=True)
    
    def create_preview_cameras(self, context):
        """Create temporary camera objects for preview"""
        import bpy
        scene = context.scene
        
        # Get properties
        camera_count = scene.mv_camera_count
        distance = scene.mv_distance
        template_camera = scene.mv_template_camera
        
        # Get scene center (same calculation as in operator)
        center = Vector((0, 0, 0))
        if scene.objects:
            mesh_objects = [obj for obj in scene.objects if obj.type == 'MESH']
            if mesh_objects:
                center = sum([obj.location for obj in mesh_objects], Vector()) / len(mesh_objects)
        
        # Create preview cameras
        for i in range(camera_count):
            # Calculate angle for this camera
            angle = (i / camera_count) * 2 * math.pi
            
            # Position camera in circle
            cam_location = Vector((
                center.x + distance * math.cos(angle),
                center.y + distance * math.sin(angle),
                center.z
            ))
            
            # Create camera
            bpy.ops.object.camera_add(location=cam_location)
            camera = context.active_object
            camera.name = f"MV_Preview_Camera_{i:02d}"
            
            # Hide from render but keep visible in viewport
            camera.hide_render = True
            camera.hide_select = True  # Hide from selection but keep visible
            
            # Copy settings from template camera if provided
            if template_camera and template_camera.data:
                # Copy all camera data properties automatically
                camera.data.user_remap(template_camera.data)
                camera.data = template_camera.data.copy()
            
            # Point camera at center
            direction = center - cam_location
            camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
            
            # Set camera color to orange for preview
            camera.color = (1.0, 0.5, 0.0, 1.0)



