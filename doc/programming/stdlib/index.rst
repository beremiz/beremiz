Standard library
================

..
    Documentation originally part of Smarteh's user Manual, and donated to Beremiz project.


.. list-table::

    * - .. figure:: library_panel.png

            Library browser

      - Library contains various groups of standard
        and user defined functions. They support the
        usage in different programmable controller
        programming languages inside POUs.


    * - .. figure:: block_properties.png

            Block Properties

      - Block Properties pop-up window can be
        opened by double-click on function block.
        Some of the blocks can have more inputs than
        default. This is selectable in the Inputs field
        (e.g. ADD block). Also an Execution Order of
        the blocks can be programmer-defined. All
        blocks have an additional Execution Control
        check-box. If it is checked than two new pins
        are added (EN – input and ENO – output) to
        control dynamically their execution.


Standard function blocks
------------------------

.. highlight:: text

.. list-table::

    * - .. figure:: std_block-012.png

            SR bistable

      - The SR bistable is a latch where the Set dominates.::

            ( BOOL:S1, BOOL:R ) => ( BOOL:Q1 )

        This function represents a standard set-dominant set/reset flip
        flop. The Q1 output become TRUE when the input S1 is TRUE and
        the R input is FALSE. In the same way, the Q1 output become
        FALSE when the input S1 is FALSE and the R input is TRUE. After
        one of these transitions, when both the S1 and R signals return to
        FALSE, the Q1 output keeps the previous state until a new
        condition occurs. If you apply a TRUE condition for both the
        signals, the Q1 output is forced to TRUE (set-dominant).


    * - .. figure:: std_block-010.png

            RS bistable

      - The RS bistable is a latch where the Reset dominates.::

            ( BOOL:S, BOOL:R1 ) => ( BOOL:Q1 )

        This function represents a standard reset-dominant set/reset flip
        flop. The Q1 output become TRUE when the input S is TRUE and
        the R1 input is FALSE. In the same way, the Q1 output become
        FALSE when the input S is FALSE and the R1 input is TRUE. After
        one of these transitions, when both the S and R1 signals return to
        FALSE, the Q1 output keeps the previous state until a new
        condition occurs. If you apply a TRUE condition for both the
        signals, the Q1 output is forced to FALSE (reset-dominant).


    * - .. figure:: std_block-019.png

            SEMA Semaphore

      - The semaphore provides a mechanism to allow software elements
        mutually exclusive access to certain resources.::

            ( BOOL:CLAIM, BOOL:RELEASE ) => ( BOOL:BUSY )

        This function block implements a semaphore function. Normally
        this function is used to synchronize events. The BUSY output is
        activated by a TRUE condition on the CLAIM input and it is de-
        activated by a TRUE condition on the RELEASE input.


    * - .. figure:: std_block-021.png

            R_TRIG Rising edge detector

      - The output produces a single pulse when a rising edge is detected.::

            ( BOOL:CLK ) => ( BOOL:Q )

        This function is a rising-edge detector. The Q output becomes
        TRUE when a 0 to 1 (or FALSE to TRUE or OFF to ON) condition is
        detected on the CLK input and it sustains this state for a complete
        scan cycle.


    * - .. figure:: std_block-023.png

            F TRIG

      - Falling edge detector
        The output Q produces a single pulse when a falling edge is
        detected.::

            ( BOOL:CLK ) => ( BOOL:Q )

        This function is a falling-edge detector. The Q output becomes
        TRUE when a 1 to 0 (or TRUE to FALSE or ON to OFF) condition is
        detected on the CLK input and it sustains this state for a complete
        scan cycle.


    * - .. figure:: std_block-030.png

            CTU
            CTU_DINT,
            CTU_LINT,
            CTU_UDINT, CTU_ULINT
            Up-counter

      - The up-counter can be used to signal when a count has reached a
        maximum value.::

            CTU:       ( BOOL:CU, BOOL:R, INT:PV ) => ( BOOL:Q, INT:CV )
            CTU_DINT:  ( BOOL:CU, BOOL:R, DINT:PV ) => ( BOOL:Q, DINT:CV )
            CTU_LINT:
            ( BOOL:CU, BOOL:R, LINT:PV ) => ( BOOL:Q, LINT:CV )
            CTU_UDINT: ( BOOL:CU, BOOL:R, UDINT:PV ) => ( BOOL:Q, UDINT:CV )
            CTU_ULINT: ( BOOL:CU, BOOL:R, ULINT:PV ) => ( BOOL:Q, ULINT:CV )

        The CTU function represents an up-counter. A rising-edge on CU
        input will increment the counter by one. When the programmed
        value, applied to the input PV, is reached, the Q output becomes
        TRUE. Applying a TRUE signal on R input will reset the counter to
        zero (Asynchronous reset). The CV output reports the current
        counting value.


    * - .. figure:: std_block-028.png

            CTD
            CTD_DINT, CTD_LINT,
            CTD_UDINT, CTD_ULINT
            Down-counter

      - The down-counter can be used to signal when a count has reached
        zero, on counting down from a pre-set value.::

            CTD:       ( BOOL:CD, BOOL:LD, INT:PV ) => ( BOOL:Q, INT:CV )
            CTD_DINT:  ( BOOL:CD, BOOL:LD, DINT:PV ) => ( BOOL:Q, DINT:CV )
            CTD_LINT:  ( BOOL:CD, BOOL:LD, LINT:PV ) => ( BOOL:Q, LINT:CV )
            CTD_UDINT: ( BOOL:CD, BOOL:LD, UDINT:PV ) => ( BOOL:Q, UDINT:CV )
            CTD_ULINT: ( BOOL:CD, BOOL:LD, ULINT:PV ) => ( BOOL:Q, ULINT:CV )

        The CTD function represents a down-counter. A rising-edge on CD
        input will decrement the counter by one. The Q output becomes
        TRUE when the current counting value is equal or less than zero.
        Applying a TRUE signal on LD (LOAD) input will load the counter
        with the value present at input PV (Asynchronous load). The CV
        output reports the current counting value.


    * - .. figure:: std_block-035.png

            CTUD
            CTUD_DINT,
            CTUD_LINT,
            CTUD_UDINT,
            CTUD_ULINT
            Up-down counter

      - The up-down counter has two inputs CU and CD. It can be used to
        both count up on one input and down on the other.::

            CTUD:       ( BOOL:CU, BOOL:CD, BOOL:R, BOOL:LD, INT:PV ) => ( BOOL:QU, BOOL:QD, INT:CV )
            CTUD_DINT:  ( BOOL:CU, BOOL:CD, BOOL:R, BOOL:LD, DINT:PV ) => ( BOOL:QU, BOOL:QD, DINT:CV )
            CTUD_LINT:  ( BOOL:CU, BOOL:CD, BOOL:R, BOOL:LD, LINT:PV ) => ( BOOL:QU, BOOL:QD, LINT:CV )
            CTUD_UDINT: ( BOOL:CU, BOOL:CD, BOOL:R, BOOL:LD, UDINT:PV ) => ( BOOL:QU, BOOL:QD, UDINT:CV )
            CTUD_ULINT: ( BOOL:CU, BOOL:CD, BOOL:R, BOOL:LD, ULINT:PV ) => ( BOOL:QU, BOOL:QD, ULINT:CV )
        
        This function represents an up-down programmable counter. A
        rising-edge on the CU (COUNT-UP) input increments the counter
        by one while a rising-edge on the CD (COUNT-DOWN) decreases
        the current value. Applying a TRUE signal on R input will reset the
        counter to zero. A TRUE condition on the LD signal will load the
        counter with the value applied to the input PV (PROGRAMMED
        VALUE). QU output becomes active when the current counting
        value is greater or equal to the programmed value. The QD output
        becomes active when the current value is less or equal to zero.
        The CV output reports the current counter value.


    * - .. figure:: std_block-037.png

            TP
            Pulse timer

      - The pulse timer can be used to generate output pulses of a given
        time duration.::

            ( BOOL:IN, TIME:PT ) => ( BOOL:Q, TIME:ET )

        This kind of timer has the same behaviour of a single-shot timer or
        a monostable timer.
        When a rising-edge transition is detected on the IN input, the Q
        output becomes TRUE immediately. This condition continues until
        the programmed time PT, applied to the relative pin, is elapsed.
        After that the PT is elapsed, the Q output keeps the ON state if
        the input IN is still asserted else the Q output returns to the OFF
        state. This timer is not re-triggerable. This means that after that
        the timer has started it can't be stopped until the complete
        session ends. The ET output reports the current elapsed time.


    * - .. figure:: std_block-042.png

            TON
            On-delay timer
                    
      - The on-delay timer can be used to delay setting an output true,
        for fixed period after an input becomes true.::

            ( BOOL:IN, TIME:PT ) => ( BOOL:Q, TIME:ET )

        Asserting the input signal IN of this function starts the timer.
        When the programmed time, applied to the input PT, is elapsed
        and the input IN is still asserted, the Q output becomes TRUE. This
        condition will continue until the input IN is released. If the IN
        input is released before time elapsing, the timer will be cleared.
        The ET output reports the current elapsed time.


    * - .. figure:: std_block-044.png

            TOF
            Off-delay timer

      - The off-delay timer can be used to delay setting an output false,
        for fixed period after input goes false.::

        ( BOOL:IN, TIME:PT ) => ( BOOL:Q, TIME:ET )

        Asserting the input signal IN of this function immediately activates
        the Q output. At this point, releasing the input IN will start the
        time elapsing. When the programmed time, applied to the input
        PT, is elapsed and the input IN is still released, the Q output
        becomes FALSE. This condition will be kept until the input IN is
        released. If the IN input is asserted again before time elapses, the
        timer will be cleared and the Q output remains TRUE. The ET
        output reports the current elapsed time.


