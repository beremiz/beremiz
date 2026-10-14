"""Test agent for Beremiz IDE GUI tests.

Loaded in IDE process with "Beremiz.py -e ide_test_agent.py", it serves XML-RPC
requests from ide_harness.py on 127.0.0.1:$BEREMIZ_TEST_AGENT_PORT.

Tests use it to get screen coordinates of widgets and IDE state, instead of
relying on OCR. Requests are executed in wx GUI thread.

Some requests take a python expression, evaluated in IDE with these names:
    frame: IDE main frame
    page: selected editor in main notebook, if any
    dialog: shown modal dialog, if any
    wx: wx module

If BEREMIZ_TEST_INSPECT is set, Ctrl+Shift+click on any widget prints agent
requests locating it in IDE console, to help writing tests (see ide_session.py).

Note: this file is exec'd in Beremiz.py globals.
"""

import os
import threading
from concurrent.futures import Future
from xmlrpc.server import SimpleXMLRPCServer

import wx


class IDETestInspector(wx.EventFilter):
    "Prints agent requests locating widget clicked with Ctrl+Shift held"

    def __init__(self, agent):
        wx.EventFilter.__init__(self)
        self.agent = agent

    def FilterEvent(self, event):
        if event.GetEventType() == wx.wxEVT_LEFT_DOWN and event.ControlDown() and event.ShiftDown():
            try:
                lines = self.agent.inspect(event.GetEventObject(), event)
            except Exception as e:
                lines = ["inspection failed: %r" % e]
            # IDE console also goes to stdout, with --devmode
            wx.CallAfter(self.agent._frame().Log.write,
                         "".join("INSPECT: %s\n" % line for line in lines))
            return self.Event_Processed
        return self.Event_Skip


