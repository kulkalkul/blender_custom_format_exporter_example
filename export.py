import bpy
import bpy_extras
import struct
import bmesh
import math
import mathutils
from mathutils import Matrix
import numpy as np

# Based on:
# https://github.com/KhronosGroup/glTF-Blender-IO/blob/main/addons/io_scene_gltf2/blender/exp/primitive_extract.py

VERSION = 1
ROUNDING_DIGIT = 4

class CustomExport(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    bl_idname = "custom.export"
    bl_label = "Custom Data Export"
    
    filename_ext = ".custom"

    export_json_debug_mode: bpy.props.BoolProperty(
        name = "Export JSON Debug Mode",
        description = "Enable export JSON debug mode",
        default = False,
    )
    
    def execute(self, context):
        export_vertices = []
        export_indices = []
        
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
                
        for obj in bpy.context.scene.objects:
            if obj.type != "MESH":
                continue

            depsgraph = context.evaluated_depsgraph_get()
            mesh = obj.evaluated_get(depsgraph).to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
            
            structured_vertices = np.empty(len(mesh.loops), dtype=np.dtype([
                ("vertex_index", np.uint32),
                ("normal", np.float32, (3,)),
            ]))
                        
            vertex_indices = np.empty(len(mesh.loops), dtype=np.intc)
            mesh.loops.foreach_get("vertex_index", vertex_indices)
            structured_vertices["vertex_index"] = vertex_indices
            
            positions = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
            mesh.vertices.foreach_get("co", positions)
            positions = positions.reshape(len(mesh.vertices), 3)
            fix_coordinate(positions)
            
            normals = np.empty(len(mesh.corner_normals) * 3, dtype=np.float32)
            mesh.corner_normals.foreach_get("vector", normals)
            normals = normals.reshape(len(mesh.corner_normals), 3)
            normals = np.round(normals, ROUNDING_DIGIT)
            
            normalized_normals = np.linalg.norm(normals, axis=1, keepdims=True)
            normals = np.divide(normals, normalized_normals, out=normals, where=normalized_normals != 0)
            
            fix_coordinate(normals)
            
            structured_vertices["normal"] = normals

            mesh.calc_loop_triangles()
            loop_indices = np.empty(len(mesh.loop_triangles) * 3, dtype=np.uint32)
            mesh.loop_triangles.foreach_get("loops", loop_indices)
           
            structured_vertices = structured_vertices[loop_indices]
            structured_vertices, indices = np.unique(structured_vertices, return_inverse=True)
            
            positions = positions[structured_vertices["vertex_index"]]
            normals = structured_vertices["normal"]
            
            for position, normal in zip(positions, normals):
                export_vertices.extend(position)
                export_vertices.append(0)
                export_vertices.extend(normal)
                export_vertices.append(0)            

            export_indices.extend(indices)
                       
        print("===== CUSTOM EXPORT =======")
        print("Exported vertices: ", len(export_vertices))
        print("Exported indices: ", len(export_indices))

        export_binary(self.filepath, export_indices, export_vertices)

        if self.export_json_debug_mode:
            export_debug_json(self.filepath, export_indices, export_vertices)

        return { "FINISHED" }

    def draw(self, context):
        self.layout.prop(self, "export_json_debug_mode")

def fix_coordinate(array):
    # swaps y and z
    array[:, (2, 1)] = array[:, (1, 2)]
    # negates z
    array[:, 2] *= -1

def export_debug_json(filepath, indices, vertices):
    import json
    with open(filepath + ".json", mode="w") as stream:
        stream.write(json.dumps(str({
            "VERSION": VERSION,
            "indices_len": len(indices),
            "vertices_len": len(vertices),
            "indices": indices,
            "vertices": vertices,
       })))

def export_binary(filepath, indices, vertices):
    with open(filepath, mode="wb") as stream:
        stream.write(struct.pack("<I", VERSION))
        
        stream.write(struct.pack("<I", len(indices)))
        stream.write(struct.pack("<I", len(vertices)))
        
        stream.write(struct.pack("<%sI" % len(indices), *indices))
        stream.write(struct.pack("<%sf" % len(vertices), *vertices))
    

def custom_export(self, context):
    self.layout.operator_context = "INVOKE_DEFAULT"
    self.layout.operator(CustomExport.bl_idname, text = "Custom Data Format (.custom)")

def register():
    bpy.utils.register_class(CustomExport)
    bpy.types.TOPBAR_MT_file_export.append(custom_export)
    
def unregister():
    bpy.utils.unregister_class(CustomExport)
    bpy.types.TOPBAR_MT_file_export.remove(custom_export)
