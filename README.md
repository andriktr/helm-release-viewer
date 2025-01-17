<img src="/images/hrv.png" width="100"/> 

# Helm-Release-Viewer

## Table of Contents

- [Helm-Release-Viewer](#helm-release-viewer)
  - [Table of Contents](#table-of-contents)
  - [Description](#description)
  - [What will be deployed](#what-will-be-deployed)
  - [Helm-Release-Viewer application](#helm-release-viewer-application)
    - [Known issues and possible improvements in Helm-Release-Viewer application](#known-issues-and-possible-improvements-in-helm-release-viewer-application)
  - [Run application locally](#run-application-locally)
  - [Helm-Release-Viewer helm chart](#helm-release-viewer-helm-chart)
    - [Known issues and possible improvements in Helm-Release-Viewer helm chart](#known-issues-and-possible-improvements-in-helm-release-viewer-helm-chart)
    - [Configure Helm-Release-Viewer chart](#configure-helm-release-viewer-chart)
    - [Test Helm-Release-Viewer chart](#test-helm-release-viewer-chart)
    - [Deploy and Upgrade Helm-Release-Viewer chart](#deploy-and-upgrade-helm-release-viewer-chart)
      - [Build and Push Docker Image](#build-and-push-docker-image)
      - [Deployment](#deployment)
  - [Use and Access Helm-Release-Viewer application](#use-and-access-helm-release-viewer-application)
  - [Remove Solution](#remove-solution)

## Description

Current repository contains a helm-release-viewer application and a helm chart to deploy it in a kubernetes cluster.

## What will be deployed

The [helm-release-viewer application](app/) will be deployed in a kubernetes cluster using the [helm-release-viewer](charts/helm-release-viewer/) helm chart. The application will be deployed in a namespace called `helm-release-viewer` and it will be exposed using an ingress. For complete details on the helm chart, please refer to the [helm-release-viewer templates](charts/helm-release-viewer/templates).

## Helm-Release-Viewer application

Helm-release-viewer is a web application that allows you to view the Helm releases in a Kubernetes cluster. Additionally, it allows you to view the details of the releases such as revision history, values, status of releases and release manifests. You also can filter releases by namespace, release name or release status as well as sort by namespace, release name, release status, chart, app version. The application is built using python and gunicorn and it uses the Helm CLI to interact with the Kubernetes cluster. Usage of the Helm CLI is necessary as there are no good libraries for helm client in python. For better performance, the application uses a cache to store the helm releases. Also it uses multiprocessing to run the helm commands in parallel.

The following parameters can be passed to the application via environment variables:

Name | Description | Default
--- | --- | ---
SELECTORS | A comma separated list of labels (key=value) to select releases only from specific namespaces | None
ENVIRONMENT | The environment in which the application is running. Environment will be displayed on home page | ""
CACHE_TTL | The time in seconds to keep the helm releases in cache | 300
CACHE_SIZE | The maximum number of entries to keep in cache | 50000
APP_PORT | The port on which the application will run | 8080
APP_WARMUP_INTERVAL | The time in seconds to automatically hit the home page to warm up the cache | 300
LOG_LEVEL | The log level for the application | info
IN_CLUSTER | If set to true, the application will use the in-cluster configuration to interact with the Kubernetes cluster | true

Application code, Dockerfile, html templates and other files are located in the [app](/app) directory.

### Known issues and possible improvements in Helm-Release-Viewer application

Issue/Improvement | Status
--- | ---
Even if we process the helm commands in parallel to query the releases it takes some time to gather all the information so in large environments it can take some seconds to load the home page. 130 namespaces with 1-2 releases in each takes around 10-15 seconds to load the home page. As workaround there is a warmup function that hits the home page every X seconds (configurable via APP_WARMUP_INTERVAL) and as data stays in cache it should load quickly for a user next time he will hit the home page. If most recent info is needed then on the same home page user can initiate cache clearance | :x:
Add a favicon to the application | :white_check_mark:
Add an authentication mechanism to the application | :x:
Add an optional feature to manage releases like rollback or uninstall | :x:

# Run application locally

To run the application locally you need to perform the following steps:

1. Clone the repository

```bash
git clone https://github.com/andriktr/helm-release-viewer.git
```

2. Change to the `app` directory

```bash
cd helm-release-viewer/app
```

3. Install the required dependencies by running `pip install -r requirements.txt`

```bash
pip install -r requirements.txt
```

4. Set the `IN_CLUSTER` environment variable to `false`

```bash
export IN_CLUSTER=false
```

5. Run the application

```bash
python helm_release_viewer.py
```

6. Access the application by opening [http://localhost:8080](http://localhost:8080) in your web browser


## Helm-Release-Viewer helm chart

The helm chart to deploy the helm-release-viewer application is located in the [helm-release-viewer](/charts/helm-release-viewer) directory. It will deploy all necessary dependencies required to run and function the application.

### Known issues and possible improvements in Helm-Release-Viewer helm chart

Issue/Improvement | Status
--- | ---
Configure sticky sessions for the ingress | :white_check_mark:
Add a Readiness probe to the application | :white_check_mark:
Add a Liveness probe to the application | :white_check_mark:
Add pod disruption budget to the deployment | :white_check_mark:
Add optional horizontal pod autocaler to the deployment | :x:
Add GitHub actions to build and push the Docker image | :white_check_mark:
Add GitHub actions to package and deploy the helm chart to a repository | :white_check_mark:

### Configure Helm-Release-Viewer chart

Helm chart is configurable by using [values.yaml](charts/helm-release-viewer/values.yaml)

Parameters that can be configured are:

Name | Description | Default
--- | --- | ---
labels | Labels to be added to the resources | {}
nameOverride | Override the name of the chart | ""
app.logLevel | Log level for the application | info
app.timeout | Timeout tolerated by gunicorn | 120
deployment.name | Name of the deployment | helm-release-viewer
deployment.replicas | Number of replicas | 2
deployment.selectorLabels | Selector labels for the deployment | {}
deployment.annotations | Annotations for the deployment | {}
deployment.podAnnotations | Annotations for the pods | {}
deployment.podSecurityContext | Security context for the pods | {}
deployment.securityContext | Security context for the containers | {}
deployment.port.name | Name of the port | http
deployment.port.containerPort | Port on which the application will run | 8080
deployment.port.protocol | Protocol for the port | TCP
deployment.resources | Resources requests and limits | {}
deployment.additionalEnvs | Additional environment variables | []
deployment.envFrom | Environment variables from secrets or configmaps | []
deployment.image.repository | Repository for the image in format `registry/repository` | ""
deployment.image.tag | Tag for the image | Defaults is the chart appVersion
deployment.image.pullPolicy | Pull policy for the image | Always
deployment.volumes | Volumes to be mounted | []
deployment.volumeMounts | Volume mounts for the containers | []
deployment.nodeSelector | Node selector for the deployment | {}
deployment.tolerations | Tolerations for the deployment | []
deployment.affinity | Affinity for the deployment | {}
deployment.topologySpreadConstraints | Topology spread constraints for the deployment | []
deployment.livenessProbe | Liveness probe for the containers | {}
deployment.readinessProbe | Readiness probe for the containers | {}
rbac.create | If true, create the necessary RBAC resources | true
rbac.readOnly | If true, create the necessary RBAC resources with read-only permissions | true
rbac.customClusterRole.enabled | If true create a custom defined cluster role instead of the default read or write for all api-resources | false
rbac.customClusterRole.rules | Rules for the custom cluster role | []
serviceAccount.create | If true, create a service account | true
serviceAccount.name | Name of the service account | helm-release-viewer
serviceAccount.annotations | Annotations for the service account | {}
service.enabled | If true, create a service | true
service.name | Name of the service | helm-release-viewer
service.type | Type of the service | ClusterIP
service.port | Port for the service | 80
service.targetPort | Target port for the service | 8080
ingress.enabled | If true, create an ingress | true
ingress.annotations | Annotations for the ingress | {}
ingress.hosts | Hosts for the ingress | []
ingress.tls | TLS configuration for the ingress | []
podDisruptionBudget.enabled | If true, create a pod disruption budget | true
podDisruptionBudget.spec | Pod disruption budget spec should contain either minAvailable or maxUnavailable | {}
azureWorkloadIdentity.enabled | If true, create an Azure Workload Identity | false
azureWorkloadIdentity.clientId | Client ID for the Azure Workload Identity | ""

### Test Helm-Release-Viewer chart

In order to test the helm chart, you can use the following command (make sure to define the correct path to the `values.yaml` file):

If you have a local copy of the Helm-Release-Viewer repository, you can use the following commands to test the helm chart:

```bash
# List chart templates
helm template helm-release-viewer helm-release-viewer --namespace helm-release-viewer --values values.yaml --debug
# Perform a dry-run install/upgrade
helm upgrade --install helm-release-viewer helm-release-viewer --namespace helm-release-viewer --values values.yaml --dry-run --debug
```

Otherwise, you can use the following commands to test the helm chart:

```bash
# Add the Helm repository
helm repo add helm-release-viewer https://sysadminas.eu/helm-release-viewer/
# Update Helm repositories
helm repo update
# List chart templates
helm template helm-release-viewer helm-release-viewer/helm-release-viewer --namespace helm-release-viewer --values values.yaml --debug
# Perform a dry-run install/upgrade
helm upgrade --install helm-release-viewer helm-release-viewer/helm-release-viewer --namespace helm-release-viewer --values values.yaml --dry-run --debug
```

### Deploy and Upgrade Helm-Release-Viewer chart

#### Build and Push Docker Image

You can pull Helm-Release-Viewer image from Docker Hub by using the following command:

```bash
# For the latest version use the following command
docker pull andriktr/helm-release-viewer:latest

# For a specific version use the following command
docker pull andriktr/helm-release-viewer:v<version>
```

In order to build and push the Docker image manually, you can use the following commands:

```bash
export DOCKER_REGISTRY=<your-registry>
export VERSION=<version>

# Build the Docker image make sure you have switched to the app directory where the Dockerfile is located
docker build -t $DOCKER_REGISTRY/helm-release-viewer:$VERSION --no-cache --pull --platform linux/amd64 .
# Push the Docker image
docker push $DOCKER_REGISTRY/helm-release-viewer:$VERSION
```

#### Deployment

To deploy the Helm-Release-Viewer application from the Helm chart stored locally, you can use the following command:

```bash
helm upgrade -i helm-release-viewer helm-release-viewer -f values.yaml -n helm-release-viewer
```

To deploy the Helm-Release-Viewer application from the Helm chart stored in the Helm repository, you can use the following command:

```bash
# Add the Helm repository
helm repo add helm-release-viewer https://sysadminas.eu/helm-release-viewer/
# Update Helm repositories
helm repo update
# Perform a dry-run install/upgrade
helm upgrade --install helm-release-viewer helm-release-viewer/helm-release-viewer --namespace helm-release-viewer --values values.yaml  --debug --create-namespace
```

## Use and Access Helm-Release-Viewer application

Depending on the configuration of the helm chart, the application can be accessed via an ingress, direct service or a port-forward.

> Note: Usage of ingress is optional however it is highly recommended if you are planning to use Helm Release Viewer in a production environment and you will need more than one replica of the Helm Release Viewer pod. Ingress allows most easiest way to configure sticky sessions which in current version of Helm Release Viewer is required to make sure that filtering and sorting works correctly in multi-replica environment.

## Remove Solution

To remove the helm-release-viewer application from the Kubernetes cluster, you can use the following command:

```bash
helm uninstall helm-release-viewer -n helm-release-viewer
```