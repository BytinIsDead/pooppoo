cmake_minimum_required(VERSION 3.10)
project(pooppoo C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(PkgConfig REQUIRED)

# Actual WebKit: try WPE (pure WebKit) first if -DWPE=ON, else WebKitGTK (GTK port, still actual WebKit source)
option(USE_WPE "Use WPE WebKit (actual WebKit without GTK port)" OFF)
if(USE_WPE)
  pkg_check_modules(GTK REQUIRED gtk+-3.0)
  pkg_check_modules(WEBKIT REQUIRED wpe-webkit-1.1)
else()
  pkg_check_modules(GTK REQUIRED gtk+-3.0)
  pkg_check_modules(WEBKIT REQUIRED webkit2gtk-4.1)
  if(NOT WEBKIT_FOUND)
    pkg_check_modules(WEBKIT REQUIRED webkit2gtk-4.0)
  endif()
endif()
pkg_check_modules(SQLITE REQUIRED sqlite3)
pkg_check_modules(JSC javascriptcoregtk-4.1)

# actual WebKit source headers from cloned webkit-source/
if(EXISTS "${CMAKE_SOURCE_DIR}/webkit-source/Source/WebKit")
  include_directories("${CMAKE_SOURCE_DIR}/webkit-source/Source/WebKit")
  include_directories("${CMAKE_SOURCE_DIR}/webkit-source/Source/WebCore")
  include_directories("${CMAKE_SOURCE_DIR}/webkit-source/Source/JavaScriptCore")
endif()

add_executable(pooppoo src/main.c)
target_include_directories(pooppoo PRIVATE ${GTK_INCLUDE_DIRS} ${WEBKIT_INCLUDE_DIRS} ${SQLITE_INCLUDE_DIRS})
target_link_directories(pooppoo PRIVATE ${GTK_LIBRARY_DIRS} ${WEBKIT_LIBRARY_DIRS} ${SQLITE_LIBRARY_DIRS})
target_compile_options(pooppoo PRIVATE ${GTK_CFLAGS_OTHER} ${WEBKIT_CFLAGS_OTHER} -Wall -O2)
target_link_libraries(pooppoo ${GTK_LIBRARIES} ${WEBKIT_LIBRARIES} ${SQLITE_LIBRARIES})

# JSC demo - actual WebKit JavaScriptCore
if(JSC_FOUND)
  add_executable(jsc-demo src/actual_webkit_demo.c)
  target_include_directories(jsc-demo PRIVATE ${JSC_INCLUDE_DIRS})
  target_compile_options(jsc-demo PRIVATE ${JSC_CFLAGS_OTHER})
  target_link_libraries(jsc-demo ${JSC_LIBRARIES})
endif()

install(TARGETS pooppoo DESTINATION bin)
