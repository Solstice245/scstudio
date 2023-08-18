import bpy
import bmesh
import math
from mathutils import Matrix, Vector, Quaternion
from .sc_io import write_scm


co_correction_mat = Matrix(([1, 0, 0], [ 0, 0, 1], [ 0, -1, 0])).to_4x4()


def pad(size):
    val = 32 - (size % 32)

    if (val > 31):
        return 0

    return val


def scm_data(ob):
    depsgraph = bpy.context.evaluated_depsgraph_get()

    # TODO exclude lod1+ bones from lod0, include only used bones on lod1+
    model_bones = ob.data.bones

    model_head_data = [b'MODL', 5]
    total_bone_data = []
    bone_name_data = []
    total_vert_data = []
    total_face_data = []

    bone_to_id = {bone:ii for ii, bone in enumerate(model_bones)}

    offset_val = 64

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

    for child in [child for child in ob.children if child.type == 'MESH']:
        bm = bmesh.new(use_operators=True)
        bm.from_object(child, depsgraph)
        bmesh.ops.triangulate(bm, faces=bm.faces)

        layer_deform = bm.verts.layers.deform.verify()

        try: layer_uv0 = bm.loops.layers.uv.values()[0]
        except KeyError: layer_uv0 = bm.loops.layers.uv.new('SCM 0')

        try: layer_uv1 = bm.loops.layers.uv.values()[1]
        except KeyError: layer_uv1 = bm.loops.layers.uv.new('SCM 1')

        # vertex group index does not necessarily match bone heirarchy, so we need to map it
        group_ii_to_bone_ii = {}
        for ii, group in enumerate(child.vertex_groups):
            bone = model_bones.get(group.name)
            if bone is not None:
                group_ii_to_bone_ii[ii] = bone_to_id[bone]

        face_to_tan = {}
        loop_to_id_index = {}
        for vert in bm.verts:
            co = co_correction_mat @ ob.matrix_local @ vert.co
            # sort by weight and then pick the first one with a matching bone
            deformation = 0
            deformation_pairs = sorted(vert[layer_deform].items(), key=lambda x: x[1])
            for deform_pair in deformation_pairs:
                if group_ii_to_bone_ii.get(deform_pair[0]):
                    deformation = group_ii_to_bone_ii[deform_pair[0]]
                    break

            for loop in vert.link_loops:
                try:
                    tan = face_to_tan[loop.face.index]
                except KeyError:
                    l0, l1, l2 = ((vert.co, L[layer_uv0].uv[1]) for L in loop.face.loops)
                    tan = face_to_tan[loop.face.index] = ((l2[1] - l0[1]) * (l1[0] - l0[0]) - (l1[1] - l0[1]) * (l2[0] - l0[0])).normalized()

                id_tuple = (*co, *tan, *vert.normal, *(vert.normal.cross(tan)), loop[layer_uv0].uv[0], -loop[layer_uv0].uv[1] + 1, loop[layer_uv1].uv[0], -loop[layer_uv1].uv[1] + 1, deformation, 0, 0, 0)
                id_index = vert_id_to_index.get(id_tuple)
                if id_index is None:
                    id_index = vert_counter
                    vert_id_to_index[id_tuple] = vert_counter
                    total_vert_data.extend(id_tuple)
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


def scm(filepath, scm_data):
    write_scm(filepath, *scm_data)
