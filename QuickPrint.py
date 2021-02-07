# -*- coding: utf-8 -*-
import os
import tempfile

from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QFileDialog, QApplication
from qgis._core import QgsLayoutExporter, QgsWkbTypes, QgsLayoutItemMap, \
    QgsLayout, QgsProject, QgsUnitTypes, QgsLayoutSize, QgsGeometry, \
    QgsVectorLayer, QgsFeature, QgsSymbol, QgsSimpleFillSymbolLayer, \
    QgsLayoutItemLegend, QgsLayerTreeGroup, QgsLegendStyle, QgsLayoutItem, \
    QgsLayoutItemLabel, QgsLayoutItemScaleBar
from qgis._gui import QgsRubberBand
from qgis.utils import iface

from .wydruk_dialog import WydrukDialog

def get_layer_with_selection():
    layer_with_selection = []
    for layer in list(QgsProject.instance().mapLayers().values()):
        if layer.type().value == 0 and layer.selectedFeatureCount():
            layer_with_selection.append(layer)
    return layer_with_selection

class PrintMapTool:
    dpi = 600
    mm_paper_sizes = {
        # '4A0': (1682, 2378),
        # '2A0': (1189, 1682),
        'A0': (841, 1189),
        'A1': (594, 841),
        'A2': (420, 594),
        'A3': (297, 420),
        'A4': (210, 297),
        'A5': (148, 210),
        # 'A6': (105, 148),
        # 'A7': (74, 105),
        # 'A8': (52, 74),
        # 'A9': (37, 52),
        # 'A10': (26, 37),
    }

    def __init__(self, iface, parent=None):
        self.iface = iface
        self.dialog = WydrukDialog()
        self.dialog.pdfRadioButton.setChecked(True)
        self.dialog.horizontalRadioButton.setChecked(True)
        self.dialog.verticalRadioButton.clicked.connect(self.create_composer)
        self.dialog.horizontalRadioButton.clicked.connect(self.create_composer)
        self.dialog.savePushButton.clicked.connect(self.save)
        self.dialog.previewPushButton.clicked.connect(self.preview)
        self.dialog.cancelPushButton.clicked.connect(self.dialog.reject)
        self.dialog.rejected.connect(self.rejected_dialog)
        self.dialog.legendCheckBox.hide()  # tymczasowe ukrycie opcji legendy
        paper_format_items = sorted(self.mm_paper_sizes.keys())
        self.dialog.paperFormatComboBox.addItems(paper_format_items)
        self.dialog.paperFormatComboBox.setCurrentIndex(
            paper_format_items.index("A4"))
        self.dialog.paperFormatComboBox.currentIndexChanged.connect(
            self.create_composer)
        self.setup_rubberband()

    def setup_rubberband(self):
        self.r = QgsRubberBand(iface.mapCanvas(), QgsWkbTypes.PolygonGeometry)
        self.r.setColor(QColor(255, 0, 0, 100))
        self.r.setWidth(5)
        self.r.setFillColor(QColor(255, 255, 255, 0))
        self.is_active = False

    def get_paper_size(self):
        paper_format = self.dialog.paperFormatComboBox.currentText()
        width, height = self.mm_paper_sizes[paper_format]

        if self.dialog.horizontalRadioButton.isChecked():
            return  height, width
        else:
            return width, height

    def get_map_item(self):
        item_object = None
        for item in self.layout.items():
            if isinstance(item, QgsLayoutItemMap):
                item_object = item
        return item_object

    def create_composer(self):
        self.reset_rubber()
        if self.is_active:
            self.layout = QgsLayout(QgsProject.instance())
            self.layout.initializeDefaults()
            self.layout.setUnits(QgsUnitTypes.LayoutMillimeters)
            page = self.layout.pageCollection().pages()[0]

            width, height = self.get_paper_size()
            x, y = 16, 16
            page.setPageSize(QgsLayoutSize(width, height))
            canvas_extent = self.iface.mapCanvas().extent()
            current_rect = QRectF(x,y,width - 2 * x, height - 2 * y)

            map_item = QgsLayoutItemMap(self.layout)
            map_item.updateBoundingRect()
            map_item.setRect(current_rect)
            map_item.setPos(x,y)
            map_item.setFrameEnabled(True)

            map_item.setLayers(QgsProject.instance().mapThemeCollection().masterVisibleLayers())
            map_item.setExtent(canvas_extent)
            map_item.attemptSetSceneRect(current_rect)
            map_item.setScale(round(self.iface.mapCanvas().scale()))
            self.r.addGeometry(QgsGeometry.fromRect(map_item.extent()),
                               QgsVectorLayer())

            self.layout.addItem(map_item)

    def reset_rubber(self):
        self.r.reset(QgsWkbTypes.PolygonGeometry)

    def rejected_dialog(self):
        self.is_active = False
        self.reset_rubber()
        try:
            self.iface.mapCanvas().scaleChanged.disconnect(
                self.create_composer
            )
        except TypeError:
            pass

    def run(self):
        if not self.is_active:
            self.is_active = True
            self.iface.mapCanvas().scaleChanged.connect(self.create_composer)
            self.create_composer()
            self.dialog.show()
            self.dialog.exec_()
        else:
            self.dialog.activateWindow()

    def save(self):
        filename, __ = QFileDialog.getSaveFileName(self.dialog, "Zapisz Plik")
        tmp_layer = self.create_tmp_layer()
        self.create_composer()
        self.save_file(filename)
        QgsProject.instance().removeMapLayers(tmp_layer)

    def preview(self):
        file_handle, filename = tempfile.mkstemp(suffix='szybki_wydruk')
        os.close(file_handle)
        tmp_layer = self.create_tmp_layer()
        self.create_composer()
        self.save_file(filename)
        QgsProject.instance().removeMapLayers(tmp_layer)

    def create_tmp_layer(self):
        layers_with_selection = get_layer_with_selection()
        temps_layer_list = []
        tmp_layer = None
        for layer_with_selection in layers_with_selection:
            if layer_with_selection:
                features = layer_with_selection.selectedFeatures()
                types = {
                    QgsWkbTypes.Point: "Point",
                    QgsWkbTypes.LineString: "LineString",
                    QgsWkbTypes.Polygon: "Polygon",
                    QgsWkbTypes.MultiPoint: "MultiPoint",
                    QgsWkbTypes.MultiLineString: "MultiLineString",
                    QgsWkbTypes.MultiPolygon: "MultiPolygon"
                }
                type = layer_with_selection.wkbType()
                try:
                    tmp_type = types[type]
                except KeyError:
                    return
                tmp_layer = QgsVectorLayer('%s?crs=%s' % (tmp_type, layer_with_selection.crs().authid()),
                                           'tmp_layer_fast_print', "memory")
                tmp_features = []
                for feature in features:
                    f = QgsFeature()
                    f.setGeometry(QgsGeometry(feature.geometry()))
                    tmp_features.append(f)
                tmp_layer.dataProvider().addFeatures(tmp_features)
                QgsProject.instance().addMapLayer(tmp_layer)
                selection_color = self.iface.mapCanvas().mapSettings().selectionColor()
                symbol = QgsSymbol.defaultSymbol(tmp_layer.geometryType())
                layer_style = {}
                color_str = ','.join([str(selection_color.red()),
                                      str(selection_color.green()),
                                      str(selection_color.blue()),
                                      str(selection_color.alpha())])
                layer_style['color'] = color_str
                layer_style['outline'] = color_str
                layer_style['color_border'] = color_str
                layer_style['style_border'] = 'no'
                symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)
                symbol.changeSymbolLayer(0, symbol_layer)
                tmp_layer.renderer().setSymbol(symbol)

                # Wazne!
                # zaczekaj az wszystkie procesy w tle zostana wykonane
                QApplication.processEvents()
            temps_layer_list.append(tmp_layer)
        return temps_layer_list

    def save_file(self, filename):
        p = self.dialog.progressBar
        w, h = self.get_paper_size()
        if self.dialog.legendCheckBox.isChecked():
            # TODO: Do zmiany generowanie legendy
            self.layout.setNumPages(2)  # utworzenie dodatkowej strony dla legendy
            self.layout.setPagesVisible(True)
            legend = QgsLayoutItemLegend(self.layout)  # inicjalizacja legendy
            layerGroup = QgsLayerTreeGroup()  # utworzenie grupy warstw
            n = 0  # licznik id
            # petla iteruje po liscie aktywnych warstw
            visibleLayers = self.iface.mapCanvas().layers()
            visibleLayersCount = len(visibleLayers)
            for the_layer in visibleLayers:
                layerGroup.insertLayer(n, the_layer)  # dodanie widocznej
                # warstwy do grupy warstw layerGroup
                n += 1  # zwiekszanie id o 1
            legend.modelV2().setRootGroup(layerGroup)
            legend.setSymbolHeight(3.0)
            legend.setSymbolWidth(5.0)
            # zmiana odstepow pomiedzy kolejnymi warstwami w legendzie dzieki
            # czemu miesci sie duzo warstw
            legend.rstyle(QgsLegendStyle.Symbol).setMargin(
                QgsLegendStyle.Top, 0.7)
            legend.setColumnCount(3)
            legend.setSplitLayer(True)  # warstwy nie są pogrupowane względem
            #  topologii
            legendSize = legend.paintAndDetermineSize(None)
            legend.setResizeToContents(True)
            self.layout.addItem(legend)
            legend.setItemPosition(5,
                                   h + 8,
                                   legendSize.width(),
                                   legendSize.height(),
                                   QgsLayoutItem.UpperLeft,
                                   2)

        if self.dialog.scaleCheckBox.isChecked():
            scale_label = QgsLayoutItemLabel(self.layout)
            scale_label.setText("SKALA: ")
            scale = QgsLayoutItemScaleBar(self.layout)
            scale.setLinkedMap(self.get_map_item())
            scale.setStyle('Numeric')
            scale_font = QFont()
            scale.setFont(scale_font)
            scale_label.setFont(scale_font)
            scale_label.adjustSizeToText()
            self.layout.addItem(scale_label)
            self.layout.addItem(scale)
            scale_label.moveBy(16, h - 14.)
            scale.moveBy(30, h - 15.)

        if self.dialog.titleLineEdit.text():
            title = QgsLayoutItemLabel(self.layout)
            current_text = ' '
            title.setText(self.dialog.titleLineEdit.text() + current_text)
            title_font = QFont()
            title_font.setPointSize(20)
            title_font.setWeight(75)
            title.setFont(title_font)
            title.adjustSizeToText()
            title.setPos((w / 2)-(len(self.dialog.titleLineEdit.text())*2), 3)
            self.layout.addItem(title)

        if self.dialog.adnotacje_lineEdit.text():
            adnotation = QgsLayoutItemLabel(self.layout)
            adnotation_font = QFont()
            default_font_Size = 10
            if w == 148 and len(self.dialog.adnotacje_lineEdit.text()) > 50:
                if 50 <= len(self.dialog.adnotacje_lineEdit.text()) <= 55:
                    default_font_Size = 7
                if 55 < len(self.dialog.adnotacje_lineEdit.text()) <= 65:
                    default_font_Size = 6
                if 65 < len(self.dialog.adnotacje_lineEdit.text()) <= 76:
                    default_font_Size = 5
                if 76 < len(self.dialog.adnotacje_lineEdit.text()) <= 96:
                    default_font_Size = 4
                if len(self.dialog.adnotacje_lineEdit.text()) > 96:
                    default_font_Size = 3
                if len(self.dialog.adnotacje_lineEdit.text()) > 128:
                    # CustomMessageBox(self.dialog, 'Adnotacja zawiera za dużo znaków').button_ok()
                    return
                else:
                    adnotation.setText(self.dialog.adnotacje_lineEdit.text())

            elif w == 210 and len(self.dialog.adnotacje_lineEdit.text()) > 90:
                if 90 <= len(self.dialog.adnotacje_lineEdit.text()) <= 98:
                    default_font_Size = 7
                if 98 < len(self.dialog.adnotacje_lineEdit.text()) <= 118:
                    default_font_Size = 6
                if 118 < len(self.dialog.adnotacje_lineEdit.text()) <= 140:
                    default_font_Size = 5
                if 140 < len(self.dialog.adnotacje_lineEdit.text()) <= 175:
                    default_font_Size = 4
                if len(self.dialog.adnotacje_lineEdit.text()) > 175:
                    default_font_Size = 3
                if len(self.dialog.adnotacje_lineEdit.text()) > 225:
                    # CustomMessageBox(self.dialog, 'Adnotacja zawiera za dużo znaków').button_ok()
                    return
                else:
                    adnotation.setText(self.dialog.adnotacje_lineEdit.text())

            elif w == 297 and len(self.dialog.adnotacje_lineEdit.text()) > 145:
                if 145 <= len(self.dialog.adnotacje_lineEdit.text()) <= 160:
                    default_font_Size = 7
                if 160 < len(self.dialog.adnotacje_lineEdit.text()) <= 190:
                    default_font_Size = 6
                if 190 < len(self.dialog.adnotacje_lineEdit.text()) <= 225:
                    default_font_Size = 5
                if 225 < len(self.dialog.adnotacje_lineEdit.text()) <= 270:
                    default_font_Size = 4
                if len(self.dialog.adnotacje_lineEdit.text()) > 270:
                    default_font_Size = 3
                if len(self.dialog.adnotacje_lineEdit.text()) > 368:
                    # CustomMessageBox(self.dialog, 'Adnotacja zawiera za dużo znaków').button_ok()
                    return
                else:
                    adnotation.setText(self.dialog.adnotacje_lineEdit.text())

            elif w == 420 and len(self.dialog.adnotacje_lineEdit.text()) > 220:
                if 220 <= len(self.dialog.adnotacje_lineEdit.text()) <= 245:
                    default_font_Size = 7
                if 245 < len(self.dialog.adnotacje_lineEdit.text()) <= 280:
                    default_font_Size = 6
                if 280 < len(self.dialog.adnotacje_lineEdit.text()) <= 345:
                    default_font_Size = 5
                if 345 < len(self.dialog.adnotacje_lineEdit.text()) <= 425:
                    default_font_Size = 4
                if len(self.dialog.adnotacje_lineEdit.text()) > 425:
                    default_font_Size = 3
                if len(self.dialog.adnotacje_lineEdit.text()) > 555:
                    # CustomMessageBox(self.dialog, 'Adnotacja zawiera za dużo znaków').button_ok()
                    return
                else:
                    adnotation.setText(self.dialog.adnotacje_lineEdit.text())

            elif w == 594 and len(self.dialog.adnotacje_lineEdit.text()) > 335:
                if 335 <= len(self.dialog.adnotacje_lineEdit.text()) <= 360:
                    default_font_Size = 7
                if 360 < len(self.dialog.adnotacje_lineEdit.text()) <= 440:
                    default_font_Size = 6
                if 440 < len(self.dialog.adnotacje_lineEdit.text()) <= 510:
                    default_font_Size = 5
                if 510 < len(self.dialog.adnotacje_lineEdit.text()) <= 640:
                    default_font_Size = 4
                if len(self.dialog.adnotacje_lineEdit.text()) > 640:
                    default_font_Size = 3
                if len(self.dialog.adnotacje_lineEdit.text()) > 850:
                    # CustomMessageBox(self.dialog, 'Adnotacja zawiera za dużo znaków').button_ok()
                    return
                else:
                    adnotation.setText(self.dialog.adnotacje_lineEdit.text())

            elif w == 841 and len(self.dialog.adnotacje_lineEdit.text()) > 475:
                if 475 <= len(self.dialog.adnotacje_lineEdit.text()) <= 540:
                    default_font_Size = 7
                if 540 < len(self.dialog.adnotacje_lineEdit.text()) <= 640:
                    default_font_Size = 6
                if 640 < len(self.dialog.adnotacje_lineEdit.text()) <= 760:
                    default_font_Size = 5
                if 760 < len(self.dialog.adnotacje_lineEdit.text()) <= 960:
                    default_font_Size = 4
                if len(self.dialog.adnotacje_lineEdit.text()) > 960:
                    default_font_Size = 3
                if len(self.dialog.adnotacje_lineEdit.text()) > 1250:
                    # CustomMessageBox(self.dialog, 'Adnotacja zawiera za dużo znaków').button_ok()
                    return
                else:
                    adnotation.setText(self.dialog.adnotacje_lineEdit.text())

            elif w == 1189 and len(self.dialog.adnotacje_lineEdit.text()) > 700:
                if 700 < len(self.dialog.adnotacje_lineEdit.text()) <= 780:
                    default_font_Size = 7
                if 780 < len(self.dialog.adnotacje_lineEdit.text()) <= 940:
                    default_font_Size = 6
                if 940 < len(self.dialog.adnotacje_lineEdit.text()) <= 1090:
                    default_font_Size = 5
                if 1090 < len(self.dialog.adnotacje_lineEdit.text()) <= 1320:
                    default_font_Size = 4
                if len(self.dialog.adnotacje_lineEdit.text()) > 1320:
                    default_font_Size = 3
                if len(self.dialog.adnotacje_lineEdit.text()) > 1250:
                    # CustomMessageBox(self.dialog, 'Adnotacja zawiera za dużo znaków').button_ok()
                    return
                else:
                    adnotation.setText(self.dialog.adnotacje_lineEdit.text()+'\n'+self.dialog.adnotacje_lineEdit.text())
            else:
                adnotation.setText(self.dialog.adnotacje_lineEdit.text()+'\n'+self.dialog.adnotacje_lineEdit.text())
            adnotation.setText(
                self.dialog.adnotacje_lineEdit.text() + '\n' + self.dialog.adnotacje_lineEdit.text())
            adnotation_font.setPointSize(int(default_font_Size))
            adnotation.setFont(adnotation_font)
            adnotation.adjustSizeToText()
            self.layout.addItem(adnotation)
            new_width = w - (len(
                self.dialog.adnotacje_lineEdit.text() )* 2.6) if w - (len(
                self.dialog.adnotacje_lineEdit.text() )* 2.6) > w / 2.6 else w / 2.6
            adnotation.setPos(new_width, h - 14)
        p.show()
        p.setValue(20)
        if filename:
            if self.dialog.jpgRadioButton.isChecked():
                ext = '.jpg'
                function = self.print_image
            elif self.dialog.pngRadioButton.isChecked():
                ext = '.png'
                function = self.print_image
            else:
                ext = '.pdf'
                function = self.print_pdf
            if not filename.endswith(ext):
                filename += ext
            function(filename)
            # only_preview_file(filename)
        p.setValue(100)
        p.hide()

    def print_pdf(self, filename):
        p = self.dialog.progressBar
        p.setValue(50)
        exporter = QgsLayoutExporter(self.layout)
        pdf_settings = exporter.PdfExportSettings()
        pdf_settings.dpi = self.dpi
        p.setValue(90)
        exporter.exportToPdf(filename,
                             pdf_settings)
        p.setValue(100)

    def print_image(self, filename):
        p = self.dialog.progressBar
        p.setValue(50)
        exporter = QgsLayoutExporter(self.layout)
        pdf_settings = exporter.ImageExportSettings()
        pdf_settings.dpi = self.dpi
        p.setValue(90)
        exporter.exportToImage(filename,
                             pdf_settings)
        p.setValue(100)

