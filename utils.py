from typing import List, Any

from PyQt5.QtCore import Qt
from qgis.PyQt import QtCore, QtGui
from qgis.PyQt.QtCore import QThread
from qgis.PyQt.QtGui import QPen, QBrush
from qgis.PyQt.QtWidgets import QApplication, QProgressDialog, \
    QStyledItemDelegate
from qgis.core import QgsProject, QgsMessageLog, Qgis

project = QgsProject.instance()


class SingletonModel:
    __instance = None

    def __new__(cls, *args):
        if SingletonModel.__instance is None:
            QgsMessageLog.logMessage(f'CREATE OBJECT OF CLASS: {cls.__name__}',
                                     "giap_layout",
                                     Qgis.Info)
            SingletonModel.__instance = object.__new__(cls, *args)
        return SingletonModel.__instance


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
    """
    Identyfikuje warstwę gdy nie mamy jej pełnej nazwy.

    :param group_name: string
    :param layer_to_find: string, początek nazwy warstwy
    :return: QgsVectorLayer
    """
    for lr in project.layerTreeRoot().findLayers():
        if lr.parent().name() == group_name \
                and lr.name().startswith(layer_to_find):
            return lr.layer()


def set_project_config(parameter, key, value):
    if isinstance(project, QgsProject):
        return project.writeEntry(parameter, key, value)


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
            QtGui.QTextDocument(index.model().data(index)).idealWidth(), 30)

    def paint(self, painter, option, index):
        painter.save()
        painter.setPen(
            QPen(QBrush(Qt.black), 1, Qt.SolidLine, Qt.SquareCap,
                 Qt.BevelJoin))
        painter.setClipRect(option.rect)
        painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
        painter.setPen(QPen(Qt.black))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(option.rect, Qt.AlignCenter,
                         index.data(Qt.DisplayRole))
        painter.restore()


