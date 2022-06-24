from typing import List, Union

import qgis
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtCore import pyqtSlot, QObject
from qgis.core import QgsMessageLog, Qgis, QgsGeometry, QgsPointXY, QgsWkbTypes


class PolygonGeometryHandler(QObject):
    def __init__(self, iface):
        super().__init__()

        def get_action_digitize_with_curve(iface: iface) -> QAction:
            name = 'advancedDigitizeToolBar'
            toolbar = getattr(iface, name, None)
            if toolbar is None:
                QgsMessageLog.logMessage(
                    f"QgisInterface missing '{name}' toolbar",
                    "GIAP-PolaMap", Qgis.Warning)
                return

            name = 'mActionDigitizeWithCurve'
            actions = [action for action in
                       iface.advancedDigitizeToolBar().actions() if
                       action.objectName() == name]
            if not actions:
                QgsMessageLog.logMessage(
                    f"QgisInterface missing '{name}' action",
                    "GIAP-PolaMap", Qgis.Warning)
                return
            return actions[0]

        self.mapCanvas = iface.mapCanvas()
        self.points = []
        self.ids_middle_curve = []
        self.is_curve = False
        if not qgis.utils.Qgis.QGIS_VERSION.startswith('3.10'):
            self.action_digitize_with_curve = get_action_digitize_with_curve(iface)
            self.action_digitize_with_curve.toggled.connect(self.toggledCurve)

    def __del__(self) -> None:
        self.action_digitize_with_curve.toggled.disconnect(self.toggledCurve)

    def count(self) -> int:
        return len(self.points)

    def add(self, point: List[int]) -> None:
        self.points.append(point)
        if self.is_curve:
            id_point = len(self.points) - 1
            if len(self.points) == 1:  # Started curve
                return

            total_ids = len(self.ids_middle_curve)
            if not total_ids:  # Added first middle point
                self.ids_middle_curve.append(id_point)
                return

            id_prev = self.ids_middle_curve[total_ids - 1]
            if id_prev == id_point - 1:  # Finished curve
                return

            self.ids_middle_curve.append(id_point)

    def pop(self, key_delete: bool = False) -> None:
        self.points.pop()
        if not key_delete and self.is_curve:
            self.ids_middle_curve.pop()
            return

        if not len(self.ids_middle_curve):
            return

        # Check id_point end of Curve
        id_point = len(self.points) - 1
        if id_point == (self.ids_middle_curve[-1]):  # Middle
            self.points.pop()  # Start
            self.ids_middle_curve.pop()

    def coordinate(self, position: int) -> List[int]:
        return self.points[position]

    def clear(self) -> None:
        self.points.clear()
        self.ids_middle_curve.clear()

    def is_middle_point(self) -> bool:
        return self.is_curve and len(self.ids_middle_curve) > 1 and \
               self.ids_middle_curve[-1] == (len(self.points) - 1)

    def geometry(self, move_point: Union[None, QgsPointXY]=None):
        total_curves = len(self.ids_middle_curve)
        points = self.points if move_point is None else self.points + [
            move_point]
        if total_curves:
            return self.get_curve_polygon(points)

        if self.mapCanvas.currentLayer().geometryType() == QgsWkbTypes.LineGeometry:
            return QgsGeometry.fromPolylineXY(points)

        poly_geom = QgsGeometry.fromPolygonXY([points])
        if poly_geom.area() > 0:
            return poly_geom
        return QgsGeometry.fromPolylineXY(points)

    def get_curve_polygon(self, points: List[int]) -> QgsGeometry:
        def to_point_string(id: int) -> str:
            point = points[id]
            return point.toString(20).replace(',', ' ')

        id_point = 0
        len_points = len(points)
        l_wkt = []
        while id_point < len_points - 1:
            # Points
            if not id_point in self.ids_middle_curve:
                l_str = [to_point_string(id_point),
                         to_point_string(id_point + 1)]
                if id_point == (len_points - 2):
                    l_str.append(to_point_string(0))
                wkt = f"( {','.join(l_str)} )"
                l_wkt.append(wkt)
                id_point += 1
                continue
            # CircularString
            circular_id = 0 if id_point == 0 else id_point - 1  # Test for first point
            l_str = (
                to_point_string(circular_id),
                to_point_string(circular_id + 1),
                to_point_string(circular_id + 2))
            wkt = f"CircularString( {','.join(l_str)} )"
            l_wkt.append(wkt)
            id_point += 2

        if l_wkt[-1].find('CircularString') > -1:
            l_str = [to_point_string(len_points - 1), to_point_string(0)]
            wkt = f"( {','.join(l_str)} )"
            l_wkt.append(wkt)

        return QgsGeometry.fromWkt(
            f"CurvePolygon( CompoundCurve( {','.join(l_wkt)} ) )")

    @pyqtSlot(bool)
    def toggledCurve(self, checked: bool) -> None:
        self.is_curve = checked
