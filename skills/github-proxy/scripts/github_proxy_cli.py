#!/usr/bin/env python3
"""GitHub Agent Proxy CLI - Tiny CLI for Hermes skill.

A deterministic CLI that interacts with the GitHub Agent Proxy.
Uses only Python stdlib. Outputs JSON with explicit exit codes.

Exit codes:
  0 - Success
  1 - Error (any type)

Usage:
  github_proxy_cli.py create-branch --repo owner/repo --branch name --base main
  github_proxy_cli.py commit-files --repo owner/repo --branch name --message "msg" --file path:content
  github_proxy_cli.py create-pr --repo owner/repo --title "Title" --head branch --base main [--body "desc"]
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


def get_env(var: str) -> str:
    """Get required environment variable or exit with error."""
    value = os.environ.get(var, "")
    if not value:
        print_json_error(f"Environment variable {var} is not set")
        sys.exit(1)
    return value


def print_json(data: dict[str, Any]) -> None:
    """Print JSON to stdout."""
    print(json.dumps(data, indent=2))


def print_json_error(message: str, error_code: str = "error") -> None:
    """Print error as JSON to stderr."""
    print(json.dumps({"error": error_code, "message": message}), file=sys.stderr)


def make_request(
    endpoint: str,
    payload: dict[str, Any],
    base_url: str,
    api_key: str,
) -> dict[str, Any]:
    """Make HTTP POST request to the proxy.

    Args:
        endpoint: API endpoint (e.g., /create-branch)
        payload: Request body
        base_url: Proxy base URL
        api_key: API key for authentication

    Returns:
        Response JSON on success

    Raises:
        SystemExit on any error
    """
    url = f"{base_url.rstrip('/')}{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = json.dumps(payload).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as e:
        # Try to parse error response
        try:
            error_body = json.loads(e.read().decode("utf-8"))
            print_json_error(
                error_body.get("message", f"HTTP {e.code}"),
                error_body.get("error", "http_error"),
            )
        except (json.JSONDecodeError, Exception):
            print_json_error(f"HTTP {e.code}: {e.reason}", "http_error")
        sys.exit(1)

    except urllib.error.URLError as e:
        print_json_error(f"Connection failed: {e.reason}", "connection_error")
        sys.exit(1)

    except Exception as e:
        print_json_error(f"Request failed: {e}", "request_error")
        sys.exit(1)


def cmd_create_branch(args: argparse.Namespace) -> None:
    """Create a new branch."""
    base_url = get_env("GITHUB_PROXY_URL")
    api_key = get_env("GITHUB_PROXY_API_KEY")

    payload = {
        "repo": args.repo,
        "branch": args.branch,
        "base": args.base,
    }

    result = make_request("/create-branch", payload, base_url, api_key)
    print_json(result)


def cmd_commit_files(args: argparse.Namespace) -> None:
    """Commit files to a branch."""
    base_url = get_env("GITHUB_PROXY_URL")
    api_key = get_env("GITHUB_PROXY_API_KEY")

    # Parse files: path:content format
    files = []
    for file_spec in args.file:
        if ":" not in file_spec:
            print_json_error(
                f"Invalid file format: {file_spec}. Use path:content",
                "validation_error",
            )
            sys.exit(1)
        path, content = file_spec.split(":", 1)
        files.append({"path": path, "content": content})

    if not files:
        print_json_error("At least one file is required", "validation_error")
        sys.exit(1)

    payload = {
        "repo": args.repo,
        "branch": args.branch,
        "message": args.message,
        "files": files,
    }

    result = make_request("/commit-files", payload, base_url, api_key)
    print_json(result)


def cmd_create_pr(args: argparse.Namespace) -> None:
    """Create a pull request."""
    base_url = get_env("GITHUB_PROXY_URL")
    api_key = get_env("GITHUB_PROXY_API_KEY")

    payload = {
        "repo": args.repo,
        "title": args.title,
        "head": args.head,
        "base": args.base,
    }

    if args.body:
        payload["body"] = args.body

    result = make_request("/create-pr", payload, base_url, api_key)
    print_json(result)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="GitHub Agent Proxy CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # create-branch subcommand
    create_branch_parser = subparsers.add_parser(
        "create-branch", help="Create a new branch"
    )
    create_branch_parser.add_argument(
        "--repo", required=True, help="Repository (owner/repo)"
    )
    create_branch_parser.add_argument(
        "--branch", required=True, help="New branch name"
    )
    create_branch_parser.add_argument(
        "--base", required=True, help="Base branch to create from"
    )
    create_branch_parser.set_defaults(func=cmd_create_branch)

    # commit-files subcommand
    commit_files_parser = subparsers.add_parser(
        "commit-files", help="Commit files to a branch"
    )
    commit_files_parser.add_argument(
        "--repo", required=True, help="Repository (owner/repo)"
    )
    commit_files_parser.add_argument(
        "--branch", required=True, help="Target branch name"
    )
    commit_files_parser.add_argument(
        "--message", required=True, help="Commit message"
    )
    commit_files_parser.add_argument(
        "--file",
        required=True,
        action="append",
        help="File to commit (path:content). Can be specified multiple times.",
    )
    commit_files_parser.set_defaults(func=cmd_commit_files)

    # create-pr subcommand
    create_pr_parser = subparsers.add_parser(
        "create-pr", help="Create a pull request"
    )
    create_pr_parser.add_argument(
        "--repo", required=True, help="Repository (owner/repo)"
    )
    create_pr_parser.add_argument("--title", required=True, help="PR title")
    create_pr_parser.add_argument(
        "--head", required=True, help="Head branch (source)"
    )
    create_pr_parser.add_argument(
        "--base", required=True, help="Base branch (target)"
    )
    create_pr_parser.add_argument("--body", help="PR body/description")
    create_pr_parser.set_defaults(func=cmd_create_pr)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
