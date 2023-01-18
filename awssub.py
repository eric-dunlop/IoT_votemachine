#! /usr/bin/env python3

# Created by Lubos Kuzma, SADT, SAIT -edited/modified by Eric Dunlop
# May, 2022
# Program sends random integers to AWS IoT Core
# You can shut down the program by pubishing message "command":"exit" to the topic "back/msgs". this is done from AWS IoT Core


from time import sleep, process_time            #process_time is used for delays. Counts the running time of process
from paho.mqtt import client as mqtt
import ssl, re, os                              #SSL, RegEx, os for shutdown command
from random import randint                      #randint for generating random #s
from json import dumps, loads, load                 #JSON manipulation. Not necessary, but makes data more readable

#IoT settings

path_to_root_cert = "pathToRootCert"                                  # local path to Amazon Root Cetificate
path_to_device_cert = "pathToDeviceCert"                                # local path to Device certificate pem or crt            
path_to_private_key = "pathToPrivateKey"                                # local path to Private key
device_id = ""
aws_url = ""                                            # taken from AWS IoT Core

publish_topic = ""
publish_qos = 1
subscribe_topic = ""
subscribe_qos = 1



#======================================================================
# logs input event to vote.log file

def log(log_entry):
  flag = 0
  try:
    with open("vote.log", "r") as vote_log:
      cur_log = vote_log.readline()

      while cur_log:
        if log_entry == cur_log:
          flag += 1
        cur_log = vote_log.readline()
  finally:
    with open("vote.log", "a") as vote_log:
      if not flag:
        print("=====Logged=====")
        vote_log.writelines(f"{log_entry}")
        return True
      else:
        return False

#===========================================================================
# updates a jason file that is used to keep track of vote counts.

def update_vote(vote):
  try:
    with open("vote.json", "r") as vote_file:
      vote_dict = load(vote_file)
  except FileNotFoundError:
    vote_dict = {}  
  if vote in vote_dict.keys():
    vote_dict[vote] += 1 
  else:
    vote_dict[vote] = 1
  with open("vote.json", "w") as vote_file:
    vote_file.writelines(dumps(vote_dict))

#=====================================================================
# display the contents on the json in readable format

def display_results():
  with open("vote.json", "r") as vote_file:
    json_dict = load(vote_file)
    for key, value in json_dict.items():
     print(f"{key}\t--->>\t{value}")

#========================================================================
#function calls

def on_connect(client, userdata, flags, rc):
    print("Device connected with result code: " + str(rc))


def on_disconnect(client, userdata, rc):
    print("Device disconnected with result code: " + str(rc))


def on_publish(client, userdata, mid):
    print("Device message sent.")

def on_message(client, userdata, message):
    new_msg = loads(message.payload)
    print("Received Message:")
    print(new_msg)

    if log(f"{new_msg['time']} : vote for {new_msg['vote']} -  {new_msg['uuid']}\n"):
      update_vote(new_msg["vote"])
    # sleep to prevent duplicate reads since qos 2 is not offered 
    # shutdown if the command from the AWS command is "command":"exit"
    # TODO: this should be rewritten in separate function
    if ('command','exit') in new_msg.items():
        shut_down()

def on_subscribe(client, userdata, mid, granted_qos):
    print("Client subscribed: ", str(mid), " with qos:", str(granted_qos))

def on_unsubscribe(client, userdata, mid):
    print("Client Unsubscribed")

def on_log(client, userdata, level, buf):
    print("Log:", str(buf))

def shut_down():
    print("\nSystem Exit initiated")
    awsClient.loop_stop()
    awsClient.disconnect()
    sleep(10)
    os._exit(0)

# MQTT Client definition
awsClient = mqtt.Client(client_id=device_id, protocol=mqtt.MQTTv311)

# MQTT callback functions
awsClient.on_connect = on_connect
awsClient.on_disconnect = on_disconnect
awsClient.on_publish = on_publish
awsClient.on_message = on_message
awsClient.on_subscribe = on_subscribe
awsClient.on_unsubscribe = on_unsubscribe
# awsClient.on_log = on_log                                             # uncomment for logging

# create ssl context and settings
ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH,cafile=path_to_root_cert)
ssl_context.load_cert_chain(certfile=path_to_device_cert, keyfile=path_to_private_key)

# MQTT Client TLS settings. All certs and the key files are required (original way to create ssl context, if used, comment out two lines above)
#awsClient.tls_set(ca_certs=path_to_root_cert, certfile=path_to_device_cert, keyfile=path_to_private_key,
#cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)

awsClient.tls_set_context(context=ssl_context)
awsClient.tls_insecure_set(False)

# MQTT Client connect
awsClient.connect(aws_url, port=8883)
awsClient.loop_start()
sleep(3)

if __name__ == "__main__":
  awsClient.subscribe((subscribe_topic, subscribe_qos))
  try:
    while True:
      pass

  except KeyboardInterrupt:
    shut_down()
