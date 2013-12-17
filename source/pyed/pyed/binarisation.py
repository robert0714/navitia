"""
Functions to launch the binaratisations
"""
from pyed.launch_exec import launch_exec
from pyed.config import ConfigException
import logging
import subprocess
import os
import pyed.task_pb2
import pika

def make_connection_string(config):
    """ Make the a connection string connection from the config """
    connection_string = 'host='+config.get("database", "host")
    connection_string += " user="+config.get("database", "user")
    connection_string += " dbname="+config.get("database", "name")
    connection_string += " password="+config.get("database", "password")
    return connection_string

def fusio2ed(fusio_filename, config, backup_directory):
    """ Unzip fusio file, remove the file, launch fusio2ed """
    pyed_logger = logging.getLogger('pyed')
    fusio_logger = logging.getLogger('fusio2ed')
    res = launch_exec("mv", [fusio_filename, backup_directory], pyed_logger)
    if res != 0:
        return 1
    fusio_bnanme = os.path.basename(fusio_filename)
    new_fusio = backup_directory + "/" +fusio_bnanme
    res = launch_exec("unzip", [new_fusio, "-d", backup_directory],
                       pyed_logger)
    if res != 0:
        return 2
    params = ["-i", backup_directory]
    try:
        aliases = config.get("instance", "aliases")
        params.append("-a")
        params.append(aliases)
    except ConfigException:
        pass
    try:
        synonyms = config.get("instance", "synonyms")
        params.append("-s")
        params.append(synonyms)
    except ConfigException:
        pass
    try :
        connection_string = make_connection_string(config)
    except ConfigException:
        pyed_logger.error("fusio2ed : Unable to make the connection string")
        return 3
    params.append("--connection-string")
    params.append(connection_string)
    res = launch_exec(config.get("instance", "exec_directory")+"/fusio2ed",
                      params, fusio_logger, pyed_logger)
    if res != 0:
        return 4
    return 0


def osm2ed(osm_filename, config, backup_directory):
    """ Move osm file to backup directory, launch osm2ed """
    pyed_logger = logging.getLogger('pyed')
    osm_logger = logging.getLogger('osm2ed')
    res = launch_exec("mv", [osm_filename, backup_directory], pyed_logger)
    if res != 0:
        error = "Error while moving " + osm_filename
        error += + " to " + backup_directory
        osm_logger(error)
        pyed_logger(error)
        return 1
    connection_string = ""
    try:
        connection_string = make_connection_string(config)
    except ConfigException:
        error = "osm2ed : Unable to make the connection string"
        pyed_logger.error(error)
        osm_logger.error(error)
        return 2
    mved_file = backup_directory
    mved_file += "/"+osm_filename.split("/")[-1]
    res = launch_exec(config.get("instance", "exec_directory")+"/osm2ed",
                ["-i", mved_file, "--connection-string", connection_string],
                osm_logger, pyed_logger)
    if res != 0:
        error = "osm2ed failed"
        pyed_logger.error(error)
        osm_logger.error(error)
        return 3
    return 0


def reload_data(config):
    """ reload data on all kraken"""
    task = pyed.task_pb2.Task()
    task.action = pyed.task_pb2.RELOAD
    pyed_logger = logging.getLogger('pyed')

    #TODO configurer la connection!!!
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=config.get('broker', 'host'),
        port=int(config.get('broker', 'port')),
        virtual_host=config.get('broker', 'vhost'),
        credentials=pika.credentials.PlainCredentials(
            config.get('broker', 'username'),
            config.get('broker', 'password'))
        ))
    channel = connection.channel()
    instance_name = config.get('instance', 'name')
    exchange_name = config.get('broker', 'exchange')
    channel.exchange_declare(exchange=exchange_name, type='topic',
            durable=True)

    pyed_logger.info("reload kraken")
    channel.basic_publish(exchange=exchange_name,
            routing_key=instance_name+'.task.reload',
            body=task.SerializeToString())
    connection.close()


def ed2nav(config):
    """ Launch ed2nav"""
    pyed_logger = logging.getLogger('pyed')
    ed2nav_logger = logging.getLogger('ed2nav')
    filename = None
    try :
        filename = config.get("instance" , "tmp_file")
    except ConfigException, error:
        ed2nav_logger.error(error)
        return 4
    try:
        connection_string = make_connection_string(config)
    except ConfigException:
        pyed_logger.error("osm2ed : Unable to make the connection string")
        return 1
    res = launch_exec(config.get("instance", "exec_directory")+"/ed2nav",
                ["-o", filename, "--connection-string", connection_string],
                ed2nav_logger, pyed_logger)
    if res != 0:
        return 2
    return 0

def nav2rt(config):
    """ Launch nav2rt"""
    pyed_logger = logging.getLogger('pyed')
    nav2rt_logger = logging.getLogger('nav2rt')
    source_filename = None
    target_filename = None
    try :
        source_filename = config.get("instance", "tmp_file")
        target_filename = config.get("instance", "target_file")
    except ConfigException, error:
        nav2rt_logger.error(error)
        return 4
    try:
        connection_string = make_connection_string(config)
    except ConfigException:
        pyed_logger.error("nav2rt: Unable to make the connection string")
        return 1
    res = launch_exec(config.get("instance", "exec_directory")+"/nav2rt",
                ["-i", source_filename, "-o", target_filename, "--connection-string", connection_string],
                nav2rt_logger, pyed_logger)
    if res != 0:
        return 2
    reload_data(config)
    return 0
