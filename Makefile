# ───────────────────────────────────────────────────────────────────────────────
# Quickstart Make Targets
# ───────────────────────────────────────────────────────────────────────────────

.PHONY: dev-setup prod-deploy

dev-setup:
	@echo "🔧 Installing/verifying dependencies..."
	@helm version --short >/dev/null 2>&1 || (echo "Error: Helm not found" && exit 1)
	@kind version >/dev/null 2>&1 || (echo "Error: Kind not found" && exit 1)
	@kubectl version --client >/dev/null 2>&1 || (echo "Error: kubectl not found" && exit 1)
	@skaffold version >/dev/null 2>&1 || (echo "Error: Skaffold not found" && exit 1)

	@echo "🚀 Creating/updating Kind cluster..."
	@kind create cluster --name haraka --config=config/kind-cluster.yaml || true

	@echo "☁️ Deploying Helm chart to Kind..."
	@helm upgrade --install haraka ./chart --namespace haraka --create-namespace

	@echo "⌛ Waiting for all pods to be READY in 'haraka' namespace..."
	@kubectl wait --for=condition=ready pod --all --namespace haraka --timeout=120s

	@echo "✅ Dev environment is bootstrapped!"

prod-deploy:
	@echo "📦 Building & pushing Docker image (prod profile)..."
	@skaffold build -p prod

	@echo "☁️ Deploying to EKS via Helm/Skaffold..."
	@skaffold deploy -p prod

	@echo "⌛ Waiting for prod rollout to complete..."
	@kubectl wait --for=condition=ready pod --all --namespace haraka --timeout=120s

	@echo "✅ Production deployment successful!"
