@tool
extends EditorImportPlugin

const MCSRMaterialHelper = preload("mcsr_material_helper.gd")

enum ImportMode {
	MODE_2D,
	MODE_3D_BILLBOARD
}

func _get_importer_name():
	return "mcsr_sprite_importer"

func _get_visible_name():
	return "MCSR Sprite Sheet"

func _get_recognized_extensions():
	return ["json"]

func _get_save_extension():
	return "tres"

func _get_resource_type():
	return "SpriteFrames"

func _get_preset_count():
	return 2

func _get_preset_name(preset_index):
	match preset_index:
		0:
			return "2D Mode"
		1:
			return "3D Billboard Mode"
		_:
			return "Unknown"

func _get_import_options(path, preset_index):
	match preset_index:
		0: # 2D Mode
			return [
				{"name": "import_mode", "default_value": ImportMode.MODE_2D},
				{"name": "create_normal_material", "default_value": true},
				{"name": "loop_animations", "default_value": true},
				{"name": "camera_angle", "default_value": 0, "property_hint": PROPERTY_HINT_RANGE, "hint_string": "0,7,1"},
				{"name": "create_scene", "default_value": false}
			]
		1: # 3D Billboard Mode
			return [
				{"name": "import_mode", "default_value": ImportMode.MODE_3D_BILLBOARD},
				{"name": "create_normal_material", "default_value": true},
				{"name": "loop_animations", "default_value": true},
				{"name": "camera_angle", "default_value": 0, "property_hint": PROPERTY_HINT_RANGE, "hint_string": "0,7,1"},
				{"name": "create_scene", "default_value": false}
			]
		_:
			return []

func _get_option_visibility(path, option_name, options):
	return true

func _get_import_order():
	return 100

func _get_priority():
	return 1.0

func _import(source_file, save_path, options, platform_variants, gen_files):
	# Check if this is actually a metadata.json file from MCSR
	if not _is_mcsr_metadata_file(source_file):
		return ERR_FILE_UNRECOGNIZED
	
	# Parse the metadata
	var metadata = _parse_metadata_file(source_file)
	if metadata == null:
		print("Error: Failed to parse metadata file: ", source_file)
		return ERR_FILE_CORRUPT
	
	# Create SpriteFrames resource and material using the helper
	var result = MCSRMaterialHelper.create_sprite_frames_with_materials(metadata, source_file, options)
	var sprite_frames = result[0]
	var material = result[1]
	
	if sprite_frames == null:
		print("Error: Failed to create SpriteFrames from metadata")
		return ERR_FILE_CORRUPT
	
	# Save the SpriteFrames resource
	var sprite_frames_path = save_path + "." + _get_save_extension()
	var save_result = ResourceSaver.save(sprite_frames, sprite_frames_path)
	
	if save_result != OK:
		print("Error: Failed to save SpriteFrames resource: ", save_result)
		return save_result
	
	# Save the material if one was created
	if material != null:
		var material_path = save_path + "_material.tres"
		var material_save_result = ResourceSaver.save(material, material_path)
		
		if material_save_result == OK:
			gen_files.append(material_path)
			print("Successfully saved material: ", material_path)
		else:
			print("Warning: Failed to save material: ", material_save_result)
	
	# Create scene if requested
	if options.get("create_scene", false):
		var scene_path = save_path + "_scene.tscn"
		var scene_result = _create_sample_scene(sprite_frames, material, options, scene_path)
		
		if scene_result == OK:
			gen_files.append(scene_path)
			print("Successfully created sample scene: ", scene_path)
		else:
			print("Warning: Failed to create sample scene: ", scene_result)
	
	print("Successfully imported MCSR sprite sheet: ", sprite_frames_path)
	return OK

func _create_sample_scene(sprite_frames: SpriteFrames, material: Material, options: Dictionary, scene_path: String) -> int:
	var scene = PackedScene.new()
	var root_node
	
	var import_mode = options.get("import_mode", ImportMode.MODE_2D)
	
	if import_mode == ImportMode.MODE_2D:
		# Create 2D scene with AnimatedSprite2D
		root_node = Node2D.new()
		root_node.name = "MCSRSprite2D"
		
		var animated_sprite = AnimatedSprite2D.new()
		animated_sprite.name = "AnimatedSprite2D"
		animated_sprite.sprite_frames = sprite_frames
		
		if material != null and material is CanvasItemMaterial:
			animated_sprite.material = material
		
		# Set to first animation
		var animations = sprite_frames.get_animation_names()
		if not animations.is_empty():
			animated_sprite.animation = animations[0]
			animated_sprite.play()
		
		root_node.add_child(animated_sprite)
		animated_sprite.owner = root_node
		
	else:
		# Create 3D scene with MeshInstance3D and QuadMesh
		root_node = Node3D.new()
		root_node.name = "MCSRSprite3D"
		
		var mesh_instance = MeshInstance3D.new()
		mesh_instance.name = "MeshInstance3D"
		
		var quad_mesh = QuadMesh.new()
		mesh_instance.mesh = quad_mesh
		
		if material != null and material is StandardMaterial3D:
			mesh_instance.material_override = material
		
		root_node.add_child(mesh_instance)
		mesh_instance.owner = root_node
	
	var packed_scene_result = scene.pack(root_node)
	if packed_scene_result != OK:
		return packed_scene_result
	
	return ResourceSaver.save(scene, scene_path)

func _is_mcsr_metadata_file(file_path: String) -> bool:
	# Check if filename ends with metadata.json
	if not file_path.ends_with("metadata.json"):
		return false
	
	# Try to read and validate basic structure
	var file = FileAccess.open(file_path, FileAccess.READ)
	if file == null:
		return false
	
	var json_text = file.get_as_text()
	file.close()
	
	var json = JSON.new()
	var parse_result = json.parse(json_text)
	if parse_result != OK:
		return false
	
	var data = json.data
	
	# Check for required MCSR metadata fields
	return (data is Dictionary and 
			data.has("fps") and 
			data.has("frameDimensions") and 
			data.has("passes") and 
			data.has("actions"))

func _parse_metadata_file(file_path: String) -> Dictionary:
	var file = FileAccess.open(file_path, FileAccess.READ)
	if file == null:
		print("Error: Cannot open metadata file: ", file_path)
		return {}
	
	var json_text = file.get_as_text()
	file.close()
	
	var json = JSON.new()
	var parse_result = json.parse(json_text)
	if parse_result != OK:
		print("Error: Invalid JSON in metadata file: ", file_path)
		return {}
	
	return json.data

# The _create_sprite_frames_from_metadata and _load_sprite_sheet_texture functions 
# have been moved to MCSRMaterialHelper.create_sprite_frames_with_materials()
# for better organization and material support.