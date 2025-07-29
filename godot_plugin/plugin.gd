@tool
extends EditorPlugin

const MCSRImporter = preload("mcsr_importer.gd")

var importer_instance

func _enter_tree():
	# Add the custom importer
	importer_instance = MCSRImporter.new()
	add_import_plugin(importer_instance)
	
	print("Multi-Cam Sprite Renderer Import Plugin activated")

func _exit_tree():
	# Remove the custom importer
	if importer_instance:
		remove_import_plugin(importer_instance)
		importer_instance = null
	
	print("Multi-Cam Sprite Renderer Import Plugin deactivated")