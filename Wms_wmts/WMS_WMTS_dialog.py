import os
import qgis
import json
import qgis.utils
from qgis.PyQt.uic import loadUiType
from qgis.PyQt.QtWidgets import QDialog, QMessageBox

from .add_WMS_WMTS_dialog import CreateConnection
from .edit_WMS_WMTS_dialog import EditConnection
from ..utils import CustomMessageBox

FORM_CLASS, _ = loadUiType(os.path.join(
    os.path.dirname(__file__), 'WMS_WMTS.ui'))


class WMS_WMTS_dialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(WMS_WMTS_dialog, self).__init__(parent)
        self.setupUi(self)
        self.json_file = json_path()
        self.close_btn.clicked.connect(self.accept)
        self.add_btn.clicked.connect(self.run_add_service)
        self.edit_btn.clicked.connect(self.run_edit_service)
        self.remove_btn.clicked.connect(self.remove_selected)
        self.wms_list = {}
        self.fill_list()
        self.plugins = qgis.utils.plugins['GIAP-PolaMap(lite)']

    def run(self) -> None:
        self.show()
        self.exec_()

    def fill_list(self) -> None:
        self.listWidget.clear()
        with open(self.json_file, "r+") as json_read:
            data = json.load(json_read)
            for key in data:
                self.listWidget.addItem(key)

    def run_add_service(self) -> None:
        self.add_wms_wmts_dialog = CreateConnection(self)
        self.add_wms_wmts_dialog.run()

    def run_edit_service(self) -> None:
        self.selected = self.listWidget.selectedItems()
        if self.selected:
            self.edit_wms_wmts_dialog = EditConnection(self)
            self.edit_wms_wmts_dialog.fill_data()
            self.edit_wms_wmts_dialog.run()
        else:
            CustomMessageBox(None, 'Nie wybrano połączenia z listy!').button_ok()

    def remove_selected(self) -> None:
        self.selected = self.listWidget.selectedItems()
        if not self.selected:
            return
        msg_box = CustomMessageBox(None, 'Czy chcesz usunąć wybraną warstwę?').button_yes_no()
        if msg_box == QMessageBox.No:
            return
        for item in self.selected:
            self.listWidget.takeItem(self.listWidget.row(item))
        with open(self.json_file, "r+") as json_read:
            data = json.load(json_read)
            del data[[item.text() for item in self.selected][0]]
            json_read.close()
        with open(self.json_file, "w+") as json_write:
            json.dump(data, json_write)
        self.plugins.orto_add.my_refresh_menu()

    def check_wms_name(self, wms_name: str) -> bool or None:
        with open(self.json_file, "r+") as json_read:
            data = json.load(json_read)
            if wms_name in data.keys():
                CustomMessageBox(None, 'Nazwa już istnieje. Proszę wybrać inną nazwę!').button_ok()
                return
        return True

    def check_if_empty_lineedits(self, name: str, url: str) -> bool or None:
        if not name or not url:
            CustomMessageBox(None, 'Pola nazwy i adresu URL nie mogą być puste!').button_ok()
            return
        return True

    def groups_combobox(self, child) -> None:
        items = self.plugins.orto_add.get_group_names()
        child.comboBox_group.addItems(items)
        child.comboBox_group.setEditable(True)


def json_path(json_name: str = 'WMS_WMTS.json') -> str:
    return os.path.join(os.path.dirname(__file__), json_name)
