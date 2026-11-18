# PlatformIO pre-build script for env:native.
# build_flags go to both the C and C++ compilers, and clang rejects "-std=c++11"
# on C files (Unity is C). CXXFLAGS only reaches the C++ compiler.
Import("env")  # noqa: F821  (provided by PlatformIO/SCons)

env.Append(CXXFLAGS=["-std=c++11"])  # noqa: F821
