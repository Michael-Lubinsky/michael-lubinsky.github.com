https://medium.com/tag/kubernetes

https://levelup.gitconnected.com/i-asked-this-kubernetes-question-in-every-interview-and-heres-the-catch-6d37cc7cb7a5

https://medium.com/@haroldfinch01/top-15-secret-kubernetes-tricks-you-didnt-know-d4cf38334f06

### Helm 
is a package manager for Kubernetes. It uses “charts” to define, install and upgrade applications.

https://blog.devgenius.io/deploying-apache-airflow-on-kubernetes-a-step-by-step-guide-for-beginners-532c15ccc914

brew install helm

## Kubernetes on   MacBook  

### Option 1: Minikube (Recommended for Beginners)

<https://minikube.sigs.k8s.io/docs/start>

Minikube runs a single-node Kubernetes cluster locally, ideal for learning.
``` 
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
- Install Minikube:
``` 
brew install minikube
```
- Install a Driver (e.g., Docker ):
 ```
brew install docker
docker --version
``` 
- Start Minikube:
``` 
minikube start --driver=docker

😄  minikube v1.35.0 on Darwin 13.3.1 (arm64)
✨  Automatically selected the docker driver
📌  Using Docker Desktop driver with root privileges
👍  Starting "minikube" primary control-plane node in "minikube" cluster
🚜  Pulling base image v0.0.46 ...
💾  Downloading Kubernetes v1.32.0 preload ...
    > gcr.io/k8s-minikube/kicbase...:  452.84 MiB / 452.84 MiB  100.00% 7.01 Mi
    > preloaded-images-k8s-v18-v1...:  314.92 MiB / 314.92 MiB  100.00% 4.05 Mi
🔥  Creating docker container (CPUs=2, Memory=4000MB) ...
🐳  Preparing Kubernetes v1.32.0 on Docker 27.4.1 ...
    ▪ Generating certificates and keys ...
    ▪ Booting up control plane ...
    ▪ Configuring RBAC rules ...
🔗  Configuring bridge CNI (Container Networking Interface) ...
🔎  Verifying Kubernetes components...
    ▪ Using image gcr.io/k8s-minikube/storage-provisioner:v5
🌟  Enabled addons: default-storageclass, storage-provisioner
🏄  Done! kubectl is now configured to use "minikube" cluster and "default" namespace by default
``` 
- Verify Installation:
``` 
minikube status
------------------
minikube
type: Control Plane
host: Running
kubelet: Running
apiserver: Running
kubeconfig: Configured

kubectl get nodes
------------------
NAME       STATUS   ROLES           AGE     VERSION
minikube   Ready    control-plane   2m29s   v1.32.0
```
- Install kubectl (if not installed with Minikube):
``` 
brew install kubectl
minikube status
minikube version
kubectl version --client
```

* Ensure Docker Desktop is running before starting Minikube or Kind.  
* Use kubectl to practice commands, e.g.  
   ```kubectl apply```, ```kubectl get```, ```kubectl describe```

```
kubectl get po -A
kubectl get pods --all-namespaces

NAMESPACE     NAME                               READY   STATUS    RESTARTS      AGE
kube-system   coredns-668d6bf9bc-cfpfl           1/1     Running   0             11m
kube-system   etcd-minikube                      1/1     Running   0             11m
kube-system   kube-apiserver-minikube            1/1     Running   0             11m
kube-system   kube-controller-manager-minikube   1/1     Running   0             11m
kube-system   kube-proxy-gpv2x                   1/1     Running   0             11m
kube-system   kube-scheduler-minikube            1/1     Running   0             11m
kube-system   storage-provisioner                1/1     Running   1 (10m ago)   11m
```  

* For Minikube errors, try ```minikube delete``` and ```minikube start``` again.
```
minikube addons enable metrics-server
minikube dashboard
http://127.0.0.1:57617/api/v1/namespaces/kubernetes-dashboard/services/http:kubernetes-dashboard:/proxy/#/workloads?namespace=default
```

### Option 2: Kind (Kubernetes in Docker)
Kind runs Kubernetes clusters in Docker containers, great for testing multi-node setups.

- Install Kind:

brew install kind

- Create a Cluster:

kind create cluster

- Verify:

kubectl cluster-info

- Install kubectl (if needed):
 
brew install kubectl

### Option 3: K3s (Lightweight Kubernetes)
K3s is a lightweight Kubernetes distribution, good for resource-constrained environments.

- Install K3s:
 
curl -sfL https://get.k3s.io | sh -

- Set Up kubectl:

export KUBECONFIG=~/.kube/config:/etc/rancher/k3s/k3s.yaml

- Verify:
 
kubectl get nodes


### Notes:
```
Minikube is the easiest for beginners, with good documentation and community support.
Kind suits those comfortable with Docker and wanting multi-node setups.
K3s is lightweight but slightly more complex to configure.
Ensure you have at least 4GB of free RAM and 20GB of disk space.
```

### To learn, try deploying a simple app:
``` 
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80 --type=NodePort
minikube service nginx
For further learning, check Kubernetes Tutorials or ask me for specific exercises!

