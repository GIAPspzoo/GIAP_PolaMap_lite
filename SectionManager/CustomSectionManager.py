import itertools
import os
from datetime import datetime
from typing import List, Union, Set

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QModelIndex, QItemSelectionModel
from qgis.PyQt.QtCore import QSortFilterProxyModel, QSettings
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem
from qgis.PyQt.QtWidgets import QDialog, QToolBar, QAction
from qgis.utils import iface

from ..utils import STANDARD_TOOLS, unpack_nested_lists, Qt, tr, \
    icon_manager, CustomMessageBox, get_tool_label, GIAP_CUSTOM_TOOLS, get_action_from_toolbar, \
    find_widget_with_menu_in_toolbar
from ..config import Config

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'UI/add_section_dialog.ui'))


class CustomSectionManager(QDialog, FORM_CLASS):
    def __init__(self, parent=None, mode=None):
        super(CustomSectionManager, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.main_qgs_widget = parent.parent
        self.mode = mode
        self.removed_idx = set()
        if Config().setts['font_changed']:
            self.set_font_custom_section_manager(QSettings().value("qgis/stylesheet/fontPointSize"))
        if mode != 'remove':
            self.add_available_tools_into_list()
            self.find_tool_searchbox.textChanged.connect(
                self.search_available_tools)
            self.toolButton_add_tool.clicked.connect(self.add_to_selected)
            self.toolButton_remove_tool.clicked.connect(
                self.remove_from_selected)
            self.wdol_narzdzie.clicked.connect(self.move_down)
            self.wgore_narzdzie.clicked.connect(self.move_up)
            self.pushButton_save.clicked.connect(self.save_section)
            self.protected = False

    def set_font_custom_section_manager(self, font_size) -> None:
        attributes = [self.pushButton_save, self.pushButton_cancel, self.title_label]
        for attr in attributes:
            attr.setStyleSheet(f'{attr.styleSheet()} font: {font_size}pt;')
        self.frame_main.setStyleSheet(
            f'{self.frame_main.styleSheet()}QFrame, QTableView, QLabel, QLineEdit, '
            f'QgsFilterLineEdit {{font: {font_size}pt;}}')

    def add_available_tools_into_list(self) -> None:
        self.availableToolTable_sort = QSortFilterProxyModel()
        model = QStandardItemModel()
        model.setColumnCount(2)
        tmp_tools_list = unpack_nested_lists(
            unpack_nested_lists([tool['btns'] for tool in STANDARD_TOOLS]))
        tools = list(
            set([tool for tool in tmp_tools_list if isinstance(tool, str)]))
        toolbar_tools = [tool.objectName() for tool in self.get_all_actions_from_qgis_toolbars()]
        [tools.append(tool) for tool in toolbar_tools if tool not in tools]
        tools.sort()
        for tool in tools:
            if not tool:
                continue
            try:
                item = QStandardItem(tr(get_tool_label(tool, self.main_qgs_widget)))
                item.setData(icon_manager([tool], self.main_qgs_widget)[tool], Qt.DecorationRole)
                model.appendRow([QStandardItem(tool), item])
            except:
                pass
        self.availableToolTable_sort.setSourceModel(model)
        self.availableToolTable_sort.setFilterCaseSensitivity(
            Qt.CaseInsensitive)
        self.availableToolTable_sort.setFilterKeyColumn(-1)
        self.availableToolTable_sort.sort(1, Qt.AscendingOrder)
        self.availableToolTable.setModel(self.availableToolTable_sort)
        self.availableToolTable.resizeColumnsToContents()
        self.availableToolTable.hideColumn(0)
        self.selectedToolTable.hideColumn(0)

    def get_all_actions_from_qgis_toolbars(self) -> List[QAction]:
        qgis_toolbars = [toolbar for toolbar in iface.mainWindow().findChildren(QToolBar)
                         if "toolbar" in toolbar.objectName().lower() and "giap" not in toolbar.objectName().lower()]
        actions = []
        for toolbar in qgis_toolbars:
            acts = get_action_from_toolbar(toolbar)
            widgs = find_widget_with_menu_in_toolbar(toolbar)
            for widg in widgs:
                [acts.append(act) for act in widg.actions()]
            actions.append(acts)

        all_actions = list(itertools.chain(*actions))
        return all_actions

    def prepare_selected_tools_list(self) -> List[str or int]:
        btns_list = []
        row = 0
        column = 0
        model = self.selectedToolTable.model()

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
        self.availableToolTable_sort.setFilterFixedString(
            self.find_tool_searchbox.value())

    def add_to_selected(self, selected_tools: List[str] = None) -> None:
        if not hasattr(self, 'selected_model'):
            self.selected_model = QStandardItemModel()
            self.selected_model.setColumnCount(2)
        if not selected_tools:
            selected_tools = \
                [item for item in
                 self.availableToolTable.selectionModel().selectedRows()]
        if not selected_tools:
            return
        selected_tools_labels = [str(item.data(0)) for item in selected_tools]

        for tool in selected_tools_labels:
            try:
                item = QStandardItem(tr(get_tool_label(tool, self.main_qgs_widget)))
                item.setData(icon_manager([tool], self.main_qgs_widget)[tool], Qt.DecorationRole)
            except:
                item = QStandardItem(tr(get_tool_label(tool, self.main_qgs_widget)))
                item.setData(icon_manager([tool], self.main_qgs_widget)[tool.replace(":", "_")], Qt.DecorationRole)

            self.selected_model.appendRow([QStandardItem(tool), item])
        self.selectedToolTable.setModel(self.selected_model)
        self.selectedToolTable.resizeColumnsToContents()
        self.selectedToolTable.hideColumn(0)
        self.availableToolTable.clearSelection()

    def remove_from_selected(self) -> None:
        selected_tools = \
            [item for item in
             self.selectedToolTable.selectionModel().selectedRows()]
        selected_tools_ids = [item.row() for item in selected_tools]
        for row_id in sorted(selected_tools_ids, reverse=True):
            self.selectedToolTable.model().removeRow(row_id)

    def move_down(self):

        table_sel_model = self.selectedToolTable.selectionModel()
        rows = table_sel_model.selectedRows()
        row_max = self.selectedToolTable.model().rowCount()-1
        if rows:
            check_is_row_move = True
            for row in rows:
                index = row.row()
                if index == row_max:
                    check_is_row_move = False
            if not check_is_row_move:
                table_sel_model.clear()
                CustomMessageBox(self, tr('Unable to move item down.')).button_ok()
                return
            else:
                for row in rows:
                    index = row.row()
                    self._move_field(index, index + 1)
            model = self.selectedToolTable.model()
            table_sel_model = self.selectedToolTable.selectionModel()
            table_sel_model.clear()
            for row in rows:
                table_sel_model.select(model.index(row.row() + 1, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows)
        else:
            CustomMessageBox(self,
                             tr('Choose tool to change order.')
                             ).button_ok()

    def move_up(self):
        table_sel_model = self.selectedToolTable.selectionModel()
        rows = table_sel_model.selectedRows()
        if rows:
            for row in rows:
                index = row.row()
                if index > 0:
                    self._move_field(index, index - 1)
                elif index == 0:
                    table_sel_model.clear()
                    CustomMessageBox(self, tr('Unable to move item up.')).button_ok()
                    return

            model = self.selectedToolTable.model()
            table_sel_model = self.selectedToolTable.selectionModel()
            table_sel_model.clear()
            for row in rows:
                table_sel_model.select(model.index(row.row() - 1, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows)
        else:
            CustomMessageBox(self,
                             tr('Choose tool to change order.')
                             ).button_ok()

    def _move_field(self, index: int, direction: int) -> None:
        model = self.selectedToolTable.model()
        model.insertRow(direction, model.takeRow(index))

    def edit_selected_item(self,
                           tool_id: Set[Union[QModelIndex, str]]) -> None:
        if not hasattr(self, 'selected_model'):
            self.selected_model = QStandardItemModel()
            self.selected_model.setColumnCount(2)
        self.selectedToolTable.setModel(self.selected_model)
        tool_section_id = tool_id[-1]
        tool_section_row_id = tool_id[0].row()
        self.get_actual_tools()
        for tools_dict_item in self.tools_dict.keys():
            if tool_section_id == tr(tools_dict_item) or tool_section_id == self.tools_dict[tools_dict_item][-1]:
                section_actions = [action_list[0] for action_list in
                                   self.tools_dict[tools_dict_item][0]
                                   if isinstance(action_list, list)]
                self.section_name_lineedit.setText(tr(self.tools_dict[tools_dict_item][-1]))
                self.section_name_backup = self.section_name_lineedit.text()
                for tool in section_actions:
                    try:
                        item = QStandardItem(tr(get_tool_label(tool, self.main_qgs_widget)))
                        item.setData(icon_manager([tool], self.main_qgs_widget)[tool], Qt.DecorationRole)
                        self.selected_model.appendRow([QStandardItem(tool), item])
                    except:
                        item = QStandardItem(tr(get_tool_label(tool, self.main_qgs_widget)))
                        item.setData(icon_manager([tool], self.main_qgs_widget)[tool.replace(":", "_")], Qt.DecorationRole)
                        self.selected_model.appendRow([QStandardItem(tool), item])
        self.edit_id = tool_section_id
        self.selectedToolTable.resizeColumnsToContents()
        self.selectedToolTable.hideColumn(0)
        if self.manage_editing_option(tool_section_row_id):
            self.protected = True

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
                not self.selectedToolTable.model() or \
                self.selectedToolTable.model().rowCount() < 1:
            CustomMessageBox(
                self, tr('Error - Check the entered data.')).button_ok()
            return
        existing_sections = self.parent.conf.load_custom_sections_setup()
        section_labels = [section['label'] for section in existing_sections]
        if self.protected:
            if tr(self.section_name_lineedit.text()) in \
                    sorted([tr(tool) for tool in GIAP_CUSTOM_TOOLS]):
                self.section_name_lineedit.setText(
                    f'{tr(self.section_name_lineedit.text())} - edytowany')
        if self.section_name_lineedit.text() in section_labels:
            if self.mode == 'edit':
                if self.section_name_backup != self.section_name_lineedit.text():
                    CustomMessageBox(
                        self,
                        tr('Error - The section name already exists.')).button_ok()
                    return
            else:
                CustomMessageBox(
                    self,
                    tr('Error - The section name already exists.')).button_ok()
                return
        section_dict = {
            "label": self.section_name_lineedit.text(),
            "id": f"custom_{datetime.now().strftime('%y%m%d%H%M%S%f')}",
            "btn_size": 30,
            "btns": self.prepare_selected_tools_list()
        }
        if not existing_sections:
            existing_sections = [section_dict]
        else:
            if hasattr(self, 'edit_id') and self.edit_id:
                if not self.protected:
                    self.remove_section(existing_sections, self.edit_id)
                del self.edit_id
            existing_sections.append(section_dict)
        self.parent.conf.save_custom_sections_setup(existing_sections)
        self.accept()

    def remove_section(self, sections, section_id) -> None:
        tmp_idx = None
        for sec in sections:
            if sec['label'] == section_id:
                tmp_idx = sections.index(sec)
                break
        try:
            sections.pop(tmp_idx)
        except TypeError:
            pass

    def remove_row(self, tool_id: Set[Union[QModelIndex, str]]) -> None:
        model = QStandardItemModel()
        self.selectedToolTable.setModel(model)
        existing_sections = self.parent.conf.load_custom_sections_setup()
        self.remove_section(existing_sections, tool_id[-1])
        self.parent.conf.save_custom_sections_setup(existing_sections)
