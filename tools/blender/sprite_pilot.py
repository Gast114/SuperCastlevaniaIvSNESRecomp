"""Blender 4.5+: import one animated character and render fixed-camera sprites.

Run with blender --background --disable-autoexec --python-exit-code 1 --python THIS_FILE -- ARGS.
Without --model, creates the export studio and a non-rendering reference only.
Never opens or changes a player profile or installs a character pack.
"""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree


def bounds(meshes):
    graph = bpy.context.evaluated_depsgraph_get()
    points = [ob.evaluated_get(graph).matrix_world @ Vector(corner)
              for ob in meshes for corner in ob.evaluated_get(graph).bound_box]
    if not points:
        raise RuntimeError('No character mesh imported')
    return [min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]


def attach_surface(surface, rigged_objects):
    """Copy weights locally to a textured version of the SAME rest-pose geometry.

    Keeps the textured mesh's UVs/materials. Rejects mismatched geometry; this is
    deliberately not automatic rigging for a different character.
    """
    rigs = [ob for ob in rigged_objects if ob.type == 'ARMATURE']
    sources = [ob for ob in rigged_objects if ob.type == 'MESH']
    if len(rigs) != 1 or not sources:
        raise ValueError('--surface requires one imported armature and its weighted mesh')
    rig = rigs[0]
    rig.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    low, high = bounds(sources)
    height = high[2] - low[2]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(surface.resolve()))
    added = set(bpy.data.objects) - before
    targets = [ob for ob in added if ob.type == 'MESH']
    if any(ob.type == 'ARMATURE' for ob in added) or not targets:
        raise ValueError('--surface must be the unrigged textured rest-pose GLB')
    bpy.context.view_layer.update()
    t_low, t_high = bounds(targets)
    scale = height / (t_high[2] - t_low[2])
    offset = Vector([(low[i] + high[i] - scale * (t_low[i] + t_high[i])) / 2
                     for i in range(3)])
    transform = Matrix.Translation(offset) @ Matrix.Scale(scale, 4)
    for ob in targets:
        ob.matrix_world = transform @ ob.matrix_world
    bpy.context.view_layer.update()
    entries = [(ob, v) for ob in sources for v in ob.data.vertices]
    tree = KDTree(len(entries))
    for index, (ob, vertex) in enumerate(entries):
        tree.insert(ob.matrix_world @ vertex.co, index)
    tree.balance()
    mappings = []
    distances = []
    for ob in targets:
        for vertex in ob.data.vertices:
            _, index, distance = tree.find(ob.matrix_world @ vertex.co)
            distances.append(distance / height)
            mappings.append((ob, vertex.index, entries[index]))
    if max(distances) > .005:
        raise ValueError('Textured mesh is not the same rest geometry; maximum distance/height: '
                         + str(max(distances)))
    for ob, index, (source, vertex) in mappings:
        for weight in vertex.groups:
            name = source.vertex_groups[weight.group].name
            group = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
            group.add([index], weight.weight, 'REPLACE')
    for ob in targets:
        world = ob.matrix_world.copy()
        ob.parent = rig
        ob.matrix_world = world
        modifier = ob.modifiers.new('Transferred original rig weights', 'ARMATURE')
        modifier.object = rig
    for ob in sources:
        ob.hide_render = True
        ob.hide_set(True)
    rig.data.pose_position = 'POSE'
    bpy.context.view_layer.update()
    return added, {'source': str(surface.resolve()), 'vertices': len(mappings),
                   'max_distance_per_height': max(distances),
                   'mean_distance_per_height': sum(distances) / len(distances)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--model', type=Path)
    parser.add_argument('--surface', type=Path, help='Textured GLB of the same rest geometry; copy rig weights locally')
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--action')
    parser.add_argument('--yaw', type=float, default=90, help='Rotate model facing -Y to screen-right')
    parser.add_argument('--samples', type=int, default=6)
    parser.add_argument('--start', type=float)
    parser.add_argument('--end', type=float)
    parser.add_argument('--height-native', type=float, default=49)
    parser.add_argument('--ground-native', type=float, default=77.35)
    parser.add_argument('--root-bone', help='Optional bone used to cancel horizontal root motion')
    parser.add_argument('--lock-root-z', action='store_true')
    parser.add_argument('--render', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if not 1 <= args.samples <= 60 or not 1 <= args.height_native <= 90:
        raise ValueError('Invalid sample count or character height')
    if args.out.exists():
        raise FileExistsError('Use a new output folder: ' + str(args.out))
    args.out.mkdir(parents=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x = scene.render.resolution_y = 960
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.render.fps = 60
    scene.render.fps_base = 1
    scene.view_settings.view_transform = 'Standard'
    scene.world = bpy.data.worlds.new('Studio world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.16, .18, .22, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .4
    height = 1.8
    world_height = 96 * height / args.height_native
    camera_z = (args.ground_native / 96 - .5) * world_height
    camera_data = bpy.data.cameras.new('Fixed orthographic camera')
    camera = bpy.data.objects.new('SPRITE_CAMERA', camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0, -8, camera_z)
    camera.rotation_euler = (Vector((0, 0, camera_z)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = world_height
    scene.camera = camera
    for name, pos, power, size in [
        ('Key', (-3, -4, 6), 500, 4), ('Fill', (4, -2, 3), 250, 4),
        ('Rim', (-2, 3, 4), 350, 3),
    ]:
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.shape, data.size = power, 'DISK', size
        ob = bpy.data.objects.new(name, data)
        scene.collection.objects.link(ob)
        ob.location = pos
        ob.rotation_euler = (Vector((0, 0, .9)) - ob.location).to_track_quat('-Z', 'Y').to_euler()
    origin = bpy.data.objects.new('GAME_ORIGIN_48_48', None)
    scene.collection.objects.link(origin)
    origin.location = (0, 0, camera_z)
    origin.empty_display_type = 'PLAIN_AXES'
    origin.empty_display_size = .12
    if args.reference:
        image = bpy.data.images.load(str(args.reference.resolve()), check_existing=True)
        image.pack()
        ob = bpy.data.objects.new('REFERENCE_ONLY_NOT_RENDERED', None)
        scene.collection.objects.link(ob)
        ob.empty_display_type = 'IMAGE'
        ob.data = image
        ob.empty_display_size = height
        ob.location = (-2.5, 0, .9)
        ob.rotation_euler = (math.pi / 2, 0, 0)
    report = {
        'blender_version': bpy.app.version_string,
        'model': str(args.model.resolve()) if args.model else None,
        'reference': str(args.reference.resolve()) if args.reference else None,
        'canvas': [960, 960], 'native_cell': 96, 'scale': 10,
        'source_fps': scene.render.fps / scene.render.fps_base,
        'native_origin': [48, 48], 'ground_native': args.ground_native,
        'height_native': args.height_native, 'yaw': args.yaw,
        'review_required': True, 'rendered': args.render, 'frames': [],
    }
    if args.model:
        before = set(bpy.data.objects)
        if args.model.suffix.lower() in ('.glb', '.gltf'):
            bpy.ops.import_scene.gltf(filepath=str(args.model.resolve()))
        elif args.model.suffix.lower() == '.fbx':
            bpy.ops.import_scene.fbx(filepath=str(args.model.resolve()))
        else:
            raise ValueError('Use a GLB, GLTF or FBX asset')
        imported = set(bpy.data.objects) - before
        # glTF's armature importer creates an Icosphere used only as a bone
        # viewport widget. It is not character geometry or part of the GLB.
        bone_widgets = {bone.custom_shape for ob in imported if ob.type == 'ARMATURE'
                        for bone in ob.pose.bones if bone.custom_shape}
        imported -= bone_widgets
        if args.surface:
            added, report['surface_transfer'] = attach_surface(args.surface, imported)
            imported |= added
        meshes = [ob for ob in imported if ob.type == 'MESH' and not ob.hide_render]
        rigs = [ob for ob in imported if ob.type == 'ARMATURE']
        root = bpy.data.objects.new('CHARACTER_ROOT', None)
        scene.collection.objects.link(root)
        for ob in imported:
            if ob.parent not in imported:
                world = ob.matrix_world.copy()
                ob.parent = root
                ob.matrix_world = world
        root.rotation_euler.z = math.radians(args.yaw)
        for rig in rigs:
            rig.data.pose_position = 'REST'
        bpy.context.view_layer.update()
        low, high = bounds(meshes)
        factor = height / (high[2] - low[2])
        root.scale = (factor,) * 3
        root.location = (-factor * (low[0] + high[0]) / 2,
                         -factor * (low[1] + high[1]) / 2, -factor * low[2])
        for rig in rigs:
            rig.data.pose_position = 'POSE'
        if args.action:
            action = bpy.data.actions.get(args.action)
            if not action or not rigs:
                raise ValueError('Requested armature action not found: ' + args.action)
            rigs[0].animation_data_create().action = action
        report['actions'] = [{'name': a.name, 'range': list(a.frame_range)} for a in bpy.data.actions]
        report['rigs'] = [{'name': r.name, 'bones': [b.name for b in r.data.bones]} for r in rigs]
        action = next((ob.animation_data.action for ob in rigs
                       if ob.animation_data and ob.animation_data.action), None)
        report['selected_action'] = action.name if action else None
        start, end = tuple(action.frame_range) if action else (1, 1)
        if args.start is not None:
            start = args.start
        if args.end is not None:
            end = args.end
        if args.render and args.samples > 1 and (not rigs or not action):
            raise RuntimeError('Animation required for a multi-frame pilot; inspect scene.json/asset first')
        scene.frame_start = math.floor(start)
        scene.frame_end = max(scene.frame_start, math.ceil(end))
        motion_root = bpy.data.objects.new('EXPORT_ROOT_MOTION_CORRECTION', None)
        scene.collection.objects.link(motion_root)
        root.parent = motion_root
        bone_name = args.root_bone
        if not bone_name and rigs:
            bone_name = next((b.name for b in rigs[0].pose.bones
                              if b.name.lower().split(':')[-1] in ('hips', 'pelvis', 'root')), None)
        report['motion_root_bone'] = bone_name
        baseline = None
        for i in range(args.samples):
            frame = start + (end - start) * i / args.samples
            motion_root.location = (0, 0, 0)
            scene.frame_set(math.floor(frame), subframe=frame % 1)
            bpy.context.view_layer.update()
            if rigs and bone_name:
                point = rigs[0].matrix_world @ rigs[0].pose.bones[bone_name].matrix.translation
                if baseline is None:
                    baseline = point.copy()
                correction = baseline - point
                if not args.lock_root_z:
                    correction.z = 0
                motion_root.location = correction
                bpy.context.view_layer.update()
            filename = f'Preview-{i+1:02d}.png'
            report['frames'].append({'file': filename, 'source_frame': frame})
            if args.render:
                scene.render.filepath = str((args.out / filename).resolve())
                bpy.ops.render.render(write_still=True)
        scene.frame_set(math.floor(start), subframe=start % 1)
        motion_root.location = (0, 0, 0)
    readme = bpy.data.texts.new('LIESMICH')
    readme.write('Simon Sprite-Pilot\n\nFeste Kamera, PNG mit Alpha, 10x.\n'
                 'Die Referenz ist nicht Teil des Renderbildes.\n'
                 'Vorschau und Posen erst vergleichen; noch keine automatische Spielinstallation.\n'
                 'Die originale Spiellogik bestimmt Bewegung und Peitsche.\n')
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_perspective = 'CAMERA'
            area.spaces.active.shading.type = 'MATERIAL'
    project = args.out / ('Simon_Pilot.blend' if args.model else 'Simon_Exportstudio.blend')
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(project.resolve()))
    report['project'] = str(project.resolve())
    (args.out / 'scene.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('SPRITE_PILOT_RESULT ' + str((args.out / 'scene.json').resolve()), flush=True)


if __name__ == '__main__':
    main()
