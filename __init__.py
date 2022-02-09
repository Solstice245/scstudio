import bpy
from timeit import timeit
from os import path
from . import sc_import

bl_info = {
    'name': 'Supreme Commander, SCM/SCA format',
    'author': 'Solstice245',
    'version': (0, 1, 0),
    'blender': (3, 0, 0),
    'location': 'Properties Editor -> Object Data -> SupCom Model Data Panel',
    'description': 'Enables import and (eventually) export of Supreme Commander model data',
    'category': 'Import-Export',
    'doc_url': 'https://github.com/Solstice245/scstudio/blob/master/README.md',
    'tracker_url': 'https://github.com/Solstice245/scstudio/issues',
}


class SCAnimationProps(bpy.types.PropertyGroup):
    bl_export: bpy.props.BoolProperty(options=set(), name='Automatically Export Animation', default=True)
    name: bpy.props.StringProperty(options=set(), name='Name')
    action: bpy.props.PointerProperty(type=bpy.types.Action)
    frame_start: bpy.props.IntProperty(options=set(), name='Start Frame', default=0)
    frame_end: bpy.props.IntProperty(options=set(), name='End Frame', default=30)


class SCAnimationImport(bpy.types.Operator):
    bl_idname = 'sc.animations_import'
    bl_label = 'Import .SCA'
    bl_description = 'Adds an animation management item and an associated action from reading the given file'
    bl_options = {'UNDO'}

    filter_glob: bpy.props.StringProperty(options={'HIDDEN'}, default='*.sca')
    filepath: bpy.props.StringProperty(name='File Path', description='File path for import operation', maxlen=1023, default='')

    def execute(self, context):
        sc_import.sca_armature_animate(context.object, self.filepath)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class SCAnimationAdd(bpy.types.Operator):
    bl_idname = 'sc.animations_add'
    bl_label = 'Add Animation'
    bl_description = 'Adds an animation management item and an associated action'
    bl_options = {'UNDO'}

    def invoke(self, context, event):
        ob = context.object
        anim = ob.sc_animations.add()
        anim.name = ob.name + '_Aanim.sca'
        anim.action = bpy.data.actions.new(anim.name)
        anim.frame_start = 0
        anim.frame_end = 30

        ob.sc_animations_index = len(ob.sc_animations) - 1
        return {'FINISHED'}


class SCAnimationRemove(bpy.types.Operator):
    bl_idname = 'sc.animations_remove'
    bl_label = 'Remove Animation'
    bl_description = 'Removes the active animation management item and the associated action'
    bl_options = {'UNDO'}

    def invoke(self, context, event):
        ob = context.object
        if len(ob.sc_animations) == 0: return {'FINISHED'}
        
        anim = ob.sc_animations[ob.sc_animations_index]

        if anim.action: anim.action.name += '(Deleted)'

        ob.sc_animations.remove(ob.sc_animations_index)

        ob.sc_animations_index -= 1 if ob.sc_animations_index > 0 or len(ob.sc_animations) == 0 else 0
        ob.sc_animations_index += 1 if ob.sc_animations_index is len(ob.sc_animations) else 0

        return {'FINISHED'}


class SCAnimationMove(bpy.types.Operator):
    bl_idname = 'sc.animations_move'
    bl_label = 'Move Animation'
    bl_description = 'Moves the active animation up/down in the list'
    bl_options = {'UNDO'}

    shift: bpy.props.IntProperty(default=0)

    def invoke(self, context, event):
        ob = context.object

        if (ob.sc_animations_index < len(ob.sc_animations) - self.shift and ob.sc_animations_index >= -self.shift):
            ob.sc_animations.move(ob.sc_animations_index, ob.sc_animations_index + self.shift)
            ob.sc_animations_index += self.shift

        return {'FINISHED'}


def sc_anim_update(self, context):
    if self.animation_data is None: self.animation_data_create()

    if self.sc_animations_index < 0: self.animation_data.action = None
    else:
        anim = self.sc_animations[self.sc_animations_index]
        if not anim.action: anim.action = bpy.data.actions.new(anim.name)
        self.animation_data.action = anim.action
        context.scene.frame_current = context.scene.frame_start = anim.frame_start
        context.scene.frame_end = anim.frame_end - 1


