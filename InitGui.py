import FreeCAD
import FreeCADGui
import os

class NavalWorkbench(FreeCADGui.Workbench):
    MenuText = "Naval"
    ToolTip = "Naval Design Workbench"
    Icon = os.path.join(
        FreeCAD.getUserAppDataDir(),
        "Mod", "NavalWorkbench", "icons", "naval_wb.svg"
    )

    def Initialize(self):
        import NavalCommand
        self.appendToolbar("Naval Tools", ["NavalCommand"])
        self.appendMenu("Naval", ["NavalCommand"])

    def Activated(self):
        FreeCAD.Console.PrintMessage("Naval Workbench aktif!\n")

    def GetClassName(self):
        return "Gui::PythonWorkbench"

FreeCADGui.addWorkbench(NavalWorkbench())