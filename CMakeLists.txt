cmake_minimum_required(VERSION 3.10)
project(pooppoo C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(PkgConfig REQUIRED)
pkg_check_modules(GTK REQUIRED gtk+-3.0)
pkg_check_modules(WEBKIT REQUIRED webkit2gtk-4.1)
# fallback for 4.0 on some distros
if(NOT WEBKIT_FOUND)
  pkg_check_modules(WEBKIT REQUIRED webkit2gtk-4.0)
endif()
pkg_check_modules(SQLITE REQUIRED sqlite3)

add_executable(pooppoo src/main.c)

target_include_directories(pooppoo PRIVATE ${GTK_INCLUDE_DIRS} ${WEBKIT_INCLUDE_DIRS} ${SQLITE_INCLUDE_DIRS})
target_link_directories(pooppoo PRIVATE ${GTK_LIBRARY_DIRS} ${WEBKIT_LIBRARY_DIRS} ${SQLITE_LIBRARY_DIRS})
target_compile_options(pooppoo PRIVATE ${GTK_CFLAGS_OTHER} ${WEBKIT_CFLAGS_OTHER} -Wall -O2)
target_link_libraries(pooppoo ${GTK_LIBRARIES} ${WEBKIT_LIBRARIES} ${SQLITE_LIBRARIES})

install(TARGETS pooppoo DESTINATION bin)
