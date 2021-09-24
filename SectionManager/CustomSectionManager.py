import os

from PyQt5.QtCore import Qt
from plugins.processing.core.ProcessingConfig import ProcessingConfig
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSortFilterProxyModel
from qgis.PyQt.QtWidgets import QDialog, QListWidget
from qgis.gui import QgsProcessingToolboxProxyModel

from ..utils import STANDARD_TOOLS, tr, unpack_nested_lists

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'UI/add_section_dialog.ui'))


class CustomSectionManager(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(CustomSectionManager, self).__init__(parent)
        self.setupUi(self)
        self.test_listWidget = QListWidget()
        tmp_tools_list = unpack_nested_lists(unpack_nested_lists(
            [tool['btns'] for tool in STANDARD_TOOLS]))
        tools = [tool for tool in tmp_tools_list if isinstance(tool, str)]
        tools.sort()
        self.sort = QSortFilterProxyModel()
        self.test_listWidget.addItems(tools)
        self.sort.setSourceModel(self.test_listWidget.model())
        self.sort.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.availableToolList.setModel(self.sort)