class IDETestAgent:
    "Answers test harness queries, from wx GUI thread"

    call_timeout = 10

    exported = ["ready", "maximize", "activate", "active_tab", "modal_dialog",
                "value", "window", "tree_item", "grid_cell", "notebook_tab", "popup_menu",
                "viewer_element", "viewer_pin", "drop"]

    def __init__(self):
        self.menus = []  # shown popup menus, innermost last
        self.dialogs = []  # shown modal dialogs, innermost last
        self.dragged = None  # data object of last drag

    def _track(self, cls, name, shown):
        """
        Keep track of objects shown by given blocking method, since wx doesn't
        tell which are. Object shown is method's first argument if any, or self.
        """
        method = getattr(cls, name)

        def tracked(window, *args, **kwargs):
            obj = args[0] if args else window
            shown.append(obj)
            try:
                return method(window, *args, **kwargs)
            finally:
                shown.remove(obj)

        setattr(cls, name, tracked)

    def start(self, port):
        self._track(wx.Window, "PopupMenu", self.menus)

        # native dialogs (wx.DirDialog, wx.MessageDialog...) have their own ShowModal
        for cls in vars(wx).values():
            if isinstance(cls, type) and issubclass(cls, wx.Dialog) and "ShowModal" in vars(cls):
                self._track(cls, "ShowModal", self.dialogs)

        # GTK Broadway backend can't drag and drop. Dragged data is kept
        # instead, and dropped by agent when harness asks for it
        def RecordedDoDragDrop(source, *args, **kwargs):
            self.dragged = source.GetDataObject()
            return wx.DragNone

        wx.DropSource.DoDragDrop = RecordedDoDragDrop

        if os.environ.get("BEREMIZ_TEST_INSPECT"):
            self.inspector = IDETestInspector(self)
            wx.EvtHandler.AddFilter(self.inspector)

        server = SimpleXMLRPCServer(("127.0.0.1", port), allow_none=True, logRequests=False)
        for name in self.exported:
            server.register_function(self._gui_call(getattr(self, name)), name)
        threading.Thread(target=server.serve_forever, daemon=True).start()

    def _gui_call(self, method):
        def call(*args):
            future = Future()

            def run():
                try:
                    future.set_result(method(*args))
                except Exception as e:
                    future.set_exception(e)

            wx.CallAfter(run)
            return future.result(timeout=self.call_timeout)
        return call

    def _frame(self):
        return wx.FindWindowByName("IDEFrame")

    def _modal_dialog(self):
        return self.dialogs[-1] if self.dialogs else None

    def _eval(self, expr):
        frame = self._frame()
        selected = frame.TabsOpened.GetSelection()
        return eval(expr, {"wx": wx, "frame": frame,
                           "page": None if selected < 0 else frame.TabsOpened.GetPage(selected),
                           "dialog": self._modal_dialog()})

    def _screen_rect(self, window, rect):
        x, y = window.ClientToScreen(rect.GetPosition())
        return {"x": x, "y": y, "width": rect.width, "height": rect.height}

    def ready(self):
        frame = self._frame()
        return frame is not None and frame.IsShown()

    def maximize(self):
        self._frame().Maximize()

    def activate(self):
        "Raise IDE main frame, so that it gets keyboard focus back, e.g. after closing a dialog"
        self._frame().Raise()

    def active_tab(self):
        "Title of selected editor tab"
        page = self._eval("page")
        return None if page is None else page.GetTitle()

    def modal_dialog(self):
        "Class name of shown modal dialog, if any"
        dialog = self._modal_dialog()
        return None if dialog is None else dialog.__class__.__name__

    def value(self, expr):
        "Value of python expression, that must be serializable by XML-RPC"
        return self._eval(expr)

    def window(self, expr):
        "Screen rect of window given by python expression"
        rect = self._eval(expr).GetScreenRect()
        return {"x": rect.x, "y": rect.y, "width": rect.width, "height": rect.height}

    def tree_item(self, label, tree="frame.ProjectTree"):
        """
        Screen rect of item with given label, or of root item if label is None,
        in tree given by python expression. Only items in expanded branches are
        considered, as tree is not expanded on behalf of test.
        """
        tree = self._eval(tree)
        labels = []
        root = tree.GetRootItem()
        item = root if label is None else self._find_tree_item(tree, root, label, labels)
        if item is None:
            raise KeyError("%r not in visible tree items: %r" % (label, labels))
        tree.EnsureVisible(item)
        # HyperTreeList items are in its main window
        window = getattr(tree, "GetMainWindow", lambda: tree)()
        return self._screen_rect(window, tree.GetBoundingRect(item))

    def _find_tree_item(self, tree, item, label, labels):
        text = tree.GetItemText(item)
        labels.append(text)
        if text == label:
            return item
        if item is tree.GetRootItem() or tree.IsExpanded(item):
            child, cookie = tree.GetFirstChild(item)
            while child is not None:
                found = self._find_tree_item(tree, child, label, labels)
                if found is not None:
                    return found
                child, cookie = tree.GetNextChild(item, cookie)
        return None

    def grid_cell(self, grid, row, column):
        "Screen rect of cell in wx.grid.Grid given by python expression, column being given by its label"
        grid = self._eval(grid)
        labels = [grid.GetColLabelValue(col) for col in range(grid.GetNumberCols())]
        if column not in labels:
            raise KeyError("%r not in grid columns: %r" % (column, labels))
        col = labels.index(column)
        grid.MakeCellVisible(row, col)
        rect = grid.CellToRect(row, col)
        rect.SetPosition(grid.CalcScrolledPosition(rect.GetPosition()))
        return self._screen_rect(grid.GetGridWindow(), rect)

    def notebook_tab(self, notebook, title):
        "Screen rect of tab with given title, in wx.Notebook given by python expression"
        notebook = self._eval(notebook)
        titles = [notebook.GetPageText(i) for i in range(notebook.GetPageCount())]
        if title not in titles:
            raise KeyError("%r not in notebook tabs: %r" % (title, titles))
        index = titles.index(title)
        # wx doesn't give tabs geometry, but tells which tab is at given point
        width, height = notebook.GetClientSize()
        hits = [(x, y) for y in range(0, min(height, 100), 2) for x in range(0, width, 4)
                if notebook.HitTest((x, y))[0] == index]
        if not hits:
            raise KeyError("%r tab not found by hit test" % title)
        xs, ys = [x for x, _y in hits], [y for _x, y in hits]
        rect = wx.Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
        return self._screen_rect(notebook, rect)

    def popup_menu(self, labels):
        """
        Positions of given labels in shown popup menu and in its submenus, counting
        only items that can be reached with keyboard
        """
        if not self.menus:
            raise KeyError("No popup menu shown")
        menu = self.menus[-1]
        positions = []
        for label in labels:
            items = [item for item in menu.GetMenuItems() if not item.IsSeparator() and item.IsEnabled()]
            texts = [item.GetItemLabelText() for item in items]
            if label not in texts:
                raise KeyError("%r not in menu: %r" % (label, texts))
            positions.append(texts.index(label))
            menu = items[positions[-1]].GetSubMenu()
        return positions

    def _viewer_element(self, text):
        "Graphical element in selected editor whose name, content or type contains text"
        viewer = self._eval("page")
        names = []
        for element in viewer.GetElements():
            for getter in ("GetName", "GetContent", "GetType"):
                name = getattr(element, getter, lambda: None)()
                if isinstance(name, str):
                    names.append(name)
                    if text in name:
                        viewer.EnsureVisible(element)
                        return viewer, element
        raise KeyError("%r not in %s: %r" % (text, viewer.GetTitle(), names))

    def viewer_element(self, text):
        "Screen rect of graphical element in selected editor whose name, content or type contains text"
        viewer, element = self._viewer_element(text)
        rect = viewer.GetScrolledRect(wx.Rect(element.GetBoundingBox()))
        return self._screen_rect(viewer.Editor, rect)

    def viewer_pin(self, text, pin):
        """
        Screen rect of wire leaving given pin of graphical element in selected
        editor whose name, content or type contains text
        """
        viewer, element = self._viewer_element(text)
        connectors = element.GetConnectors()
        pins = [connector.GetName() for connector in connectors["inputs"] + connectors["outputs"]]
        if pin not in pins:
            raise KeyError("%r not in pins: %r" % (pin, pins))
        connector = (connectors["inputs"] + connectors["outputs"])[pins.index(pin)]
        x, y = connector.GetPosition()
        dx, dy = connector.GetDirection()
        rect = viewer.GetScrolledRect(wx.Rect(x + dx * 10 - 2, y + dy * 10 - 2, 4, 4))
        return self._screen_rect(viewer.Editor, rect)

    def drop(self, x, y):
        """
        Drop data of last drag at given screen point. wx.TextDropTarget gets
        dragged text, other drop targets only get OnDrop() call.
        """
        window = wx.FindWindowAtPoint((x, y))
        while window is not None and window.GetDropTarget() is None:
            window = window.GetParent()
        if window is None:
            raise KeyError("No drop target at %d, %d" % (x, y))
        target = window.GetDropTarget()
        x, y = window.ScreenToClient((x, y))
        if isinstance(target, wx.TextDropTarget):
            return target.OnDropText(x, y, self.dragged.GetText())
        return target.OnDrop(x, y)

    def inspect(self, window, event):
        "Agent requests locating widget, and item under mouse event if any"
        pos = event.GetPosition()
        import wx.grid
        import wx.lib.agw.customtreectrl as CT
        import wx.lib.agw.hypertreelist as HTL
        requests = []

        widget = window  # located by window(), instead of its inner window if any

        tree = window.GetParent() if isinstance(window, HTL.TreeListMainWindow) else window
        if isinstance(tree, (CT.CustomTreeCtrl, HTL.HyperTreeList)):
            widget = tree
            item = window.HitTest(pos)[0]
            if item is not None:
                tree_expr = self._expression(tree)
                requests.append("tree_item(%r%s)" % (tree.GetItemText(item),
                    "" if tree_expr == "frame.ProjectTree" else ", %r" % tree_expr))

        grid = window.GetParent()
        if isinstance(grid, wx.grid.Grid) and window is grid.GetGridWindow():
            widget = grid
            cell = grid.XYToCell(*grid.CalcUnscrolledPosition(pos))
            if cell.GetRow() >= 0 and cell.GetCol() >= 0:
                requests.append("grid_cell(%r, %d, %r)" % (
                    self._expression(grid), cell.GetRow(), grid.GetColLabelValue(cell.GetCol())))

        viewer = window.GetParent()
        while viewer is not None and getattr(viewer, "Editor", None) is not window:
            viewer = viewer.GetParent()
        if viewer is not None and hasattr(viewer, "GetElements"):
            point = event.GetLogicalPosition(viewer.GetLogicalDC())
            for element in viewer.GetElements():
                if element.HitTest(point):
                    # wires are located by their output pin
                    connector = getattr(element, "EndConnected", None) or \
                        getattr(element, "TestConnector", lambda point: None)(point)
                    owner = element if connector is None else connector.GetParentBlock()
                    names = [getattr(owner, getter, lambda: None)() for getter in ("GetName", "GetContent", "GetType")]
                    name = next(name for name in names if isinstance(name, str) and name)
                    if connector is None:
                        requests.append("viewer_element(%r)" % name)
                    else:
                        requests.append("viewer_pin(%r, %r)" % (name, connector.GetName()))
                    break

        if isinstance(window, wx.Notebook):
            index, flags = window.HitTest(pos)
            if index != wx.NOT_FOUND and not flags & wx.BK_HITTEST_ONPAGE:
                requests.append("notebook_tab(%r, %r)" % (self._expression(window), window.GetPageText(index)))

        expr = self._expression(widget)
        if expr is not None:
            requests.append("window(%r)" % expr)
        elif not requests:
            return ["no request locates %s %r" % (widget.__class__.__name__, widget.GetName())]
        return ["app.agent." + request for request in requests]

    def _expression(self, window):
        "Python expression giving window, made of attributes, dict items and notebook pages"
        for name, anchor in (("dialog", self._modal_dialog()), ("page", self._eval("page")),
                             ("frame", self._frame())):
            if anchor is not None:
                path = self._path(anchor, window)
                if path is not None and self._eval(name + path) is window:
                    return name + path
        if wx.FindWindowByName(window.GetName()) is window:
            return "wx.FindWindowByName(%r)" % window.GetName()
        return None

    def _path(self, anchor, target):
        "Shortest path from anchor to target window, as a python expression suffix"
        queue = [(anchor, "")]
        seen = {id(anchor)}
        while queue:
            obj, path = queue.pop(0)
            if obj is target:
                return path
            for step, child in self._steps(obj):
                if id(child) not in seen and (child is target or child.IsDescendant(target)):
                    seen.add(id(child))
                    queue.append((child, path + step))
        return None

    def _steps(self, obj):
        "Windows that can be reached from obj, with corresponding python expression suffix"
        for name, value in vars(obj).items():
            if isinstance(value, wx.Window):
                yield "." + name, value
            elif isinstance(value, dict):
                for key, item in value.items():
                    if isinstance(item, wx.Window) and isinstance(key, (str, int)):
                        yield ".%s[%r]" % (name, key), item
            elif isinstance(value, (list, tuple)):
                for index, item in enumerate(value):
                    if isinstance(item, wx.Window):
                        yield ".%s[%d]" % (name, index), item
        if hasattr(obj, "GetPageCount") and hasattr(obj, "GetPage"):
            for index in range(obj.GetPageCount()):
                yield ".GetPage(%d)" % index, obj.GetPage(index)


IDETestAgent().start(int(os.environ["BEREMIZ_TEST_AGENT_PORT"]))
