cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr)

if(CONFIG_LLEXT STREQUAL "y")
  project(beremiz C CXX)
  # Programmable Beremiz runtime 
  # loads PLC as a LLEXT binary
  # and communicates with it via eRPC
  target_sources(app PRIVATE 
    main_programmable.cpp
    ../service/erpc_PLCObject_client.cpp
    ../service/erpc_PLCObject_interface.cpp
    ../service/erpc_PLCObject_server.cpp
    ../md5.cpp
		../blob.cpp
		../PLCObject.cpp
    ${CONFIG_BOARD}/*.c
  )

  # Create a relocatable ELF LLEXT binary
  add_llext_target(softplc
    OUTPUT  ${ZEPHYR_BINARY_DIR}/softplc.llext
    SOURCES ${PLC_C_FILES}
  )

  # TODO: produce image including runtime and LLEXT binaries
  #       for flashing to device all at once

  set(plc_target softplc_llext_lib)

else()
  project(beremiz C)
  # Non-programmable Beremiz runtime 
  # is statically linked to PLC code
  # eRPC isn't included to spare resources
  target_sources(app PRIVATE
    $<TARGET_OBJECTS:softplc>
    main_builtin.c
  )
  
  # Create an object library for the PLC code
  # in order to compile only this code with the PLC flags
  add_library(softplc OBJECT
    ${PLC_C_FILES}
  )

  set(plc_target softplc)

endif()

target_compile_options(${plc_target} PRIVATE
  ${PLC_C_FLAGS}
)

add_dependencies(app softplc)


