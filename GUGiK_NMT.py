import os
import sys
from urllib.parse import quote
import re

import requests
from PyQt5.QtCore import Qt, QVariant, pyqtSignal
from pyexpat import features

from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMessageBox
from qgis.PyQt.QtWidgets import QVBoxLayout, QPushButton, QMenu, QApplication, QDialog, QTableWidget, QHBoxLayout, \
    QDockWidget
from qgis.PyQt import QtWidgets, uic, QtCore
from qgis._core import QgsPointXY, QgsFeatureRequest, QgsRectangle, QgsWkbTypes, QgsMapLayer
from qgis._gui import QgsMapToolCapture, QgsMapTool, QgsRubberBand
from qgis.gui import QgsMapToolEmitPoint
from qgis.core import QgsVectorLayer, QgsProject, QgsFeature, QgsGeometry, QgsFields, QgsField, QgsRasterLayer, \
    QgsLayerTreeGroup, QgsCoordinateTransform, QgsCoordinateReferenceSystem
from qgis.utils import iface


project = QgsProject.instance()

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Gugik_nmt.ui'))
FORM_CLASS_LHP1, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'Gugik_low_heig.ui'))
FORM_CLASS_LHP2, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'Gugik_strona2.ui'))
FORM_CLASS_LHP3, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'Gugik_strona3.ui'))
FORM_CLASS_EM1, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'Gugik_earth.ui'))
FORM_CLASS_EM2, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'Gugik_earth_analiza.ui'))

class PolygonDrawingTool(QgsMapTool):
    def __init__(self, canvas, callback, close_callback=None, show_temp_layer=True):
        super().__init__(canvas)
        self.canvas = canvas
        self.callback = callback
        self.close_callback = close_callback
        self.show_temp_layer = show_temp_layer
        self.points = []
        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0, 100))
        self.rubberBand.setWidth(2)

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            point = self.toMapCoordinates(event.pos())
            self.points.append(point)
            self.rubberBand.addPoint(point)
        elif event.button() == Qt.RightButton:
            if len(self.points) < 3:
                QMessageBox.warning(None, "Błąd", "Należy narysować co najmniej 3 punkty.")
                return
            self.rubberBand.closePoints()
            self.finish()

    def finish(self):
        if self.points[0] != self.points[-1]:
            self.points.append(self.points[0])

        geom = QgsGeometry.fromPolygonXY([self.points])
        if not geom.isGeosValid():
            QMessageBox.warning(None, "Błąd", "Narysowany poligon jest niepoprawny geometrycznie.")
            self.reset()
            return

        polygon_wkt = geom.asWkt()
        self.callback(polygon_wkt)

        if self.show_temp_layer:
            temp_layer = QgsVectorLayer("Polygon?crs=EPSG:2180", "Zasięg", "memory")
            pr = temp_layer.dataProvider()
            pr.addAttributes([QgsField("id", QVariant.Int)])
            temp_layer.updateFields()

            feat = QgsFeature(temp_layer.fields())
            feat.setGeometry(geom)
            feat.setAttribute("id", 1)
            pr.addFeature(feat)
            QgsProject.instance().addMapLayer(temp_layer)

        self.reset()
        self.canvas.unsetMapTool(self)
        if self.close_callback:
            self.close_callback()

    def reset(self):
        self.points.clear()
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)

