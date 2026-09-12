# Reproducible commands

Use the authenticated CLI scratch directory for the design-system-modernization
debug stack.

```bash
cd /tmp/bifrost-cli-design-system-modernization
./.venv/bin/bifrost auth default
./.venv/bin/bifrost files write workflows/design_review.py --from-file \
  /home/jack/GitHub/bifrost/.claude/worktrees/design-system-modernization/docs/design-modernization/fixtures/design_review_workflow.py \
  --create-only
./.venv/bin/bifrost workflows register \
  --path workflows/design_review.py \
  --function-name design_review \
  --global \
  --access-level authenticated
./.venv/bin/bifrost forms create \
  --name "Design Review Intake" \
  --description "Synthetic intake form for design modernization review" \
  --workflow workflows/design_review.py::design_review \
  --form-schema @/home/jack/GitHub/bifrost/.claude/worktrees/design-system-modernization/docs/design-modernization/fixtures/design_review_form_schema.json \
  --access-level authenticated \
  --global
./.venv/bin/bifrost workflows execute workflows/design_review.py::design_review \
  --params '{"review_id":"DR-001","summary":"Baseline capture","priority":"high","should_fail":false,"owner":"Design Ops"}'
./.venv/bin/bifrost workflows execute workflows/design_review.py::design_review \
  --params '{"review_id":"DR-002","summary":"Intentional failure","priority":"low","should_fail":true,"owner":"Design Ops"}'
```
