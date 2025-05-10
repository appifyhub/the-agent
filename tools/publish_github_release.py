import base64
import datetime
import json
import os
import re
from typing import Any

import requests
from requests import Response

# --- Utilities ---

IGNORED_COMMIT_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in [
        ".*bump.*version.*",
        ".*increase.*version.*",
        ".*version.*bump.*",
        ".*version.*increase.*",
        ".*merge.*request.*",
        ".*request.*merge.*",
    ]
]


def strip_tag_markers(marked_tag: str | None, quality_tag: str) -> str:
    """
    Strips the 'v' prefix and the build quality and other suffixes from a marked build tag.
    Example: v1.0.0.beta -> 1.0.0; v1.0.0.dev.timestamp -> 1.0.0
    """
    if not marked_tag:
        return ""
    marked_tag = marked_tag.lstrip("v")
    last_quality_tag_index = marked_tag.rfind(f".{quality_tag}")
    if last_quality_tag_index != -1:
        marked_tag = marked_tag[:last_quality_tag_index]
    return marked_tag


def extract_repository(remote_url: str) -> str:
    """
    Extracts the owner and repository name from a remote URL.
    """
    if not remote_url:
        return ""
    remote_url = remote_url.removesuffix(".git")
    if remote_url.startswith("git@"):
        parts = remote_url.split(":")[-1].split("/")
        return f"{parts[-2]}/{parts[-1]}"
    elif remote_url.startswith("https://"):
        parts = remote_url.split("/")
        return f"{parts[-2]}/{parts[-1]}"
    else:
        return ""


# --- Main script ---

# Validate the GitHub token
github_token: str | None = os.getenv("GITHUB_TOKEN")
if not github_token:
    print("❌  Set 'GITHUB_TOKEN' environment variable to enable GitHub releases")
    exit(1)
print("✅  GitHub token is set")

# Validate the target service version
target_version: str | None = os.getenv("VERSION")
if not target_version:
    try:
        with open(".version", "r") as file:
            target_version = file.read().strip()
            if not target_version:
                print("❌  Version file is empty")
                exit(1)
    except Exception:
        print("❌  Set 'VERSION' environment variable or create a .version file to enable GitHub releases")
        exit(1)
print(f"✅  Version is set to {target_version}")

# Compute the source control attributes
if os.path.exists(".git/shallow"):
    os.system("git fetch --unshallow")
os.system("git fetch --tags")
default_build_quality: str = "DEV"
build_quality: str = os.getenv("BUILD_QUALITY", default_build_quality)
build_quality_tag: str = build_quality.lower()
default_commitish: str = os.popen("git rev-parse HEAD").read().strip() or "main"
commitish: str = os.getenv("GITHUB_SHA", default_commitish)
default_branch: str = os.popen("git rev-parse --abbrev-ref HEAD").read().strip() or "main"
branch: str = os.getenv("GITHUB_REF", default_branch)
target_tag: str = f"v{target_version}.{build_quality_tag}"
if build_quality == default_build_quality:
    timestamp: str = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d_%H-%M-%S")
    target_tag += f".{timestamp}"
print("✅  Source control attributes set:")
print(f"    - Build quality: {build_quality}")
print(f"    - Commitish: {commitish}")
print(f"    - Branch: {branch}")
print(f"    - Target tag: {target_tag}")

# Compute the latest release tag
if build_quality not in ("PR", "BETA", "GA"):
    print("❌  Invalid build quality. Only GA, BETA, and PR are supported.")
    exit(1)
print(f"✅  Build quality '{build_quality}' can fetch history")
latest_release_tag_command: str = (
    "git for-each-ref --sort=-creatordate --format '%(refname:short)' refs/tags "
    f"| grep '.{build_quality_tag}$' | head -n 1"
)
# noinspection StandardShellInjection
latest_release_tag: str = os.popen(latest_release_tag_command).read().strip()
if not latest_release_tag:
    print("❌  No latest release tag found")
    exit(1)
