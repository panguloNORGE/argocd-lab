#!/usr/bin/env python3
"""Set up a local kind cluster with ArgoCD and open the web UI."""

import base64
import subprocess

ARGOCD_MANIFEST = "https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml"


def run(cmd, capture=False):
    """Run a shell command, print it, and stop the script if it fails."""
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd, check=True, text=True, capture_output=capture)
    return result.stdout if capture else None


def cluster_exists():
    clusters = run(["kind", "get", "clusters"], capture=True)
    return "kind" in clusters.split()


def main():
    # 1. Create the cluster (skip if it already exists)
    if cluster_exists():
        print("Cluster 'kind' already exists, skipping creation.")
    else:
        run(["kind", "create", "cluster"])

    # 2. Install ArgoCD
    run(["kubectl", "create", "namespace", "argocd", "--dry-run=client", "-o", "yaml"], capture=True)
    subprocess.run("kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -",
                   shell=True, check=True)
    # run(["kubectl", "apply", "-n", "argocd", "-f", ARGOCD_MANIFEST])
    run(["kubectl", "apply", "-n", "argocd", "--server-side", "--force-conflicts", "-f", ARGOCD_MANIFEST])
    run(["kubectl", "-n", "argocd", "rollout", "status", "deployment", "argocd-server", "--timeout=300s"])

    # 3. Run the web UI over plain HTTP so Codespaces can forward it
    run(["kubectl", "-n", "argocd", "patch", "configmap", "argocd-cmd-params-cm",
         "--type", "merge", "-p", '{"data":{"server.insecure":"true"}}'])
    run(["kubectl", "-n", "argocd", "rollout", "restart", "deployment", "argocd-server"])
    run(["kubectl", "-n", "argocd", "rollout", "status", "deployment", "argocd-server", "--timeout=300s"])

    # 4. Print the admin password
    encoded = run(["kubectl", "-n", "argocd", "get", "secret", "argocd-initial-admin-secret",
                   "-o", "jsonpath={.data.password}"], capture=True)
    password = base64.b64decode(encoded).decode()
    print(f"\nArgoCD login -> user: admin   password: {password}")
    print("Open the Ports tab and click the globe icon next to port 8080.\n")

    # 5. Forward the UI (runs until you press Ctrl+C)
    run(["kubectl", "port-forward", "svc/argocd-server", "-n", "argocd", "8080:80"])


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"\nCommand failed with exit code {e.returncode}. See the error above.")
    except KeyboardInterrupt:
        print("\nStopped port-forward. Run 'kind delete cluster' when you're done.")