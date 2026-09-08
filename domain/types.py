"""Stable string identities for the reconstruction domain.

Legacy numeric class ids remain a compatibility concern in ``core/classes.py``.
New domain code should use these names (or compatible extension strings) instead.
"""


class ObservationType:
    DIMENSION_TEXT = "annotation.dimension_text"
    DIMENSION_LINE = "annotation.dimension_line"
    LEVEL_TEXT = "annotation.level_text"
    LEVEL_LINE = "annotation.level_line"
    MATERIAL_NOTE = "annotation.material_note"
    CALC_NOTE = "annotation.calc_note"
    ROOM_LABEL = "annotation.room_label"
    ELEMENT_TAG = "annotation.element_tag"
    WALL_STROKE = "drawing.wall_stroke"
    COLUMN_SYMBOL = "drawing.column_symbol"
    GRID_AXIS_SYMBOL = "drawing.grid_axis_symbol"
    OPENING_SYMBOL = "drawing.opening_symbol"


class EntityType:
    GRID_AXIS = "drawing.grid_axis"
    WALL = "building.wall"
    COLUMN = "building.column"
    OPENING = "building.opening"
    DOOR = "building.door"
    WINDOW = "building.window"
    STAIR = "building.stair"


class ConstraintType:
    DISTANCE = "distance"
    COINCIDENT = "coincident"
    PARALLEL = "parallel"
    PERPENDICULAR = "perpendicular"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    COLLINEAR = "collinear"
    CENTERED = "centered"
    EQUAL = "equal"
    OFFSET = "offset"
    CLOSED_LOOP = "closed_loop"
