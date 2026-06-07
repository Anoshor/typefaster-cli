# infra/ — Phase 2 (infrastructure)

**Not implemented yet.** Reserved for Phase 2 deployment assets:

```
infra/
├── docker-compose.yml   # server + redis + nginx
├── nginx/               # reverse proxy + SSL config
├── redis/               # persistence config
└── scripts/             # backups, monitoring helpers
```

Target: single Linux VM, minimal cost (no Kubernetes, no managed DBs).
Deployment guide will be documentation only — nothing is deployed automatically.

See [`../docs/roadmap.md`](../docs/roadmap.md).
