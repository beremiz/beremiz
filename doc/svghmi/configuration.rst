SVGHMI instances configuration
==============================

.. list-table::

    * - Multiple SVGHMI instances can be configured simultaneously in the same Beremiz  :doc:`../programming/configuration`, exposing different HMIs.

        .. image:: svghmi_multi.png

      - .. figure:: svghmi_configuration.png

        SVGHMI configuration panel

Ports, interfaces, path and MaxConnections
------------------------------------------

    Each SVGHMI instance must bind to different interface-port-path triplet. In case of conflict, a build error is issued.

    By default, interface is set to ``localhost``, port to ``8008`` and path is set to :doc:`../programming/configuration` Node's name: ``{name}``.
    As an example, in case SVGHMI instance is first node in :doc:`../programming/configuration`, default URL to reach HMI is ``http://localhost:8008/svghmi_0``

    Up to ``MaxConnections`` clients (i.e. web browser) can connect to the same SVGHMI instance simultaneously.
    This number has an influence on memory footprint of generated code.
    In case of repeated connection loss with long TCP `TTL <https://en.wikipedia.org/wiki/Time_to_live>`_, small ``MaxConnections`` number can lead to connection refusal.



About Security
^^^^^^^^^^^^^^

 ..
    TODO :


Watchdog
--------

    Purpose of SVGHMI watchdog is to detect if HMI is still functioning and connected to PLC.
    ``/HEARTBEAT`` variable is periodically updated by PLC and HMI to detect failure.
    
    When SVHGMI server doesn't receive HMI heartbeat in due time, watchdog is triggered, and ``OnWatchdog`` command is executed. 
    For example, ``OnWatchdog`` can be used to restart a new web browser in case it did crash.

    Only one single client can use watchdog at a time, and ``Watchdog`` configuration setting can be active on only one SVGHMI instance at a time.

    ``WatchdogInitial`` and ``WatchdogInterval`` define how long watchdog will accept to wait before receiving first heartbeat,
    and then how long it will wait in between heartbeats once first heartbeat has been received.


Starting and stopping browser
-----------------------------

    ``OnStart`` and ``OnStop`` configuration settings are commands meant control web browser execution when PLC is started or stopped.
    PID of commands are monitored, and the end of web browser process is awaited after command. 
    If web browser process isn't finished 3s after calling ``OnStop`` command, warning is logged.    
