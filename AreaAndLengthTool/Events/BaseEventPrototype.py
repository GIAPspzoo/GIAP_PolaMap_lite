from qgis.PyQt.QtCore import pyqtSlot, QObject, QEvent
from qgis.core import QgsCoordinateReferenceSystem, QgsUnitTypes, QgsProject, \
    QgsCoordinateTransform, QgsDistanceArea, QgsGeometry

from ...utils import tr
from ..AnnotationHandler import AnnotationHandler


class BaseEventPrototype(QObject):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.mapCanvas = self.iface.mapCanvas()

        map_renderer = self.mapCanvas.mapSettings()
        crs = map_renderer.destinationCrs().authid()
        self.crs_unit = {
            'crs': QgsCoordinateReferenceSystem(),
            'area': QgsUnitTypes.AreaHectares,
            'length': QgsUnitTypes.DistanceMeters
        }

        self.annotation_handler = AnnotationHandler()
        self.project = QgsProject.instance()
        self.project.crsChanged.connect(self.crsChanged)

        self.measure = QgsDistanceArea()
        self.measure.setSourceCrs(self.crs_unit['crs'],
                                  self.project.transformContext())

        self.coordinate_transform = QgsCoordinateTransform(
            self.project.crs(), self.crs_unit['crs'], self.project)

        self.isEnabled = False  # Annotation
        self.isEventFiltered = False
        self.objsToggleFilter = None

    @pyqtSlot()
    def crsChanged(self) -> None:
        map_renderer = self.iface.mapCanvas().mapSettings()
        crs = map_renderer.destinationCrs().authid()
        self.crs_unit['crs'] = QgsCoordinateReferenceSystem(crs)
        self.coordinate_transform.setSourceCrs(self.project.crs())

    def enable_event(self) -> None:
        self.isEnabled = True

    def disable_event(self) -> None:
        self.annotation_handler.remove()
        self.isEnabled = False

    def toggleEventFilter(self) -> None:
        if self.objsToggleFilter is None:
            return

        for obj in self.objsToggleFilter:
            event_filter = obj.removeEventFilter \
                if self.isEventFiltered else obj.installEventFilter
            event_filter(self)

        self.isEventFiltered = not self.isEventFiltered

    def string_measures(self, geometry: QgsGeometry) -> str:

        def get_string(value: float, unit: QgsUnitTypes.DistanceUnit,
                       function_measure: QgsDistanceArea) -> str:
            precision = 2
            calc_unit = QgsUnitTypes.toAbbreviatedString(unit)
            if calc_unit == 'ha':
                precision = 4
            calc_value = round(function_measure(value, unit), precision)
            return f"{calc_value} {calc_unit}"

        label_elems = []
        geometry_length = geometry.length()
        if geometry_length:
            string_length = get_string(
                geometry_length, self.crs_unit['length'],
                self.measure.convertLengthMeasurement)
            label_elems.append(f"{tr('Length:')} {string_length}")

        geometry_area = geometry.area()/10000
        if geometry_area > 0:
            string_area = get_string(
                geometry_area, self.crs_unit['area'],
                self.measure.convertAreaMeasurement)
            label_elems.append(f"{tr('Area:')} {string_area}")
        return '\n'.join(label_elems)

    @pyqtSlot(QObject, QEvent)
    def eventFilter(self, watched: QObject, event: QEvent) -> None:
        pass

    def __del__(self) -> None:
        self.project.crsChanged.disconnect(self.crsChanged)
