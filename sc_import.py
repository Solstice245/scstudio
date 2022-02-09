import bpy
import bmesh
from mathutils import Matrix, Vector, Quaternion
from os import path
from .sc_mat import generate_bl_material
from .sc_io import read_scm, read_sca, read_bp


def sca_armature_animate(ob, filename, scm_bones=None, scm_bone_names=None):
    sca = read_sca(filename)
    if not sca: return

    if not scm_bones:
        scm = read_scm(path.join(filename.rsplit('\\', 1)[0], ob.name + '_LOD0.scm'))
        if not scm: scm = read_scm(path.join(filename.rsplit('\\', 1)[0], ob.name + '_lod0.scm'))
        if scm: scm_bones, scm_bone_names = scm[0:2]
        else: return

    sc_links, sc_frames = sca

    anim = ob.sc_animations.add()
    anim.name = filename.split('\\')[-1]
    anim.action = bpy.data.actions.new(anim.name)

    bones_frames = {sc_link:[] for sc_link in sc_links}

    for sc_frame in sc_frames:
        bl_time = round(sc_frame[0] * 30)
        anim.frame_start = bl_time if bl_time < anim.frame_start else anim.frame_start
        anim.frame_end = bl_time if bl_time > anim.frame_end else anim.frame_end

        for sc_link in sc_links:
            bones_frames[sc_link].append([*sc_frame[2][sc_link], bl_time, sc_frame[1]])

    for bone_name, bone_frames in bones_frames.items():

        bone = ob.data.bones.get(bone_name)
        scm_match = [scm_bones[ii] for ii, scm_bone_name in enumerate(scm_bone_names) if scm_bone_name == bone_name]
        scm_bone = scm_match[0] if scm_match else None
        if not bone or not scm_bone: continue

        scm_mat = Quaternion((scm_bone[19], scm_bone[20], scm_bone[21], scm_bone[22])).to_matrix().to_4x4()
        scm_mat.translation = Vector((scm_bone[16], -scm_bone[18], scm_bone[17]))

        loc_path = 'pose.bones["{}"].location'.format(bone_name)
        rot_path = 'pose.bones["{}"].rotation_quaternion'.format(bone_name)

        locx = anim.action.fcurves.new(loc_path, index=0, action_group=bone_name)
        locy = anim.action.fcurves.new(loc_path, index=1, action_group=bone_name)
        locz = anim.action.fcurves.new(loc_path, index=2, action_group=bone_name)
        rotx = anim.action.fcurves.new(rot_path, index=0, action_group=bone_name)
        roty = anim.action.fcurves.new(rot_path, index=1, action_group=bone_name)
        rotz = anim.action.fcurves.new(rot_path, index=2, action_group=bone_name)
        rotw = anim.action.fcurves.new(rot_path, index=3, action_group=bone_name)

        for bone_frame in bone_frames:

            mat = (Quaternion(bone_frame[3:7])).to_matrix().to_4x4()
            mat.translation = Vector(bone_frame[0:3])
            mat.transpose()
            if not bone.parent: mat @= Matrix(([1, 0, 0], [ 0, 0, 1], [ 0, -1, 0])).to_4x4()
            mat @= bone.matrix.to_4x4()
            mat.transpose()
            
            loc = Vector(mat.translation)
            rot = mat.to_quaternion()

            locx.keyframe_points.insert(bone_frame[7], loc[0])
            locy.keyframe_points.insert(bone_frame[7], loc[1])
            locz.keyframe_points.insert(bone_frame[7], loc[2])
            rotx.keyframe_points.insert(bone_frame[7], rot[0])
            roty.keyframe_points.insert(bone_frame[7], rot[1])
            rotz.keyframe_points.insert(bone_frame[7], rot[2])
            rotw.keyframe_points.insert(bone_frame[7], rot[3])


def scm_armature(ob, sc_bones, sc_bone_names, sc_id, options):
    arm = ob.data
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    skip = []

    for sc_bone, sc_bone_name in zip(sc_bones, sc_bone_names):
        if arm.edit_bones.get(sc_bone_name): 
            skip.append(sc_bone_name)
            continue
        bone = ob.data.edit_bones.new(sc_bone_name)

    for ii, sc_bone in enumerate(sc_bones):

        sc_bone_name = sc_bone_names[ii]

        if sc_bone_name in skip: continue

        bone = ob.data.edit_bones.get(sc_bone_name)

        if sc_bone[24] >= 0:
            sc_parent = sc_bone_names[sc_bone[24]]
            bone.parent = ob.data.edit_bones[sc_parent]

        mat = Matrix((
            (sc_bone[0], sc_bone[1], sc_bone[2], sc_bone[3]),
            (sc_bone[4], sc_bone[5], sc_bone[6], sc_bone[7]),
            (sc_bone[8], sc_bone[9], sc_bone[10], sc_bone[11]),
            (sc_bone[12], sc_bone[13], sc_bone[14], sc_bone[15])
        )).inverted()

        mat @= bone.parent.matrix.inverted() if sc_bone[24] == 0 else Matrix(([1, 0, 0], [ 0, 0, 1], [ 0, -1, 0])).to_4x4()

        loc, rot, scl = mat.transposed().decompose()
        bone.head = loc
        bone.tail = (rot.to_matrix() @ Vector((0, 1, 0))) + bone.head

    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    return ob


