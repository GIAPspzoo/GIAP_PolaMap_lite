import os

from qgis.PyQt.uic import loadUiType
from qgis.PyQt.QtWidgets import QDialog

from .utils import get_wms_config, set_wms_config
from ..utils import tr

FORM_CLASS, _ = loadUiType(os.path.join(
    os.path.dirname(__file__), 'DODAJ_WMS_WMTS.ui'))

class EditConnection(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(EditConnection, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.add_btn.setText(tr('Confirm'))
        self.close_btn.clicked.connect(self.accept)
        self.add_btn.clicked.connect(self.edit_wms_wmts)
        self.parent.groups_combobox(self)
        self.wms_list = {}
        self.fill_data()

    def run(self) -> None:
        self.show()
        self.exec_()

    def fill_data(self) -> None:
        data = get_wms_config()
        data.update(self.wms_list)
        self.name = self.parent.selected[0].text()
        adr, group = data[self.name]
        self.lineEdit_name.setText(self.name)
        self.lineEdit_address.setText(adr)
        self.comboBox_group.setCurrentText(group)
        set_wms_config(data)
        self.accept()

    def edit_wms_wmts(self) -> None:
        wms_name = self.lineEdit_name.text()
        wms_address = self.lineEdit_address.text()
        wms_group = self.comboBox_group.currentText()
        check_if_empty_lineedits = self.parent.check_if_empty_lineedits(wms_name, wms_address)
        if check_if_empty_lineedits:
            self.wms_list[wms_name] = [wms_address, wms_group]
            data = get_wms_config()
            del data[self.name]
            data.update(self.wms_list)
            set_wms_config(data)
            self.parent.OrtoAddingTool.my_refresh_menu()
            self.close()

        self.parent.fill_list()
