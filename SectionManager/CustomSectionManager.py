import os
from datetime import datetime
from typing import List, Union, Set

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QModelIndex
from qgis.PyQt.QtCore import QSortFilterProxyModel
from qgis.PyQt.QtWidgets import QDialog, QListWidget

from ..CustomMessageBox import CustomMessageBox
from ..utils import STANDARD_TOOLS, unpack_nested_lists, Qt, tr

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'UI/add_section_dialog.ui'))


class CustomSectionManager(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(CustomSectionManager, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.removed_idx = set()
        self.add_available_tools_into_list()
        self.find_tool_searchbox.textChanged.connect(
            self.search_available_tools)
        self.toolButton_add_tool.clicked.connect(self.add_to_selected)
        self.toolButton_remove_tool.clicked.connect(self.remove_from_selected)
        self.pushButton_save.clicked.connect(self.save_section)

    def add_available_tools_into_list(self) -> None:
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

    def prepare_selected_tools_list(self) -> List[str or int]:
        btns_list = []
        row = 0
        column = 0
        model = self.selectedToolList.model()

        for action_id in range(model.rowCount()):
            label = model.index(action_id, 0).data(0)
            if action_id % 2 != 0:
                row = 1
            else:
                row = 0
                column += 1
            btns_list.append([label, row, column])

        return btns_list

    def search_available_tools(self) -> None:
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

    def remove_from_selected(self) -> None:
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
        if tool_section_id in self.tools_dict.keys():
            section_actions = [action_list[0] for action_list in
                               self.tools_dict[tool_section_id][0]
                               if isinstance(action_list, list)]
            self.section_name_lineedit.setText(
                self.tools_dict[tool_section_id][-1])
            self.selectedToolList.addItems(section_actions)
        self.edit_id = tool_section_id
        if self.manage_editing_option(tool_section_row_id):
            self.edit_in_protected_mode()

    def get_actual_tools(self) -> None:
        self.tools_dict = {tool['id']: [tool['btns'], tool['label']]
                           for tool in STANDARD_TOOLS}
        existing_sections = self.parent.conf.load_custom_sections_setup()
        if existing_sections:
            self.tools_dict.update({tool['id']: [tool['btns'], tool['label']]
                                    for tool in existing_sections})

    def manage_editing_option(self, selected_row_id: int) -> bool:
        amount_of_header_rows = len(self.parent.dlg.reserved_rows.keys())
        reserved_row_ids = sorted(list(self.parent.dlg.reserved_rows.keys()))
        if not reserved_row_ids:
            return True
        if amount_of_header_rows == 1 and reserved_row_ids[-1] < \
                selected_row_id or reserved_row_ids[0] < selected_row_id < \
                reserved_row_ids[-1]:
            return True
        else:
            return False

    def save_section(self) -> None:
        if not self.section_name_lineedit.text() or \
                self.selectedToolList.model().rowCount() < 1:
            CustomMessageBox(
                self, tr('Error - Check the entered data.')).button_ok()
            return
        section_dict = {
            "label": self.section_name_lineedit.text(),
            "id": f"custom_{datetime.now().strftime('%y%m%d%H%M%S%f')}",
            "btn_size": 30,
            "btns": self.prepare_selected_tools_list()
        }
        existing_sections = self.parent.conf.load_custom_sections_setup()
        if not existing_sections:
            existing_sections = [section_dict]
        else:
            if hasattr(self, 'edit_id') and self.edit_id:
                self.remove_section(existing_sections, self.edit_id)
                del self.edit_id
            existing_sections.append(section_dict)
        self.parent.conf.setts['custom_sections'] = existing_sections
        self.accept()

    def remove_section(self, sections, section_id):
        tmp_idx = None
        for sec in sections:
            if sec['id'] == section_id:
                tmp_idx = sections.index(sec)
                break
        sections.pop(tmp_idx)

    def remove_row(self, tool_id: Set[Union[QModelIndex, str]]):
        self.selectedToolList.model().removeRows(
            0, self.selectedToolList.model().rowCount())
        existing_sections = self.parent.conf.load_custom_sections_setup()
        self.remove_section(existing_sections, tool_id[-1])
        self.parent.conf.setts['custom_sections'] = existing_sections

    def edit_in_protected_mode(self) -> None:
        self.pushButton_save.setEnabled(False)
        self.section_name_lineedit.setEnabled(False)
        self.toolButton_add_tool.setEnabled(False)
        self.toolButton_remove_tool.setEnabled(False)
