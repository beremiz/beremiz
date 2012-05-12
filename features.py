libraries = ['py_ext.PythonLibrary',
             'svgui.SVGUILibrary']

catalog = [
    ('canfestival', _('CANopen support'), _('Map located variables over CANopen'), 'canfestival.canfestival.RootClass'),
    ('c_ext', _('C extention'), _('Add C code accessing located variables synchronously'), 'c_ext.c_ext.RootClass'),
    ('py_ext', _('Python file'), _('Add Python code executed asynchronously'), 'py_ext.PythonFile'),
    ('wxglade_hmi', _('WxGlade GUI'), _('Add a simple WxGlade based GUI.'), 'wxglade_hmi.WxGladeHMI'),
    ('svgui', _('SVGUI'), _('Experimental web based HMI'), 'svgui.SVGUI')]

