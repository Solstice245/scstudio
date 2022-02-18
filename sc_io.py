from os import path
import struct

# modl description
#    tag version bone_offset bone_count vertices_offset vert_unk vertices_count
#    faces_offset face_count info_offset info_count total_bone_count
# bone description
#    mxx mxy mxz mxw myx myy myz myw mzx mzy mzz mzw mwx mwy mwz mww
#    posx posy posz rotx roty rotz rotw name_offset parent_index unk0 unk1
# vertice description
#    posx posy posz tanx tany tanz norx nory norz binx biny binz
#    uv0x uv0y uv1x uv1y bone0 bone1 bone2 bone3
# frame description
#    posx posy posz rotx roty rotz rotw
# head description
#    time flags
# anim description
#    tag version frames duration bones names_offset links_offset frames_offset frame_size


def read_scm(dirname):
    if path.isfile(dirname): sc = open(dirname, 'rb')
    else: return

    modl = struct.unpack('4s11I', sc.read(48))
    sc.seek(modl[2])
    bones = tuple(struct.iter_unpack('16f3f4f4i', sc.read(108 * modl[11])))
    sc.seek(modl[4])
    vertices = tuple(struct.iter_unpack('3f3f3f3f2f2f4B', sc.read(68 * modl[6])))
    sc.seek(modl[7])
    faces = tuple(struct.unpack('h' * modl[8], sc.read(2 * modl[8])))
    sc.seek(modl[9])
    info = struct.unpack('s' * modl[10], sc.read(modl[10]))[0].decode('ascii')

    bone_names = []
    for bone in bones:
        sc.seek(bone[23])
        buffer = b''
        while True:
            b = sc.read(1)
            if b == b'\x00': break
            buffer += b
        bone_names.append(buffer.decode('ascii'))

    sc.close()
    return bones, bone_names, vertices, faces


def read_sca(dirname):
    if path.isfile(dirname): sc = open(dirname, 'rb')
    else: return

    anim = struct.unpack('4siifiiiii', sc.read(36))

    link_keys = []
    sc.seek(anim[5])
    for ii in range(anim[4]):
        buffer = b''
        while True:
            b = sc.read(1)
            if b == b'\x00': break
            buffer += b
        link_keys.append(buffer.decode('ascii'))

    # * skipping this as we assume that the skeleton will have the same heirarchy as the scm
    # sc.seek(anim[6])
    # links = struct.unpack(str(anim[4]) + 'i', sc.read(anim[4] * 4))

    sc.seek(anim[7])
    root = struct.unpack('7f', sc.read(28))
    frames = []
    for ii in range(anim[2]):
        header = struct.unpack('fi', sc.read(8))
        data = list(struct.iter_unpack('7f', sc.read(28 * anim[4])))
        frames.append([*header, {link_keys[ii]:data[ii] for ii in range(anim[4])}])

    sc.close()
    return link_keys, frames


def read_bp(dirname):  # TODO Prevent removal of spaces within strings
    if path.isfile(dirname): bpf = open(dirname, 'rb').read().decode()
    else: return

    clean_bp = ''
    for ln in bpf.split('\n'):
        clean_bp += ''.join(ln.split('#')[0]).split('--')[0]

    bp = ''.join(clean_bp.split())

    char_find = {char: bp.find(char) for char in ['{', '}', '=', ',']}
    split = ['', bp]
    split_char = ''
    flat = {}
    keys = []
    key_counter = {}
    string_char = None

    while True:
        last_split_char = split_char
        split_char = sorted((value, key) for key, value in char_find.items())[0][1]

        if string_char: 
            char_split = split[1].split(string_char, 2)
            split = ['\'' + char_split[1] + '\'', char_split[-1][1:]]
        else: split = split[1].split(split_char, 1)

        if len(split) == 1: break

        char_find = {char: split[1].find(char) for char in ['{', '}', '=', ',']}
        for key in char_find.keys(): char_find[key] = 2**16 if char_find[key] == -1 else char_find[key]

        if split_char == '=': keys.append(split[0])
        elif split_char == '{':
            if last_split_char == '{':
                key_counter['.'.join(keys)] = 0
                keys.append(str(key_counter['.'.join(keys)]))
            elif last_split_char == ',':
                key_counter['.'.join(keys)] += 1
                keys.append(str(key_counter['.'.join(keys)]))
        elif split_char == '}' and last_split_char != '{': keys = keys[:-1]
        elif split_char == ',' and last_split_char != '}':

            val = split[0]

            if string_char: val = val[1:-1]
            else:
                if val.isdigit(): val = int(val)
                elif val in ['true', 'false']: val = val == 'true'
                else: val = float(val)

            if last_split_char == '=':
                flat['.'.join(keys)] = val
                del keys[-1]
            elif last_split_char == '{': flat['.'.join(keys)] = [val]
            elif last_split_char == ',': flat['.'.join(keys)].append(val)
        
        string_char = ('\'' if split[1][0] == '\'' else '\"' if split[1][0] == '\"' else None) if len(split[1]) else None

    return flat
