cmake_minimum_required(VERSION 3.14)
project(simproxy LANGUAGES C)

option(SIMPROXY_BUILD_DRCLIENT "Build the DynamoRIO client" ON)
option(SIMPROXY_BUILD_CODEGEN "Build the proxy kernel code generator" ON)

if(SIMPROXY_BUILD_DRCLIENT)
  add_subdirectory(drclient)
endif()

if(SIMPROXY_BUILD_CODEGEN AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/codegen/CMakeLists.txt")
  add_subdirectory(codegen)
endif()
