cmake_minimum_required(VERSION 3.22)
project(BassDriverVST VERSION 1.0.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(DEFINED JUCE_ROOT AND NOT JUCE_ROOT STREQUAL "")
    add_subdirectory(${JUCE_ROOT} juce)
else()
    include(FetchContent)
    FetchContent_Declare(JUCE
        GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
        GIT_TAG 7.0.12
        GIT_SHALLOW TRUE
    )
    FetchContent_MakeAvailable(JUCE)
endif()

# the shared DSP core (also compiled into the B1on ZDL by zdl/build.py)
add_library(bddi_core STATIC ${CMAKE_CURRENT_SOURCE_DIR}/../core/bddi.c)
target_include_directories(bddi_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/../core)

juce_add_plugin(BassDriverVST
    COMPANY_NAME "sansamp-b1on"
    VERSION 1.0.0
    PLUGIN_MANUFACTURER_CODE BsDr
    PLUGIN_CODE BsDr
    PRODUCT_NAME "BassDriver"
    FORMATS VST3
    IS_SYNTH FALSE
    NEEDS_MIDI_INPUT FALSE
    NEEDS_MIDI_OUTPUT FALSE
    IS_MIDI_EFFECT FALSE
    EDITOR_WANTS_KEYBOARD_FOCUS FALSE
    COPY_PLUGIN_AFTER_BUILD TRUE
)
juce_generate_juce_header(BassDriverVST)
target_sources(BassDriverVST PRIVATE PluginProcessor.cpp PluginEditor.cpp)
target_link_libraries(BassDriverVST PRIVATE bddi_core)
target_compile_definitions(BassDriverVST PRIVATE JUCE_VST3_CAN_REPLACE_VST2=0)
target_compile_definitions(BassDriverVST_VST3 PRIVATE JUCE_VST3_CAN_REPLACE_VST2=0)
