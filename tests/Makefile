#! gmake

# beremiz/tests/Makefile :
#
#   Makefile to prepare and run Beremiz tests.
#
#   For developper to:
#       - quickly run a test (TDD) on current code 
#       - write new tests, debug existing tests 
#
#     Use cases :
#
#       run given tests
#           $ make run_python_exemple.pytest
#
#       run tests from particular test classes
#           $ make ide_tests
#
#       run IDE displayed in your browser, to help writing IDE tests
#           $ make ide_session ide_session_project=exemples/python
#
#       build minimal beremiz and matiec to run tests
#           $ make built_apps
#
#   For CI/CD scripts to catch and report all failures. Use cases :
#
#       run all tests
#           $ make
#
#   
#   Test results, and other test byproducts are in $(test_dir), 
#   $(test_dir) defaults to $(HOME)/test and can be overloaded:
#       $ make test_dir=${HOME}/other_test_dir
#
#   IDE tests run headless, IDE being displayed with GTK Broadway backend in
#   a browser driven by Playwright. See ide_tests/ide_harness.py
#
#   Matiec and Beremiz code are expected to be clean, ready to build
#   Any change in Matiec directory triggers rebuild of matiec.
#   Any change in Matiec and Beremiz directory triggers copy of source code
#   to $(test_dir)/build.
#
#   BEREMIZPYTHONPATH is expected to be absolute path to python interpreter
#
#   Please note:
#       In order to run asside a freshly build Matiec, tested beremiz instance
#       needs to run on code from $(test_dir)/build/beremiz, a fresh copy
#       of the Beremiz directory $(src)/beremiz, where we run tests from.
#   

all: source_check cli_tests ide_tests runtime_tests 

# Variable $(src) is directory such that executed 
# $(src)/Makefile is this file.
src := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

# $(workspace) is directory containing this project
workspace ?= $(abspath $(src)/../..)

test_dir ?= $(HOME)/test
build_dir = $(test_dir)/build

#
# SOURCE and BUILD
#

BUILT_PROJECTS=beremiz matiec open62541 Modbus erpc paho.mqtt.c frozen

tar_opts=--absolute-names --exclude=.hg --exclude=.git --exclude=.*.pyc --exclude=.*.swp

# sha1 checksum of source is used to force copy/compile on each change

define make_checksum_assign
$(1)_checksum = $(shell tar $(tar_opts) -c $(workspace)/$(1) | sha1sum | cut -d ' ' -f 1)
endef
$(foreach project,$(BUILT_PROJECTS),$(eval $(call make_checksum_assign,$(project))))

$(build_dir):
	mkdir -p $(build_dir)

define make_src_rule
$(build_dir)/$(1)/$($(1)_checksum).sha1: | $(build_dir) $(workspace)/$(1)
	rm -rf $(build_dir)/$(1)
	tar -C $(workspace) $(tar_opts) -c $(1) | tar -C $(build_dir) -x
	touch $$@
endef
$(foreach project,$(BUILT_PROJECTS),$(eval $(call make_src_rule,$(project))))

$(build_dir)/matiec/iec2c: $(build_dir)/matiec/$(matiec_checksum).sha1
	cd $(build_dir)/matiec && \
    autoreconf -i && \
    ./configure && \
    make

$(build_dir)/open62541/build/bin/libopen62541.a: $(build_dir)/open62541/$(open62541_checksum).sha1
	cd $(build_dir)/open62541 && \
    rm -rf build && mkdir build && cd build && \
	cmake -D UA_ENABLE_ENCRYPTION=OPENSSL .. && \
	make

$(build_dir)/Modbus/libmb.a: | $(build_dir)/Modbus/$(Modbus_checksum).sha1
	cd $(build_dir)/Modbus && \
	make

$(build_dir)/paho.mqtt.c/build/src/libpaho-mqtt3cs.a: $(build_dir)/paho.mqtt.c/$(paho.mqtt.c_checksum).sha1
	cd $(build_dir)/paho.mqtt.c && \
	rm -rf build && mkdir build && cd build && \
	cmake .. -DPAHO_BUILD_STATIC=TRUE -DPAHO_WITH_SSL=TRUE && \
	make

$(build_dir)/frozen/frozen.stamp: $(build_dir)/frozen/$(frozen_checksum).sha1
	touch $@

