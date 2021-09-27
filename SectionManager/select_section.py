import os
from copy import deepcopy

from PyQt5.QtCore import Qt
from plugins.processing.core.ProcessingConfig import ProcessingConfig
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSortFilterProxyModel
from qgis.PyQt.QtWidgets import QDialog, QListWidget
from qgis.gui import QgsProcessingToolboxProxyModel

from ..utils import STANDARD_TOOLS, tr, GIAP_CUSTOM_TOOLS, \
    SectionHeaderDelegate, TOOLS_HEADERS

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'UI/select_section_dialog.ui'))


class SelectSection(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(SelectSection, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.test_listWidget = QListWidget()
        self.header_delegate = SectionHeaderDelegate(self)
        self.tmp_tools_headers = deepcopy(TOOLS_HEADERS)
        filters = QgsProcessingToolboxProxyModel.Filters(
            QgsProcessingToolboxProxyModel.FilterToolbox)
        if ProcessingConfig.getSetting(
                ProcessingConfig.SHOW_ALGORITHMS_KNOWN_ISSUES):
            filters |= QgsProcessingToolboxProxyModel.FilterShowKnownIssues
        self.algorithmTree.setFilters(filters)
        tools = sorted([tr(tool['label']) for tool in STANDARD_TOOLS
                        if tool['id'] not in GIAP_CUSTOM_TOOLS])
        giap_tools = sorted([tr(tool) for tool in GIAP_CUSTOM_TOOLS])
        self.add_header_and_delegate(0, tools)
        tools.extend(giap_tools)
        self.add_header_and_delegate(tools.index(giap_tools[0]), tools)
        self.sort = QSortFilterProxyModel()
        self.test_listWidget.addItems(tools)
        self.sort.setSourceModel(self.test_listWidget.model())
        self.sort.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.toolList.setModel(self.sort)
        self.userSectionsTab.hide()
        self.add_searchBox.hide()

    def add_header_and_delegate(self, idx, tool_list):
        tool_list.insert(idx, tr(self.tmp_tools_headers[0]))
        self.tmp_tools_headers.pop(0)
        self.toolList.setItemDelegateForRow(idx, self.header_delegate)
