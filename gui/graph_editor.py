from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsItem, 
                             QGraphicsPathItem, QGraphicsEllipseItem, QGraphicsLineItem,
                             QApplication)
from PySide6.QtGui import QPen, QColor, QPainter, QBrush, QPainterPath, QPixmap, QImage
from PySide6.QtCore import Qt, QPointF, Signal, QRectF, QTimer

from curve_math import BezierSegment, CompositeBezier

MAX_UNDO = 50


class DraggablePoint(QGraphicsEllipseItem):
    def __init__(self, color=QColor(0, 150, 255), radius=6, is_anchor=False):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.black, 1))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.setCursor(Qt.PointingHandCursor)
        self.is_anchor = is_anchor
        self.callback = None
        self.min_x = None
        self.max_x = None

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            new_pos = value
            if self.min_x is not None and new_pos.x() < self.min_x:
                new_pos.setX(self.min_x)
            if self.max_x is not None and new_pos.x() > self.max_x:
                new_pos.setX(self.max_x)
            if self.callback:
                self.callback(self, new_pos)
            return new_pos
        return super().itemChange(change, value)


class BezierGraphEditor(QGraphicsView):
    curve_changed = Signal(object)

    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene(self)
        self._scene.setItemIndexMethod(QGraphicsScene.NoIndex)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        self.view_width = 400
        self.view_height = 400
        self._min_tangent_len = self.view_width * 0.08

        self._scene.setSceneRect(-100, -200, self.view_width + 200, self.view_height + 400)
        
        self.grid_items = []
        self.draw_grid()

        self.curve_path = QGraphicsPathItem()
        self.curve_path.setPen(QPen(QColor(255, 100, 100), 3))
        self.curve_path.setZValue(10)
        self._scene.addItem(self.curve_path)

        self.nodes = []
        
        # Undo/Redo stacks
        self._undo_stack = []
        self._redo_stack = []
        self._drag_snapshot = None  # state captured at drag start

        self.add_node(0.0, 0.0, None, (0.0, 0.0))
        self.add_node(1.0, 1.0, (1.0, 1.0), None)
        self.nodes[0][0].setFlag(QGraphicsItem.ItemIsMovable, False)
        self.nodes[-1][0].setFlag(QGraphicsItem.ItemIsMovable, False)

        # debounce timer
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(16)
        self._update_timer.timeout.connect(self._do_update_curve)

        self.update_curve()
        self.fit_to_view()

    # ── Undo / Redo ───────────────────────────

    def _capture_state(self):
        return self.get_current_data()

    def push_undo(self):
        state = self._capture_state()
        self._undo_stack.append(state)
        if len(self._undo_stack) > MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self):
        if not self._undo_stack:
            return False
        self._redo_stack.append(self._capture_state())
        state = self._undo_stack.pop()
        self._load_state_no_undo(state)
        return True

    def redo(self):
        if not self._redo_stack:
            return False
        self._undo_stack.append(self._capture_state())
        state = self._redo_stack.pop()
        self._load_state_no_undo(state)
        return True

    def _load_state_no_undo(self, segments_data):
        """Load state without pushing to undo stack."""
        for n in self.nodes:
            for item in n:
                if item:
                    self._scene.removeItem(item)
        self.nodes.clear()
        if not segments_data:
            return
        nodes_info = []
        sd0 = segments_data[0]
        nodes_info.append({'x': sd0[0], 'y': sd0[1], 'cin': None, 'cout': (sd0[2], sd0[3])})
        for i in range(len(segments_data)):
            sd = segments_data[i]
            cin = (sd[4], sd[5])
            cout = None
            if i + 1 < len(segments_data):
                cout = (segments_data[i + 1][2], segments_data[i + 1][3])
            nodes_info.append({'x': sd[6], 'y': sd[7], 'cin': cin, 'cout': cout})
        for ni in nodes_info:
            self.add_node(ni['x'], ni['y'], ni['cin'], ni['cout'])
        if self.nodes:
            self.nodes[0][0].setFlag(QGraphicsItem.ItemIsMovable, False)
            self.nodes[-1][0].setFlag(QGraphicsItem.ItemIsMovable, False)
        self.update_curve()

    def can_undo(self):
        return len(self._undo_stack) > 0

    def can_redo(self):
        return len(self._redo_stack) > 0

    # ── coordinate conversion ─────────────────

    def logical_to_view(self, lx, ly):
        return QPointF(lx * self.view_width, self.view_height - ly * self.view_height)
        
    def view_to_logical(self, vx, vy):
        return vx / self.view_width, (self.view_height - vy) / self.view_height

    # ── grid ──────────────────────────────────

    def draw_grid(self):
        for item in self.grid_items:
            self._scene.removeItem(item)
        self.grid_items.clear()

        # out-of-bounds overlay
        over_rect = QGraphicsPathItem()
        op = QPainterPath()
        op.addRect(0, -self.view_height * 1.5, self.view_width, self.view_height * 1.5)
        op.addRect(0, self.view_height, self.view_width, self.view_height * 1.5)
        over_rect.setPath(op)
        over_rect.setBrush(QBrush(QColor(50, 50, 50, 100)))
        over_rect.setPen(QPen(Qt.NoPen))
        over_rect.setZValue(0)
        self._scene.addItem(over_rect)
        self.grid_items.append(over_rect)
        
        # 4x4 internal grid
        grid_pen = QPen(QColor(120, 120, 120, 180), 1, Qt.DotLine)
        for i in range(1, 4):
            x = self.view_width * i / 4
            vline = QGraphicsLineItem(x, 0, x, self.view_height)
            vline.setPen(grid_pen)
            vline.setZValue(1)
            self._scene.addItem(vline)
            self.grid_items.append(vline)
            y = self.view_height * i / 4
            hline = QGraphicsLineItem(0, y, self.view_width, y)
            hline.setPen(grid_pen)
            hline.setZValue(1)
            self._scene.addItem(hline)
            self.grid_items.append(hline)

        # outer frame (subtle)
        rect = QGraphicsPathItem()
        p = QPainterPath()
        p.addRect(0, 0, self.view_width, self.view_height)
        rect.setPath(p)
        rect.setPen(QPen(QColor(100, 100, 100), 1.5))
        rect.setZValue(2)
        self._scene.addItem(rect)
        self.grid_items.append(rect)

    # ── node management ───────────────────────

    def add_node(self, lx, ly, l_cin=None, l_cout=None, insert_index=None):
        pos = self.logical_to_view(lx, ly)
        anchor = DraggablePoint(color=QColor(255, 200, 0), radius=8, is_anchor=True)
        anchor.setPos(pos)
        anchor.setZValue(20)
        anchor.callback = self.on_point_moved
        self._scene.addItem(anchor)
        
        cin = None
        line_in = None
        if l_cin:
            cin = DraggablePoint(color=QColor(0, 200, 255), radius=6)
            cin.setPos(self.logical_to_view(l_cin[0], l_cin[1]))
            cin.setZValue(20)
            cin.callback = self.on_point_moved
            self._scene.addItem(cin)
            line_in = QGraphicsLineItem()
            line_in.setPen(QPen(QColor(100, 100, 100), 2, Qt.DashLine))
            line_in.setZValue(5)
            self._scene.addItem(line_in)
            
        cout = None
        line_out = None
        if l_cout:
            cout = DraggablePoint(color=QColor(0, 200, 255), radius=6)
            cout.setPos(self.logical_to_view(l_cout[0], l_cout[1]))
            cout.setZValue(20)
            cout.callback = self.on_point_moved
            self._scene.addItem(cout)
            line_out = QGraphicsLineItem()
            line_out.setPen(QPen(QColor(100, 100, 100), 2, Qt.DashLine))
            line_out.setZValue(5)
            self._scene.addItem(line_out)

        node = (anchor, cin, cout, line_in, line_out)
        if insert_index is None:
            self.nodes.append(node)
        else:
            self.nodes.insert(insert_index, node)
        return node

    # ── point move callback ───────────────────

    def on_point_moved(self, point_item, new_pos):
        if getattr(self, '_is_updating', False):
            return
        self._is_updating = True
        try:
            modifiers = QApplication.keyboardModifiers()
            alt_held = bool(modifiers & Qt.AltModifier)

            for i in range(len(self.nodes)):
                anchor, cin, cout, lin, lout = self.nodes[i]
                a_pos = anchor.pos()
            
                if point_item == cout:
                    min_x = a_pos.x() + self._min_tangent_len
                    point_item.min_x = min_x
                    if i < len(self.nodes) - 1:
                        point_item.max_x = self.nodes[i + 1][0].pos().x()
                    if new_pos.x() < min_x:
                        new_pos.setX(min_x)
                    # Alt: symmetric mirror
                    if alt_held and cin:
                        dx = new_pos.x() - a_pos.x()
                        dy = new_pos.y() - a_pos.y()
                        cin.setPos(QPointF(a_pos.x() - dx, a_pos.y() - dy))

                elif point_item == cin:
                    max_x = a_pos.x() - self._min_tangent_len
                    point_item.max_x = max_x
                    if i > 0:
                        point_item.min_x = self.nodes[i - 1][0].pos().x()
                    if new_pos.x() > max_x:
                        new_pos.setX(max_x)
                    if alt_held and cout:
                        dx = new_pos.x() - a_pos.x()
                        dy = new_pos.y() - a_pos.y()
                        cout.setPos(QPointF(a_pos.x() - dx, a_pos.y() - dy))

                elif point_item == anchor:
                    if i > 0:
                        point_item.min_x = self.nodes[i - 1][0].pos().x()
                    if i < len(self.nodes) - 1:
                        point_item.max_x = self.nodes[i + 1][0].pos().x()
                    if hasattr(anchor, '_last_pos'):
                        dx = new_pos.x() - anchor._last_pos.x()
                        dy = new_pos.y() - anchor._last_pos.y()
                        if cin:
                            cin.setPos(cin.pos() + QPointF(dx, dy))
                        if cout:
                            cout.setPos(cout.pos() + QPointF(dx, dy))
                    anchor._last_pos = new_pos
        finally:
            self._is_updating = False
        self._request_update()

    def reset_tangents_for_anchor(self, anchor_index):
        if anchor_index < 0 or anchor_index >= len(self.nodes):
            return
        self.push_undo()
        anchor, cin, cout, lin, lout = self.nodes[anchor_index]
        a_pos = anchor.pos()
        default_len = self._min_tangent_len * 2
        if cin:
            cin.setPos(QPointF(a_pos.x() - default_len, a_pos.y()))
        if cout:
            cout.setPos(QPointF(a_pos.x() + default_len, a_pos.y()))
        self.update_curve()

    # ── curve update (debounced) ──────────────

    def _request_update(self):
        if not self._update_timer.isActive():
            self._update_timer.start()

    def _do_update_curve(self):
        self.update_curve()

    def update_curve(self):
        path = QPainterPath()
        if not self.nodes:
            return
        path.moveTo(self.nodes[0][0].pos())
        for i in range(len(self.nodes) - 1):
            a0, cin0, cout0, lin0, lout0 = self.nodes[i]
            a1, cin1, cout1, lin1, lout1 = self.nodes[i + 1]
            p0 = a0.pos()
            p1 = cout0.pos() if cout0 else p0
            p2 = cin1.pos() if cin1 else a1.pos()
            p3 = a1.pos()
            if lout0:
                lout0.setLine(p0.x(), p0.y(), p1.x(), p1.y())
            if lin1:
                lin1.setLine(p3.x(), p3.y(), p2.x(), p2.y())
            path.cubicTo(p1, p2, p3)
        self.curve_path.setPath(path)

    # ── preset load/save ──────────────────────

    def load_preset(self, segments_data, record_undo=True):
        if record_undo:
            self.push_undo()
        self._load_state_no_undo(segments_data)
        self.fit_to_view()

    def get_current_data(self):
        segments_data = []
        for i in range(len(self.nodes) - 1):
            a0 = self.nodes[i]
            a1 = self.nodes[i + 1]
            p0 = a0[0].pos()
            p1 = a0[2].pos() if a0[2] else p0
            p2 = a1[1].pos() if a1[1] else a1[0].pos()
            p3 = a1[0].pos()
            p0x, p0y = self.view_to_logical(p0.x(), p0.y())
            p1x, p1y = self.view_to_logical(p1.x(), p1.y())
            p2x, p2y = self.view_to_logical(p2.x(), p2.y())
            p3x, p3y = self.view_to_logical(p3.x(), p3.y())
            segments_data.append([p0x, p0y, p1x, p1y, p2x, p2y, p3x, p3y])
        return segments_data

    # ── mouse / keyboard input ────────────────

    def mousePressEvent(self, event):
        # Alt+Click on anchor: reset tangents
        if event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier:
            pos = self.mapToScene(event.pos())
            for i, node in enumerate(self.nodes):
                anchor = node[0]
                if anchor.contains(anchor.mapFromScene(pos)):
                    self.reset_tangents_for_anchor(i)
                    event.accept()
                    return

        # Capture undo snapshot when a drag starts on any DraggablePoint
        if event.button() == Qt.LeftButton:
            pos = self.mapToScene(event.pos())
            items = self._scene.items(pos)
            for item in items:
                if isinstance(item, DraggablePoint):
                    self._drag_snapshot = self._capture_state()
                    break

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        # If we had a drag snapshot and state has changed, push undo
        if self._drag_snapshot is not None:
            current = self._capture_state()
            if current != self._drag_snapshot:
                self._undo_stack.append(self._drag_snapshot)
                if len(self._undo_stack) > MAX_UNDO:
                    self._undo_stack.pop(0)
                self._redo_stack.clear()
            self._drag_snapshot = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = self.mapToScene(event.pos())
            if 0 < pos.x() < self.view_width:
                lx, ly = self.view_to_logical(pos.x(), pos.y())
                for i in range(len(self.nodes) - 1):
                    if self.nodes[i][0].pos().x() < pos.x() < self.nodes[i + 1][0].pos().x():
                        self.push_undo()
                        self.add_node(lx, ly, (lx - 0.1, ly), (lx + 0.1, ly), insert_index=i + 1)
                        self.update_curve()
                        break
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            event.accept()
            return
        super().keyPressEvent(event)

    def fit_to_view(self):
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    # ── thumbnail ─────────────────────────────

    @staticmethod
    def generate_thumbnail(segments_data, width=100, height=100):
        img = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(40, 40, 40))
        painter.drawRoundedRect(0, 0, width, height, 8, 8)
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawRect(10, 10, width - 20, height - 20)
        path = QPainterPath()
        def l2v(lx, ly):
            return QPointF(10 + lx * (width - 20), (height - 10) - ly * (height - 20))
        if not segments_data:
            painter.end()
            return QPixmap.fromImage(img)
        path.moveTo(l2v(segments_data[0][0], segments_data[0][1]))
        for sd in segments_data:
            path.cubicTo(l2v(sd[2], sd[3]), l2v(sd[4], sd[5]), l2v(sd[6], sd[7]))
        painter.setPen(QPen(QColor(255, 100, 100), 2))
        painter.drawPath(path)
        painter.end()
        return QPixmap.fromImage(img)

    # ── node add/delete ───────────────────────

    def add_midpoint_at_center(self):
        if len(self.nodes) < 2:
            return
        self.push_undo()
        mid_idx = len(self.nodes) // 2
        n_left = self.nodes[mid_idx - 1]
        n_right = self.nodes[mid_idx]
        lx_left, ly_left = self.view_to_logical(n_left[0].pos().x(), n_left[0].pos().y())
        lx_right, ly_right = self.view_to_logical(n_right[0].pos().x(), n_right[0].pos().y())
        cx = (lx_left + lx_right) / 2
        cy = (ly_left + ly_right) / 2
        self.add_node(cx, cy, (cx - 0.15, cy), (cx + 0.15, cy), insert_index=mid_idx)
        self.update_curve()

    def delete_selected_anchor(self):
        selected = self._scene.selectedItems()
        for item in selected:
            for i, node in enumerate(self.nodes):
                if item is node[0] and 0 < i < len(self.nodes) - 1:
                    self.push_undo()
                    for sub in node:
                        if sub:
                            self._scene.removeItem(sub)
                    self.nodes.pop(i)
                    self.update_curve()
                    return True
        return False

    def set_tangents_visible(self, visible):
        for node in self.nodes:
            for item in [node[1], node[2], node[3], node[4]]:
                if item:
                    item.setVisible(visible)
