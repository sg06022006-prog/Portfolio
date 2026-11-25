"""Prepare a web copy without saving over the author's Blender file."""
import bpy
import json
import sys
from mathutils import Vector
from pathlib import Path

source = Path(r'D:\Reabilitation\Blender\Project #1\First object\WorckBench_Scene\FullScene — копия.blend')
Path('model-preparation').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
report = {
    'camera': bpy.context.scene.camera.name if bpy.context.scene.camera else None,
    'engine': bpy.context.scene.render.engine,
    'objects': [{'name': obj.name, 'type': obj.type, 'visible': obj.visible_get(), 'render': not obj.hide_render,
                 'dimensions': list(obj.dimensions), 'polygons': len(obj.data.polygons) if obj.type == 'MESH' else 0}
                for obj in bpy.context.scene.objects],
    'images': [{'name': image.name, 'path': bpy.path.abspath(image.filepath), 'packed': bool(image.packed_file),
                'exists': Path(bpy.path.abspath(image.filepath)).is_file()} for image in bpy.data.images if image.source == 'FILE'],
}
Path('model-preparation/full-scene-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
missing = [image for image in report['images'] if not image['exists'] and not image['packed']]
print('Objects:', len(report['objects']), 'Missing images:', len(missing), flush=True)
if '--prepare' not in sys.argv:
    raise SystemExit()
if missing:
    raise RuntimeError('Restore missing textures before exporting')

scene = bpy.context.scene
cutters = {modifier.object for obj in scene.objects for modifier in obj.modifiers
           if modifier.type == 'BOOLEAN' and modifier.object}
for obj in scene.objects:
    if obj in cutters and obj.display_type in {'BOUNDS', 'WIRE'}:
        obj.hide_set(True)

# Both mesh and original edges use the same visible objects.
points = []
bounds = []
for obj in scene.objects:
    if obj.type != 'MESH' or not obj.visible_get():
        continue
    bounds.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    for edge in obj.data.edges:
        for index in edge.vertices:
            vertex = obj.matrix_world @ obj.data.vertices[index].co
            points.extend([round(vertex.x, 6), round(vertex.z, 6), round(-vertex.y, 6)])
Path('public/models/full-scene.edges.json').write_text(json.dumps(points, separators=(',', ':')), encoding='utf-8')
if '--render-only' not in sys.argv:
    bpy.ops.export_scene.gltf(filepath=str(Path('public/models/full-scene.glb').resolve()), export_format='GLB',
                              use_visible=True, export_apply=True, export_animations=False,
                              export_cameras=False, export_lights=False)

# A review render for the unfinished project. The source has no camera.
minimum = Vector(tuple(min(point[axis] for point in bounds) for axis in range(3)))
maximum = Vector(tuple(max(point[axis] for point in bounds) for axis in range(3)))
center = (minimum + maximum) / 2
size = (maximum - minimum).length
camera_data = bpy.data.cameras.new('Web preview camera')
camera = bpy.data.objects.new('Web preview camera', camera_data)
scene.collection.objects.link(camera)
camera.location = center + Vector((-1, 1, 0.85)).normalized() * size * 1.5
camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.type = 'ORTHO'
camera_data.ortho_scale = size * 1.15
local_points = [camera.matrix_basis.inverted() @ point for point in bounds]
left, right = min(p.x for p in local_points), max(p.x for p in local_points)
bottom, top = min(p.y for p in local_points), max(p.y for p in local_points)
camera.location += camera.rotation_euler.to_matrix() @ Vector(((left + right) / 2, (bottom + top) / 2, 0))
camera_data.ortho_scale = max(right - left, (top - bottom) * 1.6) * 1.12
scene.camera = camera
for name, offset, power in [('Preview key', (0, 1, 1.5), 2200), ('Preview fill', (-1, 0, 1), 1400)]:
    light_data = bpy.data.lights.new(name, 'AREA')
    light_data.energy = power
    light_data.shape = 'DISK'
    light_data.size = size * 0.6
    light = bpy.data.objects.new(name, light_data)
    scene.collection.objects.link(light)
    light.location = center + Vector(offset) * size * 0.6
    light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(Path('public/images/projects/full-scene.png').resolve())
bpy.ops.render.render(write_still=True)
