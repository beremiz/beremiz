cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr)
project(beremiz)

if(CONFIG_LLEXT STREQUAL "y")
  # Programmable Beremiz runtime 
  # loads PLC as a LLEXT binary
  target_sources(app PRIVATE 
    zephyr_main_programmable.c
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
  # Non-programmable Beremiz runtime 
  # is statically linked to PLC code
  target_sources(app PRIVATE
    $<TARGET_OBJECTS:softplc>
    zephyr_main_builtin.c
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


