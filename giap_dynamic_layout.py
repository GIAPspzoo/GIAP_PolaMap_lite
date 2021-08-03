import os
import webbrowser

from plugins.processing.tools.general import execAlgorithmDialog
from qgis.PyQt.QtCore import Qt, QSize, QEvent, pyqtSignal, QMimeData, QRect
from qgis.PyQt import uic
from qgis.PyQt.QtGui import QDrag, QPainter, QPixmap, QCursor, QIcon
from qgis.PyQt.QtWidgets import QWidget, QApplication, QHBoxLayout,\
    QFrame, QLabel, QPushButton, QTabBar, QToolButton, QVBoxLayout, \
    QGridLayout, QSpacerItem, QLineEdit, QWidgetItem, QAction, \
    QBoxLayout, QMessageBox, QWidgetAction
from qgis._core import QgsApplication
from qgis.utils import iface

from .QuickPrint import PrintMapTool
from .config import Config
from .CustomMessageBox import CustomMessageBox
from .OrtoTools import OrtoAddingTool
from .utils import STANDARD_TOOLS, DEFAULT_TABS, tr

from .select_section import SelectSection
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'giap_dynamic_layout.ui'))


class Widget(QWidget, FORM_CLASS):
    editChanged = pyqtSignal(bool)
    printsAdded = pyqtSignal()
    deletePressSignal = pyqtSignal()

    def __init__(self, parent=None):
        super(Widget, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.setupUi(self)
        self.parent = parent  # mainWindow()
        self.tabs = []  # list w tabwidgets
        self.edit_session = False
        self.conf = Config()
        self.save = QMessageBox.Yes
        # Custom Tools
        self.orto_add = False

        self.custom_tabbar = CustomTabBar(tr('New Tab'), self.tabWidget)
        self.tabWidget.setTabBar(self.custom_tabbar)
        self.tabWidget.tabBar().tabBarClicked.connect(self.tab_clicked)
        self.tabWidget.tabBar().tabBarDoubleClicked.connect(
            self.tab_doubleclicked)

    def add_tab(self, label=None):
        """Adds new tab at the end
        :return: tab widget
        """
        if not label:
            label = 'New Tab'
        label = tr(label)

        tab = CustomTab(label, self.tabWidget)
        self.tabs.append(tab)

        # prevent flickering
        self.tabWidget.setUpdatesEnabled(False)

        tab_ind = self.tabWidget.insertTab(
            self.tabWidget.count()-1, tab, label
        )
        if self.edit_session:
            self._section_control(tab_ind)

        self.tabWidget.setCurrentIndex(tab_ind)

        # add button to delete, its edit session so should be visible
        right = self.tabWidget.tabBar().RightSide
        cbutton = QToolButton(self.tabWidget)
        cbutton.setObjectName('giapCloseTab')
        cbutton.setText('x')
        cbutton.setMinimumSize(QSize(16, 16))
        cbutton.setMaximumSize(QSize(16, 16))

        self.tabWidget.tabBar().setTabButton(tab_ind, right, cbutton)
        cbutton.clicked.connect(lambda: self.remove_tab(tab_ind))
        self.tabWidget.setUpdatesEnabled(True)

        return tab_ind, tab

    def remove_tab(self, tind):
        """Removes tab with given tab index"""

        self.tabWidget.removeTab(tind)
        if tind > 0:
            self.tabWidget.setCurrentIndex(tind-1)

    def add_section(self, itab, lab, size=30):
        """Adds new section on tab with label and place for icons
        :itab: int
        :lab: label for section
        :size: int size of button
        :return: section widget
        """
        if itab > -1:
            itab = self.tabWidget.currentIndex()

        cwidget = self.tabWidget.widget(itab)
        if str(lab) in ['', 'False', 'None']:
            lab = tr('New section')
        section = CustomSection(str(lab), self.tabWidget)
        section.installEventFilter(self)
        if size > 30:
            section.set_size(size)

        self._section_control_remove(itab)
        cwidget.lay.addWidget(section)

        # sep = QFrame()
        # sep.setFrameShape(QFrame.VLine)
        # sep.setFrameShadow(QFrame.Raised)
        # sep.setObjectName('giapLine')
        # sep.setMinimumSize(QSize(6, 100))
        # cwidget.lay.addWidget(sep)
        section.setVisible(True)
        self._section_control(itab)

        return section

    def edit_session_toggle(self, ask=False):
        """Show controls for edti session"""

        self.edit_session = not self.edit_session

        self.conf = Config()
        if ask and self.conf.setts['ribbons_config'] != self.generate_ribbon_config():
            self.save = CustomMessageBox(None, tr("Do you want to save your changes?")).button_yes_no()
            if self.save == QMessageBox.Yes:
                self.editChanged.emit(False)
            else:
                self.editChanged.emit(True)
        else:
            self.editChanged.emit(self.edit_session)

        self._tab_controls()

    def _tab_controls(self):
        """ show tab controls"""
        right = self.tabWidget.tabBar().RightSide

        if self.edit_session:
            for i in range(self.tabWidget.count()):
                self.tabWidget.tabBar().tabButton(i, right).show()
                self._section_control(i)
            self._new_tab_tab_control()  # show add tab option
        else:
            self._new_tab_tab_control()  # hide add tab option
            for i in range(self.tabWidget.count()):
                self.tabWidget.tabBar().tabButton(i, right).hide()
                self._section_control(i)

    def _section_control(self, tabind):
        """add buttons to every tab for adding new section"""
        plug_dir = os.path.dirname(__file__)
        lay = self.tabWidget.widget(tabind).lay
        cnt = lay.count()

        # remove button
        it = lay.itemAt(cnt-1)
        if it is not None:
            if isinstance(it.widget(), QPushButton):
                it.widget().hide()
                it.widget().deleteLater()
                QApplication.processEvents()

        if self.edit_session:
            self.frm = QFrame()
            self.frm.setObjectName('giapSectionAdd')
            self.frmlay = QVBoxLayout(self.frm)

            self.secadd = CustomSectionAdd()

            self.secadd.clicked.connect(self.add_user_selected_section)
            self.frmlay.addWidget(self.secadd)

            lay = self.tabWidget.widget(tabind).lay
            cnt = lay.count()
            # there should always be something in layout, (controls)

            for i in range(cnt, -1, -1):
                if isinstance(lay.itemAt(i), QSpacerItem):
                    lay.removeItem(lay.itemAt(i))

            self.tabWidget.widget(tabind).lay.addWidget(self.frm)
            self.tabWidget.widget(tabind).lay.addStretch()

        else:
            self.tabWidget.widget(tabind).setUpdatesEnabled(False)
            self._section_control_remove(tabind)
            self.tabWidget.widget(tabind).lay.addStretch()
            if not isinstance(lay.itemAt(cnt-1), QPushButton):
                gbut = QPushButton()
                gbut.clicked.connect(lambda x: webbrowser.open('www.giap.pl'))
                gbut.setIcon(
                    QIcon(os.path.join(plug_dir, 'icons', 'giap.png'))
                )
                gbut.setCursor(QCursor(Qt.PointingHandCursor))
                gbut.setToolTip("GIAP.pl - Strona WWW")
                gbut.setStyleSheet(
                    'QPushButton{border-width: 0px; width: 220px; height:72px;'
                    'background-color: transparent;}'
                )
                gbut.setIconSize(QSize(220-4, 72-4))
                self.tabWidget.widget(tabind).lay.addWidget(gbut)
            self.tabWidget.widget(tabind).setUpdatesEnabled(True)

    def add_user_selected_section(self):
        """Show dialog to user and adds selected section to current ribbon
            if there should be more cutom tools, here is the place to put them
        """
        self.dlg = SelectSection()
        self.run_select_section()
        responce = self.dlg.exec_()

        if not responce:
            return

        ind = self.tabWidget.currentIndex()
        # selected tools
        selected = [x.text() for x in self.dlg.toolList.selectedItems()]
        self.tabWidget.setUpdatesEnabled(True)
        print_trig = False
        for sel in selected:
            secdef = [x for x in STANDARD_TOOLS if x['label'] == sel][0]
            sec = self.add_section(ind, sel, secdef['btn_size'])
            for btn in secdef['btns']:
                child = self.parent.findChild(QAction, btn[0])
                if child is None:
                    sec.add_action(*btn)
                else:
                    sec.add_action(child, *btn[1:])
                    if btn[0] in ['giapMyPrints', 'giapQuickPrint']:
                        print_trig = True

            if sel == 'Prints' or print_trig:
                self.printsAdded.emit()

        self.tabWidget.setUpdatesEnabled(True)

    def run_select_section(self):
        self.dlg.addSectionTab.clicked.connect(self.next_widget)
        self.dlg.searchToolTab.clicked.connect(self.previous_widget)
        self.dlg.addTool.clicked.connect(self.add_tool_search)
        self.dlg.addSection.clicked.connect(self.add_section_search)
        self.dlg.searchBox.textChanged.connect(self.search_tree)

    def add_tool_search(self):
        self.tabWidget.setUpdatesEnabled(True)
        selected = self.dlg.algorithmTree.selectedAlgorithm()
        sel_ind = self.dlg.algorithmTree.selectedIndexes()
        if not selected and not sel_ind:
            CustomMessageBox(self.dlg, tr("Select tool")).button_ok()
            return
        if not selected:
            CustomMessageBox(self.dlg, tr("Selected item is not a tool")).button_ok()
            return
        sec = self.add_section(self.tabWidget.currentIndex(), selected.group(), 30)
        sec.add_action(selected.id(), 0, 0)
        self.tabWidget.setUpdatesEnabled(True)
        self.dlg.close()

    def add_section_search(self):
        self.tabWidget.setUpdatesEnabled(True)
        selected = self.dlg.algorithmTree.selectedAlgorithm()
        tree_ind = self.dlg.algorithmTree.selectedIndexes()
        if not selected and not tree_ind:
            CustomMessageBox(self.dlg, tr("Select section")).button_ok()
            return
        if selected:
            CustomMessageBox(self.dlg, tr("Selected item is not a section")).button_ok()
            return
        if not self.dlg.algorithmTree.algorithmForIndex(tree_ind[0].child(0, 0)):
            CustomMessageBox(self.dlg, tr("Selected item has sub-section")).button_ok()
            return
        sec = self.add_section(self.tabWidget.currentIndex(), self.dlg.algorithmTree.algorithmForIndex(tree_ind[0].child(0, 0)).group(), 30)
        row = 0
        col = 0
        alg_ind = 0
        alg = self.dlg.algorithmTree.algorithmForIndex(tree_ind[0].child(alg_ind, 0))
        while alg:
            sec.add_action(alg.id(), row, col)
            if row == 1:
                row = 0
                col += 1
            else:
                row += 1
            alg_ind += 1
            alg = self.dlg.algorithmTree.algorithmForIndex(tree_ind[0].child(alg_ind, 0))
        self.tabWidget.setUpdatesEnabled(True)
        self.dlg.close()

    def search_tree(self):
        self.dlg.algorithmTree.setFilterString(self.dlg.searchBox.value())

    def next_widget(self):
        self.dlg.stackedWidget.setCurrentIndex(0)

    def previous_widget(self):
        self.dlg.stackedWidget.setCurrentIndex(1)

    def _section_control_remove(self, tabind):
        lay = self.tabWidget.widget(tabind).lay
        self.tabWidget.setUpdatesEnabled(False)
        for ind in range(lay.count()-1, -1, -1):
            if isinstance(lay.itemAt(ind), QSpacerItem):
                lay.removeItem(lay.itemAt(ind))
                continue
            it = lay.itemAt(ind)
            if it.widget() is not None:
                if it.widget().objectName() == 'giapSectionAdd':
                    it.widget().hide()
                    lay.removeItem(it)
        QApplication.processEvents()
        self.tabWidget.setUpdatesEnabled(True)

    def _new_tab_tab_control(self):
        """Pseudo tab to control adding fully feature tab"""

        self.tabWidget.setUpdatesEnabled(False)
        if self.edit_session:
            tab = QWidget()
            tab.setObjectName('giapAddNewTabControl')
            self.tabWidget.addTab(tab, '+')
        else:
            last_tab = self.tabWidget.tabBar().count() - 1
            if self.tabWidget.widget(last_tab).objectName() == \
                    'giapAddNewTabControl':
                self.tabWidget.removeTab(last_tab)
        self.tabWidget.setUpdatesEnabled(True)

    def tab_doubleclicked(self, ind):
        if not self.edit_session:
            return
        self.tabWidget.tabBar().editTab(ind)

    def tab_clicked(self, ind):
        if self.edit_session:
            if ind == self.tabWidget.tabBar().count() - 1:
                self.add_tab()

    def eventFilter(self, watched, ev):
        # turn off dragging while not in edit session
        if isinstance(watched, CustomSection) and not self.edit_session:
            if ev.type() == QEvent.MouseMove:
                return True
        return super().eventFilter(watched, ev)

    def keyPressEvent(self, e):
        if self.edit_session:
            if e.key() == Qt.Key_Delete:
                self.deletePressSignal.emit()

    def generate_ribbon_config(self):
        """ return ribbon setup to save in user config
        (for detail structure look in config file)
        return: list
        """
        riblist = []
        active_ind = self.tabWidget.currentIndex()
        for ind in range(self.tabWidget.count()):
            self.tabWidget.setCurrentIndex(ind)
            wid = self.tabWidget.widget(ind)
            if not isinstance(wid, CustomTab):
                continue
            tdict = wid.return_tab_config()
            # if tab name not edited by user, save eng version
            tab_name = self.tabWidget.tabText(ind)
            trans_tab_names = [tr(key) for key in DEFAULT_TABS]
            if tab_name in trans_tab_names:
                tab_name = DEFAULT_TABS[trans_tab_names.index(tab_name)]
            tdict['tab_name'] = tab_name
            riblist.append(tdict)
        self.tabWidget.setCurrentIndex(active_ind)
        return riblist


class CustomTabBar(QTabBar):
    def __init__(self, label='New Tab', parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self._editor = QLineEdit(self)
        self._editor.setWindowFlags(Qt.Popup)
        self._editor.setFocusProxy(self)
        self._editor.editingFinished.connect(self.handleEditingFinished)
        self._editor.installEventFilter(self)

    def eventFilter(self, widget, event):
        if ((event.type() == QEvent.MouseButtonPress and
             not self._editor.geometry().contains(event.globalPos())) or
            (event.type() == QEvent.KeyPress and
             event.key() == Qt.Key_Escape)):
            self.handleEditingFinished()
            self._editor.hide()
        return super().eventFilter(widget, event)

    def editTab(self, index):
        rect = self.parent().tabBar().tabRect(index)
        self._editor.setFixedSize(rect.size())
        self._editor.move(self.parent().mapToGlobal(rect.topLeft()))
        self._editor.setText(self.parent().tabText(index))
        if not self._editor.isVisible():
            self._editor.show()

    def handleEditingFinished(self):
        index = self.parent().currentIndex()
        if index >= 0:
            self._editor.hide()
            self.parent().setTabText(index, self._editor.text())


class CustomTab(QWidget):
    def __init__(self, lab, parent=None):
        super(CustomTab, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.lab = lab
        self.lay = QHBoxLayout()
        self.lay.setSpacing(0)
        self.lay.setMargin(6)
        self.setLayout(self.lay)
        self.setObjectName('giapTab')

        self.lay.addStretch()
        self.lay.setDirection(QBoxLayout.LeftToRight)

        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        e.accept()

    def dragMoveEvent(self, e):
        e.accept()

    def dropEvent(self, e):
        # accept only Custom Sections
        if not isinstance(e.source(), CustomSection):
            if isinstance(e.source(), CustomToolButton):
                e.source().drag_state = False
            e.setAccepted(False)
            return

        try:
            lay = e.source().parent().lay
        except AttributeError:
            return

        source = None
        for i in range(lay.count()):
            if not isinstance(lay.itemAt(i).widget(), CustomSection):
                continue

            it = lay.itemAt(i)
            if it.widget() is e.source():
                source = i
                break

        if source is None:
            return
        lay.takeAt(lay.count()-1)
        addsec = lay.takeAt(lay.count()-1)
        item = lay.takeAt(i)
        lay.addItem(item)
        lay.addItem(addsec)
        lay.addStretch()
        e.setAccepted(True)

    def return_tab_config(self):
        """Returns config for current tab with all sections,
        (description in config file)
        :return: dict
        """
        sec_conf = []
        for ind in range(self.lay.count()):
            it = self.lay.itemAt(ind)
            if it is None:
                continue
            wid = it.widget()
            if not isinstance(wid, CustomSection):
                continue

            sec_conf.append(wid.return_section_config())

        return {
            'tab_name': self.lab,
            'sections': sec_conf,
        }


class CustomSection(QWidget):
    def __init__(self, name='New Section', parent=None):
        super(CustomSection, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.edit = True
        self.setAcceptDrops(True)
        self.setMaximumSize(QSize(99999, 110))
        self.setMinimumSize(QSize(70, 110))

        if parent is not None:
            parent.parent().editChanged.connect(self.edit_toggle)
            parent.parent().deletePressSignal.connect(self.key_pressed)

        self.setObjectName('giapSection')

        # target of drop
        self.target = None

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setContentsMargins(7, 0, 7, 0)
        self.button_size = 30

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.horizontalLayout_2.setSpacing(0)

        self.clabel = CustomLabel(tr(name), self)
        self.clabel.setObjectName("giapSectionLabel")
        self.clabel.setMaximumSize(QSize(100000, 20))
        self.clabel.setMinimumSize(QSize(50, 20))
        self.clabel.setAlignment(Qt.AlignCenter)
        charakter = len(self.clabel.text())
        self.clabel.setMinimumSize(QSize(charakter * 8, 20))

        self.pushButton_close_sec = QToolButton(self)
        self.pushButton_close_sec.setObjectName("giapSectionClose")
        self.pushButton_close_sec.setText('x')
        self.pushButton_close_sec.setStyleSheet(
            'border-radius: 3px; font: 7pt;'
        )
        self.pushButton_close_sec.show()
        self.pushButton_close_sec.setMaximumSize(QSize(18, 18))

        self.horizontalLayout_2.addWidget(self.clabel)
        self.horizontalLayout_2.addWidget(self.pushButton_close_sec)
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.VLine)
        self.sep.setFrameShadow(QFrame.Raised)
        self.sep.setObjectName('giapLine')
        self.sep.setMinimumSize(QSize(6, 100))

        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.gridLayout = QGridLayout()
        self.gridLayout.setSpacing(10)
        self.gridLayout.setContentsMargins(0,6,0,8)
        self.gridLayout.setObjectName(u"gridLayout")

        self.verticalLayout.addLayout(self.gridLayout)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout.addLayout(self.verticalLayout)
        self.horizontalLayout.addWidget(self.sep)
        self.horizontalLayout.setContentsMargins(4, 0, 4, 2)

        self.setLayout(self.horizontalLayout)
        self.pushButton_close_sec.clicked.connect(self.unload)

    def unload(self):
        self.hide()
        self.deleteLater()
        QApplication.processEvents()

    def return_section_config(self):
        """return config for current section
        :return: {}
        """
        blist = []
        for row in range(self.gridLayout.rowCount()):
            for col in range(self.gridLayout.columnCount()):
                it = self.gridLayout.itemAtPosition(row, col)
                if it is None:
                    continue
                itw = it.widget()
                ind = self.gridLayout.indexOf(itw)
                wid = self.gridLayout.itemAt(ind).widget()
                if wid.objectName()[:4].lower() == 'giap' or not wid.actions():
                    act = wid.objectName()
                else:
                    act = wid.actions()[0].objectName()
                blist.append([act, row, col])

        lab = self.clabel.text()
        untra_lab = [ll['id'] for ll in STANDARD_TOOLS
                     if tr(ll['label']) == lab]
        if untra_lab:
            lab = untra_lab[0]
        return {
            'label': lab, 'btn_size': self.button_size, 'btns': blist,
        }

    def edit_toggle(self, state):
        if state:
            self.show_edit_options()
        else:
            self.hide_edit_options()

    def key_pressed(self):
        """user pressed delete, and we are in edit session"""
        if not self.edit:
            return

        # remove selected buttons
        for col in range(self.gridLayout.columnCount()):
            for row in [0, 1]:
                it = self.gridLayout.itemAtPosition(row, col)
                if it is None:
                    continue
                if not it.widget().selected:
                    continue

                ind = self.gridLayout.indexOf(it.widget())
                wid = self.gridLayout.takeAt(ind)
                wid.widget().turn_off_edit()
                wid.widget().deleteLater()

        self.clean_grid_layout()

    def clean_grid_layout(self):
        """ move all icons to left, after some where deleted"""
        items = [[], []]  # both rows
        for col in range(self.gridLayout.columnCount()):
            for row in [0, 1]:
                itl = self.gridLayout.itemAtPosition(row, col)
                if itl is None:
                    continue
                it = itl.widget()
                ind = self.gridLayout.indexOf(it)
                it = self.gridLayout.takeAt(ind)
                if it is not None:
                    items[row].append(it)

        for irow, row in enumerate(items):
            for icol, it in enumerate(row):
                if isinstance(it, QWidgetItem):
                    self.gridLayout.addItem(it, irow, icol, 1, 1)
                else:
                    self.gridLayout.addWidget(it, irow, icol, 1, 1)
        self.gridLayout.update()
        # self.gridLayoutWidget.adjustSize()

    def add_action(self, action, row, col):
        self.tbut = CustomToolButton(self)
        if isinstance(action, QAction):
            self.tbut.setObjectName('gp_'+action.objectName())
            self.tbut.setDefaultAction(action)
            self.tbut.org_state = action.isEnabled()
        elif QgsApplication.processingRegistry().algorithmById(action):
            alg = QgsApplication.processingRegistry().algorithmById(action)
            self.tbut.setObjectName(alg.id())
            newAct = QAction(alg.icon(), alg.displayName(), self)

            def open_window():
                execAlgorithmDialog(newAct.objectName())

            newAct.setObjectName(alg.id())
            newAct.triggered.connect(open_window)
            self.tbut.setDefaultAction(newAct)
            self.tbut.setIcon(alg.icon())
            self.tbut.org_state = True
            self.tbut.setText(alg.id())
        elif isinstance(action, str):
            self.tbut.setObjectName(action)
            self.set_custom_action()

        self.tbut.setMaximumSize(QSize(self.button_size, self.button_size))
        self.tbut.setMinimumSize(QSize(self.button_size, self.button_size))
        if self.button_size == 30:
            self.tbut.setIconSize(
                QSize(self.button_size-4, self.button_size-4)
            )
        else:
            self.tbut.setIconSize(
                QSize(self.button_size-5, self.button_size-5)
            )
        self.tbut.setEnabled(True)
        self.tbut.installEventFilter(self)
        self.gridLayout.addWidget(self.tbut, row, col, 1, 1)

        return self.tbut

    def set_custom_action(self):
        oname = self.tbut.objectName()
        dirnm = os.path.dirname(__file__)

        if oname == 'giapWMS':
            self.orto_add = OrtoAddingTool(self, self.tbut)
            connect_orto = self.orto_add.connect_ortofotomapa_group
            self.tbut.setIcon(
                QIcon(os.path.join(dirnm, 'icons', 'orto_icon2.png'))
            )
            for service in self.orto_add.services:
                service.orto_group_added.connect(connect_orto)

        if oname == 'giapCompositions':
            # this on will be find by compositions after loading
            # documentation purposes
            self.tbut.setIcon(
                QIcon(os.path.join(dirnm, 'icons', 'compositions_giap.png'))
            )
            self.tbut.setToolTip(tr("Composition settings"))

        if oname == "giapQuickPrint":
            plugin_dir = os.path.dirname(__file__)
            self.quick_print = PrintMapTool(iface, self)
            self.tbut.clicked.connect(self.quick_print.run)
            self.tbut.setToolTip(tr("Map fast print"))
            self.tbut.setIcon(QIcon(f'{plugin_dir}/icons/quick_print.png'))
    def unload_custom_actions(self):
        if self.orto_add:
            self.orto_add.disconnect_ortofotomapa_group()

    def change_label(self, lab):
        """Changes label
        :lab: str
        """
        if isinstance(lab, str) and lab not in ['', 'None', 'False']:
            self.label.setText(lab)

    def set_size(self, sz):
        """change size of button
        :sz: int
        """
        self.button_size = sz

    def _get_items(self):
        """return list with item stored in gridlayout
        :return: [[tool, tool], [tool, tool]]
        """
        items = [[], []]  # both rows
        for col in range(self.gridLayout.columnCount()):
            for row in [0, 1]:
                it = self.gridLayout.itemAtPosition(row, col)
                if it is not None:
                    items[row].append(it.widget())
        return items

    def get_toolbutton_layout_index_from_pos(self, pos):
        for i in range(self.gridLayout.count()):
            rect = self.gridLayout.itemAt(i).widget()
            # recalculate rect to compatible coord system
            rect_ok = QRect(0, 0, rect.width(), rect.height())
            if rect_ok.contains(rect.mapFromGlobal(pos)) and \
                    i != self.target:
                return i

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonPress:
            self.mousePressEvent(event)
        elif event.type() == QEvent.MouseMove and \
                isinstance(watched, CustomSection):
            self.mouseMoveEvent(event)
        elif event.type() == QEvent.MouseButtonRelease:
            self.mouseReleaseEvent(event)

        # prevent default action from qtoolbutton
        if isinstance(watched, CustomToolButton) and self.edit:
            if event.type() == QEvent.MouseButtonPress:
                watched.setDown(False)

        if event.type() == QEvent.HoverEnter:
            # if tooltip should show wtihout delay code place here
            pass
        return super().eventFilter(watched, event)

    def mouseReleaseEvent(self, event):
        event.accept()

    def mouseMoveEvent(self, e):
        print('mouse event')
        if not self.edit:
            return

        drag = QDrag(self)
        drag.setDragCursor(QPixmap("images/drag.png"), Qt.MoveAction)
        mimedata = QMimeData()

        pixmap = QPixmap(self.size())  # Get the size of the object
        painter = QPainter(pixmap)  # Set the painter’s pixmap
        painter.drawPixmap(self.rect(), self.grab())
        painter.end()

        drag.setMimeData(mimedata)
        drag.setHotSpot(e.pos())
        drag.setPixmap(pixmap)
        drag.exec_(Qt.MoveAction)
        e.accept()

    def dragEnterEvent(self, event):
        event.accept()

    def dropEvent(self, event):  # noqa
        gpos = QCursor().pos()

        if isinstance(event.source(), CustomToolButton):
            # check if source and target are in the same gridlayout
            if event.source().parent() is not self:
                event.source().drag_state = False
                return

            # swap toolbuttons
            # get origin button
            source = self.get_toolbutton_layout_index_from_pos(gpos)
            glay = event.source().parent().gridLayout
            self.target = None
            for i in range(glay.count()):
                it = glay.itemAt(i)
                if it.widget() is event.source():
                    self.target = i
                    break

            if source == self.target:
                try:
                    it.widget().drag_state = False
                except Exception:
                    pass
                return

            if None not in [source, self.target]:
                # swap qtoolbuttons
                i, j = max(self.target, source), min(self.target, source)
                p1 = self.gridLayout.getItemPosition(i)
                p2 = self.gridLayout.getItemPosition(j)
                it1 = self.gridLayout.takeAt(i)
                it2 = self.gridLayout.takeAt(j)
                it1.widget().setDown(False)
                it2.widget().setDown(False)
                it1.widget().drag_state = False
                it2.widget().drag_state = False
                self.gridLayout.addItem(it1, *p2)
                self.gridLayout.addItem(it2, *p1)

        if isinstance(event.source(), CustomSection):
            lay = self.parent().lay

            target = None
            source = None
            for i in range(lay.count()):
                if not isinstance(lay.itemAt(i).widget(), CustomSection):
                    continue

                it = lay.itemAt(i)
                if it.widget() is event.source():
                    source = i
                if it.widget().geometry().contains(
                        it.widget().parent().mapFromGlobal(gpos)):
                    target = i

            if source == target or None in [source, target]:
                return

            item = lay.takeAt(source)
            if target > source:
                target -= 1

            it_list = []
            for i in range(lay.count()-1, target-1, -1):
                it_list.append(lay.takeAt(i))
            it_list.reverse()
            lay.addItem(item)
            for it in it_list:
                lay.addItem(it)
            self.target = target

    def show_edit_options(self):
        self.pushButton_close_sec.show()
        self.edit = True
        self.clean_grid_layout()
        itms = self._get_items()
        for row in [0, 1]:
            for it in itms[row]:
                it.turn_on_edit()
                it.edit = True

    def hide_edit_options(self):
        self.pushButton_close_sec.hide()
        self.edit = False
        self.clean_grid_layout()
        itms = self._get_items()
        for row in [0, 1]:
            for it in itms[row]:
                it.turn_off_edit()


class CustomToolButton(QToolButton):
    def __init__(self, parent):
        super(CustomToolButton, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.edit = True
        self.selected = False
        self.selected_style = '*{border: 3px solid red}'
        self.org_state = True  # True - enabled for click outside edit sesion
        self.drag_state = False

    def eventFilter(self, widget, event):
        if event.type() == QEvent.MouseButtonRelease and self.edit:
            return True
        if self.edit and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                return True
        return super().eventFilter(widget, event)

    def turn_on_edit(self):
        """ toggle standard behaviour, from clicking to select"""
        self.org_state = self.isEnabled()
        self.setEnabled(True)
        self.blockSignals(True)
        self.setDown(False)

    def turn_off_edit(self):
        """ toggle standard behaviour, from clicking to select"""
        self.setStyleSheet('')
        self.selected = False
        self.setEnabled(self.org_state)
        self.blockSignals(False)
        self.edit = False

    def mouseClickEvent(self, event):
        if self.edit:
            event.accept()
            event.source.setDown(False)
        else:
            super(CustomToolButton, self).mouseClickEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.edit:
            if self.selected:
                self.selected = False
                self.setStyleSheet('')
            else:
                self.setStyleSheet(self.selected_style)
                self.selected = True
            self.drag_state = False

    def mouseMoveEvent(self, e):
        if not self.edit or not self.drag_state:
            return
        drag = QDrag(self)
        drag.setDragCursor(QPixmap("images/drag.png"), Qt.MoveAction)
        mimedata = QMimeData()

        pixmap = QPixmap(self.size())  # Get the size of the object
        painter = QPainter(pixmap)  # Set the painter’s pixmap
        painter.drawPixmap(self.rect(), self.grab())
        painter.end()

        drag.setMimeData(mimedata)
        drag.setPixmap(pixmap)
        drag.setHotSpot(e.pos())
        drag.exec_(Qt.MoveAction)

    def mousePressEvent(self, event):
        if self.edit:
            event.accept()
            self.setDown(False)
            self.drag_state = not self.drag_state
            return
        else:
            super(CustomToolButton, self).mousePressEvent(event)

    def dragEnterEvent(self, event):
        event.accept()


class CustomSectionAdd(QToolButton):
    def __init__(self, parent=None):
        super(CustomSectionAdd, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setObjectName('giapSectionAddButton')
        self.setMinimumSize(QSize(30, 30))
        self.setMaximumSize(QSize(30, 30))
        self.setText('+')
        self.setStyleSheet('font: 14px; font-weight: bold;')

        self.button_size = 30

    def bigButtons(self):
        """Set size of tools button to big"""
        self.button_size = 60


class CustomLabel(QLabel):
    def __init__(self, lab, parent=None):
        super(CustomLabel, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setText(lab)
        self.setStyleSheet(
            'font: 10pt "Segoe UI"; font-weight: bold; '
        )
        self.cinput = QLineEdit(self)
        self.cinput.setWindowFlags(Qt.Popup)
        self.cinput.setFocusProxy(self)
        self.cinput.editingFinished.connect(self.handleEditingFinished)
        self.cinput.installEventFilter(self)
        self.setAlignment(Qt.AlignCenter)

    def mousePressEvent(self, event):
        if not self.parent().edit:
            return

        rect = self.rect()
        self.cinput.setFixedSize(rect.size())
        self.cinput.move(self.mapToGlobal(rect.topLeft()))
        self.cinput.setText(self.text())
        if not self.cinput.isVisible():
            self.cinput.show()

    def eventFilter(self, widget, event):
        if ((event.type() == QEvent.MouseButtonPress and
             not self.cinput.geometry().contains(event.globalPos())) or
            (event.type() == QEvent.KeyPress and
             event.key() == Qt.Key_Escape)):
            self.handleEditingFinished()
            self.cinput.hide()
        return super().eventFilter(widget, event)

    def handleEditingFinished(self):
        self.cinput.hide()
        self.setText(self.cinput.text())
        charakter = len(self.cinput.text())
        self.setMinimumSize(QSize(charakter*8, 20))
