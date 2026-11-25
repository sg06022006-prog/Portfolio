"""Export browser drafts without saving changes to the original Blender scenes.

Run from the Portfolio folder with Blender in background mode.
Missing textures and particle systems are recorded for manual preparation.
"""
import bpy
import json
import sys
from mathutils import Vector
from pathlib import Path

source_root = Path(r'D:\Reabilitation\Blender\готов\Models')
output = Path('model-preparation/drafts').resolve()
output.mkdir(parents=True, exist_ok=True)
scenes = {
    'cafe': source_root / 'Кафе' / 'харчевня.blend',
    'forest': source_root / 'Лес' / 'forest.blend',
    'island': source_root / 'Остров' / 'остров.blend',
    'night-room': source_root / 'Ночная комната' / 'NightRoom_cleaned-review.blend',
}
only = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else None
optimize = '--optimize' in sys.argv
reports = []
if only and Path('model-preparation/export-report.json').exists():
    reports = [item for item in json.loads(Path('model-preparation/export-report.json').read_text(encoding='utf-8')) if item['name'] != only]
for name, source in scenes.items():
    if only and name != only:
        continue
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    if name == 'island':
        # glTF cannot store Geometry > Random Per Island > ColorRamp.
        # Bake the evaluated roof's original procedural color, without lighting.
        roof = bpy.data.objects.get('Cylinder.002')
        bpy.ops.object.select_all(action='DESELECT')
        roof.select_set(True)
        bpy.context.view_layer.objects.active = roof
        bpy.ops.object.convert(target='MESH')
        roof = bpy.context.object
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(island_margin=0.02)
        bpy.ops.object.mode_set(mode='OBJECT')
        material = bpy.data.materials['Material.009']
        image = bpy.data.images.new('Island roof baked color', width=1024, height=1024)
        texture = material.node_tree.nodes.new('ShaderNodeTexImage')
        texture.image = image
        material.node_tree.nodes.active = texture
        scene = bpy.context.scene
        old_engine = scene.render.engine
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 1
        scene.render.bake.use_pass_direct = False
        scene.render.bake.use_pass_indirect = False
        scene.render.bake.use_pass_color = True
        bpy.ops.object.bake(type='DIFFUSE', margin=8)
        image.filepath_raw = str(output / 'island-roof-color.png')
        image.file_format = 'PNG'
        image.save()
        image.pack()
        shader = next(node for node in material.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
        material.node_tree.links.new(texture.outputs['Color'], shader.inputs['Base Color'])
        scene.render.engine = old_engine
        # Preserve Glass BSDF water using a glTF-compatible transmission material.
        for material in bpy.data.materials:
            if not material.use_nodes:
                continue
            for node in list(material.node_tree.nodes):
                if node.type != 'BSDF_GLASS':
                    continue
                water = material.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
                water.inputs['Base Color'].default_value = node.inputs['Color'].default_value
                water.inputs['Roughness'].default_value = node.inputs['Roughness'].default_value
                water.inputs['IOR'].default_value = node.inputs['IOR'].default_value
                water.inputs['Transmission Weight'].default_value = 1
                for link in list(node.outputs[0].links):
                    material.node_tree.links.new(water.outputs['BSDF'], link.to_socket)
    # glTF texture transforms cannot represent Mapping rotations around X/Y.
    # Bake the Cafe poster's full POINT transform into UV coordinates instead.
    if name == 'cafe':
        for material_name in ['вывеска', 'плакат']:
            material = bpy.data.materials.get(material_name)
            mapping = next(node for node in material.node_tree.nodes if node.type == 'MAPPING')
            if mapping.vector_type != 'POINT':
                raise RuntimeError('Unsupported Mapping type: ' + mapping.vector_type)
            location = Vector(mapping.inputs['Location'].default_value)
            rotation = mapping.inputs['Rotation'].default_value.to_matrix()
            scale = Vector(mapping.inputs['Scale'].default_value)
            for obj in bpy.context.scene.objects:
                if obj.type != 'MESH' or not obj.data.uv_layers.active:
                    continue
                for polygon in obj.data.polygons:
                    if polygon.material_index >= len(obj.data.materials) or obj.data.materials[polygon.material_index] != material:
                        continue
                    for index in polygon.loop_indices:
                        uv = obj.data.uv_layers.active.data[index].uv
                        point = rotation @ Vector((uv.x * scale.x, uv.y * scale.y, 0)) + location
                        uv.x, uv.y = point.x, point.y
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    uv_node = material.node_tree.nodes.new('ShaderNodeUVMap')
                    uv_node.uv_map = 'UVMap'
                    material.node_tree.links.new(uv_node.outputs['UV'], node.inputs['Vector'])
    excluded = []
    boolean_cutters = {
        modifier.object.name
        for obj in bpy.context.scene.objects for modifier in obj.modifiers
        if modifier.type == 'BOOLEAN' and modifier.object
    }
    if optimize:
        # Conservative bevel settings before evaluating the export copy.
        for obj in bpy.context.scene.objects:
            for modifier in obj.modifiers:
                if modifier.type == 'BEVEL':
                    modifier.segments = min(modifier.segments, 2)
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        materials = [material for material in obj.data.materials if material]
        # A volume-only fog box has no surface. glTF cannot preserve this effect.
        volume_only = bool(materials) and all(
            material.use_nodes and any(
                node.type == 'OUTPUT_MATERIAL'
                and node.inputs['Volume'].is_linked
                and not node.inputs['Surface'].is_linked
                for node in material.node_tree.nodes
            ) for material in materials
        )
        render_backdrop = (name == 'cafe' and obj.name == 'Plane.014') or (name == 'island' and obj.name == 'Plane.042') or (name == 'night-room' and obj.name == 'Plane.011')
        helper = (obj.name in boolean_cutters and obj.display_type in {'BOUNDS', 'WIRE'}) or (name == 'night-room' and not obj.visible_camera)
        if volume_only or render_backdrop or helper:
            obj.hide_set(True)
            excluded.append({'name': obj.name, 'reason': 'render helper' if helper else 'volume-only fog' if volume_only else 'render backdrop'})
    if optimize:
        graph = bpy.context.evaluated_depsgraph_get()
        for obj in list(bpy.context.scene.objects):
            if obj.type != 'MESH' or not obj.visible_get():
                continue
            mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(graph), preserve_all_data_layers=True, depsgraph=graph)
            obj.modifiers.clear()
            obj.data = mesh
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            # Remove redundant flat edges without crossing UV or material borders.
            if len(obj.data.polygons) < 10000:
                dissolve = obj.modifiers.new('Clean flat surfaces', 'DECIMATE')
                dissolve.decimate_type = 'DISSOLVE'
                dissolve.angle_limit = 0.008727
                dissolve.delimit = {'NORMAL', 'MATERIAL', 'SEAM', 'UV'}
                bpy.ops.object.modifier_apply(modifier=dissolve.name)
            if len(obj.data.polygons) > 2000:
                reduction = obj.modifiers.new('Reduce dense geometry', 'DECIMATE')
                reduction.ratio = 0.5
                reduction.delimit = {'MATERIAL', 'SEAM', 'UV'}
                bpy.ops.object.modifier_apply(modifier=reduction.name)
    missing = []
    restored = []
    # These are the same Fabric030 maps stored in the current texture folder.
    fabric_maps = {
        'Fabric030_2K_Color.png': 'Fabric030_2K-JPG_Color.jpg',
        'Fabric030_2K_Roughness.png': 'Fabric030_2K-JPG_Roughness.jpg',
        'Fabric030_2K_Normal.png': 'Fabric030_2K-JPG_NormalGL.jpg',
        'Fabric030_2K_AmbientOcclusion.png': 'Fabric030_2K-JPG_AmbientOcclusion.jpg',
        'Fabric030_2K_Displacement.png': 'Fabric030_2K-JPG_Displacement.jpg',
    }
    for image in bpy.data.images:
        if image.source != 'FILE':
            continue
        if not image.packed_file and not Path(bpy.path.abspath(image.filepath)).is_file():
            old_name = Path(bpy.path.abspath(image.filepath)).name
            texture_root = source_root.parent.parent / 'текстуры'
            wanted = fabric_maps.get(old_name, old_name)
            replacement = next(texture_root.rglob(wanted), texture_root / wanted)
            if replacement.is_file():
                restored.append({'old': image.filepath, 'new': str(replacement)})
                image.filepath = str(replacement)
                image.reload()
            else:
                missing.append(image.filepath)
                continue
        # Limit texture resolution in this in-memory copy for a lighter draft.
        if max(image.size) > 1024:
            scale = 1024 / max(image.size)
            image.scale(max(1, round(image.size[0] * scale)), max(1, round(image.size[1] * scale)))
    particles = [obj.name for obj in bpy.context.scene.objects if obj.particle_systems]
    target = output / f'{name}{"-optimized" if optimize else ""}.glb'
    if optimize:
        bpy.ops.wm.save_as_mainfile(filepath=str(output / f'{name}-optimized.blend'))
    try:
        bpy.ops.export_scene.gltf(
            filepath=str(target), export_format='GLB',
            use_visible=True, export_apply=True,
            export_animations=False, export_cameras=False, export_lights=False,
        )
        reports.append({'name': name, 'file': target.name, 'bytes': target.stat().st_size,
                        'missing_images': missing, 'restored_images': restored, 'particle_objects': particles, 'excluded': excluded,
                        'status': 'draft_requires_visual_review'})
        print('EXPORTED', name, target.stat().st_size, flush=True)
    except Exception as error:
        reports.append({'name': name, 'error': str(error), 'status': 'failed'})
    Path('model-preparation/optimized-report.json' if optimize else 'model-preparation/export-report.json').write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
