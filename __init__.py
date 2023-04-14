if "bpy" in locals():
    import importlib
    importlib.reload(import_field_shapes)
else:
    from . import import_field_shapes

import bpy

bl_info = {
    "name": "ImportFieldShapes",
    "author": "[NMC] T-Bone",
    "description": "Import field shapes from a folder containing .fbx files",
    "blender": (3, 0, 0),
    "version": (1, 0, 2),
    "location": "View3D",
    "warning": "",
    "category": "Generic"
}

classes = (
    import_field_shapes.IMPORT_OT_FieldShapes,
    import_field_shapes.IMPORT_PT_FieldShapes
)

register, unregister = bpy.utils.register_classes_factory(classes)


if __name__ == "__main__":
    register()
