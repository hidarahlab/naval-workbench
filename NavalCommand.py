import FreeCAD
import FreeCADGui

class NavalCommand:
    def GetResources(self):
        return {
            "MenuText": "Naval Tool",
            "ToolTip": "Naval design command"
        }

    def Activated(self):
        FreeCAD.Console.PrintMessage("Naval Workbench siap!\n")

    def IsActive(self):
        return True

FreeCADGui.addCommand("NavalCommand", NavalCommand())