class ObrysTool(QgsMapToolEmitPoint):
    def __init__(self, canvas, callback, close_callback=None):
        super().__init__(canvas)
        self.canvas = canvas
        self.callback = callback
        self.close_callback = close_callback

    def canvasReleaseEvent(self, event):
        point = self.toMapCoordinates(event.pos())
        layer = iface.activeLayer()
        if not layer:
            iface.messageBar().pushWarning("Błąd", "Brak aktywnej warstwy")
            return

        rect = QgsRectangle(point.x() - 1, point.y() - 1, point.x() + 1, point.y() + 1)

        request = QgsFeatureRequest().setFilterRect(rect).setSubsetOfAttributes([]).setFlags(QgsFeatureRequest.NoFlags)
        feat = next(layer.getFeatures(request), None)

        if feat:
            geom = feat.geometry()
            if not geom:
                return

            polygon_wkt = geom.asWkt()
            self.callback(polygon_wkt)

            temp_layer = QgsVectorLayer("Polygon?crs=EPSG:2180", "Obrys", "memory")
            pr = temp_layer.dataProvider()
            pr.addAttributes([QgsField("id", QVariant.Int)])
            temp_layer.updateFields()

            new_feat = QgsFeature(temp_layer.fields())
            new_feat.setGeometry(geom)
            new_feat.setAttribute("id", 1)
            pr.addFeature(new_feat)
            QgsProject.instance().addMapLayer(temp_layer)

            iface.mapCanvas().unsetMapTool(self)
            if self.close_callback:
                self.close_callback()




