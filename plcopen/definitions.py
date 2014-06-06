from os.path import join, split, realpath
sd = split(realpath(__file__))[0]

# Override gettext _ in this module
# since we just want string to be added to dictionnary
# but translation should happen here
_ = lambda x:x

LANGUAGES = ["IL","ST","FBD","LD","SFC"]

LOCATIONDATATYPES = {"X" : ["BOOL"],
                     "B" : ["SINT", "USINT", "BYTE", "STRING"],
                     "W" : ["INT", "UINT", "WORD", "WSTRING"],
                     "D" : ["DINT", "UDINT", "REAL", "DWORD"],
                     "L" : ["LINT", "ULINT", "LREAL", "LWORD"]}

#-------------------------------------------------------------------------------
#                        Function Block Types definitions
#-------------------------------------------------------------------------------

StdTC6Libs = [(_("Standard function blocks"),  join(sd, "Standard_Function_Blocks.xml")),
              (_("Additional function blocks"),join(sd, "Additional_Function_Blocks.xml"))]

StdFuncsCSV = join(sd,"iec_std.csv")

# FIXME : since std fb now loaded from TC6 file, is that still necessary ?
StdBlockComments = {
    "SR": _("SR bistable\nThe SR bistable is a latch where the Set dominates."),
    "RS": _("RS bistable\nThe RS bistable is a latch where the Reset dominates."),
    "SEMA": _("Semaphore\nThe semaphore provides a mechanism to allow software elements mutually exclusive access to certain ressources."),
    "R_TRIG": _("Rising edge detector\nThe output produces a single pulse when a rising edge is detected."),
    "F_TRIG": _("Falling edge detector\nThe output produces a single pulse when a falling edge is detected."),
    "CTU": _("Up-counter\nThe up-counter can be used to signal when a count has reached a maximum value."),
    "CTD": _("Down-counter\nThe down-counter can be used to signal when a count has reached zero, on counting down from a preset value."),
    "CTUD": _("Up-down counter\nThe up-down counter has two inputs CU and CD. It can be used to both count up on one input and down on the other."),
    "TP": _("Pulse timer\nThe pulse timer can be used to generate output pulses of a given time duration."),
    "TON": _("On-delay timer\nThe on-delay timer can be used to delay setting an output true, for fixed period after an input becomes true."),
    "TOF": _("Off-delay timer\nThe off-delay timer can be used to delay setting an output false, for fixed period after input goes false."),
    "RTC": _("Real time clock\nThe real time clock has many uses including time stamping, setting dates and times of day in batch reports, in alarm messages and so on."),
    "INTEGRAL": _("Integral\nThe integral function block integrates the value of input XIN over time."),
    "DERIVATIVE": _("Derivative\nThe derivative function block produces an output XOUT proportional to the rate of change of the input XIN."),
    "PID": _("PID\nThe PID (proportional, Integral, Derivative) function block provides the classical three term controller for closed loop control."),
    "RAMP": _("Ramp\nThe RAMP function block is modelled on example given in the standard."),
    "HYSTERESIS": _("Hysteresis\nThe hysteresis function block provides a hysteresis boolean output driven by the difference of two floating point (REAL) inputs XIN1 and XIN2."),
}

for block_type in ["CTU", "CTD", "CTUD"]:
    for return_type in ["DINT", "LINT", "UDINT", "ULINT"]:
        StdBlockComments["%s_%s" % (block_type, return_type)] = StdBlockComments[block_type]

def GetBlockInfos(pou):
    infos = pou.getblockInfos()
    # FIXME : as well
    infos["comment"] = StdBlockComments[infos["name"]]
    infos["inputs"] = [
        (var_name, var_type, "rising")
        if var_name in ["CU", "CD"]
        else (var_name, var_type, var_modifier)
        for var_name, var_type, var_modifier in infos["inputs"]]
    return infos

#-------------------------------------------------------------------------------
#                           Data Types definitions
#-------------------------------------------------------------------------------

