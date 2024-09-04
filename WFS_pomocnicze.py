import os
from qgis.PyQt import QtWidgets, uic
from qgis.core import QgsVectorLayer, QgsProject, QgsFeature, QgsGeometry, QgsRectangle
from qgis.core import QgsVectorFileWriter, QgsDataSourceUri, QgsField
from qgis.gui import QgsMapCanvas, QgsMapToolEmitPoint, QgsMapToolIdentifyFeature, QgsMapToolIdentify
from qgis.utils import iface
from PyQt5.QtWidgets import QListView, QMessageBox, QFileDialog, QCheckBox
from PyQt5.QtCore import QStringListModel, Qt, pyqtSignal
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from owslib.wfs import WebFeatureService
from qgis.PyQt.QtWidgets import QApplication, QProgressDialog

from .utils import tr, add_map_layer_to_group, search_group_name, project, SingletonModel, icon_manager


class IdentifyGeometry(QgsMapToolIdentify):
    geomIdentified = pyqtSignal(list)

    def canvasReleaseEvent(self, mouseEvent):
        layerList = []
        layers = project.mapLayers()
        for layer in layers.values():
            if layer.type().value == 0:
                found_layer = QgsProject.instance().layerTreeRoot().findLayer(layer)
                if found_layer and found_layer.isVisible():
                    layerList.append(layer)

        results = self.identify(mouseEvent.x(), mouseEvent.y(),
                                layerList=layerList, mode=self.LayerSelection)
        self.geomIdentified.emit(results)


class TmpCopyLayer(QgsVectorLayer):
    def __init__(self, *args, **kwargs):
        super(TmpCopyLayer, self).__init__(*args, **kwargs)

    def set_fields(self, fields):
        self.dataProvider().addAttributes(fields)
        self.updateFields()

    def set_fields_from_layer(self, layer):
        fields = layer.dataProvider().fields()
        self.set_fields(fields)

    def add_features(self, features):
        feats = []
        for feature in features:
            feat = QgsFeature(feature)
            feats.append(feat)
        if feats:
            self.dataProvider().addFeatures(feats)
        iface.mapCanvas().refresh()

    def add_to_group(self, group_name):
        add_map_layer_to_group(self, group_name)
        self.triggerRepaint()
		
class ProgressDialog(QProgressDialog, SingletonModel):

    def __init__(self, parent=None, title='GIAP-PolaMap(lite)'):
        super(ProgressDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(icon_manager(['window_icon'])['window_icon'])
        self.setLabelText('Proszę czekać...')
        self.setFixedWidth(300)
        self.setFixedHeight(100)
        self.setMaximum(100)
        self.setCancelButton(None)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.rejected.connect(self.stop)
        self.setWindowModality(Qt.WindowModal)

    def make_percent_step(self, step=1, new_text=None):
        self.setValue(self.value() + step)
        if new_text:
            self.setLabelText(new_text)
        QApplication.processEvents()

    def start_steped(self, title='Trwa ładowanie danych.\n  Proszę czekać...'):
        self.setLabelText(title)
        self.setValue(1)
        self.show()
        QApplication.sendPostedEvents()
        QApplication.processEvents()

    def start(self):
        self.setFixedWidth(250)
        self.setMaximum(0)
        self.setCancelButton(None)
        self.show()
        QApplication.sendPostedEvents()
        QApplication.processEvents()

    def stop(self):
        self.setValue(100)
        self.close()