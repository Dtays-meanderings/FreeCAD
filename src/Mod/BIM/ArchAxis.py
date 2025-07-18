# SPDX-License-Identifier: LGPL-2.1-or-later

# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2011 Yorik van Havre <yorik@uncreated.net>              *
# *                                                                         *
# *   This file is part of FreeCAD.                                         *
# *                                                                         *
# *   FreeCAD is free software: you can redistribute it and/or modify it    *
# *   under the terms of the GNU Lesser General Public License as           *
# *   published by the Free Software Foundation, either version 2.1 of the  *
# *   License, or (at your option) any later version.                       *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful, but        *
# *   WITHOUT ANY WARRANTY; without even the implied warranty of            *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU      *
# *   Lesser General Public License for more details.                       *
# *                                                                         *
# *   You should have received a copy of the GNU Lesser General Public      *
# *   License along with FreeCAD. If not, see                               *
# *   <https://www.gnu.org/licenses/>.                                      *
# *                                                                         *
# ***************************************************************************

__title__  = "FreeCAD Axis System"
__author__ = "Yorik van Havre"
__url__    = "https://www.freecad.org"

## @package ArchAxis
#  \ingroup ARCH
#  \brief Axis for the Arch workbench
#
#  This module provides tools to build axis
#  An axis is a collection of planar axes with a number/tag

import math

import FreeCAD
import ArchCommands
import Draft
import Part

from FreeCAD import Vector
from draftutils import params

if FreeCAD.GuiUp:
    import re
    from pivy import coin
    from PySide import QtCore, QtGui
    from PySide.QtCore import QT_TRANSLATE_NOOP
    import FreeCADGui
    from draftutils.translate import translate
else:
    # \cond
    def translate(ctxt,txt):
        return txt
    def QT_TRANSLATE_NOOP(ctxt,txt):
        return txt
    # \endcond


class _Axis:

    "The Axis object"

    def __init__(self,obj):

        obj.Proxy = self
        self.Type = "Axis"
        self.setProperties(obj)

    def setProperties(self,obj):

        pl = obj.PropertiesList
        if not "Distances" in pl:
            obj.addProperty("App::PropertyFloatList","Distances","Axis", QT_TRANSLATE_NOOP("App::Property","The intervals between axes"), locked=True)
        if not "Angles" in pl:
            obj.addProperty("App::PropertyFloatList","Angles","Axis", QT_TRANSLATE_NOOP("App::Property","The angles of each axis"), locked=True)
        if not "Labels" in pl:
            obj.addProperty("App::PropertyStringList","Labels","Axis", QT_TRANSLATE_NOOP("App::Property","The label of each axis"), locked=True)
        if not "CustomNumber" in pl:
            obj.addProperty("App::PropertyString","CustomNumber","Axis", QT_TRANSLATE_NOOP("App::Property","An optional custom bubble number"), locked=True)
        if not "Length" in pl:
            obj.addProperty("App::PropertyLength","Length","Axis", QT_TRANSLATE_NOOP("App::Property","The length of the axes"), locked=True)
            obj.Length=3000
        if not "Placement" in pl:
            obj.addProperty("App::PropertyPlacement","Placement","Base","", locked=True)
        if not "Shape" in pl:
            obj.addProperty("Part::PropertyPartShape","Shape","Base","", locked=True)
        if not "Limit" in pl:
            obj.addProperty("App::PropertyLength","Limit","Axis", QT_TRANSLATE_NOOP("App::Property","If not zero, the axes are not represented as one full line but as two lines of the given length"), locked=True)
            obj.Limit=0

    def onDocumentRestored(self,obj):

        self.setProperties(obj)

    def execute(self,obj):

        pl = obj.Placement
        geoms = []
        dist = 0
        distances = [0]
        angles = [0]
        if hasattr(obj, "Distances"):
            distances = obj.Distances
        if hasattr(obj, "Angles"):
            angles = obj.Angles
        if distances and obj.Length.Value:
            if angles and len(distances) == len(angles):
                for i in range(len(distances)):
                    dist += distances[i]
                    ang = math.radians(angles[i])
                    ln = obj.Length.Value
                    ln = 100 * ln if abs(math.cos(ang)) < 0.01 else ln / math.cos(ang)
                    unitvec = Vector(math.sin(ang), math.cos(ang), 0)
                    p1 = Vector(dist, 0, 0)
                    p2 = p1 + unitvec * ln
                    if hasattr(obj,"Limit") and obj.Limit.Value:
                        p3 = unitvec * obj.Limit.Value
                        p4 = unitvec * -obj.Limit.Value
                        geoms.append(Part.LineSegment(p1, p1 + p3).toShape())
                        geoms.append(Part.LineSegment(p2, p2 + p4).toShape())
                    else:
                        geoms.append(Part.LineSegment(p1, p2).toShape())
        if geoms:
            sh = Part.Compound(geoms)
            obj.Shape = sh
            obj.Placement = pl

    def onChanged(self,obj,prop):

        if prop in ["Angles","Distances","Placement"]:
            obj.touch()

    def dumps(self):

        return None

    def loads(self,state):

        self.Type = "Axis"

    def getPoints(self,obj):

        "returns the gridpoints of linked axes"

        pts = []
        for e in obj.Shape.Edges:
            pts.append(e.Vertexes[0].Point)
        return pts

    def getAxisData(self,obj):
        data = []
        num = 0
        for e in obj.Shape.Edges:
            axdata = []
            axdata.append(e.Vertexes[0].Point)
            axdata.append(e.Vertexes[-1].Point)
            if obj.ViewObject:
                axdata.append(obj.ViewObject.Proxy.getNumber(obj.ViewObject,num))
            else:
                axdata.append(str(num))
            data.append(axdata)
            num += 1
        return data


