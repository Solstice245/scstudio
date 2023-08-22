import bpy
import bmesh
import math
from mathutils import Matrix, Vector, Quaternion
from os import path
from .sc_io import write_scm, write_sca


co_correction_mat = Matrix(((1, 0, 0), ( 0, 0, 1), ( 0, -1, 0))).to_4x4()


def pad(size):
    val = 16 - (size % 16)
    return val + 16 if (val < 4) else val


def scm_data(ob):
    depsgraph = bpy.context.evaluated_depsgraph_get()

    model_bones = ob.data.bones

    model_head_data = [b'MODL', 5]
    total_bone_data = []
    bone_name_data = []
    total_vert_data = []
    total_face_data = []

    bone_to_id = {bone:ii for ii, bone in enumerate(model_bones)}

    offset_val = 48
    offset_val += pad(offset_val)

    for b in model_bones:
        b_rest = b.matrix_local.transposed()
        md = (b_rest @ co_correction_mat.inverted()).inverted()
        rel_mat = b_rest @ (b.parent.matrix_local.transposed().inverted() if b.parent else co_correction_mat.inverted())
        loc, rot, scl = rel_mat.transposed().decompose()
        total_bone_data.extend((*md[0], *md[1], *md[2], *md[3], *loc, *rot, offset_val, -1 if not b.parent else bone_to_id[b.parent], 0, 0))
        offset_val += len(b.name) + 1
        bone_name_data.append(bytearray(b.name.encode('ascii')))

    offset_val += pad(offset_val)
    model_head_data.append(offset_val)
    model_head_data.append(len(model_bones))
    offset_val += len(model_bones) * 108
    offset_val += pad(offset_val)
    model_head_data.append(offset_val)

    vert_id_to_index = {}
    vert_counter = 0

    for child in [child for child in ob.children_recursive if child.type == 'MESH']:
        bm = bmesh.new(use_operators=True)
        bm.from_object(child, depsgraph)
        bmesh.ops.transform(bm, matrix=co_correction_mat @ child.matrix_local, verts=bm.verts, use_shapekey=False)
        bmesh.ops.triangulate(bm, faces=bm.faces)

        layer_deform = bm.verts.layers.deform.verify()

        try: layer_uv0 = bm.loops.layers.uv.values()[0]
        except IndexError: layer_uv0 = bm.loops.layers.uv.new('SCM 0')

        try: layer_uv1 = bm.loops.layers.uv.values()[1]
        except IndexError: layer_uv1 = bm.loops.layers.uv.new('SCM 1')

        # vertex group index does not necessarily match bone heirarchy, so we need to map it
        group_ii_to_bone_ii = {}
        for ii, group in enumerate(child.vertex_groups):
            bone = model_bones.get(group.name)
            if bone is not None:
                group_ii_to_bone_ii[ii] = bone_to_id[bone]

        face_to_tan_bi = {}
        loop_to_id_index = {}
        for vert in bm.verts:
            # sort by weight and then pick the first one with a matching bone
            deformation = 0
            deformation_pairs = sorted(vert[layer_deform].items(), key=lambda x: x[1])
            for deform_pair in deformation_pairs:
                if group_ii_to_bone_ii.get(deform_pair[0]):
                    deformation = group_ii_to_bone_ii[deform_pair[0]]
                    break

            for loop in vert.link_loops:
                id_tuple = (*vert.co, *vert.normal, *loop[layer_uv0].uv, deformation)
                id_index = vert_id_to_index.get(id_tuple)
                if id_index is None:
                    try:
                        t, b = face_to_tan_bi[loop.face.index]
                    except KeyError:
                        c1, c2, c3 = (L.vert.co for L in loop.face.loops)
                        u1, u2, u3 = (L[layer_uv0].uv[0] for L in loop.face.loops)
                        v1, v2, v3 = (1 - L[layer_uv0].uv[1] for L in loop.face.loops)
                        d = (v2 - v1) * (u3 - u1) - (u2 - u1) * (v3 - v1)
                        try:
                            t = (((v3 - v1) * (c2 - c1) - (v2 - v1) * (c3 - c1)) / d).normalized()
                            b = (((u3 - u1) * (c2 - c1) - (u2 - u1) * (c3 - c1)) / -d).normalized()
                        except ZeroDivisionError:
                            t = Vector((0, 0, 0))
                            b = Vector((0, 0, 0))
                        face_to_tan_bi[loop.face.index] = (t, b)

                    id_index = vert_counter
                    vert_id_to_index[id_tuple] = vert_counter
                    total_vert_data.extend((*vert.co, *vert.normal, *t, *b, loop[layer_uv0].uv[0], 1 - loop[layer_uv0].uv[1], loop[layer_uv1].uv[0], 1 - loop[layer_uv1].uv[1], deformation, 0, 0, 0))
                    model_head_data[3] = max(model_head_data[3], deformation)
                    vert_counter += 1
                loop_to_id_index[loop] = id_index

        for face in bm.faces:
            for loop in face.loops:
                total_face_data.append(loop_to_id_index[loop])

    model_head_data.extend((0, vert_counter))

    offset_val += vert_counter * 68
    offset_val += pad(offset_val)
    model_head_data.append(offset_val)
    model_head_data.append(len(total_face_data))

    # info offset, info length, total bones
    model_head_data.extend((0, 0, len(model_bones)))

    return model_head_data, total_bone_data, bone_name_data, total_vert_data, total_face_data, b''


def scm(dirname, ob):
    write_scm(path.join(dirname, ob.name + '.scm'), *scm_data(ob))


def sca_data(ob, sc_anim, sc_anim_index):
    ob.sc_animations_index = sc_anim_index

    frame_list = list(range(sc_anim.frame_start, sc_anim.frame_end + 1))
    # TODO filter bones to animated bones
    anim_bones = ob.pose.bones
    bone_to_ii = {bone:ii for ii, bone in enumerate(anim_bones)}

    anim_header_data = [b'ANIM', 5, len(frame_list), frame_list[-1] / 30, len(anim_bones)]
    total_frame_data = []
    total_name_data = chr(0).join([bone.name for bone in anim_bones]) + chr(0)
    total_link_data = [bone_to_ii[bone.parent] if bone.parent else -1 for bone in anim_bones]

    offset_val = 36  # header
    offset_val += pad(offset_val)
    anim_header_data.append(offset_val)
    offset_val += len(total_name_data)  # names
    offset_val += pad(offset_val)
    anim_header_data.append(offset_val)
    offset_val += len(anim_bones) * 4  # links
    offset_val += pad(offset_val)
    anim_header_data.append(offset_val)
    anim_header_data.append(8 + 28 * len(anim_bones))  # frame_size

    for frame in frame_list:
        bpy.context.scene.frame_set(frame)

        total_frame_data.extend((frame / 30, 0))

        for pb in anim_bones:

            if not pb.parent:
                rel_mat = pb.matrix.transposed() @ co_correction_mat.inverted()
            else:
                rel_mat = pb.matrix.transposed() @ pb.parent.matrix.transposed().inverted()
            rel_mat.transpose()

            total_frame_data.extend(rel_mat.to_translation())
            total_frame_data.extend(rel_mat.to_quaternion().normalized())

    return anim_header_data, total_name_data, total_link_data, total_frame_data


def sca(dirname, ob, sc_anim, sc_anim_index):
    write_sca(path.join(dirname, sc_anim.name) + '.sca', *sca_data(ob, sc_anim, sc_anim_index))