Would you like me to guide you through a sample deployment?
```


### Which of these 3 options has better GUI?

brew install lens

```
Among Minikube, Kind, and K3s,
none of them come with a built-in graphical user interface (GUI) by default,
as they are primarily CLI-driven tools designed for managing Kubernetes clusters.
However, you can pair them with external GUI tools to visualize and manage your Kubernetes clusters.
The quality of the GUI experience depends on the tool you choose rather than the Kubernetes distribution itself.

Below, I’ll evaluate the GUI options for each and their relative strengths:

1. Minikube
--------------
GUI Support: Minikube integrates well with several GUI tools, notably Kubernetes Dashboard and third-party options like Lens or Octant.
Kubernetes Dashboard:
Minikube has a built-in command to launch the official Kubernetes Dashboard:

minikube dashboard

This opens a browser-based GUI showing cluster resources (pods, deployments, services, etc.) with a clean, functional interface.
Pros: Easy to set up, lightweight, and officially supported by Kubernetes.
Cons: Basic compared to commercial tools; limited to cluster-specific views without advanced features like multi-cluster management.

Lens/Octant: Minikube clusters are easily added to Lens (now OpenLens) or Octant,
which offer modern, feature-rich GUIs with metrics, logs, and resource editing.

Lens: Polished, user-friendly, supports multiple clusters.

Octant: Open-source, lightweight, good for local development.

Verdict: Minikube’s seamless integration with the Kubernetes Dashboard and compatibility with Lens make it the most GUI-friendly out of the box.


2. Kind
-------
GUI Support: Kind doesn’t include a built-in GUI or a direct command to launch one,
 but it works with the same external tools (Kubernetes Dashboard, Lens, OpenLens, Octant).


Kubernetes Dashboard:
You can manually deploy the Dashboard to a Kind cluster:

kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml

Then access it via kubectl proxy.
This requires extra setup compared to Minikube’s one-command approach.

Lens/Octant: Kind clusters can be imported into Lens or Octant, offering the same rich GUI experience as with Minikube.

Cons: No native GUI integration; setting up the Dashboard is less streamlined.

Verdict: Kind’s GUI experience is solid with external tools but requires more manual configuration than Minikube.

3. K3s
---------
GUI Support: K3s doesn’t ship with a GUI but supports the Kubernetes Dashboard
and third-party tools like Lens or Rancher Dashboard (since K3s is developed by Rancher).

Kubernetes Dashboard:
Similar to Kind, you must manually deploy it:

kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml

Access requires additional steps (e.g., kubectl proxy or configuring ingress).

Rancher Dashboard: If you install Rancher on top of K3s, you get a powerful, enterprise-grade GUI for managing clusters.
Pros: Feature-rich, supports multi-cluster management.
Cons: Overkill for self-education, heavier resource usage, and complex setup.

Lens/Octant: K3s clusters work seamlessly with Lens or Octant, providing the same modern GUI experience.
Cons: No built-in GUI launcher; Rancher adds complexity for local learning.

Verdict:
 K3s offers good GUI options with external tools, but like Kind, it lacks Minikube’s simplicity for quick Dashboard access.

Comparison and Recommendation
---------------------------------
Best GUI Experience:

Minikube wins for its one-command access to the Kubernetes Dashboard (minikube dashboard),
 which is ideal for beginners wanting a quick, no-fuss GUI.

It also integrates effortlessly with advanced tools like Lens or Octant for a more polished experience.

--
Kind and K3s: Both rely on manual Dashboard setup or third-party tools, making them slightly less convenient for GUI users.
Their GUI experience is equivalent to Minikube’s once configured, but the setup process is less streamlined.
-----
Lens/OpenLens (Universal Option):
If you want the best GUI regardless of the tool, install Lens (free, open-source as OpenLens).
 It provides a consistent, modern interface across Minikube, Kind, and K3s,
with features like resource visualization, metrics, and terminal access.

For self-education on a MacBook, I recommend Minikube with its built-in Dashboard for simplicity,
 or pair any of the three with Lens for a richer GUI.

 Would you like me to walk you through setting up Minikube’s Dashboard or installing Lens?
```
