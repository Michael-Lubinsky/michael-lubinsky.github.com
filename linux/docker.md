### Docker

 The Bitnami image packs Hadoop and Spark in a ready-to-go cluster:
```
docker pull bitnami/spark:3
docker run -it bitnami/spark spark-shell
```

Confluent’s CP-Kafka image comes battle-tested:  
Wire up the Schema Registry image (confluentinc/cp-schema-registry)  
to enforce Avro schemas in your pipelines.
 
```
docker pull confluentinc/cp-kafka:7.4.0
docker-compose up -d zookeeper kafka
```

Postgres
```
docker pull postgres:15
docker run -d -p 5432:5432 \
  -e POSTGRES_PASSWORD=secret \
  -v db_data:/var/lib/postgresql/data \
  postgres:15
```

jupyter/datascience-notebook
```
docker pull jupyter/datascience-notebook:latest
docker run -p 8888:8888 jupyter/datascience-notebook
```

local S3-compatible storage, MinIO <https://github.com/minio/mc>

```
docker pull minio/minio
docker run -p 9000:9000 minio/minio server /data
```

Grafana and Prometheus 
```
# prometheus.yml

scrape_configs:
  - job_name: 'docker'
    static_configs:
    - targets: ['prometheus:9090']

docker pull prom/prometheus
docker pull grafana/grafana
```

### Links
https://habr.com/ru/articles/917226/

https://martynassubonis.substack.com/p/optimizing-docker-images-for-python

