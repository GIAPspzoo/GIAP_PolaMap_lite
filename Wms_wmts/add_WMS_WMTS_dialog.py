import os
import json
import qgis

from qgis.PyQt.uic import loadUiType
from qgis.PyQt.QtWidgets import QDialog

FORM_CLASS, _ = loadUiType(os.path.join(
    os.path.dirname(__file__), 'DODAJ_WMS_WMTS.ui'))


class CreateConnection(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(CreateConnection, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.json_file = self.parent.json_file
        self.plugins = qgis.utils.plugins['GIAP-PolaMap(lite)']
        self.parent.groups_combobox(self)
        self.comboBox_group.setCurrentText('')
        self.close_btn.clicked.connect(self.accept)
        self.add_btn.clicked.connect(self.add_connection)
        self.wms_dict = {}

    def run(self) -> None:
        self.show()
        self.exec_()

    def add_connection(self) -> None:
        wms_name = self.lineEdit_name.text()
        wms_address = self.lineEdit_address.text()
        wms_group = self.comboBox_group.currentText()
        check_if_empty_lineedits = self.parent.check_if_empty_lineedits(wms_name, wms_address)
        check_wms_name = self.parent.check_wms_name(wms_name)
        if check_if_empty_lineedits and check_wms_name:
            self.wms_dict[wms_name] = [wms_address, wms_group]
            self.parent.listWidget.addItem(wms_name)
            with open(self.json_file, "r+") as json_read:
                data = json.load(json_read)
                data.update(self.wms_dict)
                json_read.close()
            with open(self.json_file, "w+") as json_write:
                json.dump(data, json_write)
            self.plugins.orto_add.my_refresh_menu()
            self.close()
