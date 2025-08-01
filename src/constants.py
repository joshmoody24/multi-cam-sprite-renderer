"""Constants used throughout the Multi-Cam Sprite Renderer addon"""

# Preview object naming
PREVIEW_COLLECTION_NAME = "MCSR_Preview"
PREVIEW_PARENT_NAME = "MCSR_Preview_Parent"
PREVIEW_CAMERA_PREFIX = "MCSR_Preview_Camera_"

# Property defaults
DEFAULT_CAMERA_COUNT = 4
DEFAULT_DISTANCE = 5.0
DEFAULT_FOCAL_LENGTH = 50.0
DEFAULT_ORTHO_SCALE = 7.314
DEFAULT_CLIP_START = 0.1
DEFAULT_CLIP_END = 1000.0
DEFAULT_DOF_DISTANCE = 5.0
DEFAULT_DOF_APERTURE = 2.8
DEFAULT_SPACING = 1
DEFAULT_OUTPUT_PATH = "//renders/"

# UI colors
PREVIEW_COLOR = (1.0, 0.5, 0.0, 1.0)  # Orange

# Render limits
MAX_TEXTURE_SIZE = 16384  # Maximum texture dimension (GPU limit)
