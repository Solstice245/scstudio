from os import path
import struct

modl_keys = [
    'tag', 'version', 'bone_offset', 'bone_count', 'vertices_offset', 'vert_unk', 'vertices_count', 
    'faces_offset', 'face_count', 'info_offset', 'info_count', 'total_bone_count'
]
bone_keys = [
    'mxx', 'mxy', 'mxz', 'mxw', 'myx', 'myy', 'myz', 'myw', 'mzx', 'mzy', 'mzz', 'mzw', 'mwx', 'mwy', 'mwz', 'mww',
    'posx', 'posy', 'posz', 'rotx', 'roty', 'rotz', 'rotw', 'name_offset', 'parent_index', 'unk0', 'unk1'
]
vert_keys = [
    'posx', 'posy', 'posz', 'tanx', 'tany', 'tanz', 'norx', 'nory', 'norz', 'binx', 'biny', 'binz',
    'uv0x', 'uv0y', 'uv1x', 'uv1y', 'bone0', 'bone1', 'bone2', 'bone3'
]
fram_keys = ['posx', 'posy', 'posz', 'rotx', 'roty', 'rotz', 'rotw']
head_keys = ['time', 'flags']
anim_keys = ['tag', 'version', 'frames', 'duration', 'bones', 'names_offset', 'links_offset', 'frames_offset', 'frame_size']


def read_scm(dirname):
    if path.isfile(dirname): sc = open(dirname, 'rb')
    else: return

    modl = dict(zip(modl_keys, struct.unpack('4s11I', sc.read(48))))
    modl['tag'] = modl['tag'].decode('ascii')

    sc.seek(modl['bone_offset'])
    bones = [dict(zip(bone_keys, struct.unpack('16f3f4f4l', sc.read(108)))) for ii in range(modl['total_bone_count'])]

    for bone in bones:
        sc.seek(bone['name_offset'])
        buffer = b''
        while True:
            b = sc.read(1)
            if b == b'\x00': break
            buffer += b
        bone['name'] = buffer.decode('ascii')

    sc.seek(modl['vertices_offset'])
    vertices = [dict(zip(vert_keys, struct.unpack('3f3f3f3f2f2f4B', sc.read(68)))) for ii in range(modl['vertices_count'])]

    sc.seek(modl['faces_offset'])
    faces = struct.unpack(str(modl['face_count']) + 'h', sc.read(2 * modl['face_count']))

    sc.seek(modl['info_offset'])
    info = struct.unpack(str(modl['info_count']) + 's', sc.read(modl['info_count']))[0].decode('ascii')

    sc.close()
    return (bones, vertices, faces)


def read_sca(dirname):
    if path.isfile(dirname): sc = open(dirname, 'rb')
    else: return

    anim = dict(zip(anim_keys, struct.unpack('4siifiiiii', sc.read(36))))
    anim['tag'] = anim['tag'].decode('ascii')

    link_keys = []
    sc.seek(anim['names_offset'])
    for ii in range(anim['bones']):
        buffer = b''
        while True:
            b = sc.read(1)
            if b == b'\x00': break
            buffer += b
        link_keys.append(buffer.decode('ascii'))

    # * skipping this as we assume that the skeleton will have the same heirarchy as the scm
    # sc.seek(anim['links_offset'])
    # links = dict(zip(link_keys, struct.unpack(str(anim['bones']) + 'i', sc.read(anim['bones'] * 4))))

    sc.seek(anim['frames_offset'])
    root = struct.unpack('3f4f', sc.read(28))
    frames = []
    for ii in range(anim['frames']):
        frames.append(dict(zip(head_keys, struct.unpack('fi', sc.read(8)))))
        frames[-1]['bones'] = {}
        for ii in range(anim['bones']): frames[-1]['bones'].update({link_keys[ii]:dict(zip(fram_keys, struct.unpack('3f4f', sc.read(28))))})

    sc.close()
    return link_keys, frames


def read_bp(dirname):  # TODO Prevent removal of spaces within strings
    if path.isfile(dirname): bp = ''.join(open(dirname, 'rb').read().decode().split())
    else: return
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
