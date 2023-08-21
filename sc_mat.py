import bpy
from bpy_extras import image_utils
from os import path


def do_unit_nodes(tree, albedo_path=None, specteam_path=None, team_color=(0, 0, 1, 1)):
    albedo_image_node_im = image_utils.load_image(albedo_path, place_holder=not path.isfile(albedo_path), check_existing=True)
    albedo_image_node_im.alpha_mode = 'CHANNEL_PACKED'
    albedo_image_node = tree.nodes.new('ShaderNodeTexImage')
    albedo_image_node.image = albedo_image_node_im
    albedo_image_node.interpolation = 'Closest'
    albedo_image_node.location = (-350.0, -150.0)

    specteam_image_node_im = image_utils.load_image(specteam_path, place_holder=not path.isfile(specteam_path), check_existing=True)
    specteam_image_node_im.alpha_mode = 'CHANNEL_PACKED'
    specteam_image_node = tree.nodes.new('ShaderNodeTexImage')
    specteam_image_node.image = specteam_image_node_im
    specteam_image_node.interpolation = 'Closest'
    specteam_image_node.location = (-350.0, 150.0)

    mix_node = tree.nodes.new('ShaderNodeMixRGB')
    mix_node.inputs['Color2'].default_value = team_color

    tree.links.new(albedo_image_node.outputs['Color'], mix_node.inputs['Color1'])
    tree.links.new(specteam_image_node.outputs['Alpha'], mix_node.inputs['Fac'])

    shader = tree.nodes.new('ShaderNodeBsdfDiffuse')
    shader.location = (250.0, 0.0)
    tree.links.new(mix_node.outputs['Color'], shader.inputs['Color'])

    output = tree.nodes.new('ShaderNodeOutputMaterial')
    output.location = (500.0, 0.0)
    tree.links.new(shader.outputs['BSDF'], output.inputs['Surface'])


def do_seraphim_nodes(tree, albedo_path=None, team_color=(1, 1, 0, 1)):
    albedo_image_node_im = image_utils.load_image(albedo_path, place_holder=not path.isfile(albedo_path), check_existing=True)
    albedo_image_node_im.alpha_mode = 'CHANNEL_PACKED'
    albedo_image_node = tree.nodes.new('ShaderNodeTexImage')
    albedo_image_node.image = albedo_image_node_im
    albedo_image_node.interpolation = 'Closest'
    albedo_image_node.location = (-350.0, 0.0)

    mix_node = tree.nodes.new('ShaderNodeMixRGB')
    mix_node.inputs['Color2'].default_value = team_color

    tree.links.new(albedo_image_node.outputs['Color'], mix_node.inputs['Color1'])
    tree.links.new(albedo_image_node.outputs['Alpha'], mix_node.inputs['Fac'])

    shader = tree.nodes.new('ShaderNodeBsdfDiffuse')
    shader.location = (250.0, 0.0)
    tree.links.new(mix_node.outputs['Color'], shader.inputs['Color'])

    output = tree.nodes.new('ShaderNodeOutputMaterial')
    output.location = (500.0, 0.0)
    tree.links.new(shader.outputs['BSDF'], output.inputs['Surface'])


def generate_bl_material(dirname, sc_id, mesh=None, bp=None, lod=0):
    tex_id = '_'.join(sc_id.split('_')[:-1])
    shader = 'Unit'
    albedo = tex_id + '_albedo.dds'
    specteam = tex_id + '_specteam.dds'

    if bp:
        try:
            lod = bp['Display']['Mesh']['LODs'][lod]
            shader = lod.get('ShaderName', shader)
            albedo = lod.get('AlbedoName', albedo)
            specteam = lod.get('SpecTeamName', specteam)
        except KeyError:
            pass

    material = bpy.data.materials.new(mesh.name)
    material.use_nodes = True
    
    tree = material.node_tree
    tree.links.clear()
    tree.nodes.clear()

    tc = (1, 0, 0, 1) if shader == 'Insect' else (0, 1, 0, 1) if shader == 'Aeon' else (1, 1, 0, 1) if shader == 'Seraphim' else (0, 0, 1, 1)
    if shader == 'Seraphim': do_seraphim_nodes(tree, path.join(dirname, albedo), tc)
    else: do_unit_nodes(tree, path.join(dirname, albedo), path.join(dirname, specteam), tc)

    while len(mesh.materials) > 0: mesh.materials.pop(index=0, update_data=True)
    
    mesh.materials.append(material)
