# Cluster Management for Haraka Runtime

> **Purpose:** Guide to creating, managing, and troubleshooting Kind (local) and EKS (production) clusters.

---

## Table of Contents

1. [Local Cluster (Kind)](#local-cluster-kind)
   - [Create Cluster](#create-cluster)
   - [Delete Cluster](#delete-cluster)
   - [Verify Status](#verify-status)
2. [Production Cluster (EKS)](#production-cluster-eks)
   - [Prerequisites](#prerequisites)
   - [Create Cluster](#create-cluster-1)
   - [Manage Node Groups](#manage-node-groups)
   - [Delete Cluster](#delete-cluster-1)
3. [Context Switching & Validation](#context-switching--validation)
4. [Troubleshooting](#troubleshooting)

---

## Local Cluster (Kind)

### Create Cluster

```bash
kind create cluster   --name haraka   --config=infra/kind/kind-cluster.yaml  # annotated Kind config
```

- **Context Name:** `kind-haraka`

### Delete Cluster

```bash
kind delete cluster --name haraka
```

### Verify Status

```bash
kubectl cluster-info --context kind-haraka
kubectl get nodes --context kind-haraka
kubectl get pods --namespace haraka --context kind-haraka
```

---

## Production Cluster (EKS)

### Prerequisites

- **AWS CLI v2** (≥ 2.27.38) with profile `cli-user` or `haraka-prod`
- **kubectl** (see Local prerequisites)
- **IAM Permissions:** EKS admin, ECR access, IAM PassRole

### Create Cluster

```bash
# Create cluster with managed node group (10-15 min)
eksctl create cluster --name haraka-prod --region us-east-1 --nodegroup-name linux-nodes --node-type t2.micro --nodes 1 --managed

# Merge kubeconfig (also sets context)
aws eks update-kubeconfig --name haraka-prod --region us-east-1 --profile haraka-prod-user
```

### Manage Node Groups

#### Create Node Group

```bash
eksctl create nodegroup   --cluster haraka-prod   --region us-east-1   --profile cli-user   --name data-workers   --nodes 3   --node-type m5.xlarge   --managed
```

#### List Node Groups

```bash
eksctl get nodegroup   --cluster haraka-prod   --region us-east-1   --profile cli-user
```

#### Delete Node Group

```bash
eksctl delete nodegroup   --cluster haraka-prod   --name data-workers   --region us-east-1   --profile cli-user
```

### Delete Cluster

```bash
eksctl delete cluster   --name haraka-prod   --region us-east-1   --profile cli-user
```

---

## Context Switching & Validation

> Quickly toggle between Kind and EKS contexts and verify health.

### Local (Kind)

```bash
# Ensure Kind context
kubectl config use-context kind-haraka
kubectl cluster-info
kubectl get services,pods --namespace haraka
```

### Production (EKS)

```bash
# Ensure EKS context
aws eks update-kubeconfig --name haraka-prod --region us-east-1
kubectl config use-context arn:aws:eks:<region>:<account-id>:cluster/haraka-prod
kubectl	cluster-info
kubectl get services,pods --namespace haraka
```

```bash
kubectl wait   --for=condition=available deployment   --all   --namespace haraka   --timeout=120s
```

---

## Troubleshooting

### Common Issues

- Confirm Docker daemon is running
- Verify `kind --version` (≥ 0.29.0)
- Recreate cluster: `kind create cluster --name haraka`

* Check AWS identity: `aws sts get-caller-identity --profile cli-user`
* Validate IAM policies attached to profile

- Ensure IAM rights to launch EC2 instances
- Inspect CloudFormation stacks in AWS Console

> **Tip:** Use `kubectl logs` and `kubectl describe` for deeper pod and resource debugging.
