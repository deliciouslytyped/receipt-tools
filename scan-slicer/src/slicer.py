#TODO autosave project
#TODO really needs reordering, project saving, also there is a hard to repro crash somewhere
#TODO workable reordering, / alt: numbering range spec
#TODO front/back
#TODO stitching
#TODO rotate
#TODO drag margin for reordering slices
# TODO  drag slice preview to move it
#TODO need to add slicing to icons in catalog?
#TODO capture scroll / mouse events against slices previews
#TODO something still screwy with rotation and resizing
#TODO remove dead sizing code
import collections
#Q keyboard event for rapid dev
from math import sqrt
from typing import *
from pathlib import Path

from PyQt6.QtCore import pyqtSignal, QModelIndex, Qt, QSize, QRect, QItemSelectionModel, qDebug, QObject, QEvent, \
  QPoint, QRectF, QPointF, QSizeF, QCollator, QMimeData
from PyQt6.QtGui import QIcon, QPixmap, QImage, QMouseEvent, QPainter, QBrush, QColor, QKeyEvent, QPen, QWheelEvent, \
  QResizeEvent, QTransform, QDragLeaveEvent, QDropEvent, QStandardItemModel
from PyQt6.QtWidgets import QWidget, QListWidget, QListWidgetItem, QApplication, QVBoxLayout, QSizePolicy, \
  QGraphicsView, QPushButton, QFileDialog, QHBoxLayout, QToolBar, QGraphicsScene, QGraphicsPixmapItem, \
  QStyledItemDelegate, QStyle, QAbstractItemView, QGraphicsSceneMouseEvent, QGraphicsItem, QGraphicsRectItem, \
  QWidgetItem, QTextEdit, QLineEdit, QLabel, QStyleOptionViewItem, QLayout
import code
import re

class QGlobalWidget(QWidget):
  def keyPressEvent(self, a0: QKeyEvent) -> None:
    if a0.key() == Qt.Key.Key_Q:
      exit()
    else:
      super().keyPressEvent(a0)

def mkCollator():
  qc = QCollator()
  qc.setNumericMode(True)
  return qc

class GUICatalog(QGlobalWidget):
  #class QListWidgetItemSorting(QListWidgetItem):
  #  qc = mkCollator()
  #
  #  #def __lt__(self, other):
  #  #  res = self.qc.compare(self.text(), other.text())
  #  #  return res

  class ThumbListWidget(QListWidget):
    pathChanged = pyqtSignal([str])
    filterChanged = pyqtSignal([str])
    mySelectionChanged = pyqtSignal([str])

    # overriding __lt__ on the item for some reason eventually causes a segfault in the sort
    #def sortItems(self, order: Qt.SortOrder = ...) -> None:
    #  self.model().

    def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self.setSpacing(10)
      #self.setFlow(QListWidget.Flow.TopToBottom)
      #self.setGridSize(QSize(128, 128))
      #self.setViewMode(QListWidget.ViewMode.IconMode)
      self._path = None
      self.pathChanged.connect(self.updateImagesUsing)
      def filterChanger(f):
        self.filter = f
        if self._path:
          self.updateImagesUsing(self._path)
      self.filterChanged.connect(filterChanger)
      self.currentItemChanged.connect(self.dispatchSelected)
      #self.model().sor
      #self.setSortingEnabled(True) #TODO does this even do anything?
      #self.sortItems(Qt.SortOrder.AscendingOrder)
      self.filter = None

      self.sp = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
      self.sp.setHorizontalStretch(1)
      self.setSizePolicy(self.sp)
      #TODO why doesnt this work?
      #self.sizePolicy().setHorizontalPolicy(QSizePolicy.Policy.Minimum)
      #self.sizePolicy().setHorizontalStretch(1)

    #TODO
    def dispatchSelected(self, current: QListWidgetItem, previous):
      if current:
        userdata = current.data(Qt.ItemDataRole.UserRole)
        self.mySelectionChanged.emit(userdata)

    def normalizeName(self, s):
      return re.sub("[0-9]+", lambda x: f"{int(x.group()):05}", s)

    def updateImagesUsing(self, path: str):
      self.clear() #TODO caching
      try:
        filt = re.compile(self.filter)
      except re.error:
        return # No change
      for p in sorted(Path(path).iterdir(), key=lambda x: self.normalizeName(str(x))):
        #if any([str(p).lower().endswith(x) for x in ["jpg", "png"]]):
        if re.match(filt, p.name):
          i = QListWidgetItem(QIcon(str(p)), str(p.name))
          i.setData(Qt.ItemDataRole.UserRole, str(p))
          #i.
          #i.model(.setData(QStandardItemModel().sortRole(), self.normalizeName(str(p))) #TODO hack to get sorting to work because of the __lt__ segfault issue
          self.addItem(i)  # TODO correct parent?
      #self.sortItems()
      #  i = QListWidgetItem(QIcon(str(p)), str(p.name))
      #  i.setData(Qt.ItemDataRole.UserRole, str(p))
      #  self.addItem(i)  # TODO correct parent?

    #TODO toggle select
    # Mark front side
    def onLeftClick(self):
      pass

    # Mark back side
    def onRightClick(self):
      pass

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.build()

  def build(self):
    self.resize(400, 800)

    l = QVBoxLayout()
    self.setLayout(l)
    self.filtField = QLineEdit("paper\.[0-9]+\.jpg")
    l.addWidget(self.filtField)
    self.thumbs = GUICatalog.ThumbListWidget(parent=self)
    def updateFilter():
      self.thumbs.filterChanged.emit(self.filtField.text())
    self.filtField.textChanged.connect(updateFilter)
    updateFilter()
    l.addWidget(self.thumbs)

    #b = QPushButton("Open", parent=self)
    #l.addWidget(b)
    #b.clicked.connect(QFileDialog.open)

