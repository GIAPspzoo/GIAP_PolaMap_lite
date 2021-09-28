import os

from PyQt5.QtCore import Qt
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSortFilterProxyModel
from qgis.PyQt.QtWidgets import QDialog, QListWidget

from ..utils import STANDARD_TOOLS, unpack_nested_lists

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'UI/add_section_dialog.ui'))


class CustomSectionManager(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(CustomSectionManager, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.removed_idx = set()
        self.add_available_tools_into_list()
        self.prepare_selected_tools_list()
        self.find_tool_searchbox.textChanged.connect(
            self.search_available_tools)
        self.toolButton_add_tool.clicked.connect(self.add_to_selected)
        self.toolButton_remove_tool.clicked.connect(self.remove_from_selected)

    def add_available_tools_into_list(self):
        self.test_listWidget = QListWidget()
        tmp_tools_list = unpack_nested_lists(unpack_nested_lists(
            [tool['btns'] for tool in STANDARD_TOOLS]))
        tools = list(set([tool for tool in tmp_tools_list
                          if isinstance(tool, str)]))
        tools.sort()
        self.availableToolList_sort = QSortFilterProxyModel()
        self.test_listWidget.addItems(tools)
        self.availableToolList_sort.setSourceModel(
            self.test_listWidget.model())
        self.availableToolList_sort.setFilterCaseSensitivity(
            Qt.CaseInsensitive)
        self.availableToolList.setModel(self.availableToolList_sort)

    def prepare_selected_tools_list(self):
        pass

    def search_available_tools(self):
        self.availableToolList_sort.setFilterFixedString(
            self.find_tool_searchbox.value())

    def add_to_selected(self):
        selected_tools = [item for item in
                          self.availableToolList.selectionModel().selectedRows()]
        selected_tools_labels = [str(item.data(0)) for item in selected_tools]
        self.selectedToolList.addItems(selected_tools_labels)
        # for row_id in selected_tools_ids:
        #     self.availableToolList.model().removeRow(row_id)
        # self.removed_idx.update(set(selected_tools))

    def remove_from_selected(self):
        selected_tools = [item for item in
                          self.selectedToolList.selectionModel().selectedRows()]
        selected_tools_ids = [item.row() for item in selected_tools]
        for row_id in sorted(selected_tools_ids, reverse=True):
            self.selectedToolList.model().removeRow(row_id)
