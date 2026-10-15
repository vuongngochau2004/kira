# Modules Architecture

Modules are organized by feature first, then by layer:

```text
module_name/
  api/             # HTTP routes, request/response schemas, HTTP mapping
  application/     # Use cases, application DTOs, ports
  domain/          # Entities, value objects, domain services, domain errors
  infrastructure/  # Concrete adapters: database, storage, vector store, LLM, OCR
  composition.py   # Dependency wiring for the module
```

Allowed dependency direction:

```text
api -> application -> domain
composition -> application / infrastructure
infrastructure -> application ports / domain
```

Avoid these dependencies:

```text
domain -> api
domain -> infrastructure
application -> api
api -> infrastructure
```

Cross-module calls should go through another module's `composition.py`,
application use case, or shared port. Do not import deep infrastructure from
another feature module unless you are inside a composition boundary.

RAG has an additional `orchestration/` layer for graph, agents, and state:

```text
rag/
  application/
  domain/
  orchestration/
  infrastructure/
  composition.py
```
