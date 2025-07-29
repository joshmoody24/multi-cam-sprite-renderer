@tool
extends Resource
class_name MCSRMaterialHelper

# Helper class for creating materials with normal maps for MCSR sprites

static func create_2d_material(diffuse_texture: Texture2D, normal_texture: Texture2D = null) -> CanvasItemMaterial:
	var material = CanvasItemMaterial.new()
	
	if normal_texture != null:
		material.normal_texture = normal_texture
		# Enable normal mapping
		material.light_mode = CanvasItemMaterial.LIGHT_MODE_NORMAL
	else:
		material.light_mode = CanvasItemMaterial.LIGHT_MODE_INHERIT
	
	return material

static func create_3d_material(diffuse_texture: Texture2D, normal_texture: Texture2D = null) -> StandardMaterial3D:
	var material = StandardMaterial3D.new()
	
	# Set the albedo texture
	material.albedo_texture = diffuse_texture
	material.flags_unshaded = false
	
	if normal_texture != null:
		material.normal_enabled = true
		material.normal_texture = normal_texture
	
	# Configure for billboard/sprite usage
	material.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	material.flags_transparent = true
	material.flags_albedo_tex_force_srgb = true
	
	return material

static func create_sprite_frames_with_materials(
	metadata: Dictionary, 
	metadata_path: String, 
	options: Dictionary
) -> Array:
	# Returns [SpriteFrames, CanvasItemMaterial or StandardMaterial3D]
	var sprite_frames = SpriteFrames.new()
	var material = null
	
	# Get metadata information
	var fps = metadata.get("fps", 24)
	var frame_dimensions = metadata.get("frameDimensions", {})
	var frame_width = frame_dimensions.get("width", 1024)
	var frame_height = frame_dimensions.get("height", 1024)
	var passes = metadata.get("passes", [])
	var actions = metadata.get("actions", [])
	
	# Get base directory for finding sprite sheet images
	var base_dir = metadata_path.get_base_dir()
	
	# Load textures for the first action and specified camera angle
	var diffuse_texture = null
	var normal_texture = null
	var camera_angle = options.get("camera_angle", 0)
	
	if actions.size() > 0:
		var first_action = actions[0].get("name", "default")
		diffuse_texture = _load_sprite_sheet_texture(base_dir, first_action, "diffuse", camera_angle)
		
		if "normal" in passes:
			normal_texture = _load_sprite_sheet_texture(base_dir, first_action, "normal", camera_angle)
	
	# Create material based on import mode
	if options.get("create_normal_material", true) and diffuse_texture != null:
		var import_mode = options.get("import_mode", 0)
		
		if import_mode == 0: # MODE_2D
			material = create_2d_material(diffuse_texture, normal_texture)
		else: # MODE_3D_BILLBOARD
			material = create_3d_material(diffuse_texture, normal_texture)
	
	# Process each action as an animation
	for action in actions:
		var action_name = action.get("name", "default")
		var sprites = action.get("sprites", [])
		
		# Create animation in SpriteFrames
		sprite_frames.add_animation(action_name)
		sprite_frames.set_animation_loop(action_name, options.get("loop_animations", true))
		sprite_frames.set_animation_speed(action_name, fps)
		
		# Load the sprite sheet texture for this action and camera angle
		var action_diffuse_texture = _load_sprite_sheet_texture(base_dir, action_name, "diffuse", camera_angle)
		if action_diffuse_texture == null:
			print("Warning: Could not load diffuse texture for action: ", action_name)
			continue
		
		# Add frames to the animation
		for sprite in sprites:
			var x = sprite.get("x", 0)
			var y = sprite.get("y", 0)
			var frame_count = sprite.get("frames", 1)
			
			# Create AtlasTexture for this frame
			var atlas_texture = AtlasTexture.new()
			atlas_texture.atlas = action_diffuse_texture
			atlas_texture.region = Rect2(x, y, frame_width, frame_height)
			
			# Add frame multiple times based on frame_count for duration
			for i in range(frame_count):
				sprite_frames.add_frame(action_name, atlas_texture)
	
	# If no animations were created, create a default one
	if sprite_frames.get_animation_names().is_empty():
		sprite_frames.add_animation("default")
		print("Warning: No animations found in metadata, created default animation")
	
	return [sprite_frames, material]

static func _load_sprite_sheet_texture(base_dir: String, action_name: String, pass_name: String, camera_angle: int = 0) -> Texture2D:
	# Try multiple possible paths for the sprite sheet
	var camera_folder = "camera_" + str(camera_angle)
	var possible_paths = [
		base_dir + "/" + action_name + "/" + camera_folder + "/" + pass_name + ".png",
		base_dir + "/" + action_name + "/camera_0/" + pass_name + ".png",  # Fallback to camera_0
		base_dir + "/" + action_name + "/" + pass_name + ".png",
		base_dir + "/" + pass_name + ".png"
	]
	
	for path in possible_paths:
		if FileAccess.file_exists(path):
			var texture = load(path) as Texture2D
			if texture != null:
				return texture
	
	print("Warning: Could not find sprite sheet at any expected path for action: ", action_name, ", pass: ", pass_name, ", camera: ", camera_angle)
	return null