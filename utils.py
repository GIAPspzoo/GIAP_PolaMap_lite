from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QApplication, QProgressDialog

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
        self.children()[0].setStyleSheet('''
            QLabel {
            background-color: rgb(53, 85, 109);
            color: rgb(255, 255, 255);
            font: 10pt "Segoe UI";
            }
        ''')

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


# oba poniższe słowniki powinny być spójne
WMS_SERVERS = {
    'ORTOFOTOMAPA - WMTS': 'contextualWMSLegend=0&crs=EPSG:2180&dpiMode=0&featureCount=10&format=image/jpeg&layers=ORTOFOTOMAPA&styles=default&tileMatrixSet=EPSG:2180&url=https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMTS/StandardResolution?service%3DWMTS%26request%3DgetCapabilities',
    'Wizualizacja BDOT10k - WMS': 'contextualWMSLegend=0&crs=EPSG:2180&dpiMode=7&featureCount=10&format=image/png8&layers=RZab&layers=TPrz&layers=SOd2&layers=SOd1&layers=GNu2&layers=GNu1&layers=TKa2&layers=TKa1&layers=TPi2&layers=TPi1&layers=UTrw&layers=TLes&layers=RKr&layers=RTr&layers=ku7&layers=ku6&layers=ku5&layers=ku4&layers=ku3&layers=ku2&layers=ku1&layers=Mo&layers=Szu&layers=Pl3&layers=Pl2&layers=Pl1&layers=kanOkr&layers=rzOk&layers=row&layers=kan&layers=rz&layers=RowEt&layers=kanEt&layers=rzEt&layers=WPow&layers=LBrzN&layers=LBrz&layers=WPowEt&layers=GrPol&layers=Rez&layers=GrPK&layers=GrPN&layers=GrDz&layers=GrGm&layers=GrPo&layers=GrWo&layers=GrPns&layers=PRur&layers=ZbTA&layers=BudCm&layers=TerCm&layers=BudSp&layers=Szkl&layers=Kap&layers=SwNch&layers=SwCh&layers=BudZr&layers=BudGo&layers=BudPWy&layers=BudP2&layers=BudP1&layers=BudUWy&layers=BudU&layers=BudMWy&layers=BudMJ&layers=BudMW&layers=Bzn&layers=BHydA&layers=BHydL&layers=wyk&layers=wa6&layers=wa5&layers=wa4&layers=wa3&layers=wa2&layers=wa1&layers=IUTA&layers=ObOrA&layers=ObPL&layers=Prom&layers=PomL&layers=MurH&layers=PerA&layers=PerL&layers=Tryb&layers=UTrL&layers=LTra&layers=LKNc&layers=LKBu&layers=LKWs&layers=TSt&layers=LKNelJ&layers=LKNelD&layers=LKNelW&layers=LKZelJ&layers=LKZelD&layers=LKZelW&layers=Scz&layers=Al&layers=AlEt&layers=Sch2&layers=Sch1&layers=DrDGr&layers=DrLGr&layers=JDrLNUt&layers=JDLNTw&layers=JDrZTw&layers=JDrG&layers=DrEk&layers=JDrEk&layers=AuBud&layers=JAu&layers=NazDr&layers=NrDr&layers=Umo&layers=PPdz&layers=Prze&layers=TunK&layers=TunD&layers=Klad&layers=MosK&layers=MosD&layers=UTrP&layers=ObKom&layers=InUTP&layers=ZbTP&layers=NazUl&layers=ObOrP&layers=WyBT&layers=LTel&layers=LEle&layers=ObPP&layers=DrzPomP&layers=e13&layers=e12&layers=e11&layers=e10&layers=e9&layers=e8&layers=e7&layers=e6&layers=e5&layers=e4&layers=e3&layers=e2&layers=e1&layers=s19&layers=s18&layers=s17&layers=s16&layers=s15&layers=s14&layers=s13&layers=s12&layers=s11&layers=s10&layers=s9&layers=s8&layers=s7&layers=s6&layers=s5&layers=s4&layers=s3&layers=s2&layers=s1&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&url=http://mapy.geoportal.gov.pl/wss/service/pub/guest/kompozycja_BDOT10k_WMS/MapServer/WMSServer',
    'Mapa topograficzna - WMTS': 'contextualWMSLegend=0&crs=EPSG:2180&dpiMode=7&featureCount=10&format=image/jpeg&layers=MAPA%20TOPOGRAFICZNA&styles=default&tileMatrixSet=EPSG:2180&url=http://mapy.geoportal.gov.pl/wss/service/WMTS/guest/wmts/TOPO?SERVICE%3DWMTS%26REQUEST%3DGetCapabilities',
    'Krajowa Integracja Ewidencji Gruntów - WMS': 'contextualWMSLegend=0&crs=EPSG:2180&dpiMode=7&featureCount=10&format=image/png&layers=dzialki&layers=geoportal&layers=powiaty&layers=ekw&layers=zsin&layers=obreby&layers=numery_dzialek&layers=budynki&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&url=http://integracja.gugik.gov.pl/cgi-bin/KrajowaIntegracjaEwidencjiGruntow',
    'Bank Danych o Lasach - WMS': 'contextualWMSLegend=0&crs=EPSG:2180&dpiMode=7&featureCount=10&format=image/jpeg&layers=0&layers=1&layers=2&layers=3&layers=4&layers=5&styles=&styles=&styles=&styles=&styles=&styles=&url=http://mapserver.bdl.lasy.gov.pl/ArcGIS/services/WMS_BDL/mapserver/WMSServer',
    'Wody Polskie - mapa zagrożenia powodziowego': 'contextualWMSLegend=0&crs=EPSG:2180&dpiMode=7&featureCount=10&format=image/png&layers=OSZP1m&layers=OSZP1&layers=OSZP10&styles=&styles=&styles=&url=http://integracja.gugik.gov.pl/cgi-bin/MapaZagrozeniaPowodziowego?',
    'Monitoring Warunków Glebowych': 'contextualWMSLegend=0&crs=EPSG:2180&dpiMode=7&featureCount=10&format=image/png&layers=smois_2019_10_28_12_00_00&layers=smois_2019_10_29_12_00_00&layers=smois_2019_10_30_12_00_00&layers=smois_2019_10_31_12_00_00&layers=smois_2019_11_01_12_00_00&layers=punkty&layers=wojewodztwa&styles=&styles=&styles=&styles=&styles=&styles=&styles=&url=http://integracja.gugik.gov.pl/cgi-bin/MonitoringWarunkowGlebowych?',
    'Uzbrojenie terenu': 'contextualWMSLegend=0&crs=EPSG:2180&dpiMode=7&featureCount=10&format=image/png&layers=gesut&layers=kgesut&layers=kgesut_dane&layers=przewod_elektroenergetyczny&layers=przewod_telekomunikacyjny&layers=przewod_wodociagowy&layers=przewod_kanalizacyjny&layers=przewod_gazowy&layers=przewod_cieplowniczy&layers=przewod_specjalny&layers=przewod_inny&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&styles=&url=http://integracja.gugik.gov.pl/cgi-bin/KrajowaIntegracjaUzbrojeniaTerenu?'
}