class Catalog(GUICatalog):
  class InvalidSelection(ValueError):
    pass

  def setDirectory(self, path):
    self.thumbs._path = path
    self.thumbs.pathChanged.emit(path)

  def startSlicing(self, selection):
    if len(selection) < 1 or len(selection) > 2: #TODO technically could be generalized but paper has two sides
      raise Catalog.InvalidSelection

    self.application.launchSlicer(selection)

class SlicerRoot:
  dbgverb = False
  class ImageStore:
    def __init__(self):
      self.images = dict()

  class StitchList(QListWidget):
    def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self.build()

      self.setDragEnabled(True)
      self.setAcceptDrops(True)
      self.setDropIndicatorShown(True)
      self.setFlow(QListWidget.Flow.LeftToRight)
      self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
      self.setDefaultDropAction(Qt.DropAction.MoveAction)

      self.setViewMode(QListWidget.ViewMode.IconMode)
      self.setFlow(QListWidget.Flow.LeftToRight)

      self.setSizeAdjustPolicy(QListWidget.SizeAdjustPolicy.AdjustToContents)

      #self.dropqueue = collections.deque()
      self.ownItem: QListWidgetItem = None
      self.draggingWhat = None

    def setOwnItem(self, p):
      self.ownItem = p
    def build(self):
      pass

    #TODO why is it using qabstractscrollareas viewportsizehint instead of qlistviews?
    def viewportSizeHint(self) -> QSize:
      # see qt source
      pls = QStyleOptionViewItem();
      self.initViewItemOption(pls);
      w, h = 0, 0
      for row in range(self.model().rowCount()):
        idx = self.model().index(0)
        sh = self.itemDelegateForIndex(idx).sizeHint(pls, idx)
        w += sh.width() # TODO if top down left to right etc
        h = max(h, sh.height())
      return QSize(w, h)

    def dropEvent(self, event: QDropEvent) -> None:
      qDebug("dropev")
      src = event.source()
      if isinstance(src, SlicerRoot.StitchList) and "myrow" in event.mimeData().formats() \
              and src.item(int(bytearray(event.mimeData().data("myrow")).decode("ascii"))) != None: #TODO instead of spending time debugging this more im just going to cancel the symptoms
        parentList: SlicerRoot.GUISlicesPreview = src.ownItem.listWidget()
        row = int(bytearray(event.mimeData().data("myrow")).decode("ascii"))
        qDebug("crashrow %s" % row)
        item = src.item(row) #TODO there are cases where row is -1 and there are cases where row is a number but the entry isnt valid #TODO so this is probably two different bugs?
        qDebug("crashitem %s" % item)
        widget = src.itemWidget(item) #TODO race, should be after next line?
        item2 = src.takeItem(row)
        assert(item2 == item)
        item = item2 #TODO there is a bug where these are both null, is the myrow set wrong? or race condition with removal?
        src.model().layoutChanged.emit()
        self.addItem(item) #TODO is it safe to "reparent" items?
        SlicerRoot.GUISlicesPreview.resz2(item)

        ww = QWidget()  # reparenting hack
        l3 = QVBoxLayout()
        ww.setLayout(l3)

        childwidg = widget.property("childthing")
        l3.addWidget(childwidg)
        ww.setProperty("childthing", childwidg)

        self.setItemWidget(item, ww)
        self.model().layoutChanged.emit()
        if src.model().rowCount() == 0:
          parentList.takeItem(parentList.row(src.ownItem))
          parentList.model().layoutChanged.emit()

        parentList.rectToItem[item.data(Qt.ItemDataRole.UserRole+4)] = (self.ownItem, item) #TODO i think I dont need to update ownitem
        newgrp = parentList.row(self.ownItem)
        newrow = item.listWidget().row(item)
        parentList.updateSliceIdx(newgrp, newrow)

      #elif isinstance(src, SlicerRoot.GUISlicesPreview) and "myrow" in event.mimeData().formats():
      #  row = int(bytearray(event.mimeData("myrow").data("myrow")).decode("ascii"))
      #  item = src.takeItem(row)
      #  self.addItem(item)

      event.mimeData().removeFormat('application/x-qabstractitemmodeldatalist')
      super().dropEvent(event)
      self.model().layoutChanged.emit()  # TODO idk why this doesnt work by itself

    def dropMimeData(self, index: int, data: QMimeData, action: Qt.DropAction) -> bool:
      qDebug("mimedrop %s %s %s" % (index, data, action))
      return super().dropMimeData(index, data, action)

    def setState(self, state: 'QAbstractItemView.State') -> None:
      if state != QAbstractItemView.State.DraggingState and self.draggingWhat is not None:
        self.draggingWhat = None
      super().setState(state)

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
      super().mouseMoveEvent(e) #TODO recheck order here
      if self.state() == QAbstractItemView.State.DraggingState:
        qDebug("position %s" % e.position())
        if self.indexAt(e.position().toPoint()).row() != self.draggingWhat:
          qDebug("WTF WRONG ROW") #TODO should really debug this but instead im just gonna actively set it #TODO i.e. there is a crash mediated here
        #if self.draggingWhat is None: #TODO bug Is there any way for the source row to change without going through the setstate reset??
        #  self.draggingWhat = self.indexAt(e.position().toPoint()).row()
        #  print("", end="")
        self.draggingWhat = self.indexAt(e.position().toPoint()).row()


    def mimeData(self, items: Iterable[QListWidgetItem]) -> QMimeData:
      data = super().mimeData(items)
      #data.setData("myrow", bytearray(str(self.ownItem.listWidget().row(self.ownItem)).encode("ascii")))
      qDebug("crashsearch is draggingwhat invalid %s %s" % (self.draggingWhat, self.item(self.draggingWhat)))
      data.setData("myrow", bytearray(str(self.draggingWhat).encode("ascii")))
      return data

    #def startDrag(self, supportedActions: Qt.DropAction) -> None:
    #  super().startDrag(supportedActions)

    #def receive(self, item, ev: QDropEvent):
    #  ev.mimeData().setData("protocolstate", "haveitem")
    #  self.dropqueue.append(item)
    #  self.dropEvent(ev)

    #def dropEvent(self, event: QDropEvent) -> None:
    #  qDebug("dropev")
    #  mime = event.mimeData()
    #  if mime.data("protocolstate") == "begindrop":
    #    itemref = mime.data("itemref")
    #    self.request.emit(self, event, itemref)
    #  elif mime.data("protocolstate") == "haveitem":
    #    item = self.dropqueue.pop()
    #    self.model().layoutChanged.emit() #TODO idk why this doesnt work by itself
    #    super().dropEvent(event)
    #  else:
    #    super().dropEvent(event)


    #def dropMimeData(self, index: int, data: QMimeData, action: Qt.DropAction) -> bool:
    #  qDebug("mimedrop %s %s %s" % (index, data, action))
    #  super().dropMimeData(index, data, action)

    def onDrop(self):
      # reparent widget to list
      # update numbering
      pass

  class GUISlicesPreview(QListWidget): #TODO slicePairItem
    def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self.build()
      self.setSpacing(10)
      self.setFlow(QListWidget.Flow.LeftToRight)
      self.setViewMode(QListWidget.ViewMode.IconMode)
      #self.setGridSize(QSize(128, 128))
      self.rectToGView: Dict[QGraphicsRectItem, QGraphicsView] = dict()
      self.rectToItem: Dict[QGraphicsRectItem, Tuple[QListWidgetItem, QListWidgetItem]] = dict()

      self.setDragEnabled(True)
      self.setAcceptDrops(True)
      self.setDropIndicatorShown(True)
      self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
      self.setDefaultDropAction(Qt.DropAction.MoveAction)

      self.offset = 0


    def dropEvent(self, event: QDropEvent) -> None:
      qDebug("dropev")
      src = event.source()
      #if isinstance(src, SlicerRoot.StitchList) and "myrow" in event.mimeData().formats():
      #  row = int(bytearray(event.mimeData().data("myrow")).decode("ascii"))
      #  item = src.ownItem.listWidget().takeItem(row)
      #  self.addItem(item)
      #  event.mimeData().removeFormat('application/x-qabstractitemmodeldatalist')
      #elif isinstance(src, SlicerRoot.GUISlicesPreview) and "myrow" in event.mimeData().formats():
      #  row = int(bytearray(event.mimeData("myrow").data("myrow")).decode("ascii"))
      #  item = src.takeItem(row)
      #  self.addItem(item)
      #  event.mimeData().removeFormat('application/x-qabstractitemmodeldatalist')

      super().dropEvent(event)
      self.model().layoutChanged.emit()  # TODO idk why this doesnt work by itself

    def dropMimeData(self, index: int, data: QMimeData, action: Qt.DropAction) -> bool:
      qDebug("mimedrop %s %s %s" % (index, data, action))
      return super().dropMimeData(index, data, action)

    def build(self):
      pass

    @staticmethod
    def resz2( item):
      h, w = 0, 0
      widg = item.listWidget()
      for j in range(widg.model().rowCount()):
        s = widg.sizeHintForIndex(widg.model().index(j))
        h = max(s.height(), h)
        w += s.width()
      widg.ownItem.setSizeHint(QSize(w+40,h+40))
      widg.ownItem.listWidget().model().layoutChanged.emit()

    @staticmethod
    def reszGroup(gitem, listw):
      h, w = 0, 0
      for j in range(listw.model().rowCount()):
        s = listw.sizeHintForIndex(listw.model().index(j))
        h = max(s.height(), h)
        w += s.width()
      gitem.setSizeHint(QSize(w+40,h+40))
      gitem.listWidget().model().layoutChanged.emit()

    def _setSize(self, rectItem, size, i: QListWidgetItem, v):
      #TODO these sizehints are wrong now becase of the subwidgets
      #i.setSizeHint(QSizeF(size.width() / 3, size.height() / 3 + 60).toSize()) #TODO the +30 is a hardcoded hack fix ... attempt
      i.setSizeHint(QSizeF(size.width() / 3, size.height() / 3).toSize())
      #qDebug("sizehint %s" % i.sizeHint())
      # i.setSizeHint(size)
      i.listWidget().model().layoutChanged.emit()
      v.fitInView(rectItem.sceneBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
    def setItemSize(self, rectItem, i, v):
      size = rectItem.sceneBoundingRect().size().toSize()
      self._setSize(rectItem, size, i, v)

    def setItemSizeRot(self, rectItem, i, v, angle):
      newRect = QTransform().rotate(-angle).mapRect(rectItem.sceneBoundingRect())
      size = newRect.size().toSize()
      self._setSize(rectItem, size, i, v)

    def updateSliceIdx(self, oldgrp, oldrow):
      for grp in range(oldgrp, self.model().rowCount()):
        grpitem = self.item(grp)
        grpwid: QListWidget = self.itemWidget(grpitem).property("childthing")
        for row in range(oldrow, grpwid.model().rowCount()):
          le: QLineEdit = grpwid.item(row).data(Qt.ItemDataRole.UserRole + 2)
          if row > 0:
            le.setText("splice_{}".format(le.text().split("_")[1]))
          else:
            le.setText("{:03}_{}".format(grp + self.offset, le.text().split("_")[1]))

    def sliceAdded(self, rectItem: QGraphicsRectItem):
      class QSizeListWidItem(QListWidgetItem):
        def data(self, role: int) -> Any:
          if role == Qt.ItemDataRole.SizeHintRole:
            if self.listWidget() is not None and self.listWidget().itemWidget(self) is not None: #TODO shouldnt be needed
              return self.listWidget().itemWidget(self).sizeHint()
          return super().data(role)
        def setSizeHint(self, size: QSize) -> None:
          #if self.listWidget() is not None and self.listWidget().itemWidget(self) is not None:
          #  super().setSizeHint(self.listWidget().itemWidget(self).sizeHint())
          pass

        #TODO why isnt this called? # its because the role is usd instead
        def sizeHint(self) -> QSize:
          if self.listWidget() is not None and self.listWidget().itemWidget(self) is not None:
            sz =  self.listWidget().itemWidget(self).sizeHint()
            qDebug("sizehint %s" % sz)
            return sz
          else:
            return QSize()

      qDebug("sliceadd")
      i = QSizeListWidItem()
      i.setData(Qt.ItemDataRole.UserRole + 1, 0) # rotation
      igrp = QSizeListWidItem()
      class QGraphicsViewSized(QGraphicsView):
        def __init__(self, rect, listitem, *args, **kwargs):
          self.myrect = rect
          self.listitem: QSizeListWidItem = listitem
          super().__init__(*args, **kwargs)
          self.oldAngle = None
          self.sizething = None

        def resize(self, a0: QSize) -> None:
          qDebug("resize %s" % a0)
          super().resize(a0)
        def sizeHint(self) -> QSize:
          #sh = super().sizeHint()
          angle = self.listitem.data(Qt.ItemDataRole.UserRole + 1)
          if self.oldAngle != angle:
            newRect = QTransform().rotate(-angle).mapRect(rectItem.sceneBoundingRect())
            sh = newRect.size().toSize()
            self.sizething = QSize(sh.width()//3, sh.height()//3)
            #self.listitem.setData(Qt.ItemDataRole.SizeHintRole, self.sizething)
            #self.listitem.listWidget().itemDelegate().sizeHintChanged.emit(self.listitem.listWidget().indexFromItem(i))
          qDebug("sizehint2 %s" % self.sizething)
          return self.sizething

      v = QGraphicsViewSized(rectItem, i, rectItem.scene())
      #v.sizePolicy().setVerticalPolicy(QSizePolicy.Policy.) #TODO need to fix sizehint qlistwidgetitem sizing to use the preferred graphics size and then fit the form...


      def onResize(oldf):
        def f(ev: QResizeEvent): # todo
          v.fitInView(rectItem.sceneBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
          return oldf(ev)
        return f

      v.resizeEvent = onResize(v.resizeEvent)
      v.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
      v.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
      self.rectToGView[rectItem] = v

      def rot(a):
        v.rotate(a)

        userdata = i.data(Qt.ItemDataRole.UserRole + 1)
        if userdata:
          i.setData(Qt.ItemDataRole.UserRole + 1, userdata + a)
        else:
          i.setData(Qt.ItemDataRole.UserRole + 1, a)

        #i.setData(Qt.ItemDataRole.SizeHintRole, )
        #i.listWidget().itemDelegate().sizeHintChanged.emit(i.listWidget().indexFromItem(i))
        #i.listWidget().itemDelegateForIndex(i.listWidget().indexFromItem(i)).sizeHintChanged.emit(i.listWidget().indexFromItem(i))
        #v.adjustSize() #todo this only partly works
        #v.parent().adjustSize()
        #v.parent().layout().invalidate()
        #v.parent().layout().activate()
        self.setItemSizeRot(rectItem, i, v, i.data(Qt.ItemDataRole.UserRole+1)) #TODO i think I broke this with the new grouping thing
        SlicerRoot.GUISlicesPreview.resz2(i)

      rotL = lambda: rot(-90)
      rotR = lambda: rot(90)
      rotLButton = QPushButton("L")
      rotRButton = QPushButton("R")
      rotLButton.released.connect(rotL)
      rotRButton.released.connect(rotR)

      subtoolbar = QHBoxLayout()
      subtoolbar.addWidget(rotLButton)
      subtoolbar.addWidget(rotRButton)

      ww = QWidget()  # reparenting hack
      l3 = QVBoxLayout()
      ww.setLayout(l3)

      w = QWidget()
      l3.addWidget(w)
      ww.setProperty("childthing", w)

      l = QVBoxLayout()
      l.addWidget(v)
      l.addLayout(subtoolbar)
      i.setData(Qt.ItemDataRole.UserRole+3, rectItem.data(Qt.ItemDataRole.UserRole+1))
      i.setData(Qt.ItemDataRole.UserRole+4, rectItem)

      w.setLayout(l)
      w.setContentsMargins(10, 10, 10, 10)

      self.addItem(igrp)

      # needs to be after igrp is added to the list
      le = QLineEdit("{:03}_.jpg".format(self.indexFromItem(igrp).row() + self.offset))
      i.setData(Qt.ItemDataRole.UserRole + 2, le)
      l.addWidget(le)

      grp = SlicerRoot.StitchList()
      grp.setOwnItem(igrp)
      #def handleDropRequest(target: SlicerRoot.StitchList, ev, reference): #this is basically a shitty reimplementation of pointers
      #  item = getItem(reference)
      #  target.receive.emit(item)
      #grp.request.connect(handleDropRequest)
      grp.addItem(i)
      self.setItemSize(rectItem, i, v)
      grp.setItemWidget(i, ww)
      w2 = QWidget()

      w2.setProperty("childthing", grp)
      l2 = QVBoxLayout()
      w2.setLayout(l2)
      l2.addWidget(grp)
      grp.setContentsMargins(10, 10, 10, 10)
      self.setItemWidget(igrp, w2)
      def resz():
        h, w = 0, 0
        for j in range(grp.model().rowCount()):
          s = grp.sizeHintForIndex(grp.model().index(j))
          h = max(s.height(), h)
          w += s.width()
        igrp.setSizeHint(QSize(w+40,h+40))
        #sh = grp.viewport().size()
        #sh2 = i.sizeHint()
        #grp.setMinimumSize(QSize(max(sh.width(), sh2.width()), max(sh.height(), sh2.height()))) #TODO
        #igrp.setSizeHint(QSize(max(sh.width(), sh2.width()), max(sh.height(), sh2.height()))) #TODO
        #i.setSizeHint(QSize(max(sh.width(), sh2.width()), max(sh.height(), sh2.height()))) #TODO
      #igrp.setSizeHint(QSize(grp.horizontalScrollBar().maximum()))
      grp.model().rowsInserted.connect(resz)
      resz()
      #self.addItem(i)
      #self.setItemWidget(i, w)

      self.rectToItem[rectItem] = (igrp, i) # maybe this should have been a tree at this point

    def sliceRemoved(self, rectItem):
      qDebug("slicerem")
      igrp, i = self.rectToItem[rectItem]
      innerw = i.listWidget()
      outerw = igrp.listWidget()
      oldgrp = igrp.listWidget().indexFromItem(igrp).row()
      oldrow = innerw.indexFromItem(i).row()
      innerw.takeItem(oldrow) #TODO is there a saner way to do this? also per docs this should leak?
      if innerw.model().rowCount() == 0:
        igrp.listWidget().takeItem(oldgrp)
      else:
        if outerw.model().rowCount() != 0:
          SlicerRoot.GUISlicesPreview.reszGroup(igrp, innerw)
        self.updateSliceIdx(oldgrp, oldrow)

    # refresh image section
    def sliceCoordsChanged(self, rectItem: QGraphicsRectItem):
      #qDebug("geomchange")
      v = self.rectToGView[rectItem]
      _, i = self.rectToItem[rectItem]
      userdata = i.data(Qt.ItemDataRole.UserRole+1)
      if userdata:
        self.setItemSizeRot(rectItem, i, v, userdata)
      else:
        self.setItemSize(rectItem, i, v)

  class SliceRectItem(QGraphicsRectItem):
    def __init__(self, editor, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self.editor: SlicerRoot.SliceEditor = editor

    def itemChange(self, change: 'QGraphicsItem.GraphicsItemChange', value: Any) -> Any:
      if change == change.ItemPositionChange: #TODO geom change??
        qDebug("position changed")
        self.editor.sliceCoordsChanged.emit(self)
      return super().itemChange(change, value)

  class SliceEditor(QObject):

    sliceAdded = pyqtSignal([QGraphicsRectItem])
    sliceRemoved = pyqtSignal([QGraphicsRectItem])
    sliceCoordsChanged = pyqtSignal([QGraphicsRectItem])

    def __init__(self):
      super().__init__()
      self.scene: QGraphicsScene = None
      self.coord_a: QPoint = None
      self.pen = QPen()
      self.brush = QBrush(QColor(50, 50, 200, 50))

    def install(self, gs: QGraphicsScene):
      qDebug("installing eventfilter %s on %s" % (self, gs))
      gs.installEventFilter(self)
      self.scene = gs
      qDebug("installed %s on %s" % (self, gs))

    def eventFilter(self, obj: 'QObject', ev: 'QEvent') -> bool:
      if SlicerRoot.dbgverb:
        qDebug("event %s" % ev.type())
      if ev.type() == QEvent.Type.GraphicsSceneMouseRelease:
        if ev.button() == Qt.MouseButton.LeftButton:
          orig: QPointF = ev.buttonDownScenePos(ev.button())
          pos: QPointF = ev.scenePos()
          if sqrt((orig.x() - pos.x())**2 + (orig.y() - pos.y())**2) < 3: # if not drag #TODO not sure if this is ergonomic
            self.coord_a = orig
          return super().eventFilter(obj, ev)
        elif ev.button() == Qt.MouseButton.RightButton:
          if self.coord_a:
            r = SlicerRoot.SliceRectItem(self, QRectF(QPointF(self.coord_a.x()+i*5, self.coord_a.y()+i*5), ev.buttonDownScenePos(ev.button())).normalized())
            r.setPen(self.pen)
            r.setBrush(self.brush)
            r.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            r.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            r.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges, True)
            r.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
            r.setData(Qt.ItemDataRole.UserRole, "slice")
            image = [x for x in self.scene.items() if isinstance(x, QGraphicsPixmapItem)][0]  # TODO
            r.setData(Qt.ItemDataRole.UserRole+1, image)
            self.scene.addItem(r)
            self.coord_a = None
            qDebug("added item to scene")
            self.sliceAdded.emit(r)
            return True
      elif ev.type() == QEvent.Type.KeyPress:
        if ev.key() == Qt.Key.Key_Delete:
          for i in self.scene.selectedItems():
            self.scene.removeItem(i)
            self.sliceRemoved.emit(i)
          return True

      return super().eventFilter(obj, ev)
    def addRect(self):
      pass

    def delRect(self):
      pass

  class NavGraphicsView(QGraphicsView):
    def wheelEvent(self, event: QWheelEvent) -> None:
      savedAnchor = self.transformationAnchor()
      self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
      angle = event.angleDelta().y()
      factor = 0.9 if angle < 0 else 1.1
      self.scale(factor, factor)
      self.setTransformationAnchor(savedAnchor)

      self.sp = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
      self.sp.setHorizontalStretch(4)
      self.setSizePolicy(self.sp)

      #return self.wheelEvent(event)

  class GUISlicerWindow(QGlobalWidget):
    def __init__(self, p, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self.preview : SlicerRoot.GUISlicesPreview = p
      self.build()

      self.sp = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
      self.sp.setHorizontalStretch(4)
      self.setSizePolicy(self.sp)
      #TODO why doesnt this work?
      #self.sizePolicy().setHorizontalPolicy(QSizePolicy.Policy.Minimum)
      #self.sizePolicy().setHorizontalStretch(1)

    class DbgScene(QGraphicsScene):
      def installEventFilter(self, a0: 'QObject') -> None:
        qDebug("installing event filter %s on %s" % (a0, self))
        super().installEventFilter(a0)

    def prepareNewContext(self):
      self.gs = self.DbgScene()
      qDebug("preparenew new gs %s" % self.gs)
      self.gv.setScene(self.gs)
      qDebug("gv setscene %s" % self.gs)

      self.se = SlicerRoot.SliceEditor()
      qDebug("se install %s" % self.gs)
      self.se.install(self.gs)
      qDebug("preparenewed %s %s" % (self.gs, self.se))

      self.prepSignals()

    def prepareContext(self, gs, se):
      qDebug("prepare")
      qDebug("self se is %s" % self.se )
      self.se = se
      self.gs = gs
      qDebug("prepare gs %s" % self.gs)
      self.gv.setScene(gs)
      qDebug("gv setscene %s" % self.gs)

      #self.prepSignals()

    def prepSignals(self):
      qDebug("prepsignals")
      self.se.sliceAdded.connect(self.preview.sliceAdded)
      self.se.sliceRemoved.connect(self.preview.sliceRemoved)
      self.se.sliceCoordsChanged.connect(self.preview.sliceCoordsChanged)

    def build(self):
      self.resize(400,800)
      tb = QToolBar()
      self.gv = SlicerRoot.NavGraphicsView()
      self.gv.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

      #tb.addAction(None, "2-point")
      #tb.addAction(None, "Drag")
      tb.addWidget(QPushButton("2-point"))
      tb.addWidget(QPushButton("drag"))
      tb.setOrientation(Qt.Orientation.Vertical)

      l = QHBoxLayout()
      self.setLayout(l)
      l.addWidget(self.gv)
      l.addWidget(tb)


    def onChange(self):
      #TODO save state, change, restore state of new
      pass

  class SlicesPreview(GUISlicesPreview):
    pass

  class SlicerWindow(GUISlicerWindow):
    pass

  #def __init__(self, images):
  def __init__(self, *args, **kwargs):
    self.build()
    #self.windows = [ SlicerRoot.SlicerWindow(self, i) for i in images ]
    self.currentFrontImage = None
    self.stash = dict()
    self.gsstash = dict()
    self.sestash = dict()
    pass

  def export(self):
    savedir = QFileDialog.getExistingDirectory()
    savedir = Path(savedir)

    for grp in range(self.preview.model().rowCount()):
      grpitem = self.preview.item(grp)
      grpwid: QListWidget = self.preview.itemWidget(grpitem).property("childthing")
      le: QLineEdit = grpwid.item(0).data(Qt.ItemDataRole.UserRole + 2)
      fname = le.text()

      #TODO not sure if its possibel for qpainter to autosize this?
      x = 0
      spacer = 10
      wsum, hmax = 0, 0
      for row in range(grpwid.model().rowCount()):
        item = grpwid.item(row)
        recti = item.data(Qt.ItemDataRole.UserRole+4)
        rect: QRect = recti.sceneBoundingRect().toRect()
        rotation = item.data(Qt.ItemDataRole.UserRole+1)
        rotated = QTransform().rotate(rotation).mapRect(rect)

        hmax = max(hmax, rotated.height())
        wsum += rotated.width() + spacer

      pm = QPixmap(wsum, hmax)
      pt = QPainter()

      pt.begin(pm) #TODO not using begin and end breaks for somer reason
      items = grpwid.model().rowCount()
      for row in range(items):
        item = grpwid.item(row)
        recti = item.data(Qt.ItemDataRole.UserRole+4)

        gpx: QPixmap = item.data(Qt.ItemDataRole.UserRole + 3).pixmap()
        rect: QRect = recti.sceneBoundingRect().toRect()
        rotation = item.data(Qt.ItemDataRole.UserRole+1)
        rotated = QTransform().rotate(rotation).mapRect(rect)

        rotatedimg = gpx.copy(rect).transformed(QTransform().rotate(rotation))
        pt.drawPixmap(QRect(x, 0, rotated.width(), rotated.height()), rotatedimg, rotatedimg.rect())
        x += rotated.width() + (spacer if row < items - 1 else 0)

      pt.end()
      pm.save(str(savedir / fname))

    # for idx in range(self.preview.model().rowCount()):
    #   item = self.preview.itemFromIndex(self.preview.model().index(idx))
    #   fname = item.data(Qt.ItemDataRole.UserRole+2).text()
    #
    #   graphicspixmapitem: QGraphicsPixmapItem = item.data(Qt.ItemDataRole.UserRole+3)
    #   recti = item.data(Qt.ItemDataRole.UserRole+4)
    #   rotation = item.data(Qt.ItemDataRole.UserRole+1)
    #   rotation = rotation if rotation else 0
    #   pm = QPixmap(graphicspixmapitem.pixmap().copy(recti.sceneBoundingRect().toRect()).transformed(QTransform().rotate(rotation)))
    #   #l = QLabel()
    #   #l.setPixmap(pm)
    #   #self.w = QWidget()
    #   #ll = QVBoxLayout()
    #   #self.w.setLayout(ll)
    #   #ll.addWidget(l)
    #   #self.w.show()
    #   pm.save(str(savedir / fname))

  def build(self):
    self.preview = SlicerRoot.GUISlicesPreview()
    self.previewWindow = QWidget()
    l = QVBoxLayout()
    ll = QHBoxLayout()
    l.addWidget(self.preview)
    exportbtn = QPushButton("Export")
    exportbtn.clicked.connect(self.export)
    l.addLayout(ll)
    self.startnumbering = QLineEdit("0")
    def onEdit():
      self.preview.offset = int(self.startnumbering.text())
      self.preview.updateSliceIdx(0, 0)

    self.startnumbering.editingFinished.connect(onEdit)
    ll.addWidget(self.startnumbering)
    ll.addWidget(exportbtn)
    self.previewWindow.setLayout(l)
    self.previewWindow.show()
    self.slicerFront = SlicerRoot.SlicerWindow(self.preview)
    #self.slicerBack = SlicerRoot.SlicerWindow()
    self.slicerFront.show()
    #self.slicerBack.show()

  def onFrontChanged(self, path: str):
    print(path)
    parentImage = self.currentFrontImage
    if parentImage:
      self.gsstash[parentImage] = self.slicerFront.gs
      self.sestash[parentImage] = self.slicerFront.se

    parentImage = path
    qDebug(repr(self.gsstash))
    if parentImage in self.gsstash:
      self.slicerFront.prepareContext(self.gsstash[parentImage], self.sestash[parentImage])
    else:
      if hasattr(self.slicerFront, "gs"):
        qDebug("onfrontchanges old gs %s" % self.slicerFront.gs)
      self.slicerFront.prepareNewContext()
      self.slicerFront.gs.addItem(QGraphicsPixmapItem(QPixmap.fromImage(QImage(path))))
      self.slicerFront.gv.fitInView(self.slicerFront.gs.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio) #TODO apparently this is currently redundant?

    self.currentFrontImage = path

  def onBackChanged(self, path: str):
    print(path)
    self.slicerBack.gs.clear()
    self.slicerBack.gs.addItem(QGraphicsPixmapItem(QPixmap.fromImage(QImage(path))))


#TODO close app when closing main window or something
class App(QApplication):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.build()
    self.exec() #TODO

  def build(self):
    self.root = QWidget()
    self.root.show()

    self.catalog = Catalog()
    #self.catalog.show()
    self.catalog.setDirectory(QFileDialog.getExistingDirectory())
    self.slicer = SlicerRoot()
    self.catalog.thumbs.mySelectionChanged.connect(self.slicer.onFrontChanged)
    #self.catalog.thumbs.backSelectionChanged.connect(self.slicer.onBackChanged)

    l = QHBoxLayout()
    self.root.setLayout(l)
    l.addWidget(self.catalog)
    l.addWidget(self.slicer.slicerFront)



if __name__ == "__main__":
  a = App([])