Additional function blocks
--------------------------


.. list-table::

    * - .. figure:: std_block-055.png
    
            RTC
            Real Time Clock

      - The RTC function block sets the output CDT to the input value PDT at the next
        evaluation of the function block following a transition from 0 to 1 of the IN input. The CDT output
        of the RTC function block is undefined when the value of IN is 0.

        .. line-block:: 

            PDT = Preset date and time, loaded on rising edge of IN
            CDT = Current date and time, valid when IN=1
            Q = copy of EN

        .. code-block:: 

            (BOOL:IN, PDT:DT) => (BOOL:Q, CDT:DT)


    * - .. figure:: std_block-049.png
    
            INTEGRAL
            Integral

      - The integral function block integrates the value of input XIN over
        time.::

            ( BOOL:RUN, BOOL:R1, REAL:XIN, REAL:X0, TIME:CYCLE ) => ( BOOL:Q, REAL:XOUT )

        When input RUN is True and override R1 is False, XOUT will
        change for XIN value depends on CYCLE time value sampling
        period. When RUN is False and override R1 is True, XOUT will hold
        the last output value. If R1 is True, XOUT will be set to the X0
        value.::

            XOUT = XOUT + (XIN * CYCLE)


    * - .. figure:: std_block-051.png
    
            DERIVATIVE
            Derivative

      - The derivative function block produces an output XOUT
        proportional to the rate of change of the input XIN.::

            ( BOOL:RUN, REAL:XIN, TIME:CYCLE ) => ( REAL:XOUT )

        When RUN is True, XOUT will change proportional to the rate of
        changing of the value XIN depends on CYCLE time value sampling
        period.::

            XOUT = ((3 * (XIN - XIN(to-3))) + XIN(to-1) – XIN(to-2) ) / (10 * CYCLE)


    * - .. figure:: std_block-060.png
    
            PID
            Proportional, Integral, Derivative

      - The PID (Proportional, Integral, Derivative) function block
        provides the classical three term controller for closed loop
        control. It does not contain any output limitation parameters
        (dead-band, minimum, maximum, …) or other parameters
        normally used for real process control (see also PID_A).::

            ( BOOL:AUTO, REAL:PV, REAL:SP, REAL:X0, REAL:KP, REAL:TR, REAL:TD, TIME:CYCLE ) => ( REAL:XOUT )

        When AUTO is False, PID function block XOUT will follow X0 value.
        When AUTO is True, XOUT will be calculated from error value (PV
        process variable – SP set point), KP proportional constant, TR
        reset time, TD derivative constant and CYCLE time value sampling
        period.::

            XOUT = KP * ((PV-SP) + (I_OUT/TR) + (D_OUT * TD))


    * - .. figure:: std_block-062.png
    
            RAMP
            Ramp

      - The RAMP function block is modelled on example given in the
        standard but with the addition of a 'Holdback' feature.::

            ( BOOL:RUN, REAL:X0, REAL:X1, TIME:TR, TIME:CYCLE, BOOL:HOLDBACK, REAL:ERROR, REAL:PV ) => ( BOOL:RAMP, REAL:XOUT )

        When RUN and HOLDBACK are False, XOUT will follow X0 value.
        When RUN is True and HOLDBACK value is False, XOUT will change
        for ``OUT(to-1) + (X1 – XOUT(to-1))`` every CYCLE time value sampling
        period.


    * - .. figure:: std_block-064.png
    
            HYSTERESIS
            Hysteresis

      - The hysteresis function block provides a hysteresis boolean output
        driven by the difference of two floating point (REAL) inputs XIN1
        and XIN2.::

            ( REAL:XIN1, REAL:XIN2, REAL:EPS ) => ( BOOL:Q )

        When XIN1 value will be grater than XIN2 + EPS value, Q becomes
        True. When XIN1 value will be less than XIN2 - EPS value, Q
        becomes False.