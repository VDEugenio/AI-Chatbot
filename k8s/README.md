# Local Kubernetes Deployment

A local kind cluster running the full RAG chatbot stack. The Backend (FastAPI) and ChromaDB run as separate pods inside the cluster, connected over the cluster network. Access is via kubectl port-forward. Production runs on AWS App Runner and is independent of this environment.

## Architecture

```
Your Browser
     |
     | kubectl port-forward :8080
     |
[ backend-service ] (ClusterIP, port 80)
     |
[ Backend Pod ] (FastAPI, port 8000)
     | CHROMA_MODE=http
     | chroma-service:8000
     |
[ chroma-service ] (ClusterIP, port 8000)
     |
[ ChromaDB Pod ] (port 8000)
     |
[ chroma-pvc ] (PersistentVolumeClaim, 1Gi)
```

All resources live in the `rag-local` namespace inside a single-node kind cluster.

## Prerequisites

- [Rancher Desktop](https://rancherdesktop.io/) installed and running with **dockerd (moby)** as the container runtime
- kubectl: `winget install Kubernetes.kubectl`
- kind: `winget install Kubernetes.kind`

## Setup from scratch

### 1. Create the cluster

```powershell
kind create cluster --name rag-local --config k8s/kind-config.yaml
```

### 2. Create the namespace and set default context

```powershell
kubectl create namespace rag-local
kubectl config set-context --current --namespace=rag-local
```

### 3. Build and load the Backend image

Run from the repo root -- the Dockerfile is in `Backend/` but needs access to both `Backend/` and `Pipeline/`.

```powershell
docker build -f Backend/Dockerfile -t rag-backend:local .
kind load docker-image rag-backend:local --name rag-local
```

### 4. Create secrets

```powershell
kubectl create secret generic rag-secrets `
  --namespace=rag-local `
  --from-literal=OPENAI_API_KEY=$env:OPENAI_API_KEY `
  --from-literal=ANTHROPIC_API_KEY=$env:ANTHROPIC_API_KEY
```

Set the env vars in your PowerShell session first if they are not already set:

```powershell
$env:OPENAI_API_KEY = "your-key-here"
$env:ANTHROPIC_API_KEY = "your-key-here"
```

### 5. Deploy ChromaDB

```powershell
kubectl apply -f k8s/chroma/
```

Verify it is running:

```powershell
kubectl get pods -w
```

Wait for the chroma pod to show `1/1 Running`.

### 6. Deploy the Backend

```powershell
kubectl apply -f k8s/backend/
```

Wait for the backend pod to show `1/1 Running` (readiness probe takes ~30 seconds).

### 7. Ingest data into ChromaDB

The ChromaDB pod starts empty. You must ingest data before the chatbot can answer questions.

Open a second PowerShell window and port-forward ChromaDB:

```powershell
kubectl port-forward svc/chroma-service 8001:8000 -n rag-local
```

In your original window, set the ingest env vars and run:

```powershell
$env:CHROMA_MODE = "http"
$env:CHROMA_HOST = "localhost"
$env:CHROMA_PORT = "8001"
cd Pipeline
python ingest.py
```

Note: `Pipeline/.env` should already have these values set. The PowerShell env vars override if needed.

## Accessing the API

```powershell
kubectl port-forward svc/backend-service 8080:80 -n rag-local
```

Open `http://localhost:8080/docs` in a browser to use the Swagger UI.

Send a chat message:

```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Vaughn'\''s background?"}'
```

## Common operations

### View all resources

```powershell
kubectl get all -n rag-local
```

### View logs from all Backend pods

```powershell
kubectl logs -l app=backend --tail=50
```

### Scale the Backend

```powershell
kubectl scale deployment backend --replicas=3
```

### Roll out a config change

Edit `k8s/backend/configmap.yaml`, apply it, then restart:

```powershell
kubectl apply -f k8s/backend/configmap.yaml
kubectl rollout restart deployment/backend
```

### Roll back a deployment

```powershell
kubectl rollout undo deployment/backend
```

### Exec into a pod

```powershell
kubectl exec -it <pod-name> -- /bin/sh
```

### Re-ingest data after pipeline changes

Port-forward ChromaDB in a second window, then run `python ingest.py` from the `Pipeline/` directory.

## Tear down

```powershell
kind delete cluster --name rag-local
```

This deletes the cluster and all data including the ChromaDB PVC. To redeploy, start from step 1.

## Notes

- Access is via kubectl port-forward -- no Ingress or TLS configured
- ChromaDB data is tied to the PVC and is deleted when the cluster is deleted. Re-run ingest after recreating the cluster.
- SQLite visitor database is pod-local and not shared across replicas
- Secrets are created imperatively and are not committed to the repo
