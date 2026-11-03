# Regenerate tc6_tree_convert grammar artifacts and run its tests
#
# IEC 61131-3 Annex A grammar (iec61131-3-3rd.ebnf) is IEC copyrighted and not
# distributed, nor are grammars derived from it. Generation needs a local copy.

PYTHON ?= python3
here := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

all: generate

generate: $(here)iec61131-3-3rd_extended.ebnf

$(here)iec61131-3-3rd_fixed.ebnf: $(here)iec61131-3-3rd.ebnf $(here)fix_ebnf.py $(here)ebnf.py
	$(PYTHON) $(here)fix_ebnf.py -o $@ $<

$(here)iec61131-3-3rd_extended.ebnf: $(here)iec61131-3-3rd_fixed.ebnf $(here)tc6_xml_v201.xsd \
		$(here)extend_ebnf.py $(here)ebnf.py
	$(PYTHON) $(here)extend_ebnf.py -o $@ -t $(here)tc6_textmap.py $< $(here)tc6_xml_v201.xsd

test:
	cd $(here) && $(PYTHON) -m unittest discover -s tests -v

.PHONY: all generate test
