# A simple PostgreSQL DB read WebApp

## Build the app

Clone the repository using `git clone` and change into the root of the cloned directory.

- Specify an image name:

```code
export IMAGE="quay.io/rguske/psql-read-webapp:v1.0"
```

- Create the container image:

```code
podman build -t ${IMAGE} -f Containerfile
```

## Test the funtion

Assumptions:

- a running PostgreSQL DB instance with a DB named `vmdb` and an appropriate table configuration

Example:

```code
psql -U postgres -h 192.168.42.128 -p 5432 -d vmdb -c 'SELECT * FROM "virtual_machines"'
Password for user postgres:
 type | id | kind | name | namespace | time | cpucores | cpusockets | memory | storageclass | network
------+----+------+------+-----------+------+----------+------------+--------+--------------+---------
(0 rows)
```

- Run the function locally:

```code
podman run -e PORT=8000 -it \
--rm -p 8000:8000 \
--env DB_HOST='192.168.42.128' \
--env DB_PORT='5432' \
--env DB_NAME='vmdb' \
--env DB_USER='postgres' \
--env DB_PASSWORD='redhat' \
${IMAGE}
```

Browse http://127.0.0.1:8000/

- Alternative way to validate locally:

```code
# env (use values that can reach your DB)
export DB_HOST=192.168.42.128
export DB_USER=postgres
export DB_PASSWORD='redhat'
export DB_NAME=vmdb

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Deploy the app on Kubernetes

- specify the app namespace

```code
export NAMESPACE=postgresql-1
```

- Create the Security Context Constraint (OpenShift only)

```code
oc adm policy add-scc-to-user anyuid -z default -n $NAMESPACE
```

- Create a `secret`:

```code
kubectl -n $NAMESPACE create secret generic pg-credentials \
  --from-literal=DB_HOST=192.168.42.128 \
  --from-literal=DB_USER=postgres \
  --from-literal=DB_PASSWORD='redhat'
```

- Deploy the app:

```yaml
kubectl -n $NAMESPACE create -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vmdb-web
  labels:
    app: vmdb-web
spec:
  replicas: 2
  selector:
    matchLabels:
      app: vmdb-web
  template:
    metadata:
      labels:
        app: vmdb-web
    spec:
      containers:
      - name: web
        image: quay.io/rguske/psql-read-webapp:v1.0 # your image reference
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: pg-credentials
        env:
        - name: DB_NAME
          value: "vmdb"
        - name: DB_PORT
          value: "5432"
        - name: DB_POOL_SIZE
          value: "10"
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 20
        resources:
          requests:
            cpu: "50m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
EOF
```

- Create the Kubernetes `service`:

```yaml
kubectl -n $NAMESPACE create -f - <<EOF
apiVersion: v1
kind: Service
metadata:
  name: vmdb-web
  labels:
    app: vmdb-web
spec:
  selector:
    app: vmdb-web
  ports:
  - name: http
    port: 80
    targetPort: 8000
  type: ClusterIP
EOF
```

## Run the App with Knative Serving

```code
oc adm policy add-scc-to-user anyuid -z default -n $NAMESPACE
```

```code
kn service create postgresql-read-webapp \
  --image=quay.io/rguske/psql-read-webapp:v1.0 \
  --env-from secret:pg-credentials \
  --env DB_NAME=vmdb \
  --env DB_PORT=5432 \
  --scale-min=1 \
  --scale-max=5
```
