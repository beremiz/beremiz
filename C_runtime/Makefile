# Builds standalone C/C++ Beremiz runtime

# This Makefile is based on fragments of eRPC Makefiles

APP_NAME = beremiz_runtime

RUNTIME_ROOT = $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
ERPC_ROOT ?= $(abspath $(RUNTIME_ROOT)/../../erpc)
ERPC_C_ROOT = $(ERPC_ROOT)/erpc_c

INCLUDES += $(ERPC_C_ROOT)/infra \
            $(ERPC_C_ROOT)/port \
            $(ERPC_C_ROOT)/setup \
            $(ERPC_C_ROOT)/transports \
            $(ERPC_ROOT)/test/common/config \
            $(ERPC_ROOT)/erpcgen/src

INCLUDES := $(foreach includes, $(INCLUDES), -I $(includes))

ERPC_SOURCES += $(ERPC_ROOT)/erpcgen/src/format_string.cpp \
                $(ERPC_ROOT)/erpcgen/src/Logging.cpp \
                $(ERPC_ROOT)/erpcgen/src/options.cpp \
                $(ERPC_C_ROOT)/infra/erpc_arbitrated_client_manager.cpp \
                $(ERPC_C_ROOT)/infra/erpc_basic_codec.cpp \
                $(ERPC_C_ROOT)/infra/erpc_client_manager.cpp \
                $(ERPC_C_ROOT)/infra/erpc_crc16.cpp \
                $(ERPC_C_ROOT)/infra/erpc_server.cpp \
                $(ERPC_C_ROOT)/infra/erpc_simple_server.cpp \
                $(ERPC_C_ROOT)/infra/erpc_framed_transport.cpp \
                $(ERPC_C_ROOT)/infra/erpc_message_buffer.cpp \
                $(ERPC_C_ROOT)/infra/erpc_message_loggers.cpp \
                $(ERPC_C_ROOT)/infra/erpc_transport_arbitrator.cpp \
                $(ERPC_C_ROOT)/infra/erpc_utils.cpp \
                $(ERPC_C_ROOT)/port/erpc_port_stdlib.cpp \
                $(ERPC_C_ROOT)/port/erpc_threading_pthreads.cpp \
                $(ERPC_C_ROOT)/port/erpc_serial.cpp \
                $(ERPC_C_ROOT)/transports/erpc_serial_transport.cpp \
                $(ERPC_C_ROOT)/transports/erpc_tcp_transport.cpp
			
SOURCES +=  $(RUNTIME_ROOT)/c_erpc_PLCObject_client.cpp \
            $(RUNTIME_ROOT)/c_erpc_PLCObject_server.cpp \
            $(RUNTIME_ROOT)/erpc_PLCObject_client.cpp \
            $(RUNTIME_ROOT)/erpc_PLCObject_interface.cpp \
            $(RUNTIME_ROOT)/erpc_PLCObject_server.cpp \
			$(RUNTIME_ROOT)/posix_main.cpp \
			$(RUNTIME_ROOT)/PLCObject.cpp


# get version from version.py
BEREMIZ_VERSION := $(shell python3 $(RUNTIME_ROOT)/../version.py)

CXXFLAGS += -std=gnu++17 -Wunused-variable -Wno-deprecated-register -Wno-narrowing -Werror -DBEREMIZ_VERSION=$(BEREMIZ_VERSION)
# CFLAGS += -Os -DNDEBUG
CXXFLAGS += -g3 -O0 -DDEBUG

LIBRARIES += -lpthread -lrt -lc -lm
LD = $(CXX)

OBJS_ROOT = $(RUNTIME_ROOT)/build
SOURCES_ABS := $(foreach s,$(SOURCES),$(abspath $(s)))
SOURCES_REL := $(subst $(RUNTIME_ROOT)/,,$(SOURCES_ABS))
SOURCE_DIRS_ABS := $(sort $(foreach f,$(SOURCES_ABS),$(dir $(f))))
SOURCE_DIRS_REL := $(subst $(RUNTIME_ROOT)/,,$(SOURCE_DIRS_ABS))
CXX_SOURCES = $(filter %.cpp,$(SOURCES_REL))
OBJECTS_CXX := $(addprefix $(OBJS_ROOT)/,$(CXX_SOURCES:.cpp=.o))

$(OBJS_ROOT)/%.o: $(RUNTIME_ROOT)/%.cpp
	@echo Compiling $(subst $(RUNTIME_ROOT)/,,$<)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -MMD -MF $(basename $@).d -MP -o $@ -c $<

ERPC_OBJS_ROOT = $(RUNTIME_ROOT)/erpcbuild
ERPC_SOURCES_ABS := $(foreach s,$(ERPC_SOURCES),$(abspath $(s)))
ERPC_SOURCES_REL := $(subst $(ERPC_ROOT)/,,$(ERPC_SOURCES_ABS))
ERPC_SOURCE_DIRS_ABS := $(sort $(foreach f,$(ERPC_SOURCES_ABS),$(dir $(f))))
ERPC_SOURCE_DIRS_REL := $(subst $(ERPC_ROOT)/,,$(ERPC_SOURCE_DIRS_ABS))
ERPC_CXX_SOURCES = $(filter %.cpp,$(ERPC_SOURCES_REL))
ERPC_OBJECTS_CXX := $(addprefix $(ERPC_OBJS_ROOT)/,$(ERPC_CXX_SOURCES:.cpp=.o))

$(ERPC_OBJS_ROOT)/%.o: $(ERPC_ROOT)/%.cpp
	@echo Compiling, $(subst $(ERPC_ROOT)/,,$<)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -MMD -MF $(basename $@).d -MP -o $@ -c $<

OBJECTS_ALL := $(sort $(ERPC_OBJECTS_CXX) $(OBJECTS_CXX))
OBJECTS_DIRS := $(OBJS_ROOT) $(addprefix $(OBJS_ROOT)/,$(SOURCE_DIRS_REL)) $(ERPC_OBJS_ROOT) $(addprefix $(ERPC_OBJS_ROOT)/,$(ERPC_SOURCE_DIRS_REL))

.PHONY: all $(APP_NAME)
all: $(APP_NAME) $(OBJECTS_DIRS)

$(OBJECTS_DIRS) :
	mkdir -p $@

$(OBJECTS_ALL): | $(OBJECTS_DIRS)

$(APP_NAME): $(OBJECTS_ALL)
	@echo Linking, $(APP_NAME)
	$(LD) $(LDFLAGS) \
		$(OBJECTS_ALL) \
		-o $@ \
		$(LIBRARIES)
	@echo "Output binary:" ; echo "  $(APP_NAME)"

.PHONY: clean
clean::
	@echo "Cleaning $(APP_NAME)"
	rm -rf $(OBJECTS_ALL) $(OBJECTS_DIRS) $(APP_NAME)

-include $(OBJECTS_ALL:.o=.d)
