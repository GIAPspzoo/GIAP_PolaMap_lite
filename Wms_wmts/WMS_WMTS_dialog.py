import os
from qgis.PyQt.uic import loadUiType
from qgis.PyQt.QtWidgets import QDialog, QMessageBox

from .add_WMS_WMTS_dialog import CreateConnection
from .edit_WMS_WMTS_dialog import EditConnection
from .utils import get_wms_config, set_wms_config
from ..utils import CustomMessageBox, tr, ConfigSaveProgressDialog

FORM_CLASS, _ = loadUiType(os.path.join(
    os.path.dirname(__file__), 'WMS_WMTS.ui'))


class WMS_WMTS_dialog(QDialog, FORM_CLASS):
    def __init__(self, OrtoAddingTool, parent=None):
        super(WMS_WMTS_dialog, self).__init__(parent)
        self.setupUi(self)
        self.OrtoAddingTool = OrtoAddingTool
        self.data = get_wms_config()
        self.close_btn.clicked.connect(self.accept)
        self.add_btn.clicked.connect(self.run_add_service)
        self.edit_btn.clicked.connect(self.run_edit_service)
        self.remove_btn.clicked.connect(self.remove_selected)
        self.wms_list = {}
        self.fill_list()

    def run(self) -> None:
        self.show()
        result = self.exec_()
        if result:
            ConfigSaveProgressDialog(self).exec_()

    def fill_list(self) -> None:
        self.listWidget.clear()
        for key in self.data.keys():
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
            CustomMessageBox(None, tr('No connection selected from the list !')).button_ok()
        self.data = get_wms_config()
        self.fill_list()

    def remove_selected(self) -> None:
        self.selected = self.listWidget.selectedItems()
        if not self.selected:
            return
        msg_box = CustomMessageBox(None, tr('Do you want to delete the selected layer?')).button_yes_no()
        if msg_box == QMessageBox.No:
            return
        for item in self.selected:
            self.listWidget.takeItem(self.listWidget.row(item))
        del self.data[[item.text() for item in self.selected][0]]
        set_wms_config(self.data)
        self.OrtoAddingTool.my_refresh_menu()

    def check_wms_name(self, wms_name: str) -> bool or None:
        if wms_name in self.data.keys():
            CustomMessageBox(None, tr('Name already exists. Please choose another name!')).button_ok()
            return
        return True

    def check_if_empty_lineedits(self, name: str, url: str) -> bool or None:
        if not name or not url:
            CustomMessageBox(None, tr('The name and URL fields cannot be empty!')).button_ok()
            return
        return True

    def groups_combobox(self, child) -> None:
        items = self.OrtoAddingTool.get_group_names()
        child.comboBox_group.addItems(items)
        child.comboBox_group.setEditable(True)