class HeightPoint(QDockWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.ui = FORM_CLASS()
        self.ui.setupUi(self)
        # self.setWindowFlags(Qt.Window)
        self.setMinimumSize(550,300)
        self.setMaximumSize(550,300)
        self.setWindowOpacity(1.0)

        self.setWindowTitle("Wysokość terenu na podstawie danych NMT GUGiK")

        self.ui.pushButton_3.clicked.connect(self.nowy_pomiar)
        self.ui.pushButton_2.clicked.connect(self.kopiuj)
        self.ui.pushButton.clicked.connect(self.zapisz)

        self.map_canvas = iface.mapCanvas()
        self.tool = QgsMapToolEmitPoint(self.map_canvas)
        self.tool.canvasClicked.connect(self.punkt_na_mapie)

        self.klikamy_na_mape = False
        self.show()

    def pobierz_i_dodaj_punkt(self, point):
        x = round(point.x())
        y = round(point.y())
        try:
            url = f"https://services.gugik.gov.pl/nmt/?request=GetHByXY&x={x}&y={y}"
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                h = r.text.strip().replace(".", ",")
            else:
                h = "brak"
        except Exception:
            h = "Błąd"

        self.dodaj_pomiar(x, y, h)

    def punkt_na_mapie(self, point, button):
        self.pobierz_i_dodaj_punkt(point)

    def dodaj_pomiar(self, x, y, h):
        row = self.ui.tableWidget.rowCount()
        self.ui.tableWidget.insertRow(row)
        self.ui.tableWidget.setItem(row, 0, QtWidgets.QTableWidgetItem(str(x)))
        self.ui.tableWidget.setItem(row, 1, QtWidgets.QTableWidgetItem(str(y)))
        self.ui.tableWidget.setItem(row, 2, QtWidgets.QTableWidgetItem(str(h)))

    def nowy_pomiar(self):
        self.ui.tableWidget.clearContents()
        self.ui.tableWidget.setRowCount(0)
        try:
            self.tool.canvasClicked.disconnect()
        except Exception:
            pass
        self.tool = QgsMapToolEmitPoint(self.map_canvas)
        def punkt(point, button):
            self.map_canvas.unsetMapTool(self.tool)
            self.pobierz_i_dodaj_punkt(point)

        self.tool.canvasClicked.connect(punkt)
        self.map_canvas.setMapTool(self.tool)


    def kopiuj(self):
        tekst = "X\tY\tWysokość\n"
        for row in range(self.ui.tableWidget.rowCount()):
            x = self.ui.tableWidget.item(row, 0).text()
            y = self.ui.tableWidget.item(row, 1).text()
            h = self.ui.tableWidget.item(row, 2).text()
            tekst += f"{x}\t{y}\t{h}\n"

        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(tekst)

    def zapisz(self):
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Zapisz jako CSV", "", "CSV Files (*.csv)")
            if not path:
                return

            try:
                with open(path, 'w', encoding='utf-8') as file:
                    file.write("X;Y;Wysokość\n")
                    for row in range(self.ui.tableWidget.rowCount()):
                        x = self.ui.tableWidget.item(row, 0).text()
                        y = self.ui.tableWidget.item(row, 1).text()
                        h = self.ui.tableWidget.item(row, 2).text()
                        file.write(f"{x};{y};{h}\n")
                QtWidgets.QMessageBox.information(self, "Zapisano", f"Dane zapisano do:\n{path}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Błąd", f"Nie udało się zapisać:\n{str(e)}")


class HeightMultiPoints(QDockWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.ui = FORM_CLASS()
        self.ui.setupUi(self)
        self.setMinimumSize(550, 300)
        self.setMaximumSize(550, 300)
        self.setWindowOpacity(1.0)

        self.setWindowTitle("Wysokość terenu na podstawie danych NMT GUGiK")

        self.ui.pushButton_3.clicked.connect(self.nowy_pomiar)
        self.ui.pushButton_2.clicked.connect(self.kopiuj)
        self.ui.pushButton.clicked.connect(self.zapisz)

        self.map_canvas = iface.mapCanvas()
        self.tool = QgsMapToolEmitPoint(self.map_canvas)

        self.klikamy_na_mape = False
        self.show()

        self.map_canvas = iface.mapCanvas()
        self.tool = QgsMapToolEmitPoint(self.map_canvas)
        self.lista_punktow = []

    def dodaj_pomiar(self, x, y, h):
        row = self.ui.tableWidget.rowCount()
        self.ui.tableWidget.insertRow(row)
        self.ui.tableWidget.setItem(row, 0, QtWidgets.QTableWidgetItem(str(x)))
        self.ui.tableWidget.setItem(row, 1, QtWidgets.QTableWidgetItem(str(y)))
        self.ui.tableWidget.setItem(row, 2, QtWidgets.QTableWidgetItem(str(h)))

    def nowy_pomiar(self):
        self.lista_punktow.clear()
        self.ui.tableWidget.clearContents()

        self.mem_layer = self.stworz_warstwe_tymczasowa()

        try:
            self.tool.canvasClicked.disconnect()
        except:
            pass

        self.tool = QgsMapToolEmitPoint(self.map_canvas)

        def punkt(point, button):
            x = round(point.x())
            y = round(point.y())

            self.lista_punktow.append((x, y))
            lista_str = ";".join([f"{px} {py}" for px, py in self.lista_punktow])

            try:
                url = f"https://services.gugik.gov.pl/nmt/?request=GetHByPointList&list={lista_str}"
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    wysokosci = r.text.strip().split(";")
                    if len(wysokosci) == len(self.lista_punktow):
                        self.ui.tableWidget.setRowCount(0)
                        self.mem_layer.dataProvider().truncate()
                        features = []
                        for (px, py), h_str in zip(self.lista_punktow, wysokosci):
                            parts = h_str.strip().split()
                            if len(parts) == 3:
                                h = parts[2].replace(".", ",")
                            else:
                                h = h_str.strip().replace(".", ",")
                            self.dodaj_pomiar(px, py, h)
                            feat = QgsFeature(self.mem_layer.fields())
                            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(px, py)))
                            feat.setAttributes([px, py, h])
                            features.append(feat)
                        self.mem_layer.dataProvider().addFeatures(features)
                        self.mem_layer.triggerRepaint()
                    else:
                        QtWidgets.QMessageBox.warning(self, "Błąd", "Niepoprawna liczba wyników z serwera.")
                else:
                    QtWidgets.QMessageBox.warning(self, "Błąd", f"Błąd odpowiedzi z serwera ({r.status_code}).")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Błąd", f"Nie udało się pobrać danych:\n{str(e)}")

        self.tool.canvasClicked.connect(punkt)
        self.map_canvas.setMapTool(self.tool)

    def stworz_warstwe_tymczasowa(self):
        fields = [
            QgsField("X", QVariant.Int),
            QgsField("Y", QVariant.Int),
            QgsField("Wysokosc", QVariant.String)
        ]

        crs = self.map_canvas.mapSettings().destinationCrs()
        nazwa_warstwy = "Pomiar punktów - wysokości NMT GUGiK"

        mem_layer = QgsVectorLayer(f"Point?crs={crs.authid()}", nazwa_warstwy, "memory")
        mem_layer.dataProvider().addAttributes(fields)
        mem_layer.updateFields()

        qml_path = "znacznik_wysokośc.qml"
        if mem_layer.loadNamedStyle(qml_path):
            mem_layer.triggerRepaint()
        else:
            print("Nie udało się załadować stylu QML")

        QgsProject.instance().addMapLayer(mem_layer)
        return mem_layer

    def closeEvent(self, event):
        if hasattr(self, 'tool') and self.tool is not None:
            self.map_canvas.unsetMapTool(self.tool)
            self.tool = None
        event.accept()


    def kopiuj(self):
        tekst = "X\tY\tWysokość\n"
        for row in range(self.ui.tableWidget.rowCount()):
            x = self.ui.tableWidget.item(row, 0).text()
            y = self.ui.tableWidget.item(row, 1).text()
            h = self.ui.tableWidget.item(row, 2).text()
            tekst += f"{x}\t{y}\t{h}\n"

        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(tekst)

    def zapisz(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Zapisz jako CSV", "", "CSV Files (*.csv)")
        if not path:
            return

        try:
            with open(path, 'w', encoding='utf-8') as file:
                file.write("X;Y;Wysokość\n")
                for row in range(self.ui.tableWidget.rowCount()):
                    x = self.ui.tableWidget.item(row, 0).text()
                    y = self.ui.tableWidget.item(row, 1).text()
                    h = self.ui.tableWidget.item(row, 2).text()
                    file.write(f"{x};{y};{h}\n")
            QtWidgets.QMessageBox.information(self, "Zapisano", f"Dane zapisano do:\n{path}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Błąd", f"Nie udało się zapisać:\n{str(e)}")



class LowestHeighesPunkt(QDockWidget, FORM_CLASS_LHP1):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # self.ui = FORM_CLASS_LHP1()
        self.setupUi(self)
        # self.setWindowFlags(Qt.Window)
        self.setMinimumSize(550,100)
        self.setMaximumSize(550,100)
        self.setWindowOpacity(1.0)

        self.setWindowTitle("Wyznaczenie najniższego i najwyższego punktu")
        self.pushButton_3.clicked.connect(self.uruchom_rysowania_pol)
        self.pushButton_2.clicked.connect(self.pobierz_obrys)
        self.pushButton.clicked.connect(self.analizuj)

        self.map_canvas = iface.mapCanvas()
        self.polygon_wkt = None
        self.temp_layer = None
        self.tool = None

        self.show()

    def uruchom_rysowania_pol(self):
        self.tool = PolygonDrawingTool(self.map_canvas,callback=self.rysuj_polygon)
        self.map_canvas.setMapTool(self.tool)

    def rysuj_polygon(self, wkt=None):
        if not wkt or not isinstance(wkt,str):
            QMessageBox.warning(self, "Błąd", "Brak poprawnego poligonu do analizy.")
            return
        print(wkt, type(wkt))
        self.close()
        self.wynik = AnalizaKoniec(wkt)
        self.wynik.show()

    def pobierz_obrys(self):
        def on_obrys_gotowy(wkt):
            self.polygon_wkt = wkt
            self.close()
            self.okno_analiza = AnalizaKoniec(wkt_polygon=self.polygon_wkt)
            self.okno_analiza.show()

        self.tool = ObrysTool(self.map_canvas, callback=on_obrys_gotowy)
        self.map_canvas.setMapTool(self.tool)

    def analizuj(self):
        self.okno_lista = AnalizaLowHight("LHP")
        self.okno_lista.show()
        self.close()


class AnalizaLowHight(QDockWidget, FORM_CLASS_LHP2):
    def __init__(self, typ_okna, wys=None ,parent=None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setMinimumSize(550,150)
        self.setMaximumSize(550,150)
        self.setWindowOpacity(1.0)
        self.typ_okna = typ_okna
        self.wys = wys

        if self.typ_okna == "LHP":
            self.setWindowTitle("Wyznaczenie najniższego i najwyższego punktu - wybór warstwy")
        elif self.typ_okna == "EMC":
            self.setWindowTitle("Obliczanie objętości mas ziemnych - wybór warstwy")

        self.pushButton.clicked.connect(self.anuluj)
        self.pushButton_2.clicked.connect(self.analizuj_warstwe)


        self.map_canvas = iface.mapCanvas()
        self.temp_layer = None
        self.tool = None

        self.lista_rozwijalna()
        self.show()

    def lista_rozwijalna(self):
        self.comboBox.clear()
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                    add_layer = False
                    for feature in layer.getFeatures():
                        geom = feature.geometry()
                        if geom.isGeosValid() and geom.area() < 100000:
                            add_layer = True
                            break
                    if add_layer:
                        self.comboBox.addItem(layer.name(), layer.id())

    def analizuj_warstwe(self):
        layer_id = self.comboBox.currentData()

        if layer_id is None:
            QMessageBox.warning(self, "Błąd", "Nie wybrano żadnej warstwy")
            return

        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer:
            QMessageBox.warning(self, "Błąd", "Nie można znaleźć wybranej warstwy")
            return

        geom_union = None
        try:
            geometries = [feat.geometry() for feat in layer.getFeatures()]
            geom_union = QgsGeometry.unaryUnion(geometries)
        except Exception as e:
            QMessageBox.warning("Błąd", f"Nie udało się połączyć geometrii:\n{str(e)}")
            return

        if geom_union is None or geom_union.isEmpty():
            QMessageBox.warning(self, "Błąd", "Warstwa nie zawiera geometrii")
            return

        wkt = geom_union.asWkt()

        if self.typ_okna == "LHP":
            self.koniec_okno = AnalizaKoniec(wkt)
        elif self.typ_okna == "EMC":
            self.koniec_okno = AnalizaMassZiemi(wkt, self.wys)
        self.koniec_okno.show()

        self.hide()

    def anuluj(self):
        self.close()
        if self.typ_okna == "LHP":
            self.okno_analizy = LowestHeighesPunkt()
        elif self.typ_okna == "EMC":
            self.okno_analizy = EarthMassCal()
        self.okno_analizy.show()

class AnalizaKoniec(QDockWidget, FORM_CLASS_LHP3):
    def __init__(self,wkt_polygon, parent=None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setMinimumSize(550, 300)
        self.setMaximumSize(550, 300)
        self.setWindowOpacity(1.0)

        self.setWindowTitle("Wyznaczenie najniższego i najwyższego punktu")

        self.pushButton.clicked.connect(self.low_point)
        self.pushButton_2.clicked.connect(self.height_point)
        self.btnNewMeasurement_2.clicked.connect(self.nowy_pomiar)
        self.btnCopy_2.clicked.connect(self.copy)
        self.btnSave_2.clicked.connect(self.save)

        self.map_canvas = iface.mapCanvas()
        self.temp_layer = None
        self.tool = None


        self.wkt_polygon = wkt_polygon
        print("WKT poligonu:", self.wkt_polygon)
        self.min_max_data = None

        self.min_max_point_data()

        self.show()

    def min_max_point_data(self):
        url_template = "https://services.gugik.gov.pl/nmt/?request=GetMinMaxByPolygon&polygon={}&json"
        wkt_clean = self.wkt_polygon.strip().strip('\'"')

        wkt_clean = re.sub(r'^polygon\s*\(\(', 'POLYGON((', wkt_clean, flags=re.IGNORECASE)
        wkt_clean = re.sub(r'POLYGON\s*\(\(', 'POLYGON((', wkt_clean)

        try:
            geom = QgsGeometry.fromWkt(wkt_clean)
            area = geom.area()
            if area > 100000:
                QMessageBox.warning(self, "Za duży obszar",
                                    f"Powierzchnia wynosi {area:.2f} m².\nLimit GUGiK to 100 000 m².")
                return
        except Exception as e:
            QMessageBox.warning(self, "Błąd geometrii", f"Nieprawidłowy WKT:\n{e}")
            return

        encoded_wkt = quote(wkt_clean)
        url = url_template.format(encoded_wkt)

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            self.min_max_data = data

            self.MIn.setText(f"Wysokość minimalna: {data['Hmin']} m")
            self.Max.setText(f"Wysokość maksymalna: {data['Hmax']} m")
            self.Pow.setText(f"Powierzchnia obszaru: {data['Polygon area']} m²")
            self.siatka.setText(f"Rozdzielczość siatki: {data['Grid size [m]']} m")

        except requests.RequestException as e:
            QMessageBox.warning(self, "Błąd połączenia", f"Nie udało się pobrać danych:\n{e}")

    def low_point(self):
        if "Hmin geom" not in self.min_max_data or not self.min_max_data["Hmin geom"]:
            QMessageBox.warning(self, "Brak danych", "Brak danych wysokościowych – nie można przybliżyć.")
            return

        try:
            geom_str = self.min_max_data["Hmin geom"][0]
            coords = geom_str.replace("POINT(", "").replace(")", "").split()
            x, y = float(coords[0]), float(coords[1])
            point = QgsPointXY(x, y)

            buffer = 50
            rect = QgsRectangle(x - buffer, y - buffer, x + buffer, y + buffer)

            self.map_canvas.setExtent(rect)
            self.map_canvas.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie można przybliżyć do punktu:\n{e}")



    def height_point(self):
        if "Hmax geom" not in self.min_max_data or not self.min_max_data["Hmax geom"]:
            QMessageBox.warning(self, "Brak danych", "Brak danych wysokościowych – nie można przybliżyć.")
            return

        try:
            geom_str = self.min_max_data["Hmax geom"][0]
            coords = geom_str.replace("POINT(", "").replace(")", "").split()
            x, y = float(coords[0]), float(coords[1])
            point = QgsPointXY(x,y)

            buffer = 50
            rect = QgsRectangle(x - buffer, y - buffer, x + buffer, y + buffer)

            self.map_canvas.setExtent(rect)
            self.map_canvas.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie można przybliżyć do punktu:\n{e}")

    def nowy_pomiar(self):
        self.close()
        new_window = LowestHeighesPunkt(iface.mainWindow())
        iface.addDockWidget(Qt.RightDockWidgetArea, new_window)

    def copy(self):
        tekst = f"{self.MIn.text()} \n{self.Max.text()} \n{self.Pow.text()} \n{self.siatka.text()}"
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(tekst)

    def save(self):
        try:
            tekst = (
                f"{self.MIn.text()}\n"
                f"{self.Max.text()}\n"
                f"{self.Pow.text()}\n"
                f"{self.siatka.text()}"
            )

            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Zapisz dane",
                "wyniki.txt",
                "Pliki tekstowe (*.txt)"
            )

            if filename:
                with open(filename, "w", encoding="utf-8") as file:
                    file.write(tekst)
                QMessageBox.information(self, "Zapisano", f"Dane zapisano do:\n{filename}")
        except Exception as e:
            QMessageBox.warning(self, "Błąd zapisu", f"Nie udało się zapisać pliku:\n{e}")



class EarthMassCal(QDockWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.ui = FORM_CLASS_EM1()
        self.ui.setupUi(self)
        self.setMinimumSize(550, 200)
        self.setMaximumSize(550, 200)
        self.setWindowOpacity(1.0)

        self.setWindowTitle("Obliczanie objętości mas ziemnych")


        self.ui.pushButton_3.setEnabled(False)
        self.ui.pushButton_2.setEnabled(False)
        self.ui.pushButton.setEnabled(False)

        self.ui.lineEdit.textChanged.connect(self.sprawdz_wysokosc)

        self.ui.pushButton_3.clicked.connect(self.uruchom_rysowania_pol)
        self.ui.pushButton_2.clicked.connect(self.pobierz_obrys)
        self.ui.pushButton.clicked.connect(self.analiza)

        self.map_canvas = iface.mapCanvas()
        self.temp_layer = None
        self.tool = None
        self.wkt_polygon = None
        self.wys = None

        self.show()

    def sprawdz_wysokosc(self):
        tekst = self.ui.lineEdit.text().strip()
        try:
            wys = float(tekst)
            self.ui.pushButton_3.setEnabled(True)
            self.ui.pushButton_2.setEnabled(True)
            self.ui.pushButton.setEnabled(True)
            self.wys = wys
        except ValueError:
            self.ui.pushButton_3.setEnabled(False)
            self.ui.pushButton_2.setEnabled(False)
            self.ui.pushButton.setEnabled(False)
            self.wys = None

    def analiza(self):
        if self.wys is None:
            QMessageBox.warning(self, "Błąd", "Podaj poprawną wartość wysokości.")
            return

        if not self.wkt_polygon:
            self.close()
            self.koniec_okno = AnalizaLowHight("EMC", self.wys)
            self.koniec_okno.show()
            return

        geom = QgsGeometry.fromWkt(self.wkt_polygon)
        if geom.isEmpty():
            QMessageBox.warning(self, "Błąd", "Geometria poligonu jest pusta.")
            return

        self.close()
        self.koniec_okno = AnalizaMassZiemi(self.wkt_polygon, self.wys)
        self.koniec_okno.show()

    def uruchom_rysowania_pol(self):
        def rysuj_polygon(wkt=None):
            self.polydon_wkt = wkt
            self.close()
            self.wynik = AnalizaMassZiemi(wkt_polygon=self.polydon_wkt, wys=self.wys)
            self.wynik.show()

        self.tool = PolygonDrawingTool(self.map_canvas, callback=rysuj_polygon)
        self.map_canvas.setMapTool(self.tool)

    def pobierz_obrys(self):
        def on_obrys_gotowy(wkt):
            self.polygon_wkt = wkt
            self.close()
            self.okno_analiza = AnalizaMassZiemi(wkt_polygon=self.polygon_wkt, wys=self.wys)
            self.okno_analiza.show()

        self.tool = ObrysTool(self.map_canvas, callback=on_obrys_gotowy)
        self.map_canvas.setMapTool(self.tool)


class AnalizaMassZiemi(QDockWidget, FORM_CLASS_EM2):
    def __init__(self,wkt_polygon,wys, parent=None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setMinimumSize(550, 300)
        self.setMaximumSize(550, 300)
        self.setWindowOpacity(1.0)

        self.setWindowTitle("Obliczanie objętości mas ziemnych")

        self.pushButton.clicked.connect(self.low_point)
        self.pushButton_2.clicked.connect(self.height_point)
        self.btnNewMeasurement_2.clicked.connect(self.nowy_pomiar)
        self.btnCopy_2.clicked.connect(self.copy)
        self.btnSave_2.clicked.connect(self.save)

        self.map_canvas = iface.mapCanvas()
        self.temp_layer = None
        self.tool = None
        self.min_max_data = None
        self.wys = wys
        self.wkt_polygon = wkt_polygon
        self.earth_mass()
        self.show()

    def earth_mass(self):
        url_template_1 = "https://integracja.gugik.gov.pl/nmt/?request=GetVolume&polygon={}&level={}&json"
        url_template_zbliz = "https://services.gugik.gov.pl/nmt/?request=GetMinMaxByPolygon&polygon={}&json"
        wkt_clean = self.wkt_polygon.strip().strip('\'"')

        wkt_clean = re.sub(r'^polygon\s*\(\(', 'POLYGON((', wkt_clean, flags=re.IGNORECASE)
        wkt_clean = re.sub(r'POLYGON\s*\(\(', 'POLYGON((', wkt_clean)


        try:
            geom = QgsGeometry.fromWkt(wkt_clean)
            area = geom.area()
            if area > 100000:
                QMessageBox.warning(self, "Za duży obszar",
                                    f"Powierzchnia wynosi {area:.2f} m².\nLimit GUGiK to 100 000 m².")
                return
        except Exception as e:
            QMessageBox.warning(self, "Błąd geometrii", f"Nieprawidłowy WKT:\n{e}")
            return

        encoded_wkt = quote(wkt_clean)
        url = url_template_1.format(encoded_wkt, self.wys)
        url_zbliz = url_template_zbliz.format(encoded_wkt)

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            response_zbliz = requests.get(url_zbliz)
            response_zbliz.raise_for_status()
            data_zbliz = response_zbliz.json()
            self.min_max_data = data_zbliz

            self.MIn.setText(f"Wysokość minimalna: {data['Hmin']} m2")
            self.Max.setText(f"Wysokość maksymalna: {data['Hmax']} m2")
            self.Pow.setText(f"Powierzchnia obszaru: {data['Polygon area']} m2")
            self.siatka.setText(f"Objętość powyżej podanej wysokości: {data['Volume above']} m3")
            self.label.setText(f"Objętość poniżej podanej wysokości: {data['Volume below']} m3")

        except requests.RequestException as e:
            QMessageBox.warning(self, "Błąd połączenia", f"Nie udało się pobrać danych:\n{e}")

    def low_point(self):
        AnalizaKoniec.low_point(self)

    def height_point(self):
        AnalizaKoniec.height_point(self)

    def nowy_pomiar(self):
        self.close()
        new_window = EarthMassCal(iface.mainWindow())
        iface.addDockWidget(Qt.RightDockWidgetArea, new_window)

    def copy(self):
        tekst = f"{self.MIn.text()} \n{self.Max.text()} \n{self.Pow.text()} \n{self.siatka.text()} \n{self.label.text()}"
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(tekst)

    def save(self):
        try:
            tekst = (
                f"{self.MIn.text()}\n"
                f"{self.Max.text()}\n"
                f"{self.Pow.text()}\n"
                f"{self.siatka.text()}\n"
                f"{self.label.text()}"
            )

            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Zapisz dane",
                "wyniki.txt",
                "Pliki tekstowe (*.txt)"
            )

            if filename:
                with open(filename, "w", encoding="utf-8") as file:
                    file.write(tekst)
                QMessageBox.information(self, "Zapisano", f"Dane zapisano do:\n{filename}")
        except Exception as e:
            QMessageBox.warning(self, "Błąd zapisu", f"Nie udało się zapisać pliku:\n{e}")

class GUGiKTool(QDockWidget):
    def __init__(self, parent=None) -> None :
        super().__init__()

    def height_point_NMT(self):
        self.hp = HeightPoint()
        iface.addDockWidget(Qt.RightDockWidgetArea, self.hp)
        self.hp.show()

    def height_multiple_points(self):
        self.hmp = HeightMultiPoints()
        iface.addDockWidget(Qt.RightDockWidgetArea, self.hmp)
        self.hmp.show()

    def lowest_heighest_punkt(self):
        self.lhp = LowestHeighesPunkt()
        iface.addDockWidget(Qt.RightDockWidgetArea, self.lhp)
        self.lhp.show()

    def earth_mass_cal(self):
        self.emc = EarthMassCal()
        iface.addDockWidget(Qt.RightDockWidgetArea, self.emc)
        self.emc.show()