def scm_mesh(scm, ob, dirname, filename, options, bp=None, lod=0):
    sc_bones, sc_bone_names, sc_vertices, sc_faces = scm

    me = ob.data

    sc_vert_data = []
    for v in sc_vertices:
        sc_vert_data.append(v[0])
        sc_vert_data.append(-v[2])
        sc_vert_data.append(v[1])

    sc_face_data = []
    for ii in range(len(sc_faces)):
        sc_face_data.append(sc_faces[ii] + (2**15*2 if sc_faces[ii] < 0 else 0))
    sc_tri_seq = range(0, len(sc_faces), 3)

    me.vertices.add(len(sc_vertices))
    me.vertices.foreach_set('co', sc_vert_data)
    me.loops.add(len(sc_faces))
    me.loops.foreach_set('vertex_index', sc_face_data)
    me.polygons.add(len(sc_tri_seq))
    me.polygons.foreach_set('loop_start', [ii for ii in sc_tri_seq])
    me.polygons.foreach_set('loop_total', [3 for ii in sc_tri_seq])

    me.update()
    me.validate()

    for coord in ['uv0', 'uv1']: me.uv_layers.new(name=coord)

    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    bm = bmesh.from_edit_mesh(ob.data)

    bm.verts.layers.deform.verify()
    deform = bm.verts.layers.deform.active
    for sc_vert, bm_vert in zip(sc_vertices, bm.verts): bm_vert[deform][sc_vert[16]] = 1.0

    uvl0 = bm.loops.layers.uv[0]
    uvl1 = bm.loops.layers.uv[1]
    for face in bm.faces:
        face.smooth = options.get('smooth_shading', True)
        for loop in face.loops:
            sc_vert = sc_vertices[loop.vert.index]
            loop[uvl0].uv = (sc_vert[12], -sc_vert[13] + 1)
            loop[uvl1].uv = (sc_vert[14], -sc_vert[15] + 1)

    if options.get('generate_materials', True):
        generate_bl_material(dirname, filename, me, bp, lod)

    if options.get('sharp_edges', True):
        for edge in bm.edges: edge.smooth = len(edge.link_faces) > 1
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.00001)
        bmesh.ops.join_triangles(bm, faces=bm.faces, cmp_sharp=True, cmp_uvs=True, angle_face_threshold=0.75, angle_shape_threshold=0.75)

    bmesh.update_edit_mesh(me)
    bm.free()

    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    return me


def scm_mesh_object(scm, arm_ob, dirname, filename, options, bp=None, lod=0):
    sc_bones, sc_bone_names, sc_vertices, sc_faces = scm

    me = bpy.data.meshes.new(filename)
    ob = bpy.data.objects.new(filename, me)
    ob.parent = arm_ob
    bpy.context.collection.objects.link(ob)

    for ii, sc_bone in enumerate(sc_bones):
        if lod > 0: ob.vertex_groups.new(name=sc_bone_names[ii])
        else: ob.vertex_groups.new(name=sc_bone_names[ii])

    if lod > 0: ob.display_type = 'WIRE'

    scm_mesh(scm, ob, dirname, filename, options, bp, lod)

    modifier = ob.modifiers.new('EdgeSplit', 'EDGE_SPLIT')
    modifier.use_edge_angle = False

    modifier = ob.modifiers.new('Armature', 'ARMATURE')
    modifier.object = arm_ob

    return ob


def init(dirname, filename, options):
    dot_split = filename.split('.')[0]
    sc_id = dot_split.split('_')[0] if 'lod0' in filename.lower() else dot_split
    scm = read_scm(path.join(dirname, filename))
    sc_bones, sc_bone_names, sc_vertices, sc_faces = scm

    bp_path = path.join(dirname, dot_split.split('_')[0] + '_unit.bp')
    bp = read_bp(bp_path) if path.isfile(bp_path) else None

    arm = bpy.data.armatures.new(sc_id)
    arm_ob = bpy.data.objects.new(sc_id, arm)
    bpy.context.collection.objects.link(arm_ob)
    scm_armature(arm_ob, sc_bones, sc_bone_names, sc_id, options)
    ob = scm_mesh_object(scm, arm_ob, dirname, dot_split, options, bp, lod=0)

    if options.get('lod', True) and 'lod0' in dot_split.lower() and bp:
        lod_count = 0
        for key in bp.keys():
            if 'Display.Mesh.LODs.' in key:
                lod_ii = int(key.split('Display.Mesh.LODs.')[1].split('.')[0])
                if lod_ii > lod_count: lod_count = lod_ii

        for ii in range(1, lod_count + 1):
            lod_scm = read_scm(path.join(dirname, sc_id + '_lod' + str(ii) + '.scm'))
            if not lod_scm: continue
            scm_armature(arm_ob, lod_scm[0], lod_scm[1], sc_id, options)
            lod_ob = scm_mesh_object(lod_scm, arm_ob, dirname, sc_id + '_lod' + str(ii), options, bp, lod=ii)

    if options.get('anims', True) and bp:
        for key in bp.keys():
            end_key = key.split('.')[-1]
            if end_key == 'Animation' or end_key in ['AnimationIdle', 'AnimationLand', 'AnimationOpen', 'AnimationTakeoff', 'AnimationWalk']:
                sca = read_sca(path.join(dirname, bp[key].split('/')[-1]))
                sca_armature_animate(arm_ob, path.join(dirname, bp[key].split('/')[-1]), sc_bones, sc_bone_names)
