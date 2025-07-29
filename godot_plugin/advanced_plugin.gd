@tool
extends EditorPlugin

# Advanced editor integration for MCSR Import Plugin
# Provides UI dock and additional import options

const MCSRImporter = preload("mcsr_importer.gd")
const MCSRDock = preload("mcsr_dock.gd")

var importer_instance
var dock_instance

func _enter_tree():
	# Add the custom importer
	importer_instance = MCSRImporter.new()
	add_import_plugin(importer_instance)
	
	# Add editor dock for additional features
	dock_instance = MCSRDock.new()
	add_control_to_dock(DOCK_SLOT_LEFT_UL, dock_instance)
	
	print("Multi-Cam Sprite Renderer Import Plugin activated")

func _exit_tree():
	# Remove the custom importer
	if importer_instance:
		remove_import_plugin(importer_instance)
		importer_instance = null
	
	# Remove editor dock
	if dock_instance:
		remove_control_from_docks(dock_instance)
		dock_instance.queue_free()
		dock_instance = null
	
	print("Multi-Cam Sprite Renderer Import Plugin deactivated")