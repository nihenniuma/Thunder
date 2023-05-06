CMAKE_MINIMUM_REQUIRED(VERSION 3.5)
# SET (CMAKE_BUILD_TYPE "Debug")
# SET (CMAKE_CXX_FLAGS_DEBUG "$ENV{CXXFLAGS} -O0 -Wall -g2 -ggdb")
# SET (CMAKE_CXX_FLAGS_RELEASE "$ENV{CXXFLAGS} -O3 -Wall")

set (DCMAKE_CXX_COMPILER "/usr/bin/gcc")
set (CMAKE_CXX_STANDARD 17)

PROJECT(tweaker) #项目名称　　

find_package(pybind11 REQUIRED)
add_compile_options(-std=c++14)

AUX_SOURCE_DIRECTORY(./ SRC_LIST) #把当前目录(.)下所有源代码文件和头文件加入变量SRC_LIST
include_directories("/usr/include/c++/7/Eigen")
ADD_EXECUTABLE(tweaker ${SRC_LIST}) #生成应用程序 hello (在windows下会自动生成hello.exe)

# ADD_EXECUTABLE(tweaker main.cpp) # 调试的时候的

target_link_libraries(tweaker PRIVATE pybind11::embed)