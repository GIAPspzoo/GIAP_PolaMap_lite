import os
from copy import deepcopy
from typing import List, Set, Union

from PyQt5.QtGui import QStandardItemModel, QStandardItem
from plugins.processing.core.ProcessingConfig import ProcessingConfig
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QModelIndex
from qgis.PyQt.QtWidgets import QDialog, QListWidget, QListView
from qgis.gui import QgsProcessingToolboxProxyModel

from ..utils import STANDARD_TOOLS, tr, GIAP_CUSTOM_TOOLS, \
    SectionHeaderDelegate, TOOLS_HEADERS, STANDARD_QGIS_TOOLS, Qt, ProperSortFilterProxyModel

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'UI/select_section_dialog.ui'))


class SelectSection(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(SelectSection, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.refresh_lists()

    def prepare_sections_list(self) -> None:
        self.listWidget_obj = QListWidget()
        self.header_delegate = SectionHeaderDelegate(self)
        self.tmp_tools_headers = deepcopy(TOOLS_HEADERS)
        self.custom_sections = self.parent.conf.load_custom_sections_setup()
        data = {}
        tools = [tr(tool['label']) for tool in STANDARD_TOOLS
                 if tool['id'] not in GIAP_CUSTOM_TOOLS]
        standard_qgs_tools = [tr(tool['label'])
                              for tool in STANDARD_QGIS_TOOLS]
        giap_tools = sorted([tr(tool) for tool in GIAP_CUSTOM_TOOLS])
        if self.custom_sections:
            custom_sec = sorted(
                [tr(tool['label']) for tool in self.custom_sections
                 if tool['id'] not in GIAP_CUSTOM_TOOLS])
            custom_sec.sort()
        tools.extend(standard_qgs_tools)
        tools.sort()
        data[tr('Sections')] = deepcopy(tools)
        self.add_header_and_delegate(0, tools, self.toolList)
        tools.extend(giap_tools)
        data[tr('GIAP sections')] = giap_tools
        self.add_header_and_delegate(
            tools.index(giap_tools[0]), tools, self.toolList)
        if self.custom_sections:
            tools.extend(custom_sec)
            data[tr('User sections')] = custom_sec
            self.add_header_and_delegate(
                tools.index(custom_sec[0]), tools, self.toolList)

        self.toolList.hide()
        self.sort = ProperSortFilterProxyModel()
        self.sort.setSourceModel(self.create_tree_view(data))
        self.sort.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.treeView.setModel(self.sort)
        self.treeView.expandAll()
        self.treeView.resizeColumnToContents(0)

    def create_tree_view(self, data):
        qtvmodel = QStandardItemModel()
        root = qtvmodel.invisibleRootItem()

        def add_items(parent, dictionary):
            for key, value in dictionary.items():
                key_item = QStandardItem(str(key))
                parent.appendRow(key_item)

                if isinstance(value, list):
                    for item in value:
                        value_item = QStandardItem(str(item))
                        key_item.appendRow(value_item)
                elif isinstance(value, dict):
                    add_items(key_item, value)
                else:
                    value_item = QStandardItem(str(value))
                    key_item.appendRow(value_item)

        add_items(root, data)
        return qtvmodel

    def add_header_and_delegate(self, idx: int, tool_list: List[str],
                                listObj: QListView,
                                name: str = None) -> None:
        if name and name in self.tmp_tools_headers:
            header = tr(name)
            self.tmp_tools_headers.pop(self.tmp_tools_headers.index(name))
        else:
            header = tr(self.tmp_tools_headers[0])
            self.tmp_tools_headers.pop(0)
        tool_list.insert(idx, header)
        listObj.setItemDelegateForRow(idx, self.header_delegate)

    def prepare_toolbox_tab(self) -> None:
        filters = QgsProcessingToolboxProxyModel.Filters(
            QgsProcessingToolboxProxyModel.FilterToolbox)
        if ProcessingConfig.getSetting(
                ProcessingConfig.SHOW_ALGORITHMS_KNOWN_ISSUES):
            filters |= QgsProcessingToolboxProxyModel.FilterShowKnownIssues
        self.algorithmTree.setFilters(filters)

    def prepare_predefined_custom_sectons(self) -> None:
        self.reserved_rows = {0: tr('GIAP sections')}
        self.tools_id_dict = {}
        self.customlistWidget_obj = QListWidget()
        self.tmp_tools_headers = deepcopy(TOOLS_HEADERS)
        self.tools_id_dict_data = {}
        tools_dict = {tool['id']: tr(tool['label']) for tool in STANDARD_TOOLS
                      if tool['id'] in GIAP_CUSTOM_TOOLS}
        tools = sorted([tool for tool in tools_dict.values()])
        self.tools_id_dict_data[tr('Sections')] = deepcopy(tools)
        self.add_header_and_delegate(0, tools, self.customToolList,
                                     tr('GIAP sections'))

        if self.custom_sections:
            cust_tools_dict = {tool['id']: tr(tool['label'])
                               for tool in self.custom_sections
                               if tool['id'] not in GIAP_CUSTOM_TOOLS}
            tools_dict.update(cust_tools_dict)
            cust_tools = [tool for tool in cust_tools_dict.values()]
            tools.extend(cust_tools)
            self.tools_id_dict_data[tr('User sections')] = cust_tools
            self.add_header_and_delegate(tools.index(cust_tools[0]), tools,
                                         self.customToolList, 'User sections')
            self.reserved_rows[tools.index(tr('User sections'))] = \
                'User sections'

        for tool in tools:
            if tools.index(tool) not in self.reserved_rows.keys():
                self.tools_id_dict[tools.index(tool)] = \
                    {name: tl_id for tl_id, name in tools_dict.items()}[tool]

        self.customToolList.hide()
        self.sort_custom = ProperSortFilterProxyModel()
        self.sort_custom.setSourceModel(self.create_tree_view(self.tools_id_dict_data))
        self.sort_custom.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.treeView_2.setModel(self.sort_custom)
        self.treeView_2.expandAll()
        self.treeView_2.resizeColumnToContents(0)

    def get_selected_row(self) -> Set[Union[QModelIndex, str]] or None:
        rows = self.treeView_2.selectionModel().selectedRows()
        if rows:
            return rows[0], self.tools_id_dict_data[rows[0].parent().data()][rows[0].row()]
        return None

    def refresh_lists(self) -> None:
        self.prepare_sections_list()
        self.prepare_toolbox_tab()
        self.prepare_predefined_custom_sectons()
