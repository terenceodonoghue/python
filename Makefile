.PHONY: security-scan

security-scan:
	docker build -t home-mcp:scan -f projects/home-mcp/Dockerfile projects/home-mcp
	trivy image --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1 home-mcp:scan
