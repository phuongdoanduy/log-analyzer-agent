# Copyright 2026 Optimus Team
# MIT License
#
# Configuration for Log Analyzer Agent

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class LogAnalyzerConfig:
    """Configuration for the Log Analyzer Agent."""

    # GCP Environment Map
    env_map: dict[str, dict[str, str]] = field(default_factory=lambda: {
        "dev-vn": {
            "project": "klara-nonprod",
            "cluster": "klara-dev-vn",
            "region": "asia-southeast1-a",
            "namespace": "dev-vn",
        },
        "dev": {
            "project": "klara-nonprod",
            "cluster": "klara-nonprod",
            "region": "europe-west6-a",
            "namespace": "dev",
        },
        "test": {
            "project": "klara-nonprod",
            "cluster": "klara-nonprod",
            "region": "europe-west6-a",
            "namespace": "test",
        },
        "performance": {
            "project": "klara-performance",
            "cluster": "klara-performance",
            "region": "europe-west6-a",
            "namespace": "performance",
        },
        "prod": {
            "project": "klara-prod",
            "cluster": "klara-prod",
            "region": "europe-west6-a",
            "namespace": "prod",
        },
    })

    # Model configuration
    worker_model: str = "gemini-2.0-flash"
    critic_model: str = "gemini-2.0-flash"

    # Default analysis parameters
    default_severity: str = "ERROR"
    default_freshness: str = "1h"
    default_limit: int = 500

    # Output configuration
    report_output_dir: str = "plans/reports"
    log_output_dir: str = "/tmp"

    # MCP Server configuration
    mcp_server_name: str = "polaris-mcp-server"
    mcp_server_port: int = 3003

    def get_project(self, env: str) -> str:
        """Get GCP project ID for an environment."""
        env_config = self.env_map.get(env.lower())
        if not env_config:
            raise ValueError(
                f"Unknown environment: {env}. "
                f"Valid environments: {', '.join(self.env_map.keys())}"
            )
        return env_config["project"]

    def get_cluster(self, env: str) -> str:
        """Get GKE cluster name for an environment."""
        env_config = self.env_map.get(env.lower())
        if not env_config:
            raise ValueError(f"Unknown environment: {env}")
        return env_config["cluster"]

    def get_region(self, env: str) -> str:
        """Get GCP region for an environment."""
        env_config = self.env_map.get(env.lower())
        if not env_config:
            raise ValueError(f"Unknown environment: {env}")
        return env_config["region"]


# Global config singleton
config = LogAnalyzerConfig()
