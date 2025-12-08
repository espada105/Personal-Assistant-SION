cmake_minimum_required(VERSION 3.20)
project(SionHotkey VERSION 0.1.0 LANGUAGES CXX)

# C++ 표준 설정
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 빌드 타입 기본값
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# 컴파일러 옵션
if(MSVC)
    add_compile_options(/W4 /O2)
else()
    add_compile_options(-Wall -Wextra -O2)
endif()

# 소스 파일
set(SOURCES
    src/main.cpp
    src/hotkey_handler.cpp
    src/audio_capture.cpp
    src/python_bridge.cpp
)

# 헤더 파일
set(HEADERS
    include/hotkey_handler.h
    include/audio_capture.h
    include/python_bridge.h
)

# 실행 파일 생성
add_executable(${PROJECT_NAME} ${SOURCES} ${HEADERS})

# Include 디렉토리
target_include_directories(${PROJECT_NAME} PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Windows 전용 라이브러리
if(WIN32)
    target_link_libraries(${PROJECT_NAME} PRIVATE
        user32
        ole32
        oleaut32
    )
endif()

# Python 연동 (선택사항)
find_package(Python3 COMPONENTS Development)
if(Python3_FOUND)
    target_include_directories(${PROJECT_NAME} PRIVATE ${Python3_INCLUDE_DIRS})
    target_link_libraries(${PROJECT_NAME} PRIVATE ${Python3_LIBRARIES})
    target_compile_definitions(${PROJECT_NAME} PRIVATE PYTHON_ENABLED)
endif()

# 설치 설정
install(TARGETS ${PROJECT_NAME}
    RUNTIME DESTINATION bin
)

# 빌드 정보 출력
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
if(Python3_FOUND)
    message(STATUS "Python3 found: ${Python3_VERSION}")
endif()

