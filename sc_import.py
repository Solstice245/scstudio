import bpy
import bmesh
from mathutils import Matrix, Vector, Quaternion
from os import path
from .sc_mat import generate_bl_material
from .sc_io import read_scm, read_sca, read_bp


co_correction_mat = Matrix(((1, 0, 0), ( 0, 0, 1), ( 0, -1, 0))).to_4x4()


def sca(ob, dirname, filename):
    sca = read_sca(path.join(dirname, filename))
    if not sca: return

    sc_links, sc_frames = sca

    anim = ob.sc_animations.add()
    anim.name = filename.rsplit('.')[0]
    anim.action = bpy.data.actions.new(anim.name)

    bones_frames = {sc_link:[] for sc_link in sc_links}

    anim.frame_start = 2147483647
    anim.frame_end = -2147483648

    for sc_frame in sc_frames:
        bl_time = round(sc_frame[0] * 30)
        anim.frame_start = min(bl_time, anim.frame_start)
        anim.frame_end = max(bl_time, anim.frame_end)

        for sc_link in sc_links:
            bones_frames[sc_link].append((*sc_frame[2][sc_link], bl_time, sc_frame[1]))

    for bone_name, bone_frames in bones_frames.items():

        # TODO find closest match as sometimes bone names differ slightly from scm and sca
        bone = ob.data.bones.get(bone_name)
        if not bone: continue  # TODO warning when bone match cannot be found

        loc_path = 'pose.bones["{}"].location'.format(bone_name)
        rot_path = 'pose.bones["{}"].rotation_quaternion'.format(bone_name)

        locx = anim.action.fcurves.new(loc_path, index=0, action_group=bone_name)
        locy = anim.action.fcurves.new(loc_path, index=1, action_group=bone_name)
        locz = anim.action.fcurves.new(loc_path, index=2, action_group=bone_name)
        rotx = anim.action.fcurves.new(rot_path, index=0, action_group=bone_name)
        roty = anim.action.fcurves.new(rot_path, index=1, action_group=bone_name)
        rotz = anim.action.fcurves.new(rot_path, index=2, action_group=bone_name)
        rotw = anim.action.fcurves.new(rot_path, index=3, action_group=bone_name)

        if not bone.parent:
            bone_loc_vec = bone.head_local @ bone.matrix_local
        else:
            bone_loc_vec = (bone.head_local - bone.parent.head_local) @ (bone.matrix_local @ bone.parent.matrix_local @ co_correction_mat)

        len_frames = len(bone_frames)
        key_sel = [False] * len_frames
        key_interp = [1] * len_frames
        key_co_locx = []
        key_co_locy = []
        key_co_locz = []
        key_co_rotx = []
        key_co_roty = []
        key_co_rotz = []
        key_co_rotw = []

        for bone_frame in bone_frames:

            if not bone: continue

            sca_mat = Quaternion(bone_frame[3:7]).to_matrix().to_4x4()
            sca_mat.translation = Vector(bone_frame[0:3])
            sca_mat.transpose()
            
            if not bone.parent:
                sca_mat @= co_correction_mat
            
            pose_mat = (sca_mat @ bone.matrix.to_4x4()).transposed()
            loc, rot = pose_mat.to_translation() - bone_loc_vec, pose_mat.to_quaternion()

            key_co_locx.extend((bone_frame[7], loc[0]))
            key_co_locy.extend((bone_frame[7], loc[1]))
            key_co_locz.extend((bone_frame[7], loc[2]))
            key_co_rotx.extend((bone_frame[7], rot[0]))
            key_co_roty.extend((bone_frame[7], rot[1]))
            key_co_rotz.extend((bone_frame[7], rot[2]))
            key_co_rotw.extend((bone_frame[7], rot[3]))

        fcurve_data_pairs = ((locx, key_co_locx), (locy, key_co_locy), (locz, key_co_locz), (rotx, key_co_rotx), (roty, key_co_roty), (rotz, key_co_rotz), (rotw, key_co_rotw))

        for fcurve, key_co in fcurve_data_pairs:
            fcurve.select = False
            fcurve.keyframe_points.add(len_frames)
            fcurve.keyframe_points.foreach_set('co', key_co)
            fcurve.keyframe_points.foreach_set('interpolation', key_interp)
            fcurve.keyframe_points.foreach_set('select_control_point', key_sel)
            fcurve.keyframe_points.foreach_set('select_left_handle', key_sel)
            fcurve.keyframe_points.foreach_set('select_right_handle', key_sel)


