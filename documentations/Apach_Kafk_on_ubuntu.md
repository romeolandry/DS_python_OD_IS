# Apache Kafka

For more informations have a look in to the [documentation](https://kafka.apache.org/documentation/)

​	Apache Kafka is a messaging system 

​	producers -> Kafka server -> consumers

- it is distributed platform / application

## Installation for Kafka on Ubuntu

The provided archive of Kafka come with Zookeeper inside. download the latest version on this [page](https://www.apache.org/dyn/closer.cgi?path=/kafka/2.7.0/kafka_2.13-2.7.0.tgz) and follow the instruction bellow.

1. extract the content of tar-File in desire install directory

   ```shell
   $ tar -xvzf [downloaded_file_name.tgz]
   $ cd [extracted_directory]
   ```

   after that you all already have Kafka on your computer. lets us do the necessary configuration.

2. Zookeeper and Kafka configuration file 

   navigate in to the extracted directory , go inside **configuration-Directory**. it content one important file *server.properties* .  Open it 

   ```
   go to the section Socket Server Settings 
   uncommend the line advertised.listeners=PLAINTEXT://[server-ip-address]:9092
   and change [server-ip-address] with your IP-Adress
   
   Go to the section Zookeeper
   update the line
   	zookeeper.connect=your.computer.name:2181
   	with
   	zookeeper.connect=YOUR_IP_ADDRESS:2181
   ```



## Run Kafka Server

***Note:*** Kafka Server required  *Java 8+* Installed.

To run Kafka Server you have run  Zookeeper first and then Kafka Broker

1. Start Zookeeper 

   navigate in to Kafka-directory and the run

   ```sh
   $ bin/zookeeper-server-start.sh config/zookeeper.properties
   ```

2. Start Kafka 

   ```shell
   $ JMX_PORT=8004 bin/kafka-server-start.sh config/server.properties 
   ```

   JMX_PORT make the JMX port possible (I don't what it do)  but its important to set it .

   Kafka server (Broker) use the port **9092** and Zookeeper use the port **2181** 

## Kafka Topics

- Topic is the Kafka  component to connect Producers. 

- Producers use it to publish message to consumers 
- is multi subscriber: it cloud be connected to more than one consumer
- in Kafka cluster each topic is present in every cluster node.
- Topic is divided into parts: Partition.
  - every partition has a partition number and a partition offset.
  - the data into partition are immutable after publishing.
  - in case of multiple partition and multiple broker, the partition will be randomly distributed into each broker

an Broker is an Kafka server running and Kafka cluster can content multiple broker

## Kafka Producers

- Producers publish message to the topics of their choice: in reality the message are publish to topic partition.
- To Publish message some configuration are needed by Producer.
  - bootstrap_servers is the Kafka server address.(9.0.9.2)
  - topic: topic name to publish the message.
  - value_serialize: to serialize the content message so that it can be sending over the wire.

## Kafka Consumer

- Kafka component who consume message from Kafka topic(internally from topic partition)

- every consumer is always assigned to a consumer group. if consumer have been created without group Kafka will randomly one to this consumer

- Configuration needed  by Consumer

  - topic
  - bootstrap_servers
  - group_id

  

### Consumer group

Is logical grouping of one or more consumer

- consumer instances of same consumer group can be on different nodes.
- same partition can't be assigned to multiple consumer in same group.



## Replication in Kafka 

- Kafka is fault tolerant:  its able to continue operating without interruption when one or more of its components fail.
- Each partition is replicated across multiple server Broker(virtual or physical machine) for fault tolerance.
- only one partition will be active at a time can called **Leader**. 
- Other Partition will only replicate message are called **Followers**.
- The lead handles all read and write request for the partition while followers passively replicate the leader.

## [Command line for kafka](http://cloudurable.com/blog/kafka-tutorial-kafka-from-command-line/index.html)



# Optional: Kafka manger Interface [CMAK](https://github.com/yahoo/CMAK)

Managing Kafka its only possible on command line. To the own who need an user interfaces to manage Cluster,[ yahoo/CMAK ](https://github.com/yahoo/CMAK) was created. it required ***Kafka*** and ***Java 11+***.

## Deployment

clone this [repository](https://github.com/yahoo/CMAK.git)

```shell
# clone project dir 
$ git clone https://github.com/yahoo/CMAK.git 
# Nvigate the cloned dir 
$cd CMAK
# create and zip content the application deployement
$ ./sbt clean dist
# its will create a target folder. nigate in to target/universal.
# you find an zip- file 
$ cd target/universal
# unzip this file
$ unzip cma-*.zip
# go inside the unsiped folder. It content bin, conf directory.
# enter into conf directory and open the file application.conf to set zookeeper property:address ip
$ [your-text-editor] application.conf
# change cmak.zhosts="kafka-manager-zookeeper:2181" to cmak.zhosts="IP-Adress for-Zookeeper-Server:2181
```

## Run cmak

Make shore you already start Zookeeper and Kafka-Broker before start cmak

```shell
$ bin/cmak -Dconfig.file=conf/application.conf -Dhttp.port=8080
```

**Note:** If the given port is used it will automatic change the port to the default port (9000). take a look on the to see on which port cmak server have started. Read the [Readme](https://github.com/yahoo/CMAK) for more explanation.

# Notices

# Issue

1- Error Message

```shell
mkdir: das Verzeichnis »/opt/kafka_2.13-2.7.0/bin/../logs“ kann nicht angelegt werden: Keine Berechtigung
[0.001s][error][logging] Error opening log file '/opt/kafka_2.13-2.7.0/bin/../logs/zookeeper-gc.log': No such file or directory
[0.001s][error][logging] Initialization of output 'file=/opt/kafka_2.13-2.7.0/bin/../logs/zookeeper-gc.log' using options 'filecount=10,filesize=100M' failed.
Invalid -Xlog option '-Xlog:gc*:file=/opt/kafka_2.13-2.7.0/bin/../logs/zookeeper-gc.log:time,tags:filecount=10,filesize=100M', see error log for details.
Error: Could not create the Java Virtual Machine.
Error: A fatal exception has occurred. Program will exit.
```

	* **Solution** Run command whit sudo 