class _ViewProviderAxis:

    "A View Provider for the Axis object"

    def __init__(self,vobj):

        vobj.Proxy = self
        self.setProperties(vobj)

    def setProperties(self,vobj):

        ts = params.get_param("textheight") * params.get_param("DefaultAnnoScaleMultiplier")
        pl = vobj.PropertiesList
        if not "BubbleSize" in pl:
            vobj.addProperty("App::PropertyLength","BubbleSize","Axis", QT_TRANSLATE_NOOP("App::Property","The size of the axis bubbles"), locked=True)
            vobj.BubbleSize = ts * 1.42
        if not "NumberingStyle" in pl:
            vobj.addProperty("App::PropertyEnumeration","NumberingStyle","Axis", QT_TRANSLATE_NOOP("App::Property","The numbering style"), locked=True)
            vobj.NumberingStyle = ["1,2,3","01,02,03","001,002,003","A,B,C","a,b,c","I,II,III","L0,L1,L2"]
            vobj.NumberingStyle = "1,2,3"
        if not "DrawStyle" in pl:
            vobj.addProperty("App::PropertyEnumeration","DrawStyle","Axis",QT_TRANSLATE_NOOP("App::Property","The type of line to draw this axis"), locked=True)
            vobj.DrawStyle = ["Solid","Dashed","Dotted","Dashdot"]
        vobj.DrawStyle = "Dashdot"
        if not "BubblePosition" in pl:
            vobj.addProperty("App::PropertyEnumeration","BubblePosition","Axis",QT_TRANSLATE_NOOP("App::Property","Where to add bubbles to this axis: Start, end, both or none"), locked=True)
            vobj.BubblePosition = ["Start","End","Both","None","Arrow left","Arrow right","Bar left","Bar right"]
        if not "LineWidth" in pl:
            vobj.addProperty("App::PropertyFloat","LineWidth","Axis",QT_TRANSLATE_NOOP("App::Property","The line width to draw this axis"), locked=True)
            vobj.LineWidth = 1
        if not "LineColor" in pl:
            vobj.addProperty("App::PropertyColor","LineColor","Axis",QT_TRANSLATE_NOOP("App::Property","The color of this axis"), locked=True)
        vobj.LineColor = ArchCommands.getDefaultColor("Helpers")
        if not "StartNumber" in pl:
            vobj.addProperty("App::PropertyInteger","StartNumber","Axis",QT_TRANSLATE_NOOP("App::Property","The number of the first axis"), locked=True)
            vobj.StartNumber = 1
        if not "FontName" in pl:
            vobj.addProperty("App::PropertyFont","FontName","Axis",QT_TRANSLATE_NOOP("App::Property","The font to use for texts"), locked=True)
            vobj.FontName = params.get_param("textfont")
        if not "FontSize" in pl:
            vobj.addProperty("App::PropertyLength","FontSize","Axis",QT_TRANSLATE_NOOP("App::Property","The font size"), locked=True)
            vobj.FontSize = ts
        if not "ShowLabel" in pl:
            vobj.addProperty("App::PropertyBool","ShowLabel","Axis",QT_TRANSLATE_NOOP("App::Property","If true, show the labels"))
        if not "LabelOffset" in pl:
            vobj.addProperty("App::PropertyPlacement","LabelOffset","Axis",QT_TRANSLATE_NOOP("App::Property","A transformation to apply to each label"), locked=True)

    def onDocumentRestored(self,vobj):

        self.setProperties(vobj)

    def getIcon(self):

        import Arch_rc
        return ":/icons/Arch_Axis_Tree.svg"

    def claimChildren(self):

        return []

    def attach(self, vobj):
        self.Object = vobj.Object
        self.bubbles = None
        self.bubbletexts = []
        self.bubbledata = []
        sep = coin.SoSeparator()
        self.mat = coin.SoMaterial()
        self.linestyle = coin.SoDrawStyle()
        self.linecoords = coin.SoCoordinate3()
        self.lineset = coin.SoType.fromName("SoBrepEdgeSet").createInstance()
        self.bubbleset = coin.SoSeparator()
        self.labelset = coin.SoSeparator()
        sep.addChild(self.mat)
        sep.addChild(self.linestyle)
        sep.addChild(self.linecoords)
        sep.addChild(self.lineset)
        sep.addChild(self.bubbleset)
        sep.addChild(self.labelset)
        vobj.addDisplayMode(sep,"Default")
        self.onChanged(vobj,"BubbleSize")
        self.onChanged(vobj,"ShowLabel")
        self.onChanged(vobj,"LineColor")
        self.onChanged(vobj,"LineWidth")
        self.onChanged(vobj,"DrawStyle")

    def getDisplayModes(self,vobj):

        return ["Default"]

    def getDefaultDisplayMode(self):

        return "Default"

    def setDisplayMode(self,mode):

        return mode

    def updateData(self,obj,prop):

        if prop == "Shape":
            if obj.Shape:
                if obj.Shape.Edges:
                    verts = []
                    vset = []
                    i = 0
                    for e in obj.Shape.Edges:
                        for v in e.Vertexes:
                            verts.append(tuple(obj.Placement.inverse().multVec(v.Point)))
                            vset.append(i)
                            i += 1
                        vset.append(-1)
                    self.linecoords.point.setValues(verts)
                    self.lineset.coordIndex.setValues(0,len(vset),vset)
                    self.lineset.coordIndex.setNum(len(vset))
        elif prop in ["Placement", "Length"] and not hasattr(obj, "Distances"):
            # copy values from FlatLines/Wireframe nodes
            rn = obj.ViewObject.RootNode
            if rn.getNumChildren() < 3:
                return
            coords = rn.getChild(1)
            pts = coords.point.getValues()
            self.linecoords.point.setValues(pts)
            #self.linecoords.point.setNum(len(pts))
            sw = rn.getChild(2)
            if sw.getNumChildren() < 4:
                return
            edges = sw.getChild(sw.getNumChildren()-2)
            if not edges.getNumChildren():
                return
            if edges.getChild(0).getNumChildren() < 4:
                return
            eset = edges.getChild(0).getChild(3)
            vset = eset.coordIndex.getValues()
            self.lineset.coordIndex.setValues(0,len(vset),vset)
            self.lineset.coordIndex.setNum(len(vset))
        self.onChanged(obj.ViewObject,"BubbleSize")
        self.onChanged(obj.ViewObject,"ShowLabel")

    def onChanged(self, vobj, prop):

        if prop == "LineColor":
            if hasattr(vobj,"LineColor"):
                l = vobj.LineColor
                self.mat.diffuseColor.setValue([l[0],l[1],l[2]])
        elif prop == "DrawStyle":
            if hasattr(vobj,"DrawStyle"):
                if vobj.DrawStyle == "Solid":
                    self.linestyle.linePattern = 0xffff
                elif vobj.DrawStyle == "Dashed":
                    self.linestyle.linePattern = 0xf00f
                elif vobj.DrawStyle == "Dotted":
                    self.linestyle.linePattern = 0x0f0f
                else:
                    self.linestyle.linePattern = 0xff88
        elif prop == "LineWidth":
            if hasattr(vobj,"LineWidth"):
                self.linestyle.lineWidth = vobj.LineWidth
        elif prop in ["BubbleSize","BubblePosition","FontName","FontSize"]:
            if hasattr(self,"bubbleset"):
                if self.bubbles:
                    self.bubbleset.removeChild(self.bubbles)
                    self.bubbles = None
                if vobj.Object.Shape:
                    if vobj.Object.Shape.Edges:
                        self.bubbles = coin.SoSeparator()
                        self.bubblestyle = coin.SoDrawStyle()
                        self.bubblestyle.linePattern = 0xffff
                        self.bubbles.addChild(self.bubblestyle)
                        self.bubbletexts = []
                        self.bubbledata = []
                        pos = ["Start"]
                        if hasattr(vobj,"BubblePosition"):
                            if vobj.BubblePosition in ["Both","Arrow left","Arrow right","Bar left","Bar right"]:
                                pos = ["Start","End"]
                            elif vobj.BubblePosition == "None":
                                pos = []
                            else:
                                pos = [vobj.BubblePosition]
                        e = len(vobj.Object.Shape.Edges)
                        if getattr(vobj.Object,"Limit",0):
                            e //= 2
                        n = len(getattr(vobj.Object,"Distances",[]))
                        for i in range(min(e,n)):
                            for p in pos:
                                if getattr(vobj.Object,"Limit",0):
                                    verts = [vobj.Object.Placement.inverse().multVec(vobj.Object.Shape.Edges[i*2].Vertexes[0].Point),
                                             vobj.Object.Placement.inverse().multVec(vobj.Object.Shape.Edges[i*2+1].Vertexes[0].Point)]
                                else:
                                    verts = [vobj.Object.Placement.inverse().multVec(v.Point) for v in vobj.Object.Shape.Edges[i].Vertexes]
                                arrow = None
                                if p == "Start":
                                    p1 = verts[0]
                                    p2 = verts[1]
                                    if vobj.BubblePosition.endswith("left"):
                                        arrow = True
                                    elif vobj.BubblePosition.endswith("right"):
                                        arrow = False
                                else:
                                    p1 = verts[1]
                                    p2 = verts[0]
                                    if vobj.BubblePosition.endswith("left"):
                                        arrow = False
                                    elif vobj.BubblePosition.endswith("right"):
                                        arrow = True
                                dv = p2.sub(p1)
                                dv.normalize()
                                if hasattr(vobj.BubbleSize,"Value"):
                                    rad = vobj.BubbleSize.Value/2
                                else:
                                    rad = vobj.BubbleSize/2
                                center = p2.add(Vector(dv).multiply(rad))
                                normal = vobj.Object.Placement.Rotation.multVec(Vector(0,0,1))
                                chord = dv.cross(normal)
                                if arrow:
                                    p3 = p2.add(Vector(chord).multiply(rad/2).negative())
                                    if vobj.BubblePosition.startswith("Arrow"):
                                        p4 = p3.add(Vector(dv).multiply(rad*2).negative())
                                        p5 = p2.add(Vector(dv).multiply(rad).negative()).add(Vector(chord).multiply(rad*1.5).negative())
                                        pts = [tuple(p3),tuple(p5),tuple(p4),tuple(p3)]
                                        center = p5.add(Vector(chord).multiply(rad*2.5))
                                    else:
                                        p4 = p3.add(Vector(dv).multiply(rad/2).negative())
                                        p5 = p4.add(Vector(chord).multiply(rad*1.5).negative())
                                        p6 = p5.add(Vector(dv).multiply(rad/2))
                                        pts = [tuple(p3),tuple(p6),tuple(p5),tuple(p4),tuple(p3)]
                                        center = p5.add(Vector(chord).multiply(rad*3))
                                    coords = coin.SoCoordinate3()
                                    coords.point.setValues(0,len(pts),pts)
                                    line = coin.SoFaceSet()
                                    line.numVertices.setValue(-1)
                                    cir = Part.makePolygon(pts)
                                    cir.Placement = vobj.Object.Placement
                                    self.bubbledata.append(cir)
                                elif arrow == False:
                                    p3 = p2.add(Vector(chord).multiply(rad/2))
                                    if vobj.BubblePosition.startswith("Arrow"):
                                        p4 = p3.add(Vector(dv).multiply(rad*2).negative())
                                        p5 = p2.add(Vector(dv).multiply(rad).negative()).add(Vector(chord).multiply(rad*1.5))
                                        pts = [tuple(p3),tuple(p4),tuple(p5),tuple(p3)]
                                        center = p5.add(Vector(chord).multiply(rad*2.5).negative())
                                    else:
                                        p4 = p3.add(Vector(dv).multiply(rad/2).negative())
                                        p5 = p4.add(Vector(chord).multiply(rad*1.5))
                                        p6 = p5.add(Vector(dv).multiply(rad/2))
                                        pts = [tuple(p3),tuple(p4),tuple(p5),tuple(p6),tuple(p3)]
                                        center = p5.add(Vector(chord).multiply(rad*3).negative())
                                    coords = coin.SoCoordinate3()
                                    coords.point.setValues(0,len(pts),pts)
                                    line = coin.SoFaceSet()
                                    line.numVertices.setValue(-1)
                                    cir = Part.makePolygon(pts)
                                    cir.Placement = vobj.Object.Placement
                                    self.bubbledata.append(cir)
                                else:
                                    cir = Part.makeCircle(rad,center)
                                    buf = cir.writeInventor()
                                    try:
                                        cin = coin.SoInput()
                                        cin.setBuffer(buf)
                                        cob = coin.SoDB.readAll(cin)
                                    except Exception:
                                        # workaround for pivy SoInput.setBuffer() bug
                                        buf = buf.replace("\n","")
                                        pts = re.findall(r"point \[(.*?)\]",buf)[0]
                                        pts = pts.split(",")
                                        pc = []
                                        for point in pts:
                                            v = point.strip().split()
                                            pc.append([float(v[0]),float(v[1]),float(v[2])])
                                        coords = coin.SoCoordinate3()
                                        coords.point.setValues(0,len(pc),pc)
                                        line = coin.SoLineSet()
                                        line.numVertices.setValue(-1)
                                    else:
                                        coords = cob.getChild(1).getChild(0).getChild(2)
                                        line = cob.getChild(1).getChild(0).getChild(3)
                                    cir.Placement = vobj.Object.Placement
                                    self.bubbledata.append(cir)
                                self.bubbles.addChild(coords)
                                self.bubbles.addChild(line)
                                st = coin.SoSeparator()
                                tr = coin.SoTransform()
                                fs = rad*1.5
                                if hasattr(vobj,"FontSize"):
                                    fs = vobj.FontSize.Value
                                txpos = FreeCAD.Vector(center.x,center.y-fs/2.5,center.z)
                                tr.translation.setValue(tuple(txpos))
                                fo = coin.SoFont()
                                fn = params.get_param("textfont")
                                if hasattr(vobj,"FontName"):
                                    if vobj.FontName:
                                        try:
                                            fn = str(vobj.FontName)
                                        except Exception:
                                            pass
                                fo.name = fn
                                fo.size = fs
                                tx = coin.SoAsciiText()
                                tx.justification = coin.SoText2.CENTER
                                self.bubbletexts.append((tx,vobj.Object.Placement.multVec(center)))
                                st.addChild(tr)
                                st.addChild(fo)
                                st.addChild(tx)
                                self.bubbles.addChild(st)
                        self.bubbleset.addChild(self.bubbles)
                        self.onChanged(vobj,"NumberingStyle")
            if prop in ["FontName","FontSize"]:
                self.onChanged(vobj,"ShowLabel")
        elif prop in ["NumberingStyle","StartNumber"]:
            if hasattr(self,"bubbletexts"):
                num = 0
                if hasattr(vobj,"StartNumber"):
                    if vobj.StartNumber > 1:
                        num = vobj.StartNumber-1
                alt = False
                for t in self.bubbletexts:
                    t[0].string = self.getNumber(vobj,num)
                    num += 1
                    if hasattr(vobj,"BubblePosition"):
                        if vobj.BubblePosition in ["Both","Arrow left","Arrow right","Bar left","Bar right"]:
                            if not alt:
                                num -= 1
                    alt = not alt
        elif prop in ["ShowLabel", "LabelOffset"]:
            if hasattr(self,"labels"):
                if self.labels:
                    self.labelset.removeChild(self.labels)
            self.labels = None
            if hasattr(vobj,"ShowLabel") and hasattr(vobj.Object,"Labels"):
                if vobj.ShowLabel:
                    self.labels = coin.SoSeparator()
                    if hasattr(vobj.Object,"Limit") and vobj.Object.Limit.Value:
                        n = len(vobj.Object.Shape.Edges)/2
                    else:
                        n = len(vobj.Object.Shape.Edges)
                    for i in range(n):
                        if len(vobj.Object.Labels) > i:
                            if vobj.Object.Labels[i]:
                                vert = vobj.Object.Shape.Edges[i].Vertexes[0].Point
                                if hasattr(vobj,"LabelOffset"):
                                    pl = FreeCAD.Placement(vobj.LabelOffset)
                                    pl.Base = vert.add(pl.Base)
                                st = coin.SoSeparator()
                                tr = coin.SoTransform()
                                fo = coin.SoFont()
                                tx = coin.SoAsciiText()
                                tx.justification = coin.SoText2.LEFT
                                t = vobj.Object.Labels[i]
                                tx.string.setValue(t)
                                if hasattr(vobj,"FontSize"):
                                    fs = vobj.FontSize.Value
                                elif hasattr(vobj.BubbleSize,"Value"):
                                    fs = vobj.BubbleSize.Value*0.75
                                else:
                                    fs = vobj.BubbleSize*0.75
                                tr.translation.setValue(tuple(pl.Base))
                                tr.rotation.setValue(pl.Rotation.Q)
                                fn = params.get_param("textfont")
                                if hasattr(vobj,"FontName"):
                                    if vobj.FontName:
                                        try:
                                            fn = str(vobj.FontName)
                                        except Exception:
                                            pass
                                fo.name = fn
                                fo.size = fs
                                st.addChild(tr)
                                st.addChild(fo)
                                st.addChild(tx)
                                self.labels.addChild(st)
                    self.labelset.addChild(self.labels)

    def getNumber(self,vobj,num):

        chars = "abcdefghijklmnopqrstuvwxyz"
        roman=(('M',1000),('CM',900),('D',500),('CD',400),
               ('C',100),('XC',90),('L',50),('XL',40),
               ('X',10),('IX',9),('V',5),('IV',4),('I',1))
        if hasattr(vobj.Object,"CustomNumber") and vobj.Object.CustomNumber:
            return vobj.Object.CustomNumber
        elif hasattr(vobj,"NumberingStyle"):
            if vobj.NumberingStyle == "1,2,3":
                return str(num+1)
            elif vobj.NumberingStyle == "01,02,03":
                return str(num+1).zfill(2)
            elif vobj.NumberingStyle == "001,002,003":
                return str(num+1).zfill(3)
            elif vobj.NumberingStyle == "A,B,C":
                result = ""
                base = num//26
                if base:
                    result += chars[base].upper()
                remainder = num % 26
                result += chars[remainder].upper()
                return result
            elif vobj.NumberingStyle == "a,b,c":
                result = ""
                base = num//26
                if base:
                    result += chars[base]
                remainder = num % 26
                result += chars[remainder]
                return result
            elif vobj.NumberingStyle == "I,II,III":
                result = ""
                n = num
                n += 1
                for numeral, integer in roman:
                    while n >= integer:
                        result += numeral
                        n -= integer
                return result
            elif vobj.NumberingStyle == "L0,L1,L2":
                return "L"+str(num)
        else:
            return str(num+1)

    def getTextData(self):

        return [(t[0].string.getValues()[0],t[1]) for t in self.bubbletexts]

    def getShapeData(self):

        return self.bubbledata

    def setEdit(self, vobj, mode):
        if mode == 1 or mode == 2:
            return None

        taskd = _AxisTaskPanel()
        taskd.obj = vobj.Object
        taskd.update()
        FreeCADGui.Control.showDialog(taskd)
        return True

    def unsetEdit(self, vobj, mode):
        if mode == 1 or mode == 2:
            return None

        FreeCADGui.Control.closeDialog()
        return True

    def setupContextMenu(self, vobj, menu):
        if FreeCADGui.activeWorkbench().name() != 'BIMWorkbench':
            return
        actionEdit = QtGui.QAction(translate("Arch", "Edit"),
                                   menu)
        QtCore.QObject.connect(actionEdit,
                               QtCore.SIGNAL("triggered()"),
                               self.edit)
        menu.addAction(actionEdit)

        # The default Part::FeaturePython context menu contains a `Set colors`
        # option. This option makes no sense for Axis objects. We therefore
        # override this menu and have to add our own `Transform` item.
        # To override the default menu this function must return `True`.
        action_transform = QtGui.QAction(FreeCADGui.getIcon("Std_TransformManip.svg"),
                                         translate("Command", "Transform"), # Context `Command` instead of `Arch`.
                                         menu)
        QtCore.QObject.connect(action_transform,
                               QtCore.SIGNAL("triggered()"),
                               self.transform)
        menu.addAction(action_transform)

        return True

    def edit(self):
        FreeCADGui.ActiveDocument.setEdit(self.Object, 0)

    def transform(self):
        FreeCADGui.ActiveDocument.setEdit(self.Object, 1)

    def dumps(self):

        return None

    def loads(self,state):

        return None


