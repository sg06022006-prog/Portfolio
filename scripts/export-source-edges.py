"""Export original mesh edges, before modifiers, in glTF world coordinates."""
import bpy, json
from pathlib import Path
root = Path('D:\\Reabilitation\\Blender\\готов\\Models')
for name, source, excluded in [
    ('island', root / 'Остров' / 'остров.blend', {'Plane.042'}),
    ('cafe', root / 'Кафе' / 'харчевня.blend', {'Plane.014', 'Cube.008'}),
    ('night-room', root / 'Ночная комната' / 'NightRoom_cleaned-review.blend', {'Plane.011', 'Plane.013'}),
]:
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False, load_ui=False)
    cutters = {m.object.name for o in bpy.context.scene.objects for m in o.modifiers if m.type == 'BOOLEAN' and m.object}
    points = []
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not obj.visible_get() or obj.name in excluded:
            continue
        if obj.name in cutters and obj.display_type in {'BOUNDS', 'WIRE'}:
            continue
        materials = [m for m in obj.data.materials if m]
        if materials and all(
            m.use_nodes and any(
                n.type == 'OUTPUT_MATERIAL'
                and n.inputs['Volume'].is_linked
                and not n.inputs['Surface'].is_linked
                for n in m.node_tree.nodes
            )
            for m in materials
        ):
            continue
        for edge in obj.data.edges:
            for index in edge.vertices:
                v = obj.matrix_world @ obj.data.vertices[index].co
                points.extend([round(v.x, 6), round(v.z, 6), round(-v.y, 6)])
    Path(f'public/models/{name}.edges.json').write_text(json.dumps(points, separators=(',', ':')), encoding='utf-8')
    print(name, 'original edges', len(points) // 6)
