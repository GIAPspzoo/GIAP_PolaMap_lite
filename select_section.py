import os
from plugins.processing.core.ProcessingConfig import ProcessingConfig
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog
from qgis._gui import QgsProcessingToolboxProxyModel
from .utils import STANDARD_TOOLS, tr

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'select_section_dialog.ui'))


class SelectSection(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(SelectSection, self).__init__(parent)
        self.setupUi(self)
        filters = QgsProcessingToolboxProxyModel.Filters(QgsProcessingToolboxProxyModel.FilterToolbox)
        if ProcessingConfig.getSetting(ProcessingConfig.SHOW_ALGORITHMS_KNOWN_ISSUES):
            filters |= QgsProcessingToolboxProxyModel.FilterShowKnownIssues
        self.algorithmTree.setFilters(filters)
        tools = [tr(x['label']) for x in STANDARD_TOOLS]
        self.toolList.addItems(tools)