"""
Ordored list of common data types defined in the IEC 61131-3
Each type is associated to his direct parent type. It defines then a hierarchy
between type that permits to make a comparison of two types
"""
TypeHierarchy_list = [
    ("ANY", None),
    ("ANY_DERIVED", "ANY"),
    ("ANY_ELEMENTARY", "ANY"),
    ("ANY_MAGNITUDE", "ANY_ELEMENTARY"),
    ("ANY_BIT", "ANY_ELEMENTARY"),
    ("ANY_NBIT", "ANY_BIT"),
    ("ANY_STRING", "ANY_ELEMENTARY"),
    ("ANY_DATE", "ANY_ELEMENTARY"),
    ("ANY_NUM", "ANY_MAGNITUDE"),
    ("ANY_REAL", "ANY_NUM"),
    ("ANY_INT", "ANY_NUM"),
    ("ANY_SINT", "ANY_INT"),
    ("ANY_UINT", "ANY_INT"),
    ("BOOL", "ANY_BIT"),
    ("SINT", "ANY_SINT"),
    ("INT", "ANY_SINT"),
    ("DINT", "ANY_SINT"),
    ("LINT", "ANY_SINT"),
    ("USINT", "ANY_UINT"),
    ("UINT", "ANY_UINT"),
    ("UDINT", "ANY_UINT"),
    ("ULINT", "ANY_UINT"),
    ("REAL", "ANY_REAL"),
    ("LREAL", "ANY_REAL"),
    ("TIME", "ANY_MAGNITUDE"),
    ("DATE", "ANY_DATE"),
    ("TOD", "ANY_DATE"),
    ("DT", "ANY_DATE"),
    ("STRING", "ANY_STRING"),
    ("BYTE", "ANY_NBIT"),
    ("WORD", "ANY_NBIT"),
    ("DWORD", "ANY_NBIT"),
    ("LWORD", "ANY_NBIT")
    #("WSTRING", "ANY_STRING") # TODO
]

DefaultType = "DINT"

DataTypeRange_list = [
    ("SINT", (-2**7, 2**7 - 1)),
    ("INT", (-2**15, 2**15 - 1)),
    ("DINT", (-2**31, 2**31 - 1)),
    ("LINT", (-2**31, 2**31 - 1)),
    ("USINT", (0, 2**8 - 1)),
    ("UINT", (0, 2**16 - 1)),
    ("UDINT", (0, 2**31 - 1)),
    ("ULINT", (0, 2**31 - 1))
]

ANY_TO_ANY_FILTERS = {
    "ANY_TO_ANY":[
        # simple type conv are let as C cast
        (("ANY_INT","ANY_BIT"),("ANY_NUM","ANY_BIT")),
        (("ANY_REAL",),("ANY_REAL",)),
        # REAL_TO_INT
        (("ANY_REAL",),("ANY_SINT",)),
        (("ANY_REAL",),("ANY_UINT",)),
        (("ANY_REAL",),("ANY_BIT",)),
        # TO_TIME
        (("ANY_INT","ANY_BIT"),("ANY_DATE","TIME")),
        (("ANY_REAL",),("ANY_DATE","TIME")),
        (("ANY_STRING",), ("ANY_DATE","TIME")),
        # FROM_TIME
        (("ANY_DATE","TIME"), ("ANY_REAL",)),
        (("ANY_DATE","TIME"), ("ANY_INT","ANY_NBIT")),
        (("TIME",), ("ANY_STRING",)),
        (("DATE",), ("ANY_STRING",)),
        (("TOD",), ("ANY_STRING",)),
        (("DT",), ("ANY_STRING",)),
        # TO_STRING
        (("BOOL",), ("ANY_STRING",)),
        (("ANY_BIT",), ("ANY_STRING",)),
        (("ANY_REAL",), ("ANY_STRING",)),
        (("ANY_SINT",), ("ANY_STRING",)),
        (("ANY_UINT",), ("ANY_STRING",)),
        # FROM_STRING
        (("ANY_STRING",), ("BOOL",)),
        (("ANY_STRING",), ("ANY_BIT",)),
        (("ANY_STRING",), ("ANY_SINT",)),
        (("ANY_STRING",), ("ANY_UINT",)),
        (("ANY_STRING",), ("ANY_REAL",))],
    "BCD_TO_ANY":[
        (("BYTE",),("USINT",)),
        (("WORD",),("UINT",)),
        (("DWORD",),("UDINT",)),
        (("LWORD",),("ULINT",))],
    "ANY_TO_BCD":[
        (("USINT",),("BYTE",)),
        (("UINT",),("WORD",)),
        (("UDINT",),("DWORD",)),
        (("ULINT",),("LWORD",))]
}

# remove gettext override
del _
