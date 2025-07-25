# Paper Sprite Pipeline Roadmap

This document outlines the planned changes to transform the Multi-Cam Sprite Renderer into a more flexible and powerful tool for exporting normal-mapped sprite sheets from 3D models.

## Core Feature Changes

### 1. Multi-Object Support - COMPLETE

- Add object selection dropdown in the UI panel to select one or more objects in the scene
- Store settings per-object instead of per-scene
- Implement UI to select which object's settings to display/edit in the panel
- Each object will have its own independent configuration for cameras, actions, and render settings

### 2. Camera Reference System - COMPLETE

- Add camera selection dropdown to reference existing scene cameras
- The selected camera's exact position and rotation in the scene will be used as the starting point
- During rendering, this camera will be temporarily cloned
- The clone will be rotated around the object in a circle for each sprite capture
- Between each sprite render, the camera will be rotated by the appropriate number of degrees based on the total number of cameras
- This eliminates the need for the plugin to store camera settings directly

### 3. Animation Action Support - COMPLETE

- Add UI for selecting actions to render for each object
- If no action is selected, render only the current single frame as a "\_default" action
- If one or more actions are selected, render an animation for each specified action
- Add checkbox option to skip duplicate frames for compression
- When enabled, if an animation has the object staying in the same position for multiple frames, only export a single frame
- Store frame duration metadata for optimized animations

### 4. Customizable Angles - COMPLETE

- Allow manual override of camera angles (in degrees)
- Default to equidistant angles when camera count changes (e.g., 4 cameras = 0°, 90°, 180°, 270°)
- Lock the first camera angle at 0 degrees
- Support non-circular camera paths by allowing custom angle values
- When the number of cameras changes, reset angles to equidistant values

### 5. Render Pass System

- Maintain current pass system (diffuse, normal, etc.)
- Export each pass to separate files with appropriate naming
- Each pass will be rendered to its own file in the output structure

### 6. Compositor Integration

- Add option to select a Render Layers node as starting point for compositing
- If selected, inject custom compositing nodes after the selected Render Layers node
- If not selected, create a new temporary compositor graph (current behavior)
- Remove injected nodes after rendering is complete
- This allows support for arbitrary user-defined compositing after the plugin's compositing

### 7. Output Structure

- Implement hierarchical output folder structure:
  ```
  <output_folder>/<action_name | "_default">/camera_<n>/<pass_name>.<extension>
  ```
- Generate metadata JSON with animation timing information
- The metadata file will be named `metadata.json` and have one file per object.

## Metadata JSON Format

```json
{
  "fps": 24,
  "frameDimensions": {
    "width": 1024,
    "height": 1024
  },
  "actions": [
    {
      "name": "action_name",
      "sprites": [
        {
          "x": 0,
          "y": 0,
          "frames": 1
        },
        {
          "x": 1024,
          "y": 0,
          "frames": 2
        }
      ]
    }
  ]
}
```

## Implementation Plan

Each milestone represents a fully testable state of the plugin. The plugin should remain functional throughout the implementation process.

Note: As each milestone is completed, " - COMPLETE" will be added to its heading to track progress.

### Milestone 1: Basic Object Selection

1. Create ObjectSettings PropertyGroup with minimal properties
   - reference_camera (pointer)
   - camera_count (int)
2. Add object selection dropdown to UI
3. Move existing camera count property to object level
4. Update render operator to use selected object's camera count
5. **Testing**: Verify that:
   - Different objects can have different camera counts
   - Original rendering still works with object-specific camera counts
   - UI updates properly when switching between objects

### Milestone 2: Camera Reference System

1. Add camera selection UI to ObjectSettings
2. Update camera creation logic to clone reference camera
3. Modify positioning logic to use reference camera as starting point
4. **Testing**: Verify that:
   - Reference camera selection works
   - Camera cloning preserves all relevant settings
   - Rendering produces expected results from reference camera position

### Milestone 3: Custom Angle System

1. Add angle properties to ObjectSettings
2. Create UI for angle customization
3. Update camera positioning to use custom angles
4. Implement angle reset when camera count changes
5. **Testing**: Verify that:
   - Angles can be customized per object
   - First angle remains locked at 0
   - Angles reset correctly when camera count changes
   - Non-circular paths work as expected

### Milestone 4: Basic Action Support

1. Add action selection properties to ObjectSettings
2. Create UI for selecting actions
3. Implement basic action rendering (without optimization)
4. Update output path structure for actions
5. **Testing**: Verify that:
   - Actions can be selected per object
   - Default action works when no action selected
   - Output structure correctly organizes action renders

### Milestone 5: Action Optimization

1. Add duplicate frame detection properties
2. Implement duplicate frame detection algorithm
3. Create basic metadata.json with fps
4. **Testing**: Verify that:
   - Duplicate frames are correctly identified
   - Skipping duplicate frames works
   - Metadata file is created with correct fps

### Milestone 6: Metadata Enhancement

1. Implement frame duration override tracking
2. Update metadata.json format with frameIndexDurationOverridesInSeconds
3. **Testing**: Verify that:
   - Duration overrides are correctly calculated
   - Metadata JSON format is correct
   - Frame timing information is accurate

### Milestone 7: Compositor Integration

1. Add compositor node selection to ObjectSettings
2. Implement node injection after selected Render Layers
3. Update cleanup logic to handle injected nodes
4. **Testing**: Verify that:
   - Node selection works
   - Custom compositing chains are preserved
   - Cleanup works correctly in all scenarios

### Milestone 8: Multi-Pass System

1. Update pass system to work with new object-based structure
2. Implement pass-specific output paths
3. Ensure compatibility with compositor integration
4. **Testing**: Verify that:
   - All pass types work correctly
   - Output structure handles passes properly
   - Passes work with custom compositor setups

### Milestone 9: Final Integration

1. Ensure all systems work together seamlessly
2. Add comprehensive error handling
3. Update documentation
4. **Testing**: Verify that:
   - All features work in combination
   - Error handling covers edge cases
   - Documentation accurately reflects all features

Each milestone includes specific test criteria that must pass before moving to the next milestone. This ensures we maintain a working plugin throughout the development process and can catch issues early.

## Technical Details

### Property Structure

```python
class McsrObjectSettings(PropertyGroup):
    # Camera settings
    reference_camera: PointerProperty(type=bpy.types.Object)
    camera_count: IntProperty()
    camera_angles: CollectionProperty(type=McsrAngleSetting)

    # Action settings
    actions: CollectionProperty(type=McsrActionSetting)
    skip_duplicate_frames: BoolProperty()

    # Render settings
    passes: CollectionProperty(type=McsrPassSetting)
    compositor_node: PointerProperty(type=bpy.types.Node)
```

### Output Structure

The final output will follow this structure:

```
<output_folder>/
      metadata.json
      <action_name | "_default">/
        camera_<n>/
          <pass_name>.<extension>
```
