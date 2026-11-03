cmake_minimum_required(VERSION 3.14)
project(simproxy_bbv_client LANGUAGES C)

if(NOT DynamoRIO_DIR)
  message(FATAL_ERROR "Set DynamoRIO_DIR to the DynamoRIO cmake directory, e.g. -DDynamoRIO_DIR=/path/to/DynamoRIO-AArch64-Linux-11.91.20756/cmake")
endif()

find_package(DynamoRIO REQUIRED)

add_library(simproxy_bbv SHARED src/bbv_profiler.c)
configure_DynamoRIO_client(simproxy_bbv)
use_DynamoRIO_extension(simproxy_bbv drmgr)
use_DynamoRIO_extension(simproxy_bbv drx)
use_DynamoRIO_extension(simproxy_bbv drcontainers)
use_DynamoRIO_extension(simproxy_bbv drcovlib)

set_target_properties(simproxy_bbv PROPERTIES
  C_STANDARD 11
  C_STANDARD_REQUIRED ON
)
