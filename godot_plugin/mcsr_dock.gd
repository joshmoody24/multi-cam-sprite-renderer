@tool
extends Control

# MCSR Import Plugin Dock - provides UI for manual import and batch operations

var importer = preload("mcsr_importer.gd").new()

func _init():
	set_custom_minimum_size(Vector2(200, 300))
	name = "MCSR Importer"
	
	# Create UI
	var vbox = VBoxContainer.new()
	add_child(vbox)
	
	# Title
	var title = Label.new()
	title.text = "MCSR Sprite Importer"
	title.add_theme_font_size_override("font_size", 16)
	vbox.add_child(title)
	
	# Separator
	var separator = HSeparator.new()
	vbox.add_child(separator)
	
	# Manual import section
	var manual_label = Label.new()
	manual_label.text = "Manual Import:"
	vbox.add_child(manual_label)
	
	var import_button = Button.new()
	import_button.text = "Select metadata.json"
	import_button.pressed.connect(_on_import_button_pressed)
	vbox.add_child(import_button)
	
	# Batch import section
	vbox.add_child(HSeparator.new())
	
	var batch_label = Label.new()
	batch_label.text = "Batch Import:"
	vbox.add_child(batch_label)
	
	var batch_button = Button.new()
	batch_button.text = "Import All in Project"
	batch_button.pressed.connect(_on_batch_import_pressed)
	vbox.add_child(batch_button)
	
	# Options section
	vbox.add_child(HSeparator.new())
	
	var options_label = Label.new()
	options_label.text = "Options:"
	vbox.add_child(options_label)
	
	var create_materials_check = CheckBox.new()
	create_materials_check.text = "Create Normal Materials"
	create_materials_check.button_pressed = true
	vbox.add_child(create_materials_check)
	
	var loop_animations_check = CheckBox.new()
	loop_animations_check.text = "Loop Animations"
	loop_animations_check.button_pressed = true
	vbox.add_child(loop_animations_check)
	
	# Status section
	vbox.add_child(HSeparator.new())
	
	var status_label = Label.new()
	status_label.text = "Ready"
	status_label.name = "StatusLabel"
	vbox.add_child(status_label)

func _on_import_button_pressed():
	var file_dialog = EditorInterface.get_file_system_dock().get_file_system()
	var dialog = FileDialog.new()
	dialog.title = "Select MCSR metadata.json"
	dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
	dialog.access = FileDialog.ACCESS_RESOURCES
	dialog.add_filter("*.json", "JSON Files")
	
	get_viewport().add_child(dialog)
	dialog.file_selected.connect(_on_file_selected)
	dialog.popup_centered_ratio(0.6)

func _on_file_selected(path: String):
	_update_status("Importing " + path + "...")
	
	if importer._is_mcsr_metadata_file(path):
		var options = {
			"import_mode": 0,  # 2D mode by default
			"create_normal_material": true,
			"loop_animations": true
		}
		
		var base_path = path.get_basename()
		var result = importer._import(path, base_path, options, [], [])
		
		if result == OK:
			_update_status("Successfully imported: " + path.get_file())
			EditorInterface.get_resource_filesystem().scan()
		else:
			_update_status("Failed to import: " + path.get_file())
	else:
		_update_status("Not a valid MCSR metadata file: " + path.get_file())

func _on_batch_import_pressed():
	_update_status("Searching for metadata files...")
	
	var metadata_files = []
	_find_metadata_files("res://", metadata_files)
	
	if metadata_files.is_empty():
		_update_status("No metadata.json files found in project")
		return
	
	_update_status("Found " + str(metadata_files.size()) + " metadata file(s). Importing...")
	
	var success_count = 0
	for file_path in metadata_files:
		if importer._is_mcsr_metadata_file(file_path):
			var options = {
				"import_mode": 0,
				"create_normal_material": true,
				"loop_animations": true
			}
			
			var base_path = file_path.get_basename()
			var result = importer._import(file_path, base_path, options, [], [])
			
			if result == OK:
				success_count += 1
	
	_update_status("Batch import complete: " + str(success_count) + "/" + str(metadata_files.size()) + " successful")
	EditorInterface.get_resource_filesystem().scan()

func _find_metadata_files(dir_path: String, files: Array):
	var dir = DirAccess.open(dir_path)
	if dir == null:
		return
	
	dir.list_dir_begin()
	var file_name = dir.get_next()
	
	while file_name != "":
		var full_path = dir_path + "/" + file_name
		
		if dir.current_is_dir() and not file_name.begins_with("."):
			_find_metadata_files(full_path, files)
		elif file_name == "metadata.json":
			files.append(full_path)
		
		file_name = dir.get_next()

func _update_status(message: String):
	var status_label = find_child("StatusLabel")
	if status_label:
		status_label.text = message
	print("MCSR Importer: " + message)