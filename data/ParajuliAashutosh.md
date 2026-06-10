# Aashutosh Parajuli

**Email:** aashutoshparajuli28@gmail.com | **Phone:** +977 9843818516
**LinkedIn:** [linkedin.com/in/parajuliaashutosh](https://www.linkedin.com/in/parajuliaashutosh/) | **GitHub:** [github.com/parajuliaashutosh](https://www.github.com/parajuliaashutosh)

---

## Summary

Computer Engineering graduate with hands-on experience building and maintaining production backend systems serving millions of users. Skilled across the full backend stack — from API design and workflow orchestration to infrastructure, container orchestration, and GitOps. Passionate about system reliability, developer tooling, and self-hosted infrastructure.

---

## Experience

### Associate Software Engineer — Hamro Patro Inc.

**June 2025 – Present | Kathmandu, Nepal**

Maintaining a high-traffic platform generating USD 1.5 million monthly revenue, serving thousands of active users across two financial products.

#### Hamro Remit _(International Money Transfer)_

- Built international money order processing features including transaction initiation, status tracking, and payout flows.
- Implemented idempotent transaction handling to prevent duplicate financial operations during retries and network failures, significantly improving reliability under failure scenarios.
- Integrated Plaid to enable users to securely link and verify bank accounts as funding sources.

#### Hamro Pay _(Payment Platform)_

- Strengthened session validation logic and added security enhancements to reduce unauthorized access vectors.
- Identified and resolved performance bottlenecks, improving response times on high-frequency endpoints.

---

### Software Engineer — Information Care Pvt. Ltd.

**July 2024 – May 2025 | Kathmandu, Nepal** _(Intern → Full Time)_

Delivered full-cycle system development for government and international clients — from ER diagram and database design through to deployment and long-term maintenance.

#### Veterinary Medicine Order CRM

- Designed the full system from scratch: ER diagrams, relational schema, backend APIs, and business logic.
- Improved system workflows to reduce manual intervention and improve user experience for field agents.

#### Lalbandi Municipality – Data Visualization

- Designed the database schema and implemented materialized views to accelerate complex aggregation queries.
- Built data visualization features used by municipality staff and local residents.

#### ConnectKisan _(Farmer–Customer Bidding Platform)_

- Built a bidding platform enabling direct interaction between farmers and customers.
- Implemented a GraphQL API for flexible and efficient data retrieval across nested entities.

#### MyPalika _(Local Government Management System)_

- Developed a multi-module system covering citizen registration, local laws, tax records, and municipal workflows.

---

## Personal Projects

### Kubernetes (K3s) Homelab

A production-grade self-hosted Kubernetes homelab managed entirely via GitOps, demonstrating real-world infrastructure and DevOps practices.

- Provisioned a single-node K3s cluster on a Dell OptiPlex 7090 running Proxmox with Ubuntu Server VM.
- Managed all cluster state declaratively using Flux CD with SOPS age-encrypted secrets, following GitOps principles.
- Deployed and maintained multiple services: Vaultwarden, Temporal + Temporal UI, pgweb, Redis, Zot OCI registry, and a FastAPI portfolio chatbot.
- Configured Traefik ingress with Cloudflare Tunnel for secure public exposure without opening inbound ports or exposing a public IP.
- Implemented weekly `pg_dumpall` backups to Backblaze B2 using a custom `pg-backup` Docker image with Discord notifications on success/failure.
- Set up Flux CD webhook-based reconciliation for near-instant GitOps deploys on push.
- Built a Discord pod-watchdog CronJob for automated alerting on pod failures.
- Migrated all stateful workloads from hostPath volumes to K3s `local-path` PVCs for improved portability.

**Stack:** K3s, Flux CD, Traefik, Cloudflare Tunnel, Docker, Proxmox, Backblaze B2, SOPS, Linux
**Source:** [github.com/parajuliaashutosh/k8s-homelab](https://github.com/parajuliaashutosh/k8s-homelab) | **Registry:** [registry.aashutoshparajuli.com.np](https://registry.aashutoshparajuli.com.np) | **Status:** [status.aashutoshparajuli.com.np](https://status.aashutoshparajuli.com.np)

---

### International Money Order System

A backend solution for cross-border money order processing with reliable, workflow-driven transaction handling.

- Designed modular NestJS architecture with clear separation of concerns across order, payment, and notification domains.
- Used Temporal workflows to orchestrate multi-step transactions with automatic retries and state durability.
- Integrated Stripe webhooks for real-time payment event handling and Redis for caching frequently accessed state.

**Stack:** NestJS, TypeScript, Temporal, PostgreSQL, Redis, Stripe
**Source:** [github.com/parajuliaashutosh/nestjs-temporal-intl-money-order](https://github.com/parajuliaashutosh/nestjs-temporal-intl-money-order) | **API Docs:** [money-order-be.aashutoshparajuli.com.np/api/v1/docs](https://money-order-be.aashutoshparajuli.com.np/api/v1/docs)

---

### Discussion Forum _(GraphQL Backend)_

A GraphQL-powered backend for a community discussion forum with support for threaded posts, comments, and user interactions.

- Designed a flexible GraphQL schema supporting nested queries for posts, comments, and user relationships.
- Implemented authentication, authorization guards, and role-based access control.
- Built with a clean, layered architecture separating resolvers, services, and data access.

**Stack:** Node.js, GraphQL, PostgreSQL
**Source:** [github.com/parajuliaashutosh/discussion-forum-graphql--backend](https://github.com/parajuliaashutosh/discussion-forum-graphql--backend)

---

### Personal Bot _(Portfolio Chatbot)_

- Implemented Retrieval-Augmented Generation (RAG) using pgvector for semantic search over embedded personal data.
- Engineered a model-agnostic AI orchestration layer utilizing Server-Sent Events (SSE) to deliver low-latency, real-time token streaming responses.
- Written with functional-only code patterns using asyncpg for raw async SQL queries.

**Stack:** Python, FastAPI, pgvector, PostgreSQL, Gemini 2.0 Flash
**Source:** [github.com/parajuliaashutosh/personal-bot](https://github.com/parajuliaashutosh/personal-bot) | **API Docs:** [chatbot.aashutoshparajuli.com.np/docs](https://chatbot.aashutoshparajuli.com.np/docs)

---

### Charitable – Online Donation Platform

A platform connecting donors with organizations for clothing and book donations, built with hexagonal architecture for maintainability and loose coupling.

- Implemented a hexagonal (ports and adapters) architecture to decouple domain logic from infrastructure concerns.
- Used gRPC for inter-service communication and RabbitMQ for async event-driven workflows.
- Built a Next.js frontend integrated with the Micronaut backend.

**Stack:** Java, Micronaut, JPA, gRPC, RabbitMQ, Next.js
**Backend:** [github.com/parajuliaashutosh/charitable-backend-mn-grpc](https://github.com/parajuliaashutosh/charitable-backend-mn-grpc) | **Frontend:** [github.com/parajuliaashutosh/charitable-frontend-next](https://github.com/parajuliaashutosh/charitable-frontend-next)

---

## Skills

**Languages:** TypeScript, JavaScript, Python, Java

**Frameworks & Libraries:** NestJS, FastAPI, Express.js, Micronaut, Next.js

**Databases:** PostgreSQL, Redis, MongoDB, MySQL

**Infrastructure & DevOps:** Kubernetes (K3s), Flux CD, Docker, Proxmox, Linux, Cloudflare Tunnel, Backblaze B2, SOPS

**Messaging & Workflows:** Temporal, RabbitMQ

**APIs & Protocols:** REST, GraphQL, gRPC, WebSockets / SSE

**Tools:** Git, Postman, pgvector

---

## Education

### Bachelor of Engineering in Computer Engineering

Himalaya College of Engineering, Tribhuvan University — Kathmandu, Nepal
**Score:** 70%

### Higher Secondary (Science / +2)

**Score:** 3.17 GPA

### Secondary School Leaving Certificate (SLC)

**Score:** 3.6 GPA

---

## Standardized Tests & Certifications

| Test             | Score |
| ---------------- | ----- |
| IELTS (Academic) | 8.0   |
| GRE              | 317   |

---

## Professional Registration

**General Registered Engineer** — Nepal Engineering Council (NEC) | ID: 83472
