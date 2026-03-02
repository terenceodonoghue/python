.PHONY: setup security-scan security-scan-home-mcp security-scan-tech-mcp

setup:
	brew bundle
	uv sync
	pre-commit install

security-scan: security-scan-home-mcp security-scan-tech-mcp

security-scan-home-mcp:
	docker build -t home-mcp:scan -f projects/home-mcp/Dockerfile projects/home-mcp
	trivy image --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1 home-mcp:scan

security-scan-tech-mcp:
	docker build -t tech-mcp:scan -f projects/tech-mcp/Dockerfile projects/tech-mcp
	trivy image --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1 tech-mcp:scan
