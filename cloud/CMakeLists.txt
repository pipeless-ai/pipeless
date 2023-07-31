# Set the minimum required CMake version
cmake_minimum_required(VERSION 3.26)

# Set your project name and version
project(pupila VERSION 0.1.0)

# Set C++ standard
set(CMAKE_CXX_STANDARD 20)

# Gstreamer options. Ref: https://gstreamer.freedesktop.org/documentation/installing/on-linux.html
find_package(PkgConfig REQUIRED)
pkg_check_modules(GSTREAMER REQUIRED gstreamer-1.0)
include_directories(${GSTREAMER_INCLUDE_DIRS})

# Add the executable target and list your source files
add_executable(${PROJECT_NAME}
    main.cpp
    file1.cpp
    file2.cpp
    # Add more source files as needed
)

# Link with GStreamer libraries
target_link_libraries(${PROJECT_NAME} ${GSTREAMER_LIBRARIES})
add_definitions(${GSTREAMER_CFLAGS_OTHER})

# Additional compiler options or other flags if necessary
target_compile_options(${PROJECT_NAME} PRIVATE -Wall -Wextra)

# External libraries, you can link them here
# For example:
# find_package(OpenCV REQUIRED)
# target_link_libraries(${PROJECT_NAME} PRIVATE ${OpenCV_LIBS})

# Headers located in additional directories
# For example:
# target_include_directories(YourExecutableName PRIVATE include)

# Additional source directories
# For example:
# add_subdirectory(subdirectory_name)

# Specific flags or variables
# For example:
# set(SOME_VARIABLE "some_value")

# Custom CMake modules or scripts
# For example:
# include(cmake/CustomModule.cmake)