print(f"✅  Found latest release tag: {latest_release_tag}")
latest_release_version: str = strip_tag_markers(latest_release_tag, build_quality_tag)
if not latest_release_version:
    print("❌  No latest release version found")
    exit(1)
print(f"✅  Found latest release version: {latest_release_version}")

# Compute the commit diff
commit_diff_command: str = f"git log {latest_release_tag}..HEAD --format=oneline --abbrev-commit --no-merges"
# noinspection StandardShellInjection
commits_raw: list[str] = os.popen(commit_diff_command).read().strip().split("\n")
commits_filtered: list[str] = [
    commit.strip() for commit in commits_raw
    if not any(pattern.match(commit) for pattern in IGNORED_COMMIT_PATTERNS)
]
commits: list[str] = [commit for commit in commits_filtered if commit]
if not commits:
    print("⚠️  No commit diff found")
else:
    print(f"✅  Found {len(commits)} commit(s) in the diff")
    for commit in commits:
        trimmed_commit = (commit[:40].strip() + "...") if len(commit) > 40 else commit
        print(f"    - {trimmed_commit}")

# Compute the release attributes
remote_repo_url: str = os.popen("git config --get remote.origin.url").read().strip()
default_full_repo_name: str = extract_repository(remote_repo_url)
full_repo_name: str = os.getenv("GITHUB_REPOSITORY", default_full_repo_name)
if not full_repo_name:
    print("❌  Set 'GITHUB_REPOSITORY' environment variable to enable GitHub releases")
    exit(1)
print(f"✅  Repository name is set to {full_repo_name}")
repo_owner: str = full_repo_name.split("/")[0]
repo_name: str = full_repo_name.split("/")[1]
if not repo_owner or not repo_name:
    print("❌  Invalid repository name")
    exit(1)
print(f"✅  Repository owner is set to {repo_owner}")
artifact_raw: str = os.getenv("ARTIFACT", "release")
artifact: str = re.sub(r"\b(\w)(\w*)\b", lambda m: m.group(1).upper() + m.group(2), artifact_raw)
release_name_quality: str = f" [{build_quality}]" if build_quality != "GA" else ""
release_name: str = f"{artifact}: {target_version}{release_name_quality}"
default_release_body = "Things are better now, enjoy!"
release_body: str = f"## Changes in this release\n\n  * {"\n  * ".join(commits)}" if commits else default_release_body
is_prerelease: bool = build_quality != "GA"
body: dict[str, Any] = {
    "tag_name": target_tag,
    "name": release_name,
    "body": release_body,
    "draft": False,
    "prerelease": is_prerelease,
    "target_commitish": commitish,
}
print("✅  Release is ready to be published:")
print(f"    - Tag name: {target_tag}")
print(f"    - Release name: {release_name}")
print(f"    - Release body: {json.dumps(release_body)[:40]}...")
print(f"    - Is pre-release: {is_prerelease}")
print(f"    - Target commitish: {commitish}")

# Publish the release (intentionally fails if tag already exists)
releases_url: str = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases"
headers: dict[str, Any] = {"Authorization": f"token {github_token}"}
response: Response = requests.post(releases_url, json = body, headers = headers)
if response and response.status_code not in (200, 201):
    print("❌  Failed to publish GitHub release")
    print(response.content)
    exit(1)
print("✅  GitHub release published successfully")

# Prepare and encode the outputs
release_notes_raw: str = f"# Release v{target_version}\n\n{release_body}"
release_notes_b64: str = base64.b64encode(release_notes_raw.encode("utf-8")).decode("utf-8")
release_output: dict[str, Any] = {
    "latest_version": latest_release_version,
    "new_target_version": target_version,
    "release_quality": build_quality,
    "release_notes_b64": release_notes_b64,
}
release_output_b64 = base64.b64encode(json.dumps(release_output).encode("utf-8")).decode("utf-8")
print("✅  Release output prepared successfully:")
print(json.dumps(release_output, indent = 2))

# Store the outputs and finish
print(f"::set-output name=release_output_b64::{release_output_b64}")
print(f"::set-output name=release_version::{target_version}")
print("✅  GitHub Release script finished successfully")
