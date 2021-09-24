import os

from PyQt5.QtCore import Qt
from plugins.processing.core.ProcessingConfig import ProcessingConfig
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSortFilterProxyModel
from qgis.PyQt.QtWidgets import QDialog, QListWidget
from qgis.gui import QgsProcessingToolboxProxyModel

from ..utils import STANDARD_TOOLS, tr

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'UI/select_section_dialog.ui'))


class SelectSection(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(SelectSection, self).__init__(parent)
        self.setupUi(self)
        self.test_listWidget = QListWidget()
        filters = QgsProcessingToolboxProxyModel.Filters(
            QgsProcessingToolboxProxyModel.FilterToolbox)
        if ProcessingConfig.getSetting(
                ProcessingConfig.SHOW_ALGORITHMS_KNOWN_ISSUES):
            filters |= QgsProcessingToolboxProxyModel.FilterShowKnownIssues
        self.algorithmTree.setFilters(filters)
        tools = [tr(tool['label']) for tool in STANDARD_TOOLS]
        tools.sort()
        self.sort = QSortFilterProxyModel()
        self.test_listWidget.addItems(tools)
        self.sort.setSourceModel(self.test_listWidget.model())
        self.sort.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.toolList.setModel(self.sort)