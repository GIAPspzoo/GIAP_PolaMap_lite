import os
import re
from typing import List, Any, Dict, Optional, Union

from PyQt5.QtCore import Qt, QSortFilterProxyModel
from PyQt5.QtWidgets import QPushButton
from qgis.gui import QgsMapToolIdentify
from qgis.PyQt import QtCore, QtGui
from qgis.PyQt.QtCore import QThread, QObject, QSettings, Qt, pyqtSignal, NULL
from qgis.PyQt.QtGui import QPen, QBrush, QIcon, QPixmap
from qgis.PyQt.QtWidgets import QApplication, QProgressDialog, \
    QStyledItemDelegate, QAction, QMessageBox, QScrollArea, QWidget, \
    QGridLayout, QLabel, QDialogButtonBox, QToolButton, QToolBar
from qgis.core import QgsProject, QgsMessageLog, Qgis, QgsApplication, \
    QgsVectorLayer, QgsMapLayer, QgsCoordinateTransform, QgsGeometry, QgsPointXY, QgsRectangle
from qgis.utils import iface
import qgis

project = QgsProject.instance()
root = project.layerTreeRoot()


class CustomMessageBox(QMessageBox):
    stylesheet = """
        * {
            background-color: rgb(53, 85, 109, 220);
            color: rgb(255, 255, 255);
            font: 10pt "Segoe UI";
            border: 0px;
        }

        QAbstractItemView {
            selection-background-color:  rgb(87, 131, 167);
        }

        QPushButton {
            border: none;
            border-width: 1px;
            border-radius:3px;
            background-color: #5589B0;
        }
        QPushButton:checked {
            background-color: #5589B0;
            border: solid;
            border-width: 1px;
            border-color: #5589B0;
        }
        
        QPushButton:pressed {
            background-color: #5589B0;
            border: solid;
            border-width: 1px;
            border-color:#5589B0;
        }
        QPushButton:hover {
            background-color: #5589B0;
            border-radius: 3px;
            border: solid;
            border-style: solid;
            border-width: 1px;
            border-color: #E0DECF;
        }"""

    def __init__(self, parent=None, text='', image=''):
        super(CustomMessageBox, self).__init__(parent)
        self.text = text

        self.rebuild_layout(text, image)

    def rebuild_layout(self, text, image):
        self.setStyleSheet(self.stylesheet)

        scrll = QScrollArea(self)
        scrll.setWidgetResizable(True)
        self.qwdt = QWidget()
        self.qwdt.setLayout(QGridLayout(self))
        grd = self.findChild(QGridLayout)
        if text:
            lbl = QLabel(text, self)
            lbl.setStyleSheet(self.stylesheet)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setWordWrap(False)
            lbl.setTextInteractionFlags(
                Qt.TextSelectableByMouse)
            self.qwdt.layout().addWidget(lbl, 1, 0)
        if image:
            px_lbl = QLabel(self)
            img_path = normalize_path(image)
            pixmap = QPixmap(img_path)
            px_lbl.setPixmap(pixmap)
            px_lbl.setMinimumSize(pixmap.width(), pixmap.height())
            px_lbl.setAlignment(Qt.AlignCenter)
            px_lbl.setWordWrap(False)
            self.qwdt.layout().addWidget(px_lbl, 0, 0)

        scrll.setWidget(self.qwdt)
        scrll.setContentsMargins(15, 5, 15, 10)
        scrll.setStyleSheet(self.stylesheet)
        grd.addWidget(scrll, 0, 1)
        self.layout().removeItem(self.layout().itemAt(0))
        self.layout().removeItem(self.layout().itemAt(0))
        self.setWindowTitle('GIAP-PolaMap(lite)')
        plug_dir = os.path.dirname(__file__)
        self.setWindowIcon(QIcon(os.path.join(plug_dir, 'giap.ico')))

    def button_ok(self):
        self.setStandardButtons(QMessageBox.Ok)
        self.setDefaultButton(QMessageBox.Ok)
        self.set_proper_size()
        QMessageBox.exec_(self)

    def button_yes_no(self):
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        self.setDefaultButton(QMessageBox.No)
        self.set_proper_size()
        return QMessageBox.exec_(self)

    def set_proper_size(self):
        scrll = self.findChild(QScrollArea)
        new_size = self.qwdt.sizeHint()
        if self.qwdt.sizeHint().height() > 600:
            new_size.setHeight(600)
        else:
            new_size.setHeight(self.qwdt.sizeHint().height())
        if self.qwdt.sizeHint().width() > 800:
            new_size.setWidth(800)
            new_size.setHeight(new_size.height() + 20)
        else:
            btn_box_width = self.findChild(QDialogButtonBox).sizeHint().width()
            if self.qwdt.sizeHint().width() > btn_box_width:
                new_size.setWidth(self.qwdt.sizeHint().width())
            else:
                new_size.setWidth(btn_box_width)
        for child in self.findChild(QDialogButtonBox).children():
            if isinstance(child, QPushButton):
                child.setMinimumHeight(25)
                child.setMinimumWidth(50)
        scrll.setFixedSize(new_size)
        scrll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scrll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.show()
        scrll.horizontalScrollBar().setValue(
            int(scrll.horizontalScrollBar().maximum() / 2))


def get_simple_progressbar(max_len, title='Proszę czekać',
                           txt='Trwa przetwarzanie danych.', parent=None,
                           window_width: int = 500):
    progress = QProgressDialog(parent)
    progress.setFixedWidth(window_width)
    progress.setWindowTitle(title)
    progress.setLabelText(txt)
    progress.setMaximum(max_len)
    progress.setValue(0)
    progress.setAutoClose(True)
    progress.setCancelButton(None)
    progress.setWindowIcon(QIcon(':/plugins/GIAP-PolaMap/icons/giap_logo.png'))
    QApplication.processEvents()
    return progress


class ProperSortFilterProxyModel(QSortFilterProxyModel):
    SORTING_AS_NUMBERS = []
    SORTING_AS_NAME = []

    def __init__(self):
        QSortFilterProxyModel.__init__(self)
        self.sorting_functions = {
            'SORTING_AS_NUMBERS': self._less_than_numbers,
            'SORTING_AS_NAME': self._less_than_name
        }
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.sortOrder()

    def flags(self, index):
        source_index = self.mapToSource(index)
        if not source_index.parent().isValid():
            return Qt.NoItemFlags | Qt.ItemIsEnabled
        return super().flags(index)

    def filterAcceptsRow(self, source_row, source_parent):
        if not source_parent.isValid():
            return True

        source_index = self.sourceModel().index(source_row, 0, source_parent)
        if not source_index.isValid():
            return False
        text = source_index.data()
        if text is None:
            return False

        return self.filterRegExp().pattern().lower() in text.lower()

    def lessThan(self, left, right):
        col_num = left.column()
        for sorting_cat in self.sorting_functions:
            if col_num in getattr(self, sorting_cat):
                return self.sorting_functions[sorting_cat](left, right)
        return QSortFilterProxyModel.lessThan(self, left, right)

    def _less_than_name(self, left, right):
        try:
            lvalue = left.data()
            rvalue = right.data()

            if lvalue in (NULL, 'NULL', ''):
                lvalue = ''
            if rvalue in (NULL, 'NULL', ''):
                rvalue = ''
            if not str(lvalue).lower():
                if self.sortOrder():
                    return True
                else:
                    return False
            elif not str(rvalue).lower():
                if self.sortOrder():
                    return False
                else:
                    return True
            else:
                return str(lvalue).lower() < str(rvalue).lower()
        except (ValueError, TypeError):
            return QSortFilterProxyModel.lessThan(self, left, right)

    def _less_than_numbers(self, left, right):
        try:
            lvalue = left.data()
            rvalue = right.data()
            if lvalue in (NULL, 'NULL', ''):
                lvalue = ''
            if rvalue in (NULL, 'NULL', ''):
                rvalue = ''
            if not lvalue:
                if self.sortOrder():
                    return True
                else:
                    return False
            elif not rvalue:
                if self.sortOrder():
                    return False
                else:
                    return True
            lvalue = float(lvalue)
            rvalue = float(rvalue)
            return lvalue < rvalue
        except (ValueError, TypeError) as e:
            return QSortFilterProxyModel.lessThan(self, left, right)


class SingletonModel:
    __instance = None

    def __new__(cls, *args):
        if SingletonModel.__instance is None:
            QgsMessageLog.logMessage(f'CREATE OBJECT OF CLASS: {cls.__name__}',
                                     "giap_layout",
                                     Qgis.Info)
            SingletonModel.__instance = object.__new__(cls, *args)
        return SingletonModel.__instance


class ProgressDialog(QProgressDialog, SingletonModel):

    def __init__(self, parent=None, title='GIAP-PolaMap(lite)'):
        super(ProgressDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(icon_manager(['window_icon'])['window_icon'])
        self.setLabelText('Proszę czekać...')
        self.setFixedWidth(300)
        self.setFixedHeight(100)
        self.setMaximum(100)
        self.setCancelButton(None)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.rejected.connect(self.stop)
        self.setWindowModality(Qt.WindowModal)

    def make_percent_step(self, step=100, new_text=None):
        self.setStyleSheet(self.stylesheet)
        if new_text:
            self.setLabelText(new_text)
            if "wczytywanie" in new_text:
                for pos in range(100 - self.value()):
                    QApplication.processEvents()
                    self.setValue(self.value() + 1)
                return
        for pos in range(step):
            QApplication.processEvents()
            self.setValue(self.value() + 1)
        QApplication.sendPostedEvents()
        QApplication.processEvents()

    def start_steped(self, title='Trwa ładowanie danych.\n  Proszę czekać...'):
        self.setLabelText(title)
        self.setValue(1)
        self.show()
        QApplication.sendPostedEvents()
        QApplication.processEvents()

    def start(self):
        self.setFixedWidth(250)
        self.setMaximum(0)
        self.setCancelButton(None)
        self.show()
        QApplication.sendPostedEvents()
        QApplication.processEvents()

    def stop(self):
        self.setValue(100)
        self.close()


def identify_layer(ls, layer_to_find):
    for layer in list(ls.values()):
        if layer.name() == layer_to_find:
            return layer


def identify_layer_by_id(layerid_to_find):
    for layerid, layer in project.mapLayers().items():
        if layerid == layerid_to_find:
            return layer


def identify_layer_in_group(group_name, layer_to_find):
    for tree_layer in project.layerTreeRoot().findLayers():
        if tree_layer.parent().name() == group_name and \
                tree_layer.layer().name() == layer_to_find:
            return tree_layer.layer()


def identify_layer_in_group_by_parts(group_name, layer_to_find):
    for lr in project.layerTreeRoot().findLayers():
        if lr.parent().name() == group_name \
                and lr.name().startswith(layer_to_find):
            return lr.layer()


class IdentifyGeometryByType(QgsMapToolIdentify):
    geomIdentified = pyqtSignal(list)

    def __init__(self, canvas, wkb_type_list, get_only_visible_layers=False):
        QgsMapToolIdentify.__init__(self, canvas)
        self.wkb_types = wkb_type_list
        self.get_only_visible_layers = get_only_visible_layers

    def canvasReleaseEvent(self, mouseEvent):
        if self.get_only_visible_layers:
            layers = iface.mapCanvas().layers()
        else:
            layers = project.mapLayers().values()
        layerList = []
        for layer in layers:
            if layer.type().value == 0 and layer.wkbType() in self.wkb_types:
                layerList.append(layer)
        results = self.identify(mouseEvent.x(), mouseEvent.y(),
                                layerList=layerList, mode=self.LayerSelection)
        self.geomIdentified.emit(results)


def identify_layer_by_name(layername_to_find):
    for layer in list(project.mapLayers().values()):
        if layer.name() == layername_to_find:
            return layer


def transform_geometry(geometry, geom_layer):
    geom_layer_crs = geom_layer.crs()
    destination_crs = iface.mapCanvas().mapSettings().destinationCrs()
    xform = QgsCoordinateTransform(geom_layer_crs, destination_crs, project)
    if isinstance(geometry, (QgsPointXY, QgsRectangle)):
        geom_in_dest_crs = xform.transform(geometry)
    else:
        geom_in_dest_crs = QgsGeometry(geometry)
        geom_in_dest_crs.transform(xform)
    return geom_in_dest_crs


def set_project_config(parameter, key, value):
    if isinstance(project, QgsProject):
        return project.writeEntry(parameter, key, value)


def normalize_path(path):
    return os.path.normpath(os.sep.join(re.split(r'\\|/', path)))


def tr(message):
    """Get the translation for a string using Qt translation API.
    We implement this ourselves since we do not inherit QObject.
    :param message: String for translation.
    :type message: str, QString

    :returns: Translated version of message.
    :rtype: QString
    """
    return QApplication.translate('@default', message)


class ConfigSaveThread(QThread):
    def __init__(self, parent):
        super(ConfigSaveThread, self).__init__(parent)

    def run(self):
        project.write()


class ConfigSaveProgressDialog(QProgressDialog):
    def __init__(self, parent=None):
        super(ConfigSaveProgressDialog, self).__init__(parent)
        self.setWindowTitle('Zapisywanie ustawień')
        self.setLabelText('Proszę czekać...')
        self.setMaximum(0)
        self.setCancelButton(None)

        QApplication.processEvents()

        self.thread = ConfigSaveThread(self)
        self.thread.finished.connect(self.finished)
        self.thread.start()

    def finished(self):
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()
        self.close()


def get_project_config(parameter, key, default=''):
    value = project.readEntry(parameter, key, default)[0]
    return value


def unpack_nested_lists(n_list: List[List[Any]]) -> List[Any]:
    """
    Funkcja rozpakowuje listy list, najczęściej zwracane przez zapytajBaze
    :return: rozpakowana lista z jednym lub większą ilością elementów
    """
    return [elem for nested_list in n_list for elem in nested_list]


class SectionHeaderDelegate(QStyledItemDelegate):
    def __init__(self, parent):
        super(SectionHeaderDelegate, self).__init__(parent)

    def sizeHint(self, option, index):
        return QtCore.QSize(
            int(QtGui.QTextDocument(index.model().data(index)).idealWidth()), 30)

    def paint(self, painter, option, index):
        painter.save()
        painter.setPen(
            QPen(QBrush(Qt.white), 1, Qt.SolidLine, Qt.SquareCap,
                 Qt.BevelJoin))
        painter.setClipRect(option.rect)
        painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
        painter.setPen(QPen(Qt.white))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(option.rect, Qt.AlignCenter,
                         index.data(Qt.DisplayRole))
        painter.restore()


GIAP_NEWS_WEB_PAGE = 'https://www.giap.pl/aktualnosci/'
WFS_PRG = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/PRG/WFS/AdministrativeBoundaries"

search_group_name = 'WYNIKI WYSZUKIWANIA'

STANDARD_TOOLS = [
    {
        "label": tr("Project"),
        "id": "Project",
        "btn_size": 30,
        "btns": [
            ["mActionOpenProject", 0, 0],
            ["mActionNewProject", 0, 1],
            ["mActionSaveProject", 1, 0],
            ["mActionSaveProjectAs", 1, 1]
        ]
    },

    {
        "label": tr("Navigation"),
        "id": "Navigation",
        "btn_size": 30,
        "btns": [
            ["mActionPan", 0, 0],
            ["mActionZoomIn", 0, 1],
            ["mActionZoomOut", 0, 2],
            ["mActionZoomFullExtent", 0, 3],

            ["mActionZoomToLayer", 1, 0],
            ["mActionZoomToSelected", 1, 1],
            ["mActionZoomLast", 1, 2],
            ["mActionZoomNext", 1, 3]
        ]
    },

    {
        'label': tr('Attributes'),
        'id': 'Attributes',
        'btn_size': 30,
        'btns': [
            ['mActionIdentify', 0, 0],
            ['mActionSelectFeatures', 0, 1],
            ['mActionDeselectAll', 1, 0],
            ['mActionOpenTable', 1, 1],
        ],
    },

    {
        'label': tr('Measurement'),
        'id': 'Measurement',
        'btn_size': 30,
        'btns': [
            ['mActionMeasure', 0, 0],
            ['mActionMeasureArea', 0, 1],
            ['mActionMeasureAngle', 1, 0],
        ],
    },

    {
        'label': tr('Add Layer'),
        'id': 'Add Layer',
        'btn_size': 30,
        'btns': [
            ['mActionAddOgrLayer', 0, 0],
            ['mActionAddWmsLayer', 0, 1],
            ['mActionAddPgLayer', 0, 2],
            ['mActionAddMeshLayer', 0, 3],
            ['mActionAddWcsLayer', 0, 4],
            ['mActionAddDelimitedText', 0, 5],
            ['mActionAddMssqlLayer', 0, 6],
            ['mActionAddDb2Layer', 1, 6],
            ['mActionAddOracleLayer', 0, 7],
            ['mActionAddRasterLayer', 1, 0],
            ['mActionAddWfsLayer', 1, 1],
            ['mActionAddSpatiaLiteLayer', 1, 2],
            ['mActionAddVirtualLayer', 1, 3],
            ['mActionAddAmsLayer', 1, 4],
            ['mActionAddAfsLayer', 1, 5],
        ],
    },

    {
        'label': tr('Create Layer'),
        'id': 'Create Layer',
        'btn_size': 30,
        'btns': [
            ['mActionNewGeoPackageLayer', 1, 1],
            ['mActionNewMemoryLayer', 0, 2],
            ['mActionNewVectorLayer', 0, 1],
            ['mActionNewSpatiaLiteLayer', 1, 2],
            ['mActionNewVirtualLayer', 0, 3]
        ],
    },

    {
        'label': tr('Advanced attributes'),
        'id': 'Advanced attributes',
        'btn_size': 30,
        'btns': [
            ['mActionIdentify', 0, 0],
            ['mActionSelectFeatures', 0, 1],
            ['mActionSelectPolygon', 0, 2],
            ['mActionSelectByExpression', 0, 3],
            ['mActionInvertSelection', 0, 4],
            ['mActionDeselectAll', 0, 5],

            ['mActionOpenTable', 1, 0],
            ['mActionStatisticalSummary', 1, 1],
            ['mActionOpenFieldCalc', 1, 2],
            ['mActionMapTips', 1, 3],
            ['mActionNewBookmark', 1, 4],
            ['mActionShowBookmarks', 1, 5],
        ],
    },

    {
        'label': tr('Labels'),
        'id': 'Labels',
        'btn_size': 30,
        'btns': [
            ['mActionLabeling', 0, 0],
            ['mActionChangeLabelProperties', 0, 1],
            ['mActionPinLabels', 0, 2],
            ['mActionShowPinnedLabels', 0, 3],
            ['mActionShowHideLabels', 0, 4],
            ['mActionMoveLabel', 1, 0],
            ['mActionRotateLabel', 1, 1],
            ['mActionDiagramProperties', 1, 2],
            ['mActionShowUnplacedLabels', 1, 3],
        ]
    },

    {
        'label': tr('Vector'),
        'id': 'Vector',
        'btn_size': 30,
        'btns': [
            ['mActionToggleEditing', 0, 0],
            ['mActionSaveLayerEdits', 0, 1],
            ['mActionVertexTool', 0, 2],
            ['mActionUndo', 0, 3],
            ['mActionRedo', 0, 4],
            ['mQActionPointer', 0, 5],
            ['mActionAddFeature', 1, 0],
            ['mActionMoveFeature', 1, 1],
            ['mActionDeleteSelected', 1, 2],
            ['mActionCutFeatures', 1, 3],
            ['mActionCopyFeatures', 1, 4],
            ['mActionPasteFeatures', 1, 5],
        ],
    },

    {
        'label': tr('Vector digitization'),
        'id': 'Vector digitization',
        'btn_size': 30,
        'btns': [
            ['EnableSnappingAction', 0, 0],
            ['EnableTracingAction', 0, 1],
            ['mActionRotateFeature', 0, 2],
            ['mActionSimplifyFeature', 0, 3],
            ['mActionAddRing', 0, 4],
            ['mActionAddPart', 0, 5],
            ['mActionFillRing', 0, 6],
            ['mActionOffsetCurve', 0, 7],
            ['mActionCircularStringCurvePoint', 0, 8],

            ['mActionDeleteRing', 1, 0],
            ['mActionDeletePart', 1, 1],
            ['mActionReshapeFeatures', 1, 2],
            ['mActionSplitParts', 1, 3],
            ['mActionSplitFeatures', 1, 4],
            ['mActionMergeFeatureAttributes', 1, 5],
            ['mActionMergeFeatures', 1, 6],
            ['mActionReverseLine', 1, 7],
            ['mActionTrimExtendFeature', 1, 8],
        ]
    },

    {
        'label': tr('Prints'),
        'id': 'Prints',
        'btn_size': 30,
        'btns': [
            ['mActionNewPrintLayout', 0, 0],
            ['giapMyPrints', 0, 1],
            ['mActionShowLayoutManager', 1, 0],
            ['giapQuickPrint', 1, 1],
        ]
    },

    {
        'label': tr('GIAP Tools'),
        'id': 'GIAP Tools',
        'btn_size': 60,
        'btns': [
            ['giapCompositions', 0, 0],
            ['giapWMS', 0, 1],
            ['giapQuickPrint', 0, 2],
            ['giapAreaLength', 0, 3],
        ]
    },
    {
        'label': tr('Extras'),
        'id': 'Extras',
        'btn_size': 30,
        'btns': [
            ['giapPRNG', 0, 0],
            ['giapgeokodowanie', 1, 0]
            ['giapGeoportal', 0, 1],
            ['giapOrtoContr', 1, 1],
        ]
    },
    {
        'label': tr('Geoprocessing Tools'),
        'id': 'Geoprocessing Tools',
        'btn_size': 30,
        'btns': [
            ['mProcessingUserMenu_native:buffer', 0, 0],
            ['mProcessingUserMenu_native:clip', 1, 0],
            ['mProcessingUserMenu_native:convexhull', 0, 1],
            ['mProcessingUserMenu_native:difference', 0, 2],
            ['mProcessingUserMenu_native:dissolve', 0, 3],
            ['mProcessingUserMenu_native:intersection', 1, 1],
            ['mProcessingUserMenu_native:symmetricaldifference', 1, 2],
            ['mProcessingUserMenu_native:union', 1, 3],
            ['mProcessingUserMenu_qgis:eliminateselectedpolygons', 0, 4],
        ],
    },

    {
        'label': tr('Geometry Tools'),
        'id': 'Geometry Tools',
        'btn_size': 30,
        'btns': [
            ['mProcessingUserMenu_native:centroids', 0, 0],
            ['mProcessingUserMenu_native:collect', 0, 1],
            ['mProcessingUserMenu_native:densifygeometries', 0, 2],
            ['mProcessingUserMenu_native:extractvertices', 0, 3],
            ['mProcessingUserMenu_native:multiparttosingleparts', 0, 4],
            ['mProcessingUserMenu_native:polygonstolines', 0, 5],
            ['mProcessingUserMenu_native:simplifygeometries', 1, 0],
            ['mProcessingUserMenu_qgis:checkvalidity', 1, 1],
            ['mProcessingUserMenu_qgis:delaunaytriangulation', 1, 2],
            ['mProcessingUserMenu_qgis:exportaddgeometrycolumns', 1, 3],
            ['mProcessingUserMenu_qgis:linestopolygons', 1, 4],
            ['mProcessingUserMenu_qgis:voronoipolygons', 1, 5],
        ],
    },

    {
        'label': tr('Analysis Tools'),
        'id': 'Analysis Tools',
        'btn_size': 30,
        'btns': [
            ['mProcessingUserMenu_native:countpointsinpolygon', 0, 0],
            ['mProcessingUserMenu_native:lineintersections', 0, 1],
            ['mProcessingUserMenu_native:meancoordinates', 0, 2],
            ['mProcessingUserMenu_native:nearestneighbouranalysis', 0, 3],
            ['mProcessingUserMenu_native:sumlinelengths', 1, 0],
            ['mProcessingUserMenu_qgis:basicstatisticsforfields', 1, 1],
            ['mProcessingUserMenu_qgis:distancematrix', 1, 2],
            ['mProcessingUserMenu_qgis:listuniquevalues', 1, 3],
        ],
    },

    {
        'label': tr('Research Tools'),
        'id': 'Research Tools',
        'btn_size': 30,
        'btns': [
            ['mProcessingUserMenu_native:creategrid', 0, 0],
            ['mProcessingUserMenu_native:polygonfromlayerextent', 0, 1],
            ['mProcessingUserMenu_native:randompointsinextent', 0, 2],
            ['mProcessingUserMenu_native:randompointsinpolygons', 0, 3],
            ['mProcessingUserMenu_native:randompointsonlines', 0, 4],
            ['mProcessingUserMenu_native:selectbylocation', 0, 5],
            ['mProcessingUserMenu_qgis:randompointsinlayerbounds', 1, 0],
            ['mProcessingUserMenu_qgis:randompointsinsidepolygons', 1, 1],
            ['mProcessingUserMenu_qgis:randomselection', 1, 2],
            ['mProcessingUserMenu_qgis:randomselectionwithinsubsets', 1, 3],
            ['mProcessingUserMenu_qgis:regularpoints', 1, 4],
        ],
    },

    {
        'label': tr('Data Management Tools'),
        'id': 'Data Management Tools',
        'btn_size': 30,
        'btns': [
            ['mProcessingUserMenu_native:createspatialindex', 0, 0],
            ['mProcessingUserMenu_native:joinattributesbylocation', 0, 1],
            ['mProcessingUserMenu_native:mergevectorlayers', 0, 2],
            ['mProcessingUserMenu_native:reprojectlayer', 1, 0],
            ['mProcessingUserMenu_native:splitvectorlayer', 1, 1],
        ],
    },

    {
        'label': tr('Raster'),
        'id': 'Raster',
        'btn_size': 30,
        'btns': [
            ['mActionShowRasterCalculator', 0, 0],
            ['mActionShowGeoreferencer', 0, 1],
            ['mActionShowAlignRasterTool', 0, 2],
        ],
    },

    {
        'label': tr('Raster analysis'),
        'id': 'Raster analysis',
        'btn_size': 30,
        'btns': [
            ['mProcessingUserMenu_gdal:aspect', 0, 0],
            ['mProcessingUserMenu_gdal:fillnodata', 0, 1],
            ['mProcessingUserMenu_gdal:gridaverage', 0, 2],
            ['mProcessingUserMenu_gdal:griddatametrics', 0, 3],
            ['mProcessingUserMenu_gdal:gridinversedistance', 0, 4],
            ['mProcessingUserMenu_gdal:gridnearestneighbor', 0, 5],
            ['mProcessingUserMenu_gdal:hillshade', 0, 6],
            ['mProcessingUserMenu_gdal:nearblack', 1, 0],
            ['mProcessingUserMenu_gdal:proximity', 1, 1],
            ['mProcessingUserMenu_gdal:roughness', 1, 2],
            ['mProcessingUserMenu_gdal:sieve', 1, 3],
            ['mProcessingUserMenu_gdal:slope', 1, 4],
            ['mProcessingUserMenu_gdal:tpitopographicpositionindex', 1, 5],
            ['mProcessingUserMenu_gdal:triterrainruggednessindex', 1, 6],
        ],
    },

    {
        'label': tr('Projections'),
        'id': 'Projections',
        'btn_size': 60,
        'btns': [
            ['mProcessingUserMenu_gdal:warpreproject', 0, 0],
            ['mProcessingUserMenu_gdal:assignprojection', 0, 1],
            ['mProcessingUserMenu_gdal:extractprojection', 0, 2],
        ],
    },

    {
        'label': tr('Miscellaneous'),
        'id': 'Miscellaneous',
        'btn_size': 30,
        'btns': [
            ['mProcessingUserMenu_gdal:buildvirtualraster', 0, 0],
            ['mProcessingUserMenu_gdal:gdalinfo', 0, 1],
            ['mProcessingUserMenu_gdal:merge', 0, 2],
            ['mProcessingUserMenu_gdal:overviews', 1, 0],
            ['mProcessingUserMenu_gdal:tileindex', 1, 1],
        ],
    },

    {
        'label': tr('Extract Projection'),
        'id': 'Extract Projection',
        'btn_size': 30,
        'btns': [
            ['mProcessingUserMenu_gdal:cliprasterbyextent', 0, 0],
            ['mProcessingUserMenu_gdal:cliprasterbymasklayer', 0, 1],
            ['mProcessingUserMenu_gdal:contour', 1, 0],
        ],
    },

    {
        'label': tr('Conversion'),
        'id': 'Conversion',
        'btn_size': 30,
        'btns': [
            ['mProcessingUserMenu_gdal:pcttorgb', 0, 0],
            ['mProcessingUserMenu_gdal:rgbtopct', 0, 1],
            ['mProcessingUserMenu_gdal:polygonize', 0, 1],
            ['mProcessingUserMenu_gdal:rasterize', 1, 0],
            ['mProcessingUserMenu_gdal:translate', 1, 1],
        ],
    },

    {
        'label': tr('Data base'),
        'id': 'Data base',
        'btn_size': 30,
        'btns': [
            ['dbManager', 0, 0],
        ],
    },
    {
        'label': tr('Digitizing'),
        'id': 'Digitizing',
        'btn_size': 30,
        'btns': [
            ['mActionAllEdits', 0, 0],
            ['mActionToggleEditing', 0, 1],
            ['mActionSaveLayerEdits', 0, 2],
            ['mActionAddFeature', 0, 3],
            ['mActionVertexTool', 0, 4],
            ['mActionMultiEditAttributes', 0, 5],
            ['mActionMultiEditAttributes', 1, 0],
            ['mActionDeleteSelected', 1, 1],
            ['mActionCutFeatures', 1, 2],
            ['mActionCopyFeatures', 1, 3],
            ['mActionPasteFeatures', 1, 4],
            ['mActionCopyFeatures', 1, 5],
            ['mActionUndo', 0, 6],
            ['mActionRedo', 1, 6]
        ],
    },
    {
        'label': tr('Selection'),
        'id': 'Selection',
        'btn_size': 30,
        'btns': [
            ['mActionSelectFeatures', 0, 0],
            ['mActionSelectFreehand', 0, 1],
            ['mActionSelectPolygon', 1, 0],
            ['mActionSelectRadius', 1, 1],
            ['qgis:selectbyattribute', 0, 2],
            ['qgis:selectbyexpression', 0, 3],
            ['mActionSelectAll', 1, 2],
            ['mActionInvertSelection', 1, 3],
            ['mActionDeselectAll', 0, 4],
            ['mActionDeselectActiveLayer', 1, 4],
            ['mProcessingAlg_native:selectbylocation', 1, 5],
        ],
    },
    {
        'label': tr('Help'),
        'id': 'Help',
        'btn_size': 30,
        'btns': [
            ['mActionHelpContents', 0, 0],
        ],
    },
    {
        'label': tr('Plugins'),
        'id': 'Plugins',
        'btn_size': 30,
        'btns': [
            ['mActionShowPythonDialog', 0, 0]
        ],
    },
    {
        'label': tr('Data Source Manager'),
        'id': 'Data Source Manager',
        'btn_size': 30,
        'btns': [
            ['mActionDataSourceManager', 0, 0],
            ['mActionNewGeoPackageLayer', 0, 1],
            ['mActionNewVectorLayer', 0, 2],
            ['mActionNewSpatiaLiteLayer', 1, 0],
            ['mActionNewMemoryLayer', 1, 1],
            ['mActionNewVirtualLayer', 1, 2]
        ],
    },
    {
        'label': tr('Advanced digitizing tools'),
        'id': 'Advanced digitizing tools',
        'btn_size': 30,
        'btns': [
            ['mActionDigitizeWithCurve', 0, 0],
            ['mEnableAction', 0, 1],
            ['mActionMoveFeature', 0, 2],
            ['mActionMoveFeatureCopy', 0, 3],
            ['mActionRotateFeature', 0, 4],
            ['mActionSimplifyFeature', 0, 5],
            ['mActionAddRing', 0, 6],
            ['mActionAddPart', 0, 7],
            ['mActionFillRing', 0, 8],
            ['mActionDeleteRing', 0, 9],
            ['mActionDeletePart', 0, 10],
            ['mActionAddRing', 1, 0],
            ['mActionAddPart', 1, 1],
            ['mActionReshapeFeatures', 1, 2],
            ['mActionOffsetCurve', 1, 3],
            ['mActionReverseLine', 1, 4],
            ['mActionTrimExtendFeature', 1, 5],
            ['mActionSplitFeatures', 1, 6],
            ['mActionSplitParts', 1, 7],
            ['mActionMergeFeatures', 1, 8],
            ['mActionMergeFeatureAttributes', 1, 9],
            ['mActionRotatePointSymbols', 1, 10]
        ],
    },

]

STANDARD_QGIS_TOOLS = [
    {
        "label": tr("Project "),
        "id": "qgisProject",
        "btn_size": 30,
        "btns": [
            ['mActionNewProject', 0, 0],
            ['mActionOpenProject', 0, 1],
            ['mActionSaveProject', 1, 0],
            ['mActionNewPrintLayout', 1, 1],
            ['mActionShowLayoutManager', 0, 2],
            ['mActionStyleManager', 1, 2]
        ]
    },
    {
        "label": tr("Attributes "),
        "id": "qgisAttributes",
        "btn_size": 30,
        "btns": [
            ['mActionIdentify', 0, 0],
            ['mActionOpenTable', 1, 0],
            ['mActionOpenFieldCalc', 0, 1],
            ['mActionStatisticalSummary', 1, 1],
            ['mActionMeasure', 0, 2],
            ['mActionMeasureArea', 1, 2],
            ['mActionMeasureAngle', 0, 3],
            ['mActionMapTips', 1, 3],
            ['mActionTextAnnotation', 0, 4],
            ['mActionFormAnnotation', 1, 4],
            ['mActionHtmlAnnotation', 0, 5],
            ['mActionSvgAnnotation', 1, 5],
            ['mActionAnnotation', 0, 6],
            ['toolboxAction', 1, 6],
        ]
    },
    {
        "label": tr("Map Navigation "),
        "id": "qgisNavigation",
        "btn_size": 30,
        "btns": [
            ['mActionPan', 0, 0],
            ['mActionPanToSelected', 1, 0],
            ['mActionZoomIn', 0, 1],
            ['mActionZoomOut', 1, 1],
            ['mActionZoomFullExtent', 0, 2],
            ['mActionZoomToSelected', 1, 2],
            ['mActionZoomToLayer', 0, 3],
            ['mActionZoomActualSize', 1, 3],
            ['mActionZoomLast', 0, 4],
            ['mActionZoomNext', 1, 4],
            ['mActionNewMapCanvas', 0, 5],
            ['mActionNew3DMapCanvas', 1, 5],
            ['mActionNewBookmark', 0, 6],
            ['mActionShowBookmarks', 1, 6],
            ['mActionTemporalController', 0, 7],
            ['mActionDraw', 1, 7],
        ]
    },
    {
        "label": tr("Manage Layers "),
        "id": "qgisLayers",
        "btn_size": 30,
        "btns": [
            ['mActionAddOgrLayer', 0, 0],
            ['mActionAddRasterLayer', 1, 0],
            ['mActionAddMeshLayer', 0, 1],
            ['mActionAddDelimitedText', 1, 1],
            ['mActionAddSpatiaLiteLayer', 0, 2],
            ['mActionAddVirtualLayer', 1, 2],
            ['mActionAddPgLayer', 0, 3],
            ['mActionAddMssqlLayer', 1, 3],
            ['mActionAddDb2Layer', 0, 4],
            ['mActionAddOracleLayer', 1, 4],
            ['mActionAddWmsLayer', 0, 5],
            ['mActionAddAmsLayer', 1, 5],
            ['mActionAddWfsLayer', 0, 6],
            ['mActionAddAfsLayer', 1, 6],
            ['mActionNewVectorLayer', 0, 7],
            ['mActionNewSpatiaLiteLayer', 1, 7],
            ['mActionNewGeoPackageLayer', 0, 8],
            ['mActionNewMemoryLayer', 1, 8],
        ]
    },
    {
        "label": tr("Selection "),
        "id": "qgisSelection",
        "btn_size": 30,
        "btns": [
            ['mActionSelectFeatures', 0, 0],
            ['mActionSelectFreehand', 1, 0],
            ['mActionSelectPolygon', 0, 1],
            ['mActionSelectRadius', 1, 1],
            ['mActionSelectByForm', 0, 2],
            ['mActionSelectByExpression', 1, 2],
            ['mActionSelectAll', 0, 3],
            ['mActionInvertSelection', 1, 3],
            ['mActionDeselectAll', 0, 4],
            ['mActionDeselectActiveLayer', 1, 4],
            ['mProcessingAlg_native:selectbylocation', 0, 5],
        ]
    },
    {
        'label': tr('Annotations'),
        'id': 'Annotations',
        'btn_size': 30,
        'btns': [
            ['mActionCreateAnnotationLayer', 0, 0],
            ['mMainAnnotationLayerProperties', 0, 1],
            ['mActionModifyAnnotation', 0, 2],
            ['mAnnotationsToolBar_1_action', 0, 3],
            ['mAnnotationsToolBar_2_action', 0, 4],
            ['mAnnotationsToolBar_3_action', 0, 5],
            ['mAnnotationsToolBar_4_action', 1, 0],
            ['mActionTextAnnotation', 1, 1],
            ['mActionFormAnnotation', 1, 2],
            ['mActionHtmlAnnotation', 1, 3],
            ['mActionSvgAnnotation', 1, 4],
            ['mActionAnnotation', 1, 5],

        ]
    },
    {
        'label': tr('Mesh digitizing'),
        'id': 'MeshDigitizing',
        'btn_size': 30,
        'btns': [
            ['mMeshToolBar_0_action', 0, 0],
            ['ActionMeshSelectByPolygon', 0, 1],
            ['ActionMeshSelectByExpression', 0, 2],
            ['mMeshToolBar_1_action', 1, 0],
            ['mMeshToolBar_1_menu', 1, 1],
        ]
    },

]

DEFAULT_STYLE = "GIAP Navy Blue"
DEFAULT_TABS = ['Main tools', 'Advanced tools', 'Vector', 'Raster']
GIAP_CUSTOM_TOOLS = ['GIAP Tools', 'Vector digitization', 'Measurement',
                     'Project', 'Attributes', 'Advanced attributes',
                     'Selection', 'Navigation', 'Add Layer', 'Create Layer',
                     'Prints', 'Extras']
TOOLS_HEADERS = [
    'Sections',
    'GIAP sections',
    'User sections'
]
TOOL_LIST = [
    'mProcessingUserMenu_native_buffer',
    'mProcessingUserMenu_native_centroids',
    'mProcessingUserMenu_native_clip',
    'mProcessingUserMenu_native_collect',
    'mProcessingUserMenu_native_convexhull',
    'mProcessingUserMenu_native_countpointsinpolygon',
    'mProcessingUserMenu_native_creategrid',
    'mProcessingUserMenu_native_difference',
    'mProcessingUserMenu_native_extractvertices',
    'mProcessingUserMenu_native_intersection',
    'mProcessingUserMenu_native_lineintersections',
    'mProcessingUserMenu_native_meancoordinates',
    'mProcessingUserMenu_native_multiparttosingleparts',
    'mProcessingUserMenu_native_nearestneighbouranalysis',
    'mProcessingUserMenu_native_polygonfromlayerextent',
    'mProcessingUserMenu_native_polygonstolines',
    'mProcessingUserMenu_native_randompointsinextent',
    'mProcessingUserMenu_native_simplifygeometries',
    'mProcessingUserMenu_native_sumlinelengths',
    'mProcessingUserMenu_native_symmetricaldifference',
    'mProcessingUserMenu_native_union',
    'mProcessingUserMenu_qgis_basicstatisticsforfields',
    'mProcessingUserMenu_qgis_checkvalidity',
    'mProcessingUserMenu_qgis_delaunaytriangulation',
    'mProcessingUserMenu_qgis_distancematrix',
    'mProcessingUserMenu_qgis_eliminateselectedpolygons',
    'mProcessingUserMenu_qgis_exportaddgeometrycolumns',
    'mProcessingUserMenu_qgis_linestopolygons',
    'mProcessingUserMenu_qgis_listuniquevalues',
    'mProcessingUserMenu_qgis_randompointsinsidepolygons',
    'mProcessingUserMenu_qgis_regularpoints',
    'mProcessingUserMenu_qgis_voronoipolygons',
    'mProcessingUserMenu_native_dissolve',
    'mProcessingUserMenu_qgis_randompointsinlayerbounds',
    'mProcessingUserMenu_native_densifygeometries',
    'mProcessingUserMenu_gdal_aspect',
    'mProcessingUserMenu_gdal_fillnodata',
    'mProcessingUserMenu_gdal_gridaverage',
    'mProcessingUserMenu_gdal_griddatametrics',
    'mProcessingUserMenu_gdal_gridinversedistance',
    'mProcessingUserMenu_gdal_gridnearestneighbor',
    'mProcessingUserMenu_gdal_hillshade',
    'mProcessingUserMenu_gdal_roughness',
    'mProcessingUserMenu_gdal_slope',
    'mProcessingUserMenu_gdal_tpitopographicpositionindex',
    'mProcessingUserMenu_gdal_triterrainruggednessindex',
    'mProcessingUserMenu_native_createspatialindex',
    'mProcessingUserMenu_native_joinattributesbylocation',
    'mProcessingUserMenu_native_reprojectlayer',

    'mActionZoomTo', 'mActionZoomOut', 'mActionZoomToSelected',
    'mActionZoomToLayer', 'mActionZoomToBookmark',
    'mActionZoomToArea', 'mActionZoomNext', 'mActionZoomLast',
    'mActionZoomIn', 'mActionZoomFullExtent',
    'mActionZoomActual', 'mActionWhatsThis',
    'mActionViewScaleInCanvas', 'mActionViewExtentInCanvas',
    'mActionVertexToolActiveLayer', 'mActionVertexTool',
    'mActionUnlockAll', 'mActionUnlink',
    'mActionUngroupItems', 'mActionUndo', 'mActionTrimExtendFeature',
    'mActionTracing', 'mActionTouch',
    'mActionToggleSelectedLayers', 'mActionToggleEditing',
    'mActionToggleAllLayers', 'mActionTiltUp',
    'mActionTiltDown', 'mActionTextAnnotation', 'mActionTerminal',
    'mActionSvgAnnotation', 'mActionSum',
    'mActionStyleManager', 'mActionStreamingDigitize', 'mActionStop',
    'mActionStart', 'mActionSimplify',
    'mActionShowUnplacedLabel', 'mActionShowSelectedLayers',
    'mActionShowPluginManager',
    'mActionShowPinnedLabels', 'mActionShowMeshCalculator',
    'mActionShowHideLabels', 'mActionShowBookmarks',
    'mActionShowAllLayersGray', 'mActionSharingImport',
    'mActionSharingExport', 'mActionSharing',
    'mActionSetToCanvasScale', 'mActionSplitParts',
    'mActionSetToCanvasEtent', 'mActionSetProjection',
    'mActionSelectRectangle', 'mActionSelectRadius',
    'mActionSelectPolygon', 'mActionSelectPan',
    'mActionShowAllLayers', 'mACtionSelectFreehand',
    'mActionSelectedToTop', 'mActionSelectAllTree',
    'mActionSelectAll', 'mActionSelect', 'mActionScriptOpen',
    'mActionScaleHighlightFeature',
    'mActionScaleFeature', 'mActionScaleBar', 'mActionSaveMapAsImage',
    'mActionSaveEdits', 'mActionSaveAsSVG',
    'mActionSaveAsPython', 'mActionSaveAsPDF', 'mActionSplitFeatures',
    'mActionSaveAllEdits',
    'mActionRotatePointSymbols', 'mActionRotateFeature',
    'mActionRollbackEdits', 'mActionRollbackAllEdits',
    'mActionReverseLine', 'mActionResizeWidest',
    'mActionResizeTallest', 'mActionResizeSquare',
    'mActionResizeShortest', 'mActionResizeNarrowest',
    'mActionReshape', 'mActionRemoveSelectedFeature',
    'mActionRemoveLayer', 'mActionRemoveAllFromOverview',
    'mActionRemove', 'mActionReload',
    'mActionRegularPolygonCenterPoint',
    'mActionRegularPolygonCenterCorner',
    'mActionRegularPolygon2Points',
    'mActionRefresh', 'mActionRedo', 'mActionRectangleExtent',
    'mActionRectangleCenter',
    'mActionRectangle3PointsProjected',
    'mActionRectangle3PointsDistance', 'mActionRecord',
    'mActionRaiseItems', 'mActionPropertyItem',
    'mActionPropertiesWidget', 'mActionProjectProperties',
    'mActionProcessSelected', 'mActionPrevious', 'mActionPlay',
    'mActionPinLabels', 'mActionRotateLabel',
    'mActionPanToSelected', 'mActionPanTo',
    'mActionPanHighlightFeature', 'mActionOptions',
    'mActionOpenTableVisible', 'mActionOpenTableSelected',
    'mActionOpenTableEdited', 'mActionOpenTable',
    'mActionOffsetPointSymbols', 'mActionOffsetCurve', 'mActionNext',
    'mActionNewVirtualLayer',
    'mActionNewVectorLayer', 'mActionNewTableRow',
    'mActionNewSpatiaLiteLayer', 'mActionNewReport',
    'mActionNewPage', 'mActionNewMeshLayer', 'mActionNewMap',
    'mActionNewLayout', 'mActionNewGeoPackageLayer',
    'mActionNewFolder', 'mActionNewComposer', 'mActionNewBookmark',
    'mActionNewAttribute',
    'mActionNew3DMap', 'mActionMultiEdit', 'mActionMoveVertex',
    'mActionMoveLabel', 'mActionMoveItemsToTop',
    'mActionMoveItemsToBottom', 'mActionMoveItemContent',
    'mActionMoveFeaturePoint',
    'mActionMoveFeatureLine', 'mActionMoveFeatureCopyLine',
    'mActionMoveFeatureCopyPoint',
    'mActionMoveFeatureCopy', 'mActionMoveFeature',
    'mActionMeshDigitizing', 'mActionMeshDigitizing',
    'mActionMergeFeatures', 'mActionMergeFeaturesAttributes',
    'mActionMeasureBearing',
    'mActionMeasureArea', 'mActionMeasureAngle', 'mActionMapTips',
    'mActionMapSettings',
    'mActionMapIdentification', 'mActionLowerItems', 'mActionFeature',
    'mActionLockItems',
    'mActionLockExtent', 'mActionLocalHistogramStretch',
    'mActionLocalCumulativeCutStretch',
    'mActionLink', 'mActionLayoutManager', 'mActionLast',
    'mActionLabeling', 'mActionLabelAnchorStart',
    'mActionLabelAnchorEnd', 'mActionLabelAnchorCustom',
    'mActionLabelAnchorCenter', 'mActionLabel',
    'mActionKeyboardShortcuts', 'mActionInvertSelection',
    'mActionInterfaceCustomization',
    'mActionInOverview', 'mActionIncreaseGamma', 'mActionIncreaseFont',
    'mActionIncreaseContrast',
    'mActionIncreaseBrightness', 'mActionIdentifyByRectangle',
    'mActionIdentifyByRadius',
    'mActionIdentifyByPolygon',
    'mActionIdentifyByFreehand', 'mActionIdentify', 'mActionIconView',
    'mActionHtmlAnnotation',
    'mActionHistory', 'mActionHighlightFeature',
    'mActionHideSelectedLayers',
    'mActionHideDeselectedLayers', 'mActionHideAllLayers',
    'mActionHelpContents',
    'mActionHelpAbout', 'mActionHandleStoreFilterExpressionUnchecked',
    'mActionHandleStoreFilterExpressionChecked',
    'mActionGroupItems', 'mActionFullHistogramStretch',
    'mActionFullCumulativeCutStretch',
    'mActionFromSelectedFeature', 'mActionFromLargestFeature',
    'mActionFormView', 'mActionFormAnnotation',
    'mActionFolder', 'mActionFirst', 'mActionFindReplace',
    'mActionFilterTableFields', 'mActionFilter2',
    'mActionFilter', 'mActionFillRing', 'mActionFileSaveAs',
    'mActionFileSave', 'mActionFilePrint',
    'mActionFileNew', 'mActionFileExit', 'mActionExport',
    'mActionExpandTree', 'mActionExpandNewTree',
    'mActionEllipseExtent', 'mActionEllipseCenterPoint',
    'mActionEllipseCenter2Points',
    'mActionEditTable', 'mActionEditPaste', 'mActionEditNodesItem',
    'mActionEditModelComponent',
    'mActionEditHtml', 'mActionEditHelpContent', 'mActionEditCut',
    'mActionEditCopy', 'mActionDuplicateLayout',
    'mActionDuplicateLayer', 'mActionDuplicateFeatureDigitized',
    'mActionDuplicateFeature',
    'mActionDuplicateComposer', 'mActionDoubleArrowRight',
    'mActionDoubleArrowLeft', 'mActionDistributeVSpace',
    'mActionDistributeVCenter', 'mActionDistributeTop',
    'mActionDistributeRight', 'mActionDistributeLeft',
    'mActionDistributeHSpace', 'mActionDistributeHCenter',
    'mActionDistributeBottom',
    'mActionDigitizeWithCurve',
    'mActionDeselectAllTree', 'mActionDeselectAll',
    'mActionDeselectActiveLayer', 'mActionDeleteTable',
    'mActionDeleteSelectedFeatures', 'mActionDeleteSelected',
    'mActionDeleteRing', 'mActionDeletePart',
    'mActionDeleteModelComponent', 'mActionDeleteAttribute',
    'mActionDecreaseGamma', 'mActionDecreaseFont',
    'mActionDecreaseContrast', 'mActionDecreaseBrightness',
    'mActionDataSourceManager',
    'mActionCustomProjection',
    'mActionCreateTable', 'mActionCreateMemory',
    'mActionConditionalFormatting', 'mActionComposerManager',
    'mActionCollapseTree', 'mActionCircularStringRadius',
    'mActionCircularStringCurvePoint',
    'mActionCircleExtent', 'mActionCircleCenterPoint',
    'mActionCircle3Tangents', 'mActionCircle3Points',
    'mActionCircle2TangentsPoint', 'mActionCircle2Points',
    'mActionChangeLabelProperties',
    'mActionCapturePoint', 'mActionCaptureLine', 'mActionCancelEdits',
    'mActionCancelAllEdits',
    'mActionCalculateField', 'mActionAvoidIntersetionsLayers',
    'mActionAvoidIntersectionsCurrentLayer',
    'mActionAtlasSettings', 'mActionAtlasPrev', 'mActionAtlasNext',
    'mActionAtlasLast', 'mActionAtlasFirst',
    'mActionArrowUp', 'mActionArrowRight', 'mActionArrowLeft',
    'mActionArrowDown', 'mActionAnnotation',
    'mActionAllowIntersections', 'mActionAllEdits',
    'mActionAlignVCenter', 'mActionAlignTop',
    'mActionAlignRight', 'mActionAlignLeft', 'mActionAlignHCenter',
    'mActionAlignBottom',
    'mActionAddTable', 'mActionAddPolyline', 'mActionAddPolygon',
    'mActionAddPointCloudLayer',
    'mActionAddNodesItem', 'mActionAddMssqlLayer',
    'mActionAddMeshLayer', 'mActionAddMarker',
    'mActionAddMap', 'mActionAddManualTable', 'mActionAddLegend',
    'mActionAddLayer', 'mActionAddImage',
    'mActionAddHtml', 'mActionAddHanaLayer', 'mActionAddGroup',
    'mActionAddPackageLayer',
    'mActionAddGeomodeLayer',
    'mActionAddExpression', 'mActionAddDelimitedTextLayer',
    'mActionAddDb2Layer', 'mActionAddBasicTriangle',
    'mActionAddBasicShape', 'mActionAddBasicRectangle',
    'mActionAddBasicCircle', 'mActionAddArrow',
    'mActionAddAmsLayer', 'mActionAddAllToOverview',
    'mActionAddAfsLayer', 'mActionAdd3DMap',
    'mActionAdd', 'mActionActive', 'mAction3DNavigation', 'mAction',
    'mActionMeasure', 'mActionPan',
    'mActionFileOpen', 'mActionAddWmsLayer', 'mActionAddWfsLayer',
    'mActionAddWcsLayer',
    'mActionAddVirtualLayer',
    'mActionAddSpatiaLiteLayer', 'mActionAddRing',
    'mActionAddRasterLayer', 'mActionAddPostgisLayer',
    'mActionAddPart', 'mActionAddOgrLayer',
    'mAlgorithmBasicStatistics', 'mActionStatisticalSummary',
    'mProcessingUserMenu_native_selectbylocation',
    'mProcessingUserMenu_qgis_randomselection',
    'native_fuzzifyrasterlinearmembership',
    'native_fuzzifyrastergaussianmembership',
    'native_fuzzifyrasterlargemembership',
    'native_fuzzifyrasternearmembership',
    'native_fuzzifyrasterpowermembership',
    'native_fuzzifyrastersmallmembership', 'native_cellstatistics',
    'qgis_concavehull',
    'native_createconstantrasterlayer', 'native_fillnodata',
    'native_linedensity',
    'native_serviceareafromlayer',
    'native_serviceareafrompoint',
    'native_shortestpathlayertopoint',
    'native_shortestpathpointtolayer',
    'native_shortestpathpointtopoint',
    'native_createrandomnormalrasterlayer',
    'native_createrandomexponentialrasterlayer',
    'native_createrandompoissonrasterlayer',
    'native_createrandomuniformrasterlayer',
    'native_createrandomgammarasterlayer',
    'native_roundrastervalues',
    'qgis_heatmapkerneldensityestimation',
    'mActionToggleAdvancedDigitizeToolBar',
    'dbManager',
    'mActionEllipseFoci', 'mActionOpenProject', 'mActionNewProject',
    'mActionSaveProject',
    'mActionSaveProjectAs', 'mActionCapturePolygon',
    'mActionSelectFeatures', 'mActionAddPgLayer',
    'mActionAddDelimitedText', 'mActionNewMemoryLayer',
    'mActionShowUnplacedLabels', 'mActionCutFeatures',
    'mActionPasteFeatures', 'mActionCopyFeatures',
    'EnableSnappingAction',
    'EnableTracingAction', 'mActionSimplifyFeature',
    'mActionReshapeFeatures',
    'mActionSelectByExpression',
    'mProcessingAlg_native_selectbylocation', 'mActionOpenFieldCalc',
    'mActionAddFeature', 'mActionSaveLayerEdits',
    'mActionShowLayoutManager', 'mActionAddOracleLayer',
    'mActionNewPrintLayout', 'qgis_selectbyattribute',
    'mMainAnnotationLayerProperties',
]

custom_icon_dict = {
    'giapWMS': 'orto_icon2.png',
    'giapCompositions': 'compositions_giap.png',
    "giapQuickPrint": 'quick_print.png',
    "giapMyPrints": 'my_prints.png',
    "giapAreaLength": 'measuring.png',
    'mActionShowAlignRasterTool': 'mActionShowAlignRasterTool.png',
    'mActionNewMemoryLayer': 'mActionNewMemoryLayer.png',
    'mActionSaveProjectAs': 'mActionSaveProjectAs.png',
    'window_icon': 'giap_logo.png',
    'giapPRNG': 'giapPRNG.png',
    'giapGeoportal': 'giapGeoportal.png',
    'giapOrtoContr': 'giapOrtoContr.png',
    'giapgeokodowanie': 'giapgeokodowanie.png',
}

custom_label_dict = {
    'giapWMS': "Add WMS/WMTS services",
    'giapCompositions': "Composition settings",
    "giapQuickPrint": "Map quick print",
    "giapMyPrints": "My Prints",
    "giapAreaLength": 'Area and length',
    'giapPRNG': 'PRNG Tool',
    'giapGeoportal': 'Geoportal',
    'giapOrtoContr': 'Ortofotomapa archiwalna',
    "giapgeokodowanie": 'geokodowanie',
}

max_ele_nazwy = 4


def icon_manager(tool_list: List[str], main_qgs_widget: QObject = None) -> \
        Dict[str, Union[Optional[QIcon], Any]]:
    dirnm = normalize_path(os.path.join(os.path.dirname(__file__), 'icons'))
    icon_dict = {}
    for tool in tool_list:
        icon = None
        action = None
        alg = QgsApplication.processingRegistry().algorithmById(tool)
        if main_qgs_widget:
            action = main_qgs_widget.findChild(QAction, tool)
        if alg:
            icon = alg.icon()
        elif action:
            icon = action.icon()
        elif 'mProcessing' in tool:
            tool = tool.replace(':', '_')
        if tool in TOOL_LIST and not icon:
            icon = QIcon(os.path.join(dirnm, f'{tool}.png'))
        if tool in custom_icon_dict.keys():
            icon = QIcon(os.path.join(dirnm, custom_icon_dict[tool]))
        icon_dict[tool] = icon
    return icon_dict


def get_tool_label(tool: str, main_qgs_widget: QObject = None) -> str:
    label = tool
    if main_qgs_widget.findChild(QAction, tool):
        label = main_qgs_widget.findChild(QAction, tool).text()
    if tool in custom_label_dict.keys():
        label = custom_label_dict[tool]
    if len(label) < 2:
        label = tool
    for char in ('&', '~', '`'):
        label = label.replace(char, '')
    return label


def add_map_layer_to_group(
        layer: Union[QgsVectorLayer, QgsMapLayer],
        group_name: str, main_group_name:
        str = None, important: bool = False, position: int = 0,
        force_create: bool = False):
    if not layer.isValid():
        QgsMessageLog.logMessage(
            f'Warstwa nieprawidłowa {layer.name()}. Wymagana interwencja.',
            "GIAP - PolaMap Lite",
            Qgis.Info)
    if main_group_name and root.findGroup(main_group_name):
        group = root.findGroup(main_group_name).findGroup(group_name)
    else:
        group = root.findGroup(group_name)
    if not group:
        if force_create:
            group = root.addGroup(group_name)
        else:
            project.addMapLayer(layer)
            return
    project.addMapLayer(layer, False)
    if group_name:
        group.insertLayer(position, layer)


def find_widget_with_menu_in_toolbar(toolbar: QToolBar) -> List[QToolButton]:
    lista_widgets = toolbar.children()
    qmenu_list = []
    for widget in lista_widgets:
        if isinstance(widget, QToolButton):
            if widget.popupMode():
                qmenu_list.append(widget)
    return qmenu_list


def get_action_from_toolbar(toolbar: QToolBar) -> List[QAction]:
    lista_widgets = toolbar.children()
    act_list = []
    for widget in lista_widgets:
        if isinstance(widget, QToolButton):
            if not widget.popupMode() and widget.actions():
                act_list.append(widget.actions()[0])
    return act_list


def add_action_from_toolbar(iface: iface, sec, btn: list) -> None:
    if iface.mainWindow().findChild(QToolBar, btn[0].split('_')[0]):
        dlu = len(btn[0].split('_'))
        if dlu == max_ele_nazwy:
            objname_toolbar, ind, typ, ind_menu = btn[0].split('_')
        else:
            objname_toolbar, ind, typ = btn[0].split('_')

        toolbar = iface.mainWindow().findChild(QToolBar, objname_toolbar)
        if typ == "action":
            action = get_action_from_toolbar(toolbar) \
                [int(ind)]
            action.setObjectName(btn[0])
            sec.add_action(get_action_from_toolbar(toolbar)
                           [int(ind)], btn[1], btn[2])
        if typ == "menu":
            widgs = find_widget_with_menu_in_toolbar(toolbar)
            widg = widgs[int(ind)]

            if dlu == max_ele_nazwy:
                if widg.menu():
                    # Wyciąganie i dodawanie pojdeynczej akcji z menu
                    sel_act_from_menu = widg.menu().actions()[int(ind_menu)]
                    objname = sel_act_from_menu.objectName()
                    sel_act_from_menu.setObjectName(btn[0])
                    sec.add_action(sel_act_from_menu, btn[1], btn[2])
                    sel_act_from_menu.setObjectName(objname)
                else:
                    # Dodawanie wybranej akcji
                    sel_act = widg.actions()[int(ind_menu)]
                    objname = sel_act.objectName()
                    sel_act.setObjectName(btn[0])
                    sec.add_action(sel_act, btn[1], btn[2])
                    sel_act.setObjectName(objname)
            else:
                # Dodawanie menu i domyślnej akcji
                objname = widg.defaultAction().objectName()
                widg.defaultAction().setObjectName(btn[0])
                sec.add_action(widg.defaultAction(), btn[1], btn[2],
                               widg.menu())
                widg.defaultAction().setObjectName(objname)
