#TODO autosave project
#TODO workable reordering, / alt: numbering range spec
#TODO front/back
#TODO stitching
#TODO rotate
#TODO drag margin for reordering slices
# TODO  drag slice preview to move it
#TODO need to add slicing to icons in catalog?
#TODO capture scroll / mouse events against slices previews



#Q keyboard event for rapid dev
from math import sqrt
from typing import *
from pathlib import Path

from PyQt6.QtCore import pyqtSignal, QModelIndex, Qt, QSize, QRect, QItemSelectionModel, qDebug, QObject, QEvent, \
  QPoint, QRectF, QPointF, QSizeF, QCollator
from PyQt6.QtGui import QIcon, QPixmap, QImage, QMouseEvent, QPainter, QBrush, QColor, QKeyEvent, QPen, QWheelEvent, \
  QResizeEvent, QTransform, QDragLeaveEvent, QDropEvent, QStandardItemModel
from PyQt6.QtWidgets import QWidget, QListWidget, QListWidgetItem, QApplication, QVBoxLayout, QSizePolicy, \
  QGraphicsView, QPushButton, QFileDialog, QHBoxLayout, QToolBar, QGraphicsScene, QGraphicsPixmapItem, \
  QStyledItemDelegate, QStyle, QAbstractItemView, QGraphicsSceneMouseEvent, QGraphicsItem, QGraphicsRectItem, \
  QWidgetItem, QTextEdit, QLineEdit, QLabel
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
  class QListWidgetItemSorting(QListWidgetItem):
    qc = mkCollator()

    #def __lt__(self, other):
    #  res = self.qc.compare(self.text(), other.text())
    #  return res

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
      self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
      #self.model().sor
      #self.setSortingEnabled(True) #TODO does this even do anything?
      #self.sortItems(Qt.SortOrder.AscendingOrder)
      self.filter = None

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
          i = GUICatalog.QListWidgetItemSorting(QIcon(str(p)), str(p.name))
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
  dbgverb = True
  class ImageStore:
    def __init__(self):
      self.images = dict()

  class GUISlicesPreview(QListWidget): #TODO slicePairItem
    # image and coords
    def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self.build()
      self.setSpacing(10)
      self.setFlow(QListWidget.Flow.LeftToRight)
      self.setViewMode(QListWidget.ViewMode.IconMode)
      #self.setGridSize(QSize(128, 128))
      #self.setViewMode(QListWidget.ViewMode.IconMode)
      self.rectToGView: Dict[QGraphicsRectItem, QGraphicsView] = dict()
      self.rectToItem: Dict[QGraphicsRectItem, QListWidgetItem] = dict()

      self.setDragEnabled(True)
      self.setAcceptDrops(True)
      self.setDropIndicatorShown(True)
      self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

      self.offset = 0

    def dropEvent(self, event: QDropEvent) -> None:
      qDebug("dropev")
      self.model().layoutChanged.emit() #TODO idk why this doesnt work by itself
      super().dropEvent(event)

    def build(self):
      pass


    def _setSize(self, rectItem, size, i, v):
      #TODO these sizehints are wrong now becase of the subwidgets
      #i.setSizeHint(QSizeF(size.width() / 3, size.height() / 3 + 60).toSize()) #TODO the +30 is a hardcoded hack fix ... attempt
      i.setSizeHint(QSizeF(size.width() / 3, size.height() / 3).toSize())
      # i.setSizeHint(size)
      v.fitInView(rectItem.sceneBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
      self.model().layoutChanged.emit()
    def setItemSize(self, rectItem, i, v):
      size = rectItem.sceneBoundingRect().size().toSize()
      self._setSize(rectItem, size, i, v)

    def setItemSizeRot(self, rectItem, i, v, angle):
      newRect = QTransform().rotate(-angle).mapRect(rectItem.sceneBoundingRect())
      size = newRect.size().toSize()
      self._setSize(rectItem, size, i, v)

    def updateSliceIdx(self, oldrow):
      for row in range(oldrow, self.model().rowCount()):
        le: QLineEdit = self.item(row).data(Qt.ItemDataRole.UserRole+2)
        le.setText("{:03}_{}".format(row + self.offset, le.text().split("_")[1]))

    def sliceAdded(self, rectItem: QGraphicsRectItem):
      qDebug("sliceadd")
      i = QListWidgetItem()
      self.addItem(i)
      v = QGraphicsView(rectItem.scene())

      def onResize(oldf):
        def f(ev: QResizeEvent): # todo
          v.fitInView(rectItem.sceneBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
          return oldf(ev)
        return f

      v.resizeEvent = onResize(v.resizeEvent)
      v.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
      v.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
      self.setItemSize(rectItem, i, v)
      self.rectToGView[rectItem] = v
      self.rectToItem[rectItem] = i

      def rot(a):
        v.rotate(a)

        userdata = i.data(Qt.ItemDataRole.UserRole + 1)
        if userdata:
          i.setData(Qt.ItemDataRole.UserRole + 1, userdata + a)
        else:
          i.setData(Qt.ItemDataRole.UserRole + 1, a)

        self.setItemSizeRot(rectItem, i, v, i.data(Qt.ItemDataRole.UserRole+1))

      rotL = lambda: rot(-90)
      rotR = lambda: rot(90)
      rotLButton = QPushButton("L")
      rotRButton = QPushButton("R")
      rotLButton.released.connect(rotL)
      rotRButton.released.connect(rotR)

      subtoolbar = QHBoxLayout()
      subtoolbar.addWidget(rotLButton)
      subtoolbar.addWidget(rotRButton)

      w = QWidget()
      l = QVBoxLayout()
      l.addWidget(v)
      l.addLayout(subtoolbar)
      le = QLineEdit("{:03}_.jpg".format(self.indexFromItem(i).row() + self.offset))
      i.setData(Qt.ItemDataRole.UserRole+2, le)
      i.setData(Qt.ItemDataRole.UserRole+3, rectItem.data(Qt.ItemDataRole.UserRole+1))
      i.setData(Qt.ItemDataRole.UserRole+4, rectItem)

      l.addWidget(le)
      w.setLayout(l)
      w.setContentsMargins(10, 10, 10, 10)
      self.setItemWidget(i, w)

    def sliceRemoved(self, rectItem):
      qDebug("slicerem")
      i = self.rectToItem[rectItem]
      oldrow= self.indexFromItem(i).row()
      self.takeItem(self.indexFromItem(i).row()) #TODO is there a saner way to do this? also per docs this should leak?
      self.updateSliceIdx(oldrow)

    # refresh image section
    def sliceCoordsChanged(self, rectItem: QGraphicsRectItem):
      #qDebug("geomchange")
      v = self.rectToGView[rectItem]
      i = self.rectToItem[rectItem]
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
            r = SlicerRoot.SliceRectItem(self, QRectF(self.coord_a, ev.buttonDownScenePos(ev.button())))
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

      #return self.wheelEvent(event)

  class GUISlicerWindow(QGlobalWidget):
    def __init__(self, p, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self.preview : SlicerRoot.GUISlicesPreview = p
      self.build()

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
    for idx in range(self.preview.model().rowCount()):
      item = self.preview.itemFromIndex(self.preview.model().index(idx))
      fname = item.data(Qt.ItemDataRole.UserRole+2).text()
      graphicspixmapitem: QGraphicsPixmapItem = item.data(Qt.ItemDataRole.UserRole+3)
      recti = item.data(Qt.ItemDataRole.UserRole+4)
      rotation = item.data(Qt.ItemDataRole.UserRole+1)
      rotation = rotation if rotation else 0
      pm = QPixmap(graphicspixmapitem.pixmap().copy(recti.sceneBoundingRect().toRect()).transformed(QTransform().rotate(rotation)))
      #l = QLabel()
      #l.setPixmap(pm)
      #self.w = QWidget()
      #ll = QVBoxLayout()
      #self.w.setLayout(ll)
      #ll.addWidget(l)
      #self.w.show()
      pm.save(str(savedir / fname))

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
      self.preview.updateSliceIdx(0)

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
