bl_info = {
    "name": "Custom Data Format",
    "blender": (4, 2, 0),
    "category": "Game Engine",
}

if "bpy" in locals():
    import importlib

    if "export" in locals():
        importlib.reload(export)

import bpy
from . import export

def register():
    export.register()
    
def unregister():
    export.unregister()

if __name__ == "__main__":
    register()
