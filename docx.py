from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.set_font("Arial", size=12)

pdf.set_font("Arial", "B", 16)
pdf.cell(200, 10, "Complete DevOps + SRE Roadmap (0 to 3 Years Experience)", ln=True, align="C")
pdf.ln(10)
pdf.set_font("Arial", size=12)

content = """
 Week-by-Week Learning Plan – DevOps + SRE (0–3 Years Experience)

=====================
WEEK 1–2: FOUNDATION
=====================
- Learn: DevOps vs SRE, Linux Basics, Git
- Tools: Ubuntu/Linux, Git, GitHub
- Tasks:
  • Practice Git commands (clone, commit, push, pull, branch)
  • Learn file handling, permissions, processes, logs

=========================
WEEK 3–4: SCRIPTING & CI/CD
=========================
- Learn: Shell Scripting, Bash, CI/CD Basics
- Tools: Bash, Python, GitHub Actions or Jenkins
- Tasks:
  • Write health-check scripts
  • Create simple CI/CD pipeline (build + test)

===============================
WEEK 5–6: CONTAINERIZATION
===============================
- Learn: Docker, Dockerfiles, Docker Compose
- Tools: Docker CLI, DockerHub
- Tasks:
  • Create Dockerfile for sample app
  • Run containers, use volumes, expose ports

============================
WEEK 7–8: KUBERNETES BASICS
============================
- Learn: Pods, Services, Deployments, YAML
- Tools: Minikube, kubectl, k9s
- Tasks:
  • Deploy app to Kubernetes
  • Scale services, use liveness/readiness probes

==============================
WEEK 9–10: MONITORING & LOGGING
==============================
- Learn: Observability, Metrics, Logs
- Tools: Prometheus, Grafana, Loki, Alertmanager
- Tasks:
  • Install Prometheus + Grafana
  • Create dashboard, alerts for CPU/memory/disk

==============================
WEEK 11–12: INFRASTRUCTURE AS CODE
==============================
- Learn: Terraform Basics, Provisioning Resources
- Tools: Terraform, AWS/GCP
- Tasks:
  • Write Terraform scripts to create EC2/VM
  • Use variables, outputs, state file

==============================
WEEK 13–14: CONFIGURATION MANAGEMENT
==============================
- Learn: Ansible Basics, Playbooks, Roles
- Tools: Ansible
- Tasks:
  • Create playbook to install nginx or Docker
  • Use roles and inventories

===============================
WEEK 15–16: ADVANCED CI/CD + GITOPS
===============================
- Learn: ArgoCD, Jenkins Pipelines
- Tools: ArgoCD, Jenkins, GitHub Actions
- Tasks:
  • Deploy using GitOps
  • Create multi-stage pipelines (build, test, deploy)

==============================
WEEK 17–18: SITE RELIABILITY ENGINEERING (SRE)
==============================
- Learn: SLIs, SLOs, Error Budgets, Postmortems
- Tools: Prometheus, Grafana, Alertmanager
- Tasks:
  • Set SLOs (e.g. 99.9% uptime)
  • Create alert rules, simulate incidents, write postmortems

===============================
WEEK 19–20: CLOUD NATIVE DEPLOYMENTS
===============================
- Learn: Helm, Kustomize, Service Mesh
- Tools: Helm, Istio/Linkerd, Kustomize
- Tasks:
  • Use Helm to deploy apps
  • Explore Istio for service mesh

===============================
WEEK 21–24: PROJECT + INTERVIEW PREP
===============================
- Learn: Design full CI/CD workflow with monitoring and IaC
- Tools: Docker, Kubernetes, Jenkins, Terraform, Prometheus
- Tasks:
  • Final project: Full DevOps + SRE stack
  • Prepare resume, mock interviews, common Q&As

 By End of This Plan (6 Months):
- Strong hands-on with DevOps + SRE tools
- Real-world project ready for resume
- Ready for jobs up to 3 years experience
"""

for line in content.split("\n"):
    pdf.multi_cell(0, 10, line)

pdf.output("DevOps_SRE.pdf")
