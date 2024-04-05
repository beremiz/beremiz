Pages, Jumps and HMI_NODE relativity
====================================

Pages are full screen. Only one page is displayed at the same time.

Page change is triggered by ``HMI:Jump`` and ``HMI:Back``, or by changing ``/CURRENTPAGE_N``.

.. code-block:: text

    HMI:Page:PageName[@RootPath]
    HMI:Jump:PageName[@RelativePath]
    HMI:Back

Absolute and relative pages
---------------------------

When ``[@RootPath]`` is given, page is relative.

When using ``HMI:Jump`` to reach a relative page, a compatible
``[@RelativePath]`` may be provided.

To be compatible, ``RootPath`` and ``RelativePath`` must both point to
HMI tree nodes of type ``HMI_NODE`` instanciated from same POU.

Every widget using a path descendant of ``RootPath`` in a relative
page is relative. Relative widgets get the ``RootPath`` section of
their path replaced by ``RelativePath``.

Relative page label::

    HMI:Page:PageName

Absolute page label::

    HMI:Page:PageName@RootPath

.. image:: svghmi_relative.svg


Jump and Back
-------------


``HMI:Jump`` can have ``inactive``, ``active`` and ``disabled`` labeled children:

    * ``inactive`` is shown when target page is not currently displayed
    * ``active`` is shown when target page is currently displayed
    * ``disabled`` is shown when relative page's RootPath is set to 0, disabling jump.

Relative page label::

    HMI:Jump:PageName[@RelativePath]

Absolute page label::

    HMI:Jump:PageName


``HMI:Back`` takes no parameter and just go back one step in page change history.


Special ``/CURRENTPAGE_N`` variable
-----------------------------------

..
    TODO


Overlapping geometry
--------------------

If widget's bounding box is included in page bounding box, then widget is part of page.

..
    TODO


References frames
-----------------

References frames help to unclutter page and widgets.

..
    TODO

Screensaver
-----------

..
    TODO

Fading
------

..
    TODO

Go full screen
--------------

..
    TODO