# oba poniższe słowniki powinny być spójne
WMS_SERVERS = {
    'ORTOFOTOMAPA - WMTS': 'contextualWMSLegend=0&crs=EPSG:2180&dpiMode=0&featureCount=10&format=image/jpeg&layers=ORTOFOTOMAPA&styles=default&tileMatrixSet=EPSG:2180&url=https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMTS/StandardResolution?service%3DWMTS%26request%3DgetCapabilities',
    'Wizualizacja BDOT10k - WMS': 'contextualWMSLegend=0&crs=EPSG:2180&dpiMode=7&featureCount=10&format=image/png8&layers=RZab&layers=TPrz&layers=SOd2&layers=SOd1&layers=GNu2&layers=GNu1&layers=TKa2&layers=TKa1&layers=TPi2&layers=TPi1&layers=UTrw&layers=TLes&layers=RKr&layers=RTr&layers=ku7&layers=ku6&layers=ku5&layers=ku4&layers=ku3&layers=ku2&layers=ku1&layers=Mo&layers=Szu&layers=Pl3&layers=Pl2&layers=Pl1&layers=kanOkr&layers=rzOk&layers=row&layers=kan&layers=rz&layers=RowEt&layers=kanEt&layers=rzEt&layers=WPow&layers=LBrzN&layers=LBrz&layers=WPowEt&layers=GrPol&layers=Rez&layers=GrPK&layers=GrPN&layers=GrDz&layers=GrGm&layers=GrPo&layers=GrWo&layers=GrPns&layers=PRur&layers=ZbTA&layers=BudCm&layers=TerCm&layers=BudSp&layers=Szkl&layers=Kap&layers=SwNch&layers=SwCh&layers=BudZr&layers=BudGo&layers=BudPWy&layers=BudP2&layers=BudP1&layers=BudUWy&layers=BudU&layers=BudMWy&layers=BudMJ&layers=BudMW&layers=Bzn&layers=BHydA&layers=BHydL&layers=wyk&layers=wa6&layers=wa5&layers=wa4&layers=wa3&layers=wa2&layers=wa1&layers=IUTA&layers=ObOrA&layers=ObPL&layers=Prom&layers=PomL&layers=MurH&layers=PerA&layers=PerL&layers=Tryb&layers=UTrL&layers=LTra&layers=LKNc&layers=LKBu&layers=LKWs&layers=TSt&layers=LKNelJ&layers=LKNelD&layers=LKNelW&layers=LKZelJ&layers=LKZelD&layers=LKZelW&layers=Scz&layers=Al&layers=AlEt&layers=Sch2&layers=Sch1&layers=DrDGr&layers=DrLGr&layers=JDrLNUt&layers=JDLNTw&layers=JDrZTw&layers=JDrG&layers=DrEk&layers=JDrEk&layers=AuBud&layers=JAu&layers=NazDr&layers=NrDr&layers=Umo&layers=PPdz&layers=Prze&layers=TunK&layers=TunD&layers=Klad&layers=MosK&layers=MosD&layers=UTrP&layers=ObKom&layers=InUTP&layers=ZbTP&layers=NazUl&layers=ObOrP&layers=WyBT&layers=LTel&layers=LEle&layers=ObPP&layers=DrzPomP&layers=e13&layers=e12&layers=e11&layers=e10&layers=e9&layers=e8&layers=e7&layers=e6&layers=e5&layers=e4&layers=e3&layers=e2&layers=e1&layers=s19&layers=s18&layers=s17&layers=s16&layers=s15&layers=s14&layers=s13&layers=s12&layers=s11&layers=s10&layers=s9&layers=s8&layers=s7&layers=s6&layers=s5&layers=s4&layers=s3&layers=s2&layers=s1&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&url=http://mapy.geoportal.gov.pl/wss/service/pub/guest/kompozycja_BDOT10k_WMS/MapServer/WMSServer',
    'Mapa topograficzna - WMTS': 'contextualWMSLegend=0&crs=EPSG:2180&dpiMode=7&featureCount=10&format=image/jpeg&layers=MAPA%20TOPOGRAFICZNA&styles=default&tileMatrixSet=EPSG:2180&url=http://mapy.geoportal.gov.pl/wss/service/WMTS/guest/wmts/TOPO?SERVICE%3DWMTS%26REQUEST%3DGetCapabilities',
    'Krajowa Integracja Ewidencji Gruntów - WMS': 'contextualWMSLegend=0&crs=EPSG:2180&dpiMode=7&featureCount=10&format=image/png&layers=dzialki&layers=geoportal&layers=powiaty&layers=ekw&layers=zsin&layers=obreby&layers=numery_dzialek&layers=budynki&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&url=http://integracja.gugik.gov.pl/cgi-bin/KrajowaIntegracjaEwidencjiGruntow',
    'Bank Danych o Lasach - WMS': 'contextualWMSLegend=0&crs=EPSG:2180&dpiMode=7&featureCount=10&format=image/jpeg&layers=0&layers=1&layers=2&layers=3&layers=4&layers=5&styles=&styles=&styles=&styles=&styles=&styles=&url=http://mapserver.bdl.lasy.gov.pl/ArcGIS/services/WMS_BDL/mapserver/WMSServer',
    'Wody Polskie - mapa zagrożenia powodziowego': 'contextualWMSLegend=0&crs=EPSG:2180&dpiMode=7&featureCount=10&format=image/png&layers=OSZP1m&layers=OSZP1&layers=OSZP10&styles=&styles=&styles=&url=http://integracja.gugik.gov.pl/cgi-bin/MapaZagrozeniaPowodziowego?',
    'Monitoring Warunków Glebowych': 'contextualWMSLegend=0&crs=EPSG:2180&dpiMode=7&featureCount=10&format=image/png&layers=smois_2021_07_03_12_00_00&layers=smois_2021_07_04_12_00_00&layers=smois_2021_07_05_12_00_00&layers=smois_2021_07_06_12_00_00&layers=smois_2021_07_07_12_00_00&layers=punkty&layers=wojewodztwa&styles&styles&styles&styles&styles&styles&styles&url=https://integracja.gugik.gov.pl/cgi-bin/MonitoringWarunkowGlebowych',
    'Uzbrojenie terenu': 'contextualWMSLegend=0&crs=EPSG:2180&dpiMode=7&featureCount=10&format=image/png&layers=gesut&layers=kgesut&layers=kgesut_dane&layers=przewod_elektroenergetyczny&layers=przewod_telekomunikacyjny&layers=przewod_wodociagowy&layers=przewod_kanalizacyjny&layers=przewod_gazowy&layers=przewod_cieplowniczy&layers=przewod_specjalny&layers=przewod_inny&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&url=http://integracja.gugik.gov.pl/cgi-bin/KrajowaIntegracjaUzbrojeniaTerenu?'
}

group_name = "WMS/WMTS"
WMS_SERVERS_GROUPS = {
    'ORTOFOTOMAPA - WMTS': group_name,
    'Wizualizacja BDOT10k - WMS': group_name,
    'Mapa topograficzna - WMTS': group_name,
    'Krajowa Integracja Ewidencji Gruntów - WMS': group_name,
    'Bank Danych o Lasach - WMS': group_name,
    'Wody Polskie - mapa zagrożenia powodziowego': group_name,
    'Monitoring Warunków Glebowych': group_name,
    'Uzbrojenie terenu': group_name
}

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
        'btn_size': 60,
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
]

DEFAULT_STYLE = "GIAP Navy Blue"
DEFAULT_TABS = ['Main tools', 'Advanced tools', 'Vector', 'Raster']
GIAP_CUSTOM_TOOLS = ['GIAP Tools', 'Vector digitization', 'Measurement',
                     'Project', 'Attributes', 'Advanced attributes',
                     'Selection', 'Navigation', 'Add Layer', 'Create Layer',
                     'Prints']
TOOLS_HEADERS = [
    'Sections',
    'GIAP sections',
    'User sections'
]
