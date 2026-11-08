include("$ENV{DEVRABIT_PLATFORM_DIR}/cmake/arduino-component.cmake")
idf_component_register(SRCS "main.cpp" INCLUDE_DIRS "." REQUIRES ${DEVRABIT_ARDUINO_COMPONENT})
