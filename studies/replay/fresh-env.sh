# Source this before `flywheel replay mine|check|run` with fresh-repos.json or full-repos.json.
# Environments live outside the repositories, under /home/user/replay-env (built with uv).
E=/home/user/replay-env
export VERITY_PY=$E/verity/bin/python VERITY_BIN=$E/verity/bin
export FOOTHOLD_PY=$E/foothold/bin/python FOOTHOLD_BIN=$E/foothold/bin
export FATHOM_PY=$E/fathom/bin/python FATHOM_BIN=$E/fathom/bin
export MARGINALIA_PY=$E/marginalia/bin/python MARGINALIA_BIN=$E/marginalia/bin
export ERP_PY=$E/erp/bin/python ERP_BIN=$E/erp/bin
export STUDBOOK_PY=$E/studbook/bin/python STUDBOOK_BIN=$E/studbook/bin
export SHU_PY=$E/shu/bin/python SHU_BIN=$E/shu/bin
export STUDBOOK_AGENT_PY=$E/studbook-agent/bin/python STUDBOOK_AGENT_BIN=$E/studbook-agent/bin
export AGENTOPS_PY=$E/agentops/bin/python AGENTOPS_BIN=$E/agentops/bin
export LODESTAR_PY=$E/lodestar/bin/python LODESTAR_BIN=$E/lodestar/bin
export GARVIS_PY=$E/garvis/bin/python GARVIS_BIN=$E/garvis/bin
export CHANGELENS_PY=$E/flywheel/bin/python CHANGELENS_BIN=$E/flywheel/bin
export WASL_NM=$E/wasl/node_modules AUSPEX_NM=$E/auspex/node_modules
export ATELIER_NM=$E/atelier/node_modules PORTFOLIO_NM=$E/portfolio/node_modules
# Tests must never need keys or a database.
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN STUDBOOK_DATABASE_URL STUDBOOK_INGEST_DATABASE_URL SHU_DATABASE_URL
# No network for tracing or telemetry during tests.
export LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false LANGSMITH_TRACING_V2=false DBT_SEND_ANONYMOUS_USAGE_STATS=false