class SCDataPanel(bpy.types.Panel):
    bl_idname = 'OBJECT_PT_SC_ANIMATION'
    bl_label = 'SupCom Model Data'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        return context.object.type == 'ARMATURE'

    def draw(self, context):
        ob = context.object
        layout = self.layout
        layout.use_property_split = True

        rows = 4 if len(ob.sc_animations) else 2

        layout.label(text='Animations')
        layout.operator('sc.animations_import')
        row = layout.row()
        col = row.column()
        col.template_list('UI_UL_list', 'sc_animations', ob, 'sc_animations', ob, 'sc_animations_index', rows=rows)
        col = row.column(align=True)
        col.operator('sc.animations_add', icon='ADD', text='')
        col.operator('sc.animations_remove', icon='REMOVE', text='')

        if len(ob.sc_animations) > 1:
            col.separator()
            col.operator('sc.animations_move', icon='TRIA_UP', text='').shift = -1
            col.operator('sc.animations_move', icon='TRIA_DOWN', text='').shift = 1

        if ob.sc_animations_index < 0: return

        anim = ob.sc_animations[ob.sc_animations_index]
        layout.prop(anim, 'frame_start')
        layout.prop(anim, 'frame_end')
        layout.prop(anim, 'bl_export')


class SCImportProps(bpy.types.PropertyGroup):
    smooth_shading: bpy.props.BoolProperty(default=True, options=set(), name='Smooth Shading')
    sharp_edges: bpy.props.BoolProperty(default=True, options=set(), name='Sharp Edges')
    generate_materials: bpy.props.BoolProperty(default=True, options=set(), name='Generate Blender Materials')
    lods: bpy.props.BoolProperty(default=True, options=set(), name='Import LOD Meshes')
    anims: bpy.props.BoolProperty(default=True, options=set(), name='Import Animations')


class SCImportOperator(bpy.types.Operator):
    bl_idname = 'sc.import'
    bl_label = 'Import .SCM'
    bl_options = {'UNDO'}

    filter_glob: bpy.props.StringProperty(options={'HIDDEN'}, default='*.scm')
    filepath: bpy.props.StringProperty(name='File Path', description='File path for import operation', maxlen=1023, default='')

    def execute(self, context):
        sc_import.init(*path.split(self.properties.filepath), dict(context.scene.sc_import_props))

        # options = dict(context.scene.sc_import_props)
        # tim = timeit(lambda: sc_import.init(*path.split(self.properties.filepath), options), number=1)
        # print(tim)
        
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        import_props = context.scene.sc_import_props
        self.layout.prop(import_props, 'anims')
        self.layout.prop(import_props, 'lods')
        self.layout.prop(import_props, 'smooth_shading')
        self.layout.prop(import_props, 'sharp_edges')
        self.layout.prop(import_props, 'generate_materials')


def top_bar_import(self, context): self.layout.operator('sc.import', text='Supreme Commander Model (.scm)')
# def top_bar_export(self, context): self.layout.operator('sc.export', text='Supreme Commander Model (.scm)')


classes = (
    SCAnimationProps,
    SCAnimationAdd,
    SCAnimationRemove,
    SCAnimationMove,
    SCAnimationImport,
    SCDataPanel,
    SCImportProps,
    SCImportOperator,
)


def register():
    for clss in classes: bpy.utils.register_class(clss)
    bpy.types.Scene.sc_import_props = bpy.props.PointerProperty(type=SCImportProps)
    bpy.types.Object.sc_animations = bpy.props.CollectionProperty(type=SCAnimationProps)
    bpy.types.Object.sc_animations_index = bpy.props.IntProperty(default=-1, options=set(), update=sc_anim_update)
    bpy.types.TOPBAR_MT_file_import.append(top_bar_import)
    # bpy.types.TOPBAR_MT_file_export.append(top_bar_export)


def unregister():
    for clss in reversed(classes): bpy.utils.unregister_class(clss)
    bpy.types.TOPBAR_MT_file_import.remove(top_bar_import)
    # bpy.types.TOPBAR_MT_file_export.remove(top_bar_export)


if __name__ == '__main__': register()
