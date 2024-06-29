cmake_minimum_required(VERSION 3.12)
project(udprx)
set(CMAKE_INCLUDE_CURRENT_DIR ON)

set (CMAKE_CXX_STANDARD 11)
include_directories(.)

set(udprx_SRC udprx.cpp common/Socket.cpp common/Timer.cpp)
set(udprx_INC common/Socket.h common/Timer.h common/TSCTimer.h)
add_executable(udprx ${udprx_SRC} ${udprx_INC})

set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)
target_link_libraries(udprx PRIVATE Threads::Threads)

set(CMAKE_THREAD_PREFER_PTHREAD On)
