import os
import json
import qgis

from qgis.PyQt.uic import loadUiType
from qgis.PyQt.QtWidgets import QDialog
from ..utils import tr

FORM_CLASS, _ = loadUiType(os.path.join(
    os.path.dirname(__file__), 'DODAJ_WMS_WMTS.ui'))

class EditConnection(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(EditConnection, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.json_file = self.parent.json_file
        self.add_btn.setText(tr('Confirm'))
        self.close_btn.clicked.connect(self.accept)
        self.add_btn.clicked.connect(self.edit_wms_wmts)
        self.plugins = qgis.utils.plugins['GIAP-PolaMap(lite)']
        self.parent.groups_combobox(self)

        self.wms_list = {}
        self.fill_data()

    def run(self) -> None:
        self.show()
        self.exec_()

    def fill_data(self) -> None:
        with open(self.json_file,"r+") as json_getaddress:
            data = json.load(json_getaddress)
            data.update(self.wms_list)
            self.name = self.parent.selected[0].text()
            adr, group = data[self.parent.selected[0].text()]
            self.lineEdit_name.setText(self.name)
            self.lineEdit_address.setText(adr)
            self.comboBox_group.setCurrentText(group)
            json_getaddress.close()
        with open(self.json_file, "w+") as json_write:
            json.dump(data, json_write)
        self.accept()

    def edit_wms_wmts(self) -> None:
        wms_name = self.lineEdit_name.text()
        wms_address = self.lineEdit_address.text()
        wms_group = self.comboBox_group.currentText()
        check_if_empty_lineedits = self.parent.check_if_empty_lineedits(wms_name, wms_address)
        if check_if_empty_lineedits:
            self.wms_list[wms_name] = [wms_address, wms_group]
            with open(self.json_file, "r+") as json_read:
                data = json.load(json_read)
                del data[self.name]
                data.update(self.wms_list)
                json_read.close()
            with open(self.json_file, "w+") as json_write:
                json.dump(data, json_write)
            self.plugins.orto_add.my_refresh_menu()
            self.close()

        self.parent.fill_list()
