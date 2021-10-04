import os
from typing import List, Union, Set

from qgis.PyQt.QtCore import QModelIndex
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSortFilterProxyModel
from qgis.PyQt.QtWidgets import QDialog, QListWidget

from ..utils import STANDARD_TOOLS, unpack_nested_lists, Qt

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
        self.pushButton_save.clicked.connect(self.save_section)

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

    def add_to_selected(self, selected_tools: List[str] = None):
        if not selected_tools:
            selected_tools = \
                [item for item in
                 self.availableToolList.selectionModel().selectedRows()]
        selected_tools_labels = [str(item.data(0)) for item in selected_tools]
        self.selectedToolList.addItems(selected_tools_labels)
        self.availableToolList.clearSelection()
        # for row_id in selected_tools_ids:
        #     self.availableToolList.model().removeRow(row_id)
        # self.removed_idx.update(set(selected_tools))

    def remove_from_selected(self):
        selected_tools = \
            [item for item in
             self.selectedToolList.selectionModel().selectedRows()]
        selected_tools_ids = [item.row() for item in selected_tools]
        for row_id in sorted(selected_tools_ids, reverse=True):
            self.selectedToolList.model().removeRow(row_id)

    def edit_selected_item(self, tool_id: Set[Union[QModelIndex, str]]):
        self.selectedToolList.model().removeRows(
            0, self.selectedToolList.model().rowCount())
        tool_section_id = tool_id[-1]
        tool_section_row_id = tool_id[0].row()
        self.get_actual_tools()
        section_actions = {}
        if tool_section_id in self.tools_dict.keys():
            section_actions = [action_list[0] for action_list in
                               self.tools_dict[tool_section_id][0]
                               if isinstance(action_list, list)]
            self.section_name_lineedit.setText(
                self.tools_dict[tool_section_id][-1])
            self.selectedToolList.addItems(section_actions)
        if not [sec_id for sec_id in
                sorted(list(self.parent.dlg.reserved_columns.keys()))
                if sec_id > tool_section_row_id]:
            self.edit_in_protected_mode()


    def get_actual_tools(self):
        self.tools_dict = {tool['id']: [tool['btns'], tool['label']]
                           for tool in STANDARD_TOOLS}

    def save_section(self):
        pass

    def edit_in_protected_mode(self):
        self.pushButton_save.setEnabled(False)
