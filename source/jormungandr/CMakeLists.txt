INSTALL_FILES(/srv/jormungandr FILES find_extrem_datetimes.py instance_manager.py jormungandr.py protobuf_to_dict.py swagger.py ${CMAKE_CURRENT_SOURCE_DIR}/type_pb2.py validate.py apis.py renderers.py singleton.py universals.py ${CMAKE_CURRENT_SOURCE_DIR}/request_pb2.py ${CMAKE_CURRENT_SOURCE_DIR}/response_pb2.py conf.py error.py jormungandr.wsgi)

add_subdirectory("scripts")
add_subdirectory("interfaces")