# scstudio - Blender Import-Export for .scm and .sca file formats

__Blender__ addon to ___import and export___ 3D model/animation files used in the game __Supreme Commander__

Created by *John Wharton*

## Installation

1. Download the most recent version at __(https://github.com/Solstice245/scstudio)__
2. Install the addon using one of these methods:
- __Option A__ (automatic):
    1. From the Blender menu, navigate to `Edit -> Preferences -> Add-ons`.
    2. Click on the _Install_ button and select the ___zipped___ folder containing the addon.
- __Option B__ (manual):
    1. Extract the files from the ___zipped___ folder to `scstudio` directory.
    2. Place the newly made folder into the following location (Adjust for the installed version of Blender):
        - `%APPDATA%\Blender Foundation\Blender\3.0x\scripts\addons` _(Assumes a Windows operating system)_
    - _(If the addon does not appear as a choice in Blender's preferences click the `Refresh` button or restart the application.)_
3. Activate the addon in Blender's preferences by toggling the checkbox for the `Supreme Commander SCM & SCA format` entry in the Add-ons tab.

## Usage

The following operation is added to the _Import_ top bar:
- __Supreme Commander Model (.scm)__
    - Opens a file manager from which you can select _multiple_ files at a time.
    - Option: __Generate Materials__
        - If the file is being imported from the same directory as the blueprint and texture files, Blender will try to have material nodes set up to use those textures automatically.
    - For each file, an armature object and child mesh object are placed into the scene using data from the file.

The following operation is added to the _Export_ top bar:
- __Supreme Commander Model (.scm)__
    - Operates on all selected armature objects.
    - All mesh vertices must be rigged to their parent armature via vertex groups.
    - Opens a file manager from which you may select an output directory. The output file name is derived from the armature object's name.
    - The output data is derived from the armature object and all mesh objects which are parented under it.

The following panel is added to the _Data_ tab of the properties editor:
- __Supreme Commander Animations__
    - Operator: __Import (.sca)__
        - Opens a file manager from which you can select _multiple_ files at a time, and import the animation data into Blender. Once imported, the animation names are added to the animation list, and then assigned the action and custom frame range values.
    - UI List:
        - Lists all of the animations which have been imported onto the armature. Each entry has an action drop down and frame range values.
        - Selecting an animation in the list will automatically adjust the scene so that the armature is using the animation's action, and the timeline is using the animation's defined frame range.
        - To return to an unanimated state, right click an item in the list and select _"Reset to Default Value"_ from the dropdown.
        - Operator: __Export (.sca)__
            - Operates on the selected animation in the list.
            - Opens a file manager from which you may select an output directory. The output file name is derived from the name given to the animation entry in the list.
            - The output data is derived from the animation's selected action and frame range.