class _AxisTaskPanel:

    '''The editmode TaskPanel for Axis objects'''

    def __init__(self):

        # the panel has a tree widget that contains categories
        # for the subcomponents, such as additions, subtractions.
        # the categories are shown only if they are not empty.

        self.updating = False

        self.obj = None
        self.form = QtGui.QWidget()
        self.form.setObjectName("TaskPanel")
        self.grid = QtGui.QGridLayout(self.form)
        self.grid.setObjectName("grid")
        self.title = QtGui.QLabel(self.form)
        self.grid.addWidget(self.title, 0, 0, 1, 2)

        # tree
        self.tree = QtGui.QTreeWidget(self.form)
        self.grid.addWidget(self.tree, 1, 0, 1, 2)
        self.tree.setColumnCount(4)
        self.tree.header().resizeSection(0,50)
        self.tree.header().resizeSection(1,80)
        self.tree.header().resizeSection(2,60)

        # buttons
        self.addButton = QtGui.QPushButton(self.form)
        self.addButton.setObjectName("addButton")
        self.addButton.setIcon(QtGui.QIcon(":/icons/Arch_Add.svg"))
        self.grid.addWidget(self.addButton, 3, 0, 1, 1)
        self.addButton.setEnabled(True)

        self.delButton = QtGui.QPushButton(self.form)
        self.delButton.setObjectName("delButton")
        self.delButton.setIcon(QtGui.QIcon(":/icons/Arch_Remove.svg"))
        self.grid.addWidget(self.delButton, 3, 1, 1, 1)
        self.delButton.setEnabled(True)

        QtCore.QObject.connect(self.addButton, QtCore.SIGNAL("clicked()"), self.addElement)
        QtCore.QObject.connect(self.delButton, QtCore.SIGNAL("clicked()"), self.removeElement)
        QtCore.QObject.connect(self.tree, QtCore.SIGNAL("itemChanged(QTreeWidgetItem *, int)"), self.edit)
        self.update()

    def isAllowedAlterSelection(self):

        return False

    def isAllowedAlterView(self):

        return True

    def getStandardButtons(self):

        return QtGui.QDialogButtonBox.Close

    def update(self):

        'fills the treewidget'
        self.updating = True
        self.tree.clear()
        if self.obj and hasattr(self.obj, "Distances"):
            for i in range(len(self.obj.Distances)):
                item = QtGui.QTreeWidgetItem(self.tree)
                item.setText(0,str(i+1))
                if len(self.obj.Distances) > i:
                    item.setText(1,str(self.obj.Distances[i]))
                if len(self.obj.Angles) > i:
                    item.setText(2,str(self.obj.Angles[i]))
                if hasattr(self.obj,"Labels"):
                    if len(self.obj.Labels) > i:
                        item.setText(3,str(self.obj.Labels[i]))
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                item.setTextAlignment(0,QtCore.Qt.AlignLeft)
        self.retranslateUi(self.form)
        self.updating = False

    def addElement(self):

        item = QtGui.QTreeWidgetItem(self.tree)
        item.setText(0,str(self.tree.topLevelItemCount()))
        item.setText(1,"1.0")
        item.setText(2,"0.0")
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        self.resetObject()

    def removeElement(self):

        it = self.tree.currentItem()
        if it:
            nr = int(it.text(0))-1
            self.resetObject(remove=nr)
            self.update()

    def edit(self,item,column):

        if not self.updating:
            self.resetObject()

    def resetObject(self,remove=None):

        "transfers the values from the widget to the object"

        d = []
        a = []
        l = []
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.findItems(str(i+1),QtCore.Qt.MatchExactly,0)[0]
            if (remove is None) or (remove != i):
                if it.text(1):
                    d.append(float(it.text(1)))
                else:
                    d.append(0.0)
                if it.text(2):
                    a.append(float(it.text(2)))
                else:
                    a.append(0.0)
                l.append(it.text(3))
        self.obj.Distances = d
        self.obj.Angles = a
        self.obj.Labels = l
        self.obj.touch()
        FreeCAD.ActiveDocument.recompute()

    def reject(self):

        FreeCAD.ActiveDocument.recompute()
        FreeCADGui.ActiveDocument.resetEdit()
        return True

    def retranslateUi(self, TaskPanel):

        TaskPanel.setWindowTitle(QtGui.QApplication.translate("Arch", "Axes", None))
        self.delButton.setText(QtGui.QApplication.translate("Arch", "Remove", None))
        self.addButton.setText(QtGui.QApplication.translate("Arch", "Add", None))
        self.title.setText(QtGui.QApplication.translate("Arch", "Distances (mm) and angles (deg) between axes", None))
        self.tree.setHeaderLabels([QtGui.QApplication.translate("Arch", "Axis", None),
                                   QtGui.QApplication.translate("Arch", "Distance", None),
                                   QtGui.QApplication.translate("Arch", "Angle", None),
                                   QtGui.QApplication.translate("Arch", "Label", None)])
