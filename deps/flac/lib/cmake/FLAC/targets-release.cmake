#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "FLAC::FLAC" for configuration "Release"
set_property(TARGET FLAC::FLAC APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(FLAC::FLAC PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "C"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libFLAC.a"
  )

list(APPEND _IMPORT_CHECK_TARGETS FLAC::FLAC )
list(APPEND _IMPORT_CHECK_FILES_FOR_FLAC::FLAC "${_IMPORT_PREFIX}/lib/libFLAC.a" )

# Import target "FLAC::flacapp" for configuration "Release"
set_property(TARGET FLAC::flacapp APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(FLAC::flacapp PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/flac"
  )


# Import target "FLAC::metaflac" for configuration "Release"
set_property(TARGET FLAC::metaflac APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(FLAC::metaflac PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/metaflac"
  )


# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
