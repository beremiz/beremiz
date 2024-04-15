Include fonts in HMI
====================

Text inside HMI designed with Inkscape may not display properly in web browser.
The reason is that Inkscape and targeted web browser may disagree on fonts support.

To keep HMI text design consistent, missing fonts can be added to project in order
to have them served together with HMI so that web browser can support them.

Fonts used by Inkscape
----------------------

* System fonts

    Vector fonts available at system level are systematically available
    in Inkscape

* User fonts

    When selected in Inkscape preferences, Inkscape also considers fonts
    from these sources:

    - "fonts" directory in Inkscape user's directory

    - arbitrary absolute font directories set by user 

    There is no way to point to a directory relative to the SVG file
    being edited.
    At the time of writing this documentation, Inkscape doesn't support
    embedding font in SVG file.

    User then have to regularly update Inkscape preferences to ensure
    that fonts used in currently edited design are available when editing
    it.


Supported font types in SVGHMI
------------------------------

    * Web Open Font Format 1 and 2

        ``.woff```, ``.woff2``

    * TrueType fonts

        ``.ttf``

    * OpenType fonts

        ``.otf``

    .. note:: 

        In order to be embedded in HMI, fonts are encoded base64 

Add/remove fonts
----------------