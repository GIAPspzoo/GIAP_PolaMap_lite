from qgis.PyQt.QtCore import QPointF, QSizeF, pyqtSlot, QObject
from qgis.PyQt.QtGui import QFont, QTextDocument
from qgis.core import QgsProject, QgsTextAnnotation, QgsFillSymbol, \
    QgsMarkerSymbol, QgsPointXY


class AnnotationHandler(QObject):
    def __init__(self):
        super().__init__()
        self.annotationManager = QgsProject.instance().annotationManager()
        self.annotationManager.annotationAboutToBeRemoved.connect(
            self.annotationAboutToBeRemoved)
        self._create()

    def setText(self, text: str, point_xy: QgsPointXY) -> None:
        if not self.annot in self.annotationManager.annotations():
            self._create()
            self.annotationManager.addAnnotation(self.annot)

        self.annot.setMapPosition(point_xy)

        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        text_document = QTextDocument(text)
        text_document.setDefaultFont(font)
        self.annot.setFrameOffsetFromReferencePointMm(QPointF(0, 0))
        self.annot.setFrameSizeMm(QSizeF(80, 14))
        self.annot.setDocument(text_document)

        self.annot.setVisible(True)

    def remove(self) -> None:
        if self.annot:
            self.annotationManager.removeAnnotation(self.annot)
            self.annot = None

    def isVisible(self) -> bool:
        if self.annot is None:
            return False

        return self.annot.isVisible()

    def toggle(self) -> None:
        if not self.annot is None:
            self.annot.setVisible(not self.annot.isVisible())
            return
        self._create()

    @pyqtSlot('QgsAnnotation*')
    def annotationAboutToBeRemoved(self, annot: QgsTextAnnotation) -> None:
        if annot == self.annot:
            self.annot = None

    def _create(self) -> None:
        annot = QgsTextAnnotation()
        opacity = 0.8
        symbolization_dict = {
            'fill': {
                'create': QgsFillSymbol.createSimple,
                'setSymbol': annot.setFillSymbol,
                'properties': {
                    'color': 'white',
                    'width_border': '0.1',
                    'outline_color': 'gray', 'outline_style': 'solid'
                }
            },
            'marker': {
                'create': QgsMarkerSymbol.createSimple,
                'setSymbol': annot.setMarkerSymbol,
                'properties': {'name': 'cross'}
            },
        }
        for key in symbolization_dict:
            symbol = symbolization_dict[key]['create'](symbolization_dict[key]['properties'])
            symbol.setOpacity(opacity)
            symbolization_dict[key]['setSymbol'](symbol)

        self.annot = annot
