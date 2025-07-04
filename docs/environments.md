## Environments

### Run Modes

| Mode               | What Runs Where                                                                          | Commands / Config                                                                                                          | Purpose                                                      |
|--------------------|------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------|
| **Local Headless** (Dev) | • External services (i.e. Redis, Kafka, etc) in Kind<br>• FastAPI & orchestrator on host | ```bash<br>make init-kind<br>make tilt-headless  # Tilt infra + port-forwards<br>uvicorn src.app.main:app --reload --port 8000``` | Fast feedback loop against real infra                        |
| **Local Headed** (Dev)   | • External services (i.e. Redis, Kafka, etc) and FastAPI all in Kind                     | ```bash<br>make tilt-headed  # Tilt infra + in-cluster app with live_update```                                             | True “dev-cluster” test with live-update in pods             |
| **Deployed Headed** (Test) | • All services in Kind (no live-update)                                                  | ```bash<br>tilt up -f Tiltfile             # with TILT_HEADLESS=false<br>skaffold apply -p test```                             | Validate full manifests & image builds in a dev cluster      |
| **Prod** (EKS)          | • All services in EKS via Helm/Skaffold                                                  | ```bash<br>skaffold build -p prod<br>skaffold deploy -p prod<br>skaffold delete -p prod```                                   | Production deployment with immutable images & automated rollouts |

### Configuration Details

- **make tilt-headless**
  1. Sets `TILT_HEADLESS=true`
  2. Runs `tilt up --port=10350 -f Tiltfile` in the background  
  3. Backgrounds:
     - `kubectl port-forward service/redis 6379:6379`
     - `kubectl port-forward service/kafka 9092:9092`
  4. Your FastAPI (and Haraka Runtime) binds to `localhost:6379` & `localhost:9092`

- **make tilt-headed**
  1. Sets `TILT_HEADLESS=false`
  2. Runs `tilt up -f Tiltfile`
     - Applies `k8s/app.yaml`
     - Builds `she2pookie:dev`
     - Live-updates code into the pod
  3. Forwards port `8000` from the in-cluster Service back to `localhost`

- **Skaffold Profiles**
  - **dev**: same as `tilt-headed`, but using Skaffold’s `live_update` instead of Tilt
  - **test**: applies manifests without live updates; ensures fresh images
  - **prod**: builds with `--tag=vX.Y.Z`, pushes to registry, then deploys via Helm or `skaffold deploy`

### Acceptance Criteria

**Given** I have cloned the repo  
**When** I open `README.md`  
**Then** I see an **Environments** section that:

1. Describes the **dev** workflow (e.g. Kind cluster + Skaffold/Tilt commands)  
2. Describes the **prod** workflow (e.g. Helm chart + EKS deployment commands)  
3. Clearly contrasts differences in:
   - config files
   - environment variables
   - namespaces  