def scm_armature(sc_bones, sc_bone_names, sc_id, options):
    arm = bpy.data.armatures.new(sc_id)
    ob = bpy.data.objects.new(sc_id, arm)
    bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    for sc_bone, sc_bone_name in zip(sc_bones, sc_bone_names):
        bone = ob.data.edit_bones.new(sc_bone_name)

        if sc_bone[24] >= 0:
            sc_parent = sc_bone_names[sc_bone[24]]
            bone.parent = ob.data.edit_bones[sc_parent]

        mat = Matrix((sc_bone[0:4], sc_bone[4:8], sc_bone[8:12], sc_bone[12:16])).inverted()
        mat @= bone.parent.matrix.inverted() if sc_bone[24] == 0 else co_correction_mat
        mat.transpose()

        bone.head = mat.translation
        bone.tail = (mat.to_quaternion().to_matrix() @ Vector((0, 1, 0))) + bone.head
        bone.matrix = mat

    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    arm.show_axes = True

    return ob


def scm_mesh(scm, me, options):
    sc_bones, sc_bone_names, sc_vertices, sc_faces = scm

    sc_vert_data = []
    for v in sc_vertices:
        sc_vert_data.extend((v[0], -v[2], v[1]))

    sc_face_data = []
    for ii in range(len(sc_faces)):
        sc_face_data.append(sc_faces[ii])
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

    bm = bmesh.new()
    bm.from_mesh(me)

    bm.verts.layers.deform.verify()
    deform = bm.verts.layers.deform.active
    for sc_vert, bm_vert in zip(sc_vertices, bm.verts): bm_vert[deform][sc_vert[16]] = 1.0

    uvl0 = bm.loops.layers.uv.new('SCM 0')
    uvl1 = bm.loops.layers.uv.new('SCM 1')
    for face in bm.faces:
        face.smooth = True
        for loop in face.loops:
            sc_vert = sc_vertices[loop.vert.index]
            loop[uvl0].uv = (sc_vert[12], -sc_vert[13] + 1)
            loop[uvl1].uv = (sc_vert[14], -sc_vert[15] + 1)

    doubles = bmesh.ops.find_doubles(bm, verts=bm.verts, dist=0.00001)['targetmap']
    for origin in list(doubles.keys()):
        target = doubles[origin]

        for edge in [*origin.link_edges, *target.link_edges]:
            if len(edge.link_faces) == 1:
                edge.smooth = False

        sv0 = sc_vertices[origin.index]
        sv1 = sc_vertices[target.index]

        if (*sv0[6:9], *sv0[12:18]) != (*sv0[6:9], *sv0[12:18]):
            del doubles[origin]
    bmesh.ops.weld_verts(bm, targetmap=doubles)

    if options.get('destructive', True):
        bmesh.ops.dissolve_limit(bm, angle_limit=0.1, use_dissolve_boundaries=False, verts=bm.verts, edges=bm.edges, delimit={'NORMAL', 'UV'})
        bmesh.ops.join_triangles(bm, faces=bm.faces, cmp_sharp=True, cmp_uvs=True, angle_face_threshold=1.0, angle_shape_threshold=1.0)

    bm.to_mesh(me)
    bm.free()


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

    scm_mesh(scm, me, options)

    modifier = ob.modifiers.new('Armature', 'ARMATURE')
    modifier.object = arm_ob

    modifier = ob.modifiers.new('EdgeSplit', 'EDGE_SPLIT')
    modifier.use_edge_angle = False

    if options.get('generate_materials', True) and bp:
        generate_bl_material(dirname, filename, me, bp, lod)

    return ob


def scm(dirname, filename, options):
    sc_id = filename.rsplit('.')[0]
    scm = read_scm(path.join(dirname, filename))
    sc_bones, sc_bone_names, sc_vertices, sc_faces = scm

    bp_path = path.join(dirname, '_'.join(sc_id.split('_')[:-1]) + '_unit.bp')
    bp = read_bp(bp_path) if path.isfile(bp_path) else None

    try: lod = int(sc_id.rsplit('_lod')[1][0])
    except (ValueError, IndexError) as e: lod = 0

    arm_ob = scm_armature(sc_bones, sc_bone_names, sc_id, options)
    ob = scm_mesh_object(scm, arm_ob, dirname, sc_id, options, bp, lod=lod)
