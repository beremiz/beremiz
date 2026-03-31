Pre-made Widget Library
=======================

Each widget type such as for example ``HMI:Meter`` can be applied to different
SVG elements to make a new widget in an HMI.

+------------------------------------+---------------------------------+
| Meter Widget Template (`HMI:Meter`)|      Voltmeter (`HMI:Meter`)    | 
+====================================+=================================+
| .. image:: svghmi_meter.svg        | .. image:: svghmi_voltmeter.svg |
+------------------------------------+---------------------------------+

It is possible to collect customized widgets into libraries in order to re-use
them in future HMI designs.


Widget selection and configuration
----------------------------------

SVGHMI comes with a UI dedicated to:

    * Select SVG widget from a library

        Button on top of library tree opens a directory selector dialog to select another widget library.
        When a widget is selected in library tree, a miniature of this widget is displayed in preview panel.

    * Set widget arguments

        Given values are checked against expected argument types and boundaries, and validity is shown as a 
        check mark on the right side of each argument.

    * Bind widget to HMI Tree variables

        Variables are dragged from HMI Tree to text fields in "Widget's variables" section, and then a 
        valid path corresponding to selected variable is assigned to this field.

        .. image:: svghmi_library_ui.svg

    * Place widget in HMI design

        Once configured, widget is placed in HMI design by dragging widget preview in Inkscape directly.

        .. image:: svghmi_dnd.svg


How to create a widget library
------------------------------

    A widget library is a directory containing SVG files organized into arbitrarily nested subdirectories.

    Individual SVG file must only contain one widget, no nested widgets, and no pages.
    It can be created by simply copying an existing widget into an empty SVG file.
    Existing attributes are ignored when using widget from library and can be left as-is.