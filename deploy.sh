#!/usr/bin/env bash
set -euo pipefail

# Wordle app deployment script
# Usage: ./deploy.sh [build|deploy|all|status|logs]
#   build   - Build and push Docker image
#   deploy  - Apply k8s manifests and update deployment
#   all     - Build + deploy (default)
#   status  - Show deployment status
#   logs    - Tail application logs

REGISTRY="ghcr.io"
IMAGE_NAME="jmelloy/wordle"
FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}"
DEPLOYMENT="wordle"
K8S_DIR="$(cd "$(dirname "$0")" && pwd)/k8s"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[deploy]${NC} $*"; }
warn() { echo -e "${YELLOW}[deploy]${NC} $*"; }
err()  { echo -e "${RED}[deploy]${NC} $*" >&2; }

check_prerequisites() {
    local missing=()
    command -v docker >/dev/null 2>&1 || missing+=("docker")
    command -v kubectl >/dev/null 2>&1 || missing+=("kubectl")

    if [[ ${#missing[@]} -gt 0 ]]; then
        err "Missing required tools: ${missing[*]}"
        exit 1
    fi
}

build() {
    local tag="${1:-$(git rev-parse --short HEAD)}"
    log "Building image ${FULL_IMAGE}:${tag}"

    docker build -t "${FULL_IMAGE}:${tag}" -t "${FULL_IMAGE}:latest" .

    log "Pushing ${FULL_IMAGE}:${tag}"
    docker push "${FULL_IMAGE}:${tag}"
    docker push "${FULL_IMAGE}:latest"

    log "Build complete: ${FULL_IMAGE}:${tag}"
    echo "${tag}"
}

deploy() {
    local tag="${1:-$(git rev-parse --short HEAD)}"
    log "Deploying ${FULL_IMAGE}:${tag}"

    # Apply manifests
    kubectl apply -f "${K8S_DIR}/"

    # Update image to specific tag
    kubectl set image "deployment/${DEPLOYMENT}" "${DEPLOYMENT}=${FULL_IMAGE}:${tag}"

    # Wait for rollout
    log "Waiting for rollout to complete..."
    if kubectl rollout status "deployment/${DEPLOYMENT}" --timeout=120s; then
        log "Deployment successful"
    else
        err "Rollout failed or timed out"
        warn "Rolling back..."
        kubectl rollout undo "deployment/${DEPLOYMENT}"
        kubectl rollout status "deployment/${DEPLOYMENT}" --timeout=60s
        exit 1
    fi
}

status() {
    echo "=== Deployment ==="
    kubectl get deployment "${DEPLOYMENT}" -o wide
    echo ""
    echo "=== Pods ==="
    kubectl get pods -l "app=${DEPLOYMENT}" -o wide
    echo ""
    echo "=== Service ==="
    kubectl get service "${DEPLOYMENT}"
    echo ""
    echo "=== Ingress ==="
    kubectl get ingress "${DEPLOYMENT}"
}

logs() {
    kubectl logs -l "app=${DEPLOYMENT}" --tail=100 -f
}

# Main
ACTION="${1:-all}"
TAG="${2:-$(git rev-parse --short HEAD 2>/dev/null || echo "latest")}"

check_prerequisites

case "${ACTION}" in
    build)
        build "${TAG}"
        ;;
    deploy)
        deploy "${TAG}"
        ;;
    all)
        build "${TAG}"
        deploy "${TAG}"
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    *)
        err "Unknown action: ${ACTION}"
        echo "Usage: $0 [build|deploy|all|status|logs] [tag]"
        exit 1
        ;;
esac
