# Haraka Runtime

> **Overview:** This repository contains everything you need to develop and deploy the Haraka Runtime microservices using Kind (local) and EKS (production).

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Configuration Files](#configuration-files)
3. [Run Modes](#run-modes)
4. [Commands & Validation](#commands--validation)
5. [IAM Roles & Policies](#iam-roles--policies)
6. [EKS Cluster Creation (Optional)](#eks-cluster-creation-optional)
7. [Context Switching](#context-switching)

---

## Prerequisites

### Local (Kind)

> **Note:** Install the following tools to run Haraka locally on a Kind cluster.

- **Docker** (≥ 27.10) – [Install Guide](https://docs.docker.com/engine/install/)
- **Kind** (≥ 0.29.0) – [Quick Start](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
- **kubectl** (≥ 1.33.2)
  - [Linux](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/)
  - [macOS](https://kubernetes.io/docs/tasks/tools/install-kubectl-macos/)
  - [Windows](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/)
- **Skaffold** (≥ 2.16.1) – [Install](https://skaffold.dev/docs/install/)
- **Tilt** (≥ 0.35.0) – [Install](https://docs.tilt.dev/install.html)

### Production (EKS)

> **Note:** These tools are required for deploying to AWS EKS.

- **AWS CLI** (≥ 2.27.38) – [Install Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **Helm** (≥ 3.18.3) – [Install Guide](https://helm.sh/docs/intro/install/)
- **kubectl** (≥ 1.33.2) – *See Local section above*

---

## Configuration Files

> **Reference:** Customize these samples before deploying.

| File                                        | Description                                      |
|---------------------------------------------|--------------------------------------------------|
| `infra/kind/kind-cluster.yaml`              | Kind cluster definition (annotated)              |
| `infra/skaffold/profiles/skaffold.dev.yaml` | Skaffold "dev" override profile                  |
| `infra/skaffold/profiles/skaffold.prod.yaml` | Skaffold "prod" override profile                 |
| `infra/helm/values.yaml`         | Helm values file                          |
| `.env.example`                              | All required environment variables               |

---

## Run Modes

> **Purpose:** Choose a mode based on your development or deployment stage.

| Mode                       | What Runs Where                                      | Purpose                                                          |
|----------------------------|------------------------------------------------------|------------------------------------------------------------------|
| **Local Headless** (Dev)   | • All adapters in Kind<br>• Core app on host         | Fast feedback loop against real infra                            |
| **Local Headed** (Dev)     | • All adapters & core app in Kind                    | True dev-cluster test with live updates                          |
| **Deployed Headed** (Test) | • All services in Kind (no live-update)              | Validate manifests & image builds in a dev cluster               |
| **Prod** (EKS)             | • All services in EKS via Helm/Skaffold              | Production deployment with immutable images & automated rollouts |

### Local Headless
```bash
make init-kind         # Create Kind cluster with annotated config
make tilt-headless     # Tilt infra + port-forwards
uvicorn src.app.main:app --reload --port 8000
```
<details>
<summary>Environment Variables</summary>

- `TILT_HEADLESS=true`
- Adapter-specific mappings (e.g. `ADAPTER_A_HOST`, `ADAPTER_B_PORT`)
</details>

### Local Headed
```bash
make tilt-headed       # Tilt infra + in-cluster live_update
uvicorn src.app.main:app --reload --port 8000  # via PyCharm or CLI
```
<details>
<summary>Environment Variables</summary>

- `TILT_HEADLESS=false`
- Adapter-specific config (e.g. `ADAPTER_A_CONFIG_PATH`)
</details>

### Deployed Headed (Test)
```bash
# Tilt (no live-update)
TILT_HEADLESS=false tilt up -f Tiltfile
# or Skaffold
skaffold apply -p test
```
<details>
<summary>Environment Variables</summary>

- `SKAFFOLD_PROFILE=test`
- Adapter credentials/endpoints
</details>

### Prod (EKS)
```bash
skaffold build -p prod
skaffold deploy -p prod
skaffold delete -p prod  # Tear down
```
<details>
<summary>Environment Variables</summary>

- `SKAFFOLD_PROFILE=prod`
- Kubernetes secrets & adapter configs via Helm
</details>

---

## Commands & Validation

> **Usage Notes:** What each Make target and profile actually does.
### Quickstart Make Targets

| Target          | What it does                                                                                                           |
|-----------------|------------------------------------------------------------------------------------------------------------------------|
| `make dev-setup`  | Installs/verifies dependencies (Helm, Kind, kubectl, Skaffold), creates/updates the Kind cluster, deploys Helm chart to Kind, and waits for all pods to be READY before exiting. |
| `make prod-deploy`| Builds & pushes the Docker image (prod), deploys via Skaffold/Helm to EKS, and waits for the new pods to roll out successfully before exiting. |

```bash
# Bootstrap local dev (Kind)
make dev-setup

# Deploy to production (EKS)
make prod-deploy


### `make tilt-headless`
1. Exports `TILT_HEADLESS=true`
2. Runs `tilt up --port=10350 -f Tiltfile` in background
3. Port-forwards all adapters to host
4. Core app binds to configured host ports

### `make tilt-headed`
1. Exports `TILT_HEADLESS=false`
2. Runs `tilt up -f Tiltfile` with live-update in-cluster
3. Forwards core app service port to localhost

### Skaffold Profiles
- **dev:** live_update on code changes
- **test:** manifests only; fresh image builds
- **prod:** version-tagged builds pushed and deployed via Helm

---

## IAM Roles & Policies

### EKS Cluster Role
```bash
aws iam create-role   --role-name EKSClusterRole   --assume-role-policy-document file://eks-cluster-trust.json
aws iam attach-role-policy   --role-name EKSClusterRole   --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
```

### EKS Nodegroup Role
```bash
aws iam create-role   --role-name EKSNodegroupRole   --assume-role-policy-document file://eks-node-trust.json
aws iam attach-role-policy   --role-name EKSNodegroupRole   --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
aws iam attach-role-policy   --role-name EKSNodegroupRole   --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
```

<details>
<summary>Custom Adapter-Controller Policy (Optional)</summary>

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "elasticloadbalancing:*",
        "ec2:DescribeVpcs",
        "route53:GetHostedZone"
      ],
      "Resource": "*"
    }
  ]
}
```
```bash
aws iam put-role-policy   --role-name EKSClusterRole   --policy-name AdapterControllerPolicy   --policy-document file://adapter-policy.json
```
</details>

---

## EKS Cluster Creation (Optional)
```bash
eksctl create cluster   --name my-cluster   --region us-east-1   --nodegroup-name linux-nodes   --node-type t3.medium   --nodes 3
```

> **Tip:** For multi-account/region setups, use separate AWS profiles or assume-role configurations.

---

## Context Switching

### Local (Kind)
```bash
kubectl config use-context kind-haraka
kubectl cluster-info
kubectl get services,pods --namespace haraka
```

### Production (EKS)
```bash
aws eks update-kubeconfig --name haraka-prod --region us-east-1
kubectl config use-context arn:aws:eks:<region>:<account-id>:cluster/haraka-prod
kubectl cluster-info
kubectl get services,pods --namespace haraka
```
<details>
<summary>Wait for Deployments Ready</summary>

```bash
kubectl wait   --for=condition=available deployment   --all   --namespace haraka   --timeout=120s
```
</details>

---

## Troubleshooting

### Common Issues

- Confirm Docker daemon is running
- Verify `kind --version` (≥ 0.29.0)
- Recreate cluster: `kind create cluster --name haraka`

- Check AWS identity: `aws sts get-caller-identity --profile cli-user`
- Validate IAM policies attached to profile

- Ensure IAM rights to launch EC2 instances
- Inspect CloudFormation stacks in AWS Console

> **Tip:** Use `kubectl logs` and `kubectl describe` for deeper pod and resource debugging.
