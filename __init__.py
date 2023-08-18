import bpy
from time import time
from os import path
from . import sc_import
from . import sc_export

bl_info = {
    'name': 'Supreme Commander, SCM/SCA format',
    'author': 'Solstice245',
    'version': (0, 2, 0),
    'blender': (3, 0, 0),
    'location': 'Properties Editor -> Object Data -> SupCom Model Data Panel',
    'description': 'Enables import and (eventually) export of Supreme Commander model data',
    'category': 'Import-Export',
    'doc_url': 'https://github.com/Solstice245/scstudio/blob/master/README.md',
    'tracker_url': 'https://github.com/Solstice245/scstudio/issues',
}


class SCAnimationActionNew(bpy.types.Operator):
    bl_idname = 'sc.animation_action_new'
    bl_label = 'New Action'
    bl_description = 'Create new action'
    bl_options = {'UNDO'}

    def invoke(self, context, event):
        ob = context.object
        anim = ob.sc_animations[ob.sc_animations_index]
        anim.action = bpy.data.actions.new(name=f'{anim.id_data.name}_{anim_group.name}_{anim.name}')
        return {'FINISHED'}


class SCAnimationActionUnlink(bpy.types.Operator):
    bl_idname = 'sc.animation_action_unlink'
    bl_label = 'Unlink Action'
    bl_description = 'Unlink this action from the active action slot'
    bl_options = {'UNDO'}

    def invoke(self, context, event):
        ob = context.object
        anim = ob.sc_animations[ob.sc_animations_index]
        anim.action = None
        return {'FINISHED'}


class SCAnimationProps(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(options=set(), name='Name')
    action: bpy.props.PointerProperty(type=bpy.types.Action)
    frame_start: bpy.props.IntProperty(options=set(), name='Start Frame', default=0)
    frame_end: bpy.props.IntProperty(options=set(), name='End Frame', default=30)


class SCAnimationImport(bpy.types.Operator):
    bl_idname = 'sc.animations_import'
    bl_label = 'Import .SCA Files'
    bl_description = 'Adds an animation management item and an associated action from reading the given file'
    bl_options = {'UNDO'}

    filter_glob: bpy.props.StringProperty(options={'HIDDEN'}, default='*.sca')
    directory: bpy.props.StringProperty(options={'HIDDEN'})
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        print(self.directory)
        for filename in self.files:
            sc_import.sca(context.object, self.directory, filename.name)
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
        layout.template_ID(anim, 'action', new='sc.animation_action_new', unlink='sc.animation_action_unlink')
        row = layout.row()
        row.prop(anim, 'frame_start', text='Frame Range')
        row.prop(anim, 'frame_end', text='')


class SCImportProps(bpy.types.PropertyGroup):
    destructive: bpy.props.BoolProperty(default=True, options=set(), name='Destructive Operations', description='Performs destructive operations on the imported mesh data in an attempt to improve editability, but may cause undesirable artifacts')
    generate_materials: bpy.props.BoolProperty(default=True, options=set(), name='Generate Blender Materials')


class SCImportOperator(bpy.types.Operator):
    bl_idname = 'sc.import'
    bl_label = 'Import .SCM'
    bl_options = {'UNDO'}

    filter_glob: bpy.props.StringProperty(options={'HIDDEN'}, default='*.scm')
    directory: bpy.props.StringProperty(options={'HIDDEN'})
    filename: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        t = time()
        sc_import.scm(self.directory, self.filename, dict(context.scene.sc_import_props))
        print('import time', self.directory, self.filename, time() - t)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        import_props = context.scene.sc_import_props
        self.layout.prop(import_props, 'destructive')
        self.layout.prop(import_props, 'generate_materials')


class SCExportOperator(bpy.types.Operator):
    '''Saves SCM/SCA files from an armature'''
    bl_idname = 'sc.export'
    bl_label = 'Export SCM/SCA'

    filename_ext = '.scm'
    filter_glob: bpy.props.StringProperty(options={'HIDDEN'}, default='*.scm')
    filepath: bpy.props.StringProperty(name='File Path', description='File path for export operation', maxlen=1023, default='')

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'ARMATURE')

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        t = time()
        sc_export.scm(self.filepath, sc_export.scm_data(context.active_object))
        print('export time', self.filepath, time() - t)
        return {'FINISHED'}


def top_bar_import(self, context): self.layout.operator('sc.import', text='Supreme Commander Model (.scm)')
def top_bar_export(self, context): self.layout.operator('sc.export', text='Supreme Commander Model (.scm)')


classes = (
    SCAnimationProps,
    SCAnimationActionNew,
    SCAnimationActionUnlink,
    SCAnimationAdd,
    SCAnimationRemove,
    SCAnimationMove,
    SCAnimationImport,
    SCDataPanel,
    SCImportProps,
    SCImportOperator,
    SCExportOperator,
)


def register():
    for clss in classes: bpy.utils.register_class(clss)
    bpy.types.Scene.sc_import_props = bpy.props.PointerProperty(type=SCImportProps)
    bpy.types.Object.sc_animations = bpy.props.CollectionProperty(type=SCAnimationProps)
    bpy.types.Object.sc_animations_index = bpy.props.IntProperty(default=-1, options=set(), update=sc_anim_update)
    bpy.types.TOPBAR_MT_file_import.append(top_bar_import)
    bpy.types.TOPBAR_MT_file_export.append(top_bar_export)


def unregister():
    for clss in reversed(classes): bpy.utils.unregister_class(clss)
    bpy.types.TOPBAR_MT_file_import.remove(top_bar_import)
    bpy.types.TOPBAR_MT_file_export.remove(top_bar_export)


if __name__ == '__main__': register()
