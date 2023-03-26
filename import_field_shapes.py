import bpy
import os
import re
from mathutils import Vector, Matrix


def import_fbx(folder_path):
    obj_before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=folder_path, bake_space_transform=True)
    obj_after = set(bpy.context.scene.objects)
    return obj_after - obj_before


def set_origin(obj):
    if obj.type != 'MESH':
        return

    mesh_data = obj.data
    mesh_data.update()

    # Calculate the center of mass (average of vertex positions)
    num_vertices = len(mesh_data.vertices)
    bbox = sum((obj.matrix_world @ vertex.co for vertex in mesh_data.vertices), Vector()) / num_vertices

    # Move the object origin to bbox
    obj.location = obj.matrix_world.inverted() @ bbox

    # Move mesh so in opposite direction
    for vertex in mesh_data.vertices:
        vertex.co = obj.matrix_world.inverted() @ (obj.matrix_world @ vertex.co - bbox)


def create_empty(name, location=(0, 0, 0)):
    empty = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(empty)
    empty.location = location
    return empty


def separate_parts(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.context.active_object.select_set(True)
    # Save the current area type and change it to VIEW_3D
    old_area = bpy.context.area.type
    bpy.context.area.type = 'VIEW_3D'

    # Enter edit mode, separate loose parts, and exit edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.separate(type='LOOSE')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

    # Restore the original area type
    bpy.context.area.type = old_area


bpy.types.Scene.field_shapes_folder = bpy.props.StringProperty(
    name="Folder Path",
    description="Select a folder",
    default="",
    subtype='DIR_PATH'
)


class IMPORT_OT_FieldShapes(bpy.types.Operator):
    bl_idname = "field_shape.import_field_shapes"
    bl_label = "Import Field Shapes"
    bl_description = "Import FBX files, set origins, and separate loose parts"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        folder = context.scene.field_shapes_folder
        if not folder:
            self.report({'ERROR'}, "No path to folder set")
            return {'CANCELLED'}
        file_count = 0
        for file in os.listdir(folder):
            if file.endswith('.fbx'):
                file_count += 1
                filepath = os.path.join(folder, file)
                empty_name = re.sub(r'\.fbx$', '', file)

                imported_obj = import_fbx(filepath)
                for ob in imported_obj:
                    set_origin(ob)
                    empty = create_empty(empty_name, ob.location)
                    matrix_world = ob.matrix_world.copy()
                    ob.parent = empty
                    ob.matrix_parent_inverse = Matrix.Identity(4)
                    ob.matrix_world = matrix_world

                    separate_parts(ob)
        self.report({'INFO'}, f"Imported {file_count} fbx files successfully")
        return {'FINISHED'}


class IMPORT_PT_FieldShapes(bpy.types.Panel):
    bl_idname = 'field_shape.import_field_shapes_panel'
    bl_label = 'Import Field Shapes'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Import Field Shapes'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "field_shapes_folder")
        row = layout.row()
        row.operator(IMPORT_OT_FieldShapes.bl_idname, text="Run")
