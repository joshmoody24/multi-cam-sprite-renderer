import bpy
from bpy.props import IntProperty, FloatProperty, StringProperty, BoolProperty


def update_preview(self, context):
    """Update preview when settings change"""
    if not hasattr(context.scene, 'mv_show_preview') or not context.scene.mv_show_preview:
        return
    
    # Clean up existing preview cameras
    cameras_to_remove = [obj for obj in bpy.data.objects if obj.name.startswith("MV_Preview_Camera_")]
    for cam in cameras_to_remove:
        bpy.data.objects.remove(cam, do_unlink=True)
    
    # Recreate preview cameras with new settings
    import math
    from mathutils import Vector
    
    scene = context.scene
    camera_count = scene.mv_camera_count
    distance = scene.mv_distance
    template_camera = getattr(scene, 'mv_template_camera', None)
    
    # Get scene center
    center = Vector((0, 0, 0))
    if scene.objects:
        mesh_objects = [obj for obj in scene.objects if obj.type == 'MESH']
        if mesh_objects:
            center = sum([obj.location for obj in mesh_objects], Vector()) / len(mesh_objects)
    
    # Create new preview cameras
    for i in range(camera_count):
        angle = (i / camera_count) * 2 * math.pi
        cam_location = Vector((
            center.x + distance * math.cos(angle),
            center.y + distance * math.sin(angle),
            center.z
        ))
        
        bpy.ops.object.camera_add(location=cam_location)
        camera = context.active_object
        camera.name = f"MV_Preview_Camera_{i:02d}"
        camera.hide_render = True
        camera.hide_select = True
        camera.color = (1.0, 0.5, 0.0, 1.0)
        
        # Copy settings from template camera if provided
        if template_camera and template_camera.data:
            # Copy all camera data properties automatically
            camera.data.user_remap(template_camera.data)
            camera.data = template_camera.data.copy()
        
        # Point at center
        direction = center - cam_location
        camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

def register_properties():
    bpy.types.Scene.mv_camera_count = IntProperty(
        name="Camera Count",
        description="Number of cameras to render from",
        default=6,
        min=3,
        max=24,
        update=update_preview
    )
    
    bpy.types.Scene.mv_distance = FloatProperty(
        name="Distance",
        description="Distance from center to cameras",
        default=5.0,
        min=0.1,
        max=100.0,
        update=update_preview
    )
    
    bpy.types.Scene.mv_output_path = StringProperty(
        name="Output Path",
        description="Directory to save rendered images",
        default="//renders/",
        subtype='DIR_PATH'
    )
    
    bpy.types.Scene.mv_spacing = IntProperty(
        name="Sprite Spacing",
        description="Pixels between each sprite in the sheet",
        default=1,
        min=0,
        max=50
    )
    
    bpy.types.Scene.mv_template_camera = bpy.props.PointerProperty(
        name="Template Camera",
        description="Camera to copy settings from",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'CAMERA'
    )
    
    bpy.types.Scene.mv_show_preview = BoolProperty(
        name="Show Preview",
        description="Show camera positions in viewport",
        default=False
    )


def unregister_properties():
    # Clean up any preview cameras
    cameras_to_remove = [obj for obj in bpy.data.objects if obj.name.startswith("MV_Preview_Camera_")]
    for cam in cameras_to_remove:
        bpy.data.objects.remove(cam, do_unlink=True)
    
    del bpy.types.Scene.mv_camera_count
    del bpy.types.Scene.mv_distance
    del bpy.types.Scene.mv_output_path
    del bpy.types.Scene.mv_spacing
    del bpy.types.Scene.mv_template_camera
    del bpy.types.Scene.mv_show_preview


class MultiViewPanel(bpy.types.Panel):
    bl_label = "Multi-View Renderer"
    bl_idname = "MV_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MultiView"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "mv_camera_count")
        layout.prop(scene, "mv_distance")
        layout.prop(scene, "mv_spacing")
        layout.prop(scene, "mv_template_camera")
        
        # Show camera settings if template camera is selected
        if scene.mv_template_camera:
            layout.separator()
            layout.label(text="Camera Settings:")
            cam_data = scene.mv_template_camera.data
            layout.prop(cam_data, "type")
            if cam_data.type == 'ORTHO':
                layout.prop(cam_data, "ortho_scale")
            else:
                layout.prop(cam_data, "lens")
            layout.prop(cam_data, "clip_start")
            layout.prop(cam_data, "clip_end")
        
        layout.prop(scene, "mv_output_path")

        layout.separator()
        
        # Preview button with different text based on state
        if scene.mv_show_preview:
            layout.operator("mv.toggle_preview", text="Hide Preview", icon="HIDE_OFF")
        else:
            layout.operator("mv.toggle_preview", text="Show Preview", icon="HIDE_ON")
            
        layout.separator()
        
        # Two render buttons like Blender's default
        layout.operator("mv.render_still", text="Render Image", icon="RENDER_STILL")
        layout.operator("mv.render_animation", text="Render Animation", icon="RENDER_ANIMATION")