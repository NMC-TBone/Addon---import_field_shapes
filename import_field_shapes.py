import bpy
from mathutils import Vector, Matrix
from pathlib import Path
import time


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
    matrix_world_inv = obj.matrix_world.inverted()
    obj.location = matrix_world_inv @ bbox

    # Move mesh so in opposite direction
    bbox_offset = matrix_world_inv @ bbox
    for vertex in mesh_data.vertices:
        vertex.co = matrix_world_inv @ obj.matrix_world @ vertex.co - bbox_offset


def create_empty(name, location=(0, 0, 0)):
    empty = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(empty)
    empty.location = location
    return empty


def separate_all(ob_name_list):
    last_obj = None
    for obj in bpy.data.objects:
        if obj.name in ob_name_list:
            obj.select_set(True)
            last_obj = obj

    if last_obj is not None:
        bpy.context.view_layer.objects.active = last_obj

    old_area = bpy.context.area.type
    bpy.context.area.type = 'VIEW_3D'

    # Enter edit mode, separate loose parts, and exit edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.separate(type='LOOSE')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    bpy.ops.object.select_all(action='DESELECT')

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
        if not context.scene.field_shapes_folder:
            self.report({'ERROR'}, "No folder path set")
            return {'CANCELLED'}

        folder = Path(context.scene.field_shapes_folder)
        if not folder.is_dir():
            self.report({'ERROR'}, "Invalid folder path")
            return {'CANCELLED'}

        fbx_files = list(folder.glob("*.fbx"))
        if not fbx_files:
            self.report({'ERROR'}, "No FBX files found in the folder")
            return {'CANCELLED'}

        start_time = time.time()
        all_names = []
        bpy.context.window_manager.progress_begin(0, len(fbx_files))
        imported_files = 0
        for i, file in enumerate(fbx_files):
            filepath = str(file)
            empty_name = file.stem

            try:
                imported_obj = import_fbx(filepath)
            except Exception as e:
                self.report({'WARNING'}, f"Error importing file {filepath}: {str(e)}")
                continue

            for ob in imported_obj:
                all_names.append(ob.name)
                set_origin(ob)
                empty = create_empty(empty_name, ob.location)
                matrix_world = ob.matrix_world.copy()
                ob.parent = empty
                ob.matrix_parent_inverse = Matrix.Identity(4)
                ob.matrix_world = matrix_world
            bpy.context.window_manager.progress_update(i)
            imported_files += 1
        separate_all(all_names)
        bpy.context.window_manager.progress_end()
        elapsed_time = time.time() - start_time
        self.report({'INFO'}, f"Imported {imported_files} fbx files successfully in {elapsed_time:.2f} seconds")
        return {'FINISHED'}


class IMPORT_PT_FieldShapes(bpy.types.Panel):
    bl_idname = 'IMPORT_PT_FieldShapes'
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
