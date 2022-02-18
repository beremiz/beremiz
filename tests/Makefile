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
#           $ make run_python_exemple.sikuli
#
#       run tests from particular test classes
#           $ make ide_tests
#
#       run one particular test in a Xnest window
#           $ make xnest_run_python_exemple.sikuli
#
#       run Xnest window with just xterm
#           $ make xnest_xterm
#
#       run Xnest window with sikuli IDE and xterm
#           $ make xnest_sikuli
#
#       build minimal beremiz and matiec to run tests
#           $ make own_apps
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
#   Makefile attemps to use xvfb-run to run each test individually with its own
#   X server instance. This behavior can be overloaded
#       $ DISPLAY=:42 make xserver_command='echo "Using $DISPLAY X Server !";'
#
#   Matiec and Beremiz code are expected to be clean, ready to build
#   Any change in Matiec directory triggers rebuild of matiec.
#   Any change in Matiec and Beremiz directory triggers copy of source code
#   to $(test_dir)/build.
#
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

OWN_PROJECTS=beremiz matiec

# sha1 checksum of source is used to force copy/compile on each change

define make_checksum_assign
$(1)_checksum = $(shell tar --exclude=.hg --exclude=.git --exclude=.*.swp -c $(workspace)/$(1) | sha1sum | cut -d ' ' -f 1)
endef
$(foreach project,$(OWN_PROJECTS),$(eval $(call make_checksum_assign,$(project))))

$(build_dir):
	mkdir -p $(build_dir)

define make_src_rule
$(build_dir)/$(1)/$($(1)_checksum).sha1: $(build_dir) $(workspace)/$(1)
	rm -rf $(build_dir)/$(1)
	cp -a $(workspace)/$(1) $(build_dir)/$(1)
	touch $$@
endef
$(foreach project,$(OWN_PROJECTS),$(eval $(call make_src_rule,$(project))))

$(build_dir)/matiec/iec2c: | $(build_dir)/matiec/$(matiec_checksum).sha1
	cd $(build_dir)/matiec && \
    autoreconf -i && \
    ./configure && \
    make

# TODO: use packge (deb/snap ?)
own_apps: $(build_dir)/matiec/iec2c $(build_dir)/beremiz/$(beremiz_checksum).sha1
	touch $@

ide_tests = $(subst $(src)/ide_tests/,,$(wildcard $(src)/ide_tests/*.sikuli))

define idetest_command
	(fluxbox &); BEREMIZPATH=$(build_dir)/beremiz sikulix -r $(src)/ide_tests/$(1) | tee test_stdout.txt; exit $$$${pipestatus[0]}
endef

# Xnest based interactive sessions for tests edit and debug. 
# Would be nice with something equivalent to xvfb-run, waiting for USR1.
# Arbitrary "sleep 1" is probably enough for interactive use
define xnest_run
	Xnest :42 -geometry 1920x1080+0+0 & export xnestpid=$$!; sleep 1; DISPLAY=:42 $(1); export res=$$?; kill $${xnestpid} 2>/dev/null; exit $${res}
endef

xserver_command ?= xvfb-run -s '-screen 0 1920x1080x24'

define make_idetest_rule
$(test_dir)/$(1)_idetest/.passed: own_apps
	rm -rf $(test_dir)/$(1)_idetest
	mkdir $(test_dir)/$(1)_idetest
	cd $(test_dir)/$(1)_idetest; $(xserver_command) bash -c '$(call idetest_command, $(1))'
	touch $$@

# Manually invoked rule {testname}.sikuli
$(1): $(test_dir)/$(1)_idetest/.passed

# Manually invoked rule xnest_{testname}.sikuli
# runs test in xnest so that one can see what happens
xnest_$(1): own_apps
	rm -rf $(test_dir)/$(1)_idetest
	mkdir $(test_dir)/$(1)_idetest
	cd $(test_dir)/$(1)_idetest; $$(call xnest_run, bash -c '$(call idetest_command, $(1))')

ide_tests_targets += $(test_dir)/$(1)_idetest/.passed
endef
$(foreach idetest,$(ide_tests),$(eval $(call make_idetest_rule,$(idetest))))

ide_tests : $(ide_tests_targets)
	echo "$(ide_tests_targets)" : Passed

xnest_xterm: own_apps
	$(call xnest_run, bash -c '(fluxbox &);xterm')

xnest_sikuli: own_apps
	$(call xnest_run, bash -c '(fluxbox &);(xterm -e sikulix &);xterm')


# in case VNC would be used 
	#xvfb-run -s '-screen 0 1920x1080x24' bash -c '(fluxbox &);(x11vnc &);xterm;'


clean:
	rm -rf $(ide_tests_targets) $(build_dir)


# TODOs 

source_check:
	echo TODO $@

cli_tests :
	echo TODO $@

runtime_tests:
	echo TODO $@



