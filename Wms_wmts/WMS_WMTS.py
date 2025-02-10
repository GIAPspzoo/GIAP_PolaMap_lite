from .WMS_WMTS_dialog import WMS_WMTS_dialog
from qgis.PyQt.QtCore import QObject


class WMS_WMTS(QObject):

    def __init__(self, parent=None):
        self.parent = parent

    def run(self):
        self.configure_wms_dlg = WMS_WMTS_dialog(self.parent)
        self.configure_wms_dlg.run()