WMS_SERVERS_GROUPS = {
    'ORTOFOTOMAPA - WMTS': 'ORTOFOTOMAPA',
    'Wizualizacja BDOT10k - WMS': 'DANE DODATKOWE',
    'Mapa topograficzna - WMTS': 'DANE DODATKOWE',
    'Krajowa Integracja Ewidencji Gruntów - WMS': 'DANE DODATKOWE',
    'Bank Danych o Lasach - WMS': 'DANE DODATKOWE',
    'Wody Polskie - mapa zagrożenia powodziowego': 'DANE DODATKOWE',
    'Monitoring Warunków Glebowych': 'DANE DODATKOWE',
    'Uzbrojenie terenu': 'DANE DODATKOWE'
}

STANDARD_TOOLS = [
            {
                "label": "Project",
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
                "label": "Navigation",
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
                'label': 'Attributes',
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
                'label': 'Measures',
                'id': 'Measures',
                'btn_size': 60,
                'btns': [
                    ['mActionMeasure', 0, 0],
                    ['mActionMeasureArea', 0, 1],
                    ['mActionMeasureAngle', 0, 2],
                ],
            },

            {
                'label': 'Layers',
                'id': 'Layers',
                'btn_size': 30,
                'btns': [
                    ['mActionAddOgrLayer', 0, 0],
                    ['mActionAddWmsLayer', 0, 1],
                    ['mActionAddPgLayer', 0, 2],
                    ['mActionAddMeshLayer', 0, 3],
                    ['mActionAddWcsLayer', 0, 4],
                    ['mActionAddDelimitedText', 0, 5],

                    ['mActionAddRasterLayer', 1, 0],
                    ['mActionAddWfsLayer', 1, 1],
                    ['mActionAddSpatiaLiteLayer', 1, 2],
                    ['mActionAddVirtualLayer', 1, 3],
                    ['mActionNewMemoryLayer', 1, 4],
                ],
            },

            {
                'label': 'Adv. Attributes',
                'id': 'Adv. Attributes',
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
                'label': 'Labels',
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
                'label': 'Vector',
                'id': 'Vector',
                'btn_size': 30,
                'btns': [
                    ['mActionToggleEditing', 0, 0],
                    ['mActionSaveLayerEdits', 0, 1],
                    ['mActionVertexTool', 0, 2],
                    ['mActionUndo', 0, 3],
                    ['mActionRedo', 0, 4],

                    ['mActionAddFeature', 1, 0],
                    ['mActionMoveFeature', 1, 1],
                    ['mActionDeleteSelected', 1, 2],
                    ['mActionCutFeatures', 1, 3],
                    ['mActionCopyFeatures', 1, 4],
                    ['mActionPasteFeatures', 1, 5],
                ],
            },

            {
                'label': 'Digitalization',
                'id': 'Digitalization',
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
                'label': 'Prints',
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
                'label': 'GIAP Tools',
                'id': 'GIAP Tools',
                'btn_size': 60,
                'btns': [
                    ['giapCompositions', 0, 0],
                    ['giapWMS', 0, 1],
                    ['giapWWWSite', 0, 2],
                ]
            },


]
