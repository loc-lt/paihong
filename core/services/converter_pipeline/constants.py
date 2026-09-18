# SVG Geometric Processing Constants
JOIN_TOL = 2.0             # Tolerance for joining endpoints of fragmented paths (pixels/units)
AREA_MIN = 5000            # Minimum area to be considered an "Anchor" (main cut region)
NUMBER_POINT_D = 20        # Minimum number of anchor points for an Anchor path
MAX_BACKGROUND_RATIO = 0.8 # Max area ratio (relative to page) to remove background frames
EXPAND_REGION_FACTOR = 1.5 # Expansion factor for region shapes when checking intersection
MIN_INSIDE_LEN = 10.0      # Minimum length inside an anchor to assign a path to it
MIN_INSIDE_RATIO = 0.5     # Minimum length ratio inside an anchor to assign a path to it
DOMINANT_RATIO = 0.8       # If a path is >= 80% inside an anchor, it strongly belongs to it