$(build_dir)/beremiz/C_runtime/beremiz_runtime: $(build_dir)/erpc/$(erpc_checksum).sha1
	cd $(build_dir)/beremiz/C_runtime && \
	make

built_apps: $(build_dir)/matiec/iec2c $(build_dir)/beremiz/$(beremiz_checksum).sha1 \
			$(build_dir)/open62541/build/bin/libopen62541.a \
			$(build_dir)/Modbus/libmb.a \
			$(build_dir)/paho.mqtt.c/build/src/libpaho-mqtt3cs.a \
			$(build_dir)/frozen/frozen.stamp \
			$(build_dir)/beremiz/C_runtime/beremiz_runtime
	touch $@

define log_command
	$(call $(1),$(2)) | tee test_stdout.txt; exit $$$${PIPESTATUS[0]}
endef

define prep_test
	rm -rf $(test_dir)/$(1)_results
	mkdir $(test_dir)/$(1)_results
	cd $(test_dir)/$(1)_results
endef

#
# IDE TESTS
#

ide_test_dir = $(src)/ide_tests
pytest_ide_tests = $(subst $(ide_test_dir)/,,$(wildcard $(ide_test_dir)/*.pytest))

fluxbox_command ?= echo "session.screen0.toolbar.placement: TopCenter" > fluxbox_init; (fluxbox -rc fluxbox_init >/dev/null 2>&1 &)

DELAY=400
KILL_DELAY=430
PYTEST=$(dir $(BEREMIZPYTHONPATH))pytest
define pytest_idetest_command
	BEREMIZPATH=$(build_dir)/beremiz PYTHONPATH=$(ide_test_dir) timeout -k $(KILL_DELAY) $(DELAY) $(PYTEST) --maxfail=1 --timeout=100  $(src)/ide_tests/$(1)
endef


define make_pytest_idetest_rule
$(test_dir)/$(1)_results/.passed: built_apps
	$(call prep_test,$(1)); bash -c '$(call log_command,$(2),$(1))'
	touch $$@

# Manually invoked rule {testname}.pytest
$(1): $(test_dir)/$(1)_results/.passed

ide_tests_targets += $(test_dir)/$(1)_results/.passed
endef
$(foreach idetest,$(pytest_ide_tests),$(eval $(call make_pytest_idetest_rule,$(idetest),pytest_idetest_command)))

ide_tests : $(ide_tests_targets)
	echo "$(ide_tests_targets) : Passed"

pytest_ide_tests_targets = $(patsubst %,$(test_dir)/%_results/.passed,$(pytest_ide_tests))

pytest_ide_tests : $(pytest_ide_tests_targets)
	echo "$(pytest_ide_tests_targets) : Passed"

# Interactive IDE session, to help writing IDE tests. See ide_tests/ide_session.py
ide_session: built_apps
	BEREMIZPATH=$(build_dir)/beremiz PYTHONPATH=$(ide_test_dir) $(BEREMIZPYTHONPATH) $(ide_test_dir)/ide_session.py $(ide_session_project)

#
# CLI TESTS
#

cli_test_dir = $(src)/cli_tests
cli_tests = $(subst $(cli_test_dir)/,,$(wildcard $(cli_test_dir)/*.bash))

define clitest_command
	BEREMIZPATH=$(build_dir)/beremiz source $(src)/cli_tests/$(1)
endef

define make_clitest_rule
$(test_dir)/$(1)_results/.passed: built_apps
	$(call prep_test,$(1)); timeout 600 bash -c '$(call log_command,$(2),$(1))' || (echo "Test $(1) timed out or failed"; exit 1)
	touch $$@

# Manually invoked rule
$(1): $(test_dir)/$(1)_results/.passed

cli_tests_targets += $(test_dir)/$(1)_results/.passed
endef
$(foreach clitest,$(cli_tests),$(eval $(call make_clitest_rule,$(clitest),clitest_command)))

cli_tests: $(cli_tests_targets)
	echo "$(cli_tests_targets) : Passed"

clean_results:
	rm -rf $(test_dir)/*_results

clean: clean_results
	rm -rf $(build_dir)


# TODOs 

source_check:
	echo TODO $@

runtime_tests:
	echo TODO $@



