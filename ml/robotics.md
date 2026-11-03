# ROS Bags and MCAP: Formats for Robotics and Sensor Data

ROS bags and MCAP are technologies used to record, store, and replay time-series data from robots, autonomous vehicles, drones, and other systems with multiple sensors.

They are particularly important in autonomous driving, robotics, and physical AI.

The key distinction is:

- ROS bag describes a recording mechanism and ecosystem associated with ROS (Robot Operating System).
- MCAP is a file format designed to store timestamped messages efficiently, including ROS messages, Protobuf, and other serialized data.

## 1. What is a ROS bag?

ROS = Robot Operating System

ROS is an open-source robotics framework providing communication between software components.

For example, an autonomous vehicle may publish several streams of data:

Camera

Images · 30 FPS

LiDAR

Point clouds · 10 Hz

GPS

Coordinates · 1 Hz

IMU

Acceleration · 100 Hz

ROS topics

ROS bag recorder

Captures timestamped messages from multiple topics

Recorded bag

Stored messages that can be replayed later

A ROS bag preserves messages from different sensors with their timestamps, so engineers can reconstruct what the robot observed during an experiment.

For example:

```
/camera/image_raw
/lidar/points
/gps/fix
/imu/data
/vehicle/speed
/vehicle/steering_angle
```

Each topic can have a different message schema and sampling frequency.

A bag recording is particularly useful for debugging because the same sensor data can be replayed through different versions of an algorithm.

## 2. What is MCAP?

MCAP is an open-source container file format for recording timestamped, heterogeneous messages.

