# Resolve exactly the package selected by PlatformIO, including version suffixes.
# Environment is intentional: IDF 4.4 extracts REQUIRES in a separate cmake -P
# process which does not inherit ordinary root CMake/cache variables.
if(DEFINED ENV{RCDEV_ARDUINO_DIR})
    file(TO_CMAKE_PATH "$ENV{RCDEV_ARDUINO_DIR}" rcdev_arduino_dir)
else()
    file(TO_CMAKE_PATH "$ENV{DEVRABIT_ARDUINO_DIR}" rcdev_arduino_dir)
endif()

if(NOT IS_DIRECTORY "${rcdev_arduino_dir}" OR
   NOT EXISTS "${rcdev_arduino_dir}/CMakeLists.txt")
    message(FATAL_ERROR "RCDEV: missing PlatformIO Arduino package identity")
endif()

get_filename_component(RCDEV_ARDUINO_COMPONENT "${rcdev_arduino_dir}" NAME)
set(DEVRABIT_ARDUINO_COMPONENT "${RCDEV_ARDUINO_COMPONENT}")
idf_component_get_property(rcdev_registered_dir "${RCDEV_ARDUINO_COMPONENT}" COMPONENT_DIR)
get_filename_component(rcdev_expected_dir "${rcdev_arduino_dir}" REALPATH)
get_filename_component(rcdev_registered_dir "${rcdev_registered_dir}" REALPATH)
if(NOT rcdev_registered_dir STREQUAL rcdev_expected_dir)
    message(FATAL_ERROR "RCDEV: Arduino component does not match PlatformIO package")
endif()