Official website: [mcap.dev](https://mcap.dev/?utm_source=chatgpt.com)

GitHub: [foxglove/mcap](https://github.com/foxglove/mcap?utm_source=chatgpt.com)

Unlike a ROS bag, which is associated with the ROS recording ecosystem, MCAP is designed to be independent of ROS.

An MCAP file can contain:

- Camera frames
- LiDAR point clouds
- GPS measurements
- IMU readings
- Vehicle telemetry
- Robot control commands
- Other custom serialized messages

MCAP supports multiple serialization formats, such as ROS 1 messages, ROS 2 messages, and Protobuf.

### Conceptual MCAP file structure

Header

Schema definitions + channels

Timestamped messages

10:00:00.000

Camera

10:00:00.005

IMU

10:00:00.010

LiDAR

10:00:00.015

GPS

Optional indexes + summary

Simplified logical layout. Actual MCAP records include message metadata, optional chunks, indexes, and footer records.

MCAP can support efficient time-based seeking and topic filtering through its indexing structures, without requiring a full scan of every message.

## 3. ROS bag vs MCAP

| Feature             | ROS bag                              | MCAP                        |
| ------------------- | ------------------------------------ | --------------------------- |
| What is it?         | Recording system / bag format family | File format                 |
| Associated with ROS | Yes                                  | Optional                    |
| ROS 1 support       | Yes                                  | Yes                         |
| ROS 2 support       | Yes                                  | Yes                         |
| Protobuf support    | Not native to traditional ROS bags   | Yes                         |
| Random access       | Depends on storage format            | Indexed access supported    |
| Compression         | Depends on implementation            | Chunk compression supported |
| Python support      | Yes                                  | Yes                         |
| Typical extension   | `.bag`, `.db3`, `.mcap`              | `.mcap`                     |

Important: ROS 2 can use MCAP as its storage backend. They are not mutually exclusive technologies.

For example, ROS 2's `rosbag2` can record into SQLite3 (`.db3`) or MCAP (`.mcap`) depending on the storage plugin.

## 4. How to use MCAP with Python

You can read and write MCAP files without installing ROS.

Install the Python package:

```
pip install mcap
```

Read messages:

```
from mcap.reader import make_readerwith open("recording.mcap", "rb") as f:    reader = make_reader(f)    for schema, channel, message in reader.iter_messages():        print(            channel.topic,            message.log_time,            len(message.data),        )
```

`message.log_time` is the message's log timestamp in nanoseconds.

The raw `message.data` contains serialized bytes. To interpret those bytes as Python objects, you need an appropriate decoder for the channel's message encoding, such as Protobuf or ROS messages.

### Writing a simple MCAP file

```
from mcap.writer import Writerwith open("telemetry.mcap", "wb") as f:    writer = Writer(f)    writer.start()    schema_id = writer.register_schema(        name="VehicleTelemetry",        encoding="jsonschema",        data=b'{"type":"object"}',    )    channel_id = writer.register_channel(        topic="/vehicle/telemetry",        message_encoding="json",        schema_id=schema_id,    )    writer.add_message(        channel_id=channel_id,        log_time=1_700_000_000_000_000_000,        publish_time=1_700_000_000_000_000_000,        data=b'{"speed":45.2,"battery":82}',    )    writer.finish()
```

This creates an MCAP file containing one JSON-encoded telemetry message.

## 5. How does MCAP compare with Parquet, Kafka, and Delta Lake?

This is especially relevant for data engineering.

| Technology     | Main purpose                                  |
| -------------- | --------------------------------------------- |
| MCAP           | Store and replay synchronized sensor messages |
| Apache Parquet | Columnar analytical storage                   |
| Kafka          | Streaming event transport and retention       |
| Delta Lake     | Transactional analytical tables               |
| ROS bag        | Record and replay ROS topics                  |

An MCAP file is not optimized for the same workloads as Parquet.

For example, suppose you have 100 GB of autonomous vehicle recordings.

MCAP is a good choice when you want to:

- Replay camera and LiDAR messages in timestamp order.
- Reproduce a vehicle's sensor observations.
- Debug a perception algorithm.
- Synchronize multiple sensor streams.

Parquet is a better choice when you want to:

- Calculate average vehicle speed by day.
- Aggregate battery statistics across millions of vehicles.
- Run distributed SQL analytics.
- Store normalized tabular telemetry in a lakehouse.

In practice, a data platform may use both:

Autonomous vehicle sensors

MCAP recordings in S3

Python / Spark extraction pipeline

Parquet / Delta Lake

Structured telemetry for analytics

Databricks / StarRocks / dashboards

The original MCAP files can remain in S3 for full-fidelity replay, while extracted telemetry is stored in Parquet or Delta Lake for analytical queries.

## 6. Tools for inspecting MCAP files

[Foxglove standardizes robotics data recording with MCAP - The Robot Report](https://images.openai.com/static-rsc-4/EPA3lSONZScv1mQdpVNDurQNXwUBiyQAwU-K5qxvQrnAx8-I5MJIUGmpWn0kSSNuW7YyKAHobBU-5WBl-dr9bzgMlNYse3wgE7_uhB2bNEJa7SvWY6Akvu_2kVv0uc_At25L4F5OUQ_y1AtBOGRKD1-jsrjhI_6ASM1WvhG2vaM?purpose=inline)

Foxglove

Visualizes MCAP recordings, including 3D point clouds, images, plots, and time-synchronized sensor data.

[foxglove.dev](https://foxglove.dev/?utm_source=chatgpt.com)

[View ROS 2 Messages with Plotjuggler - MBARI-WEC](https://images.openai.com/static-rsc-4/bWTWXfN55yUubhIbY5AsGDRBYJYWa5guHn64z2Li5_kTVoKG6-EEb8cMJ9estiHgFHdMf7QNXsrjvWodhnrv1i-O-btA94hHyimLE4KS3BBWQVSbTE7k__Kc4vw47p0jJg4SppfF9GgSJTegVKkJMeQ82aLmwRvLd8yyYcBaxQo?purpose=inline)

PlotJuggler

Useful for exploring and plotting numeric telemetry, with ROS bag support through plugins.

[GitHub](https://github.com/facontidavide/PlotJuggler?utm_source=chatgpt.com)

Given your experience with vehicle GPS telemetry and Databricks, MCAP is worth learning if you plan to work with autonomous vehicles, robotics, or multimodal sensor data.

A useful hands-on project would be to take a public MCAP recording, extract GPS and IMU data with Python, synchronize them by timestamp, convert the results to Parquet, and analyze vehicle trajectories using SQL.
