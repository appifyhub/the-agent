import base64
import datetime
import os
import re
from typing import List

import requests

# Environment setup and validations
github_token = os.getenv("GITHUB_TOKEN")
if not github_token:
    print("Set 'GITHUB_TOKEN' environment variable to enable GitHub releases")
    exit(1)

version = os.getenv("VERSION")
if not version:
    # noinspection PyBroadException
    try:
        with open(".version", "r") as file:
            version = file.read().strip()
            if not version:
                raise ValueError("Version file is empty")
    except Exception:
        print("Set 'VERSION' environment variable or create a .version file to enable GitHub releases")
        exit(1)

full_repo_name = os.getenv("GITHUB_REPOSITORY")
if not full_repo_name:
    print("Set 'GITHUB_REPOSITORY' environment variable to enable GitHub releases")
    exit(1)

build_quality = os.getenv("BUILD_QUALITY", "Debug")
default_commitish = os.popen("git rev-parse HEAD").read().strip() or "main"
commitish = os.getenv("GITHUB_SHA", default_commitish)
print(f"Using '{commitish}' as commitish")

# Determine the tag based on build quality
tag = f"v{version}.{build_quality.lower()}"
if build_quality == "Debug":
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d-%H-%M-%S")
    tag += f".{timestamp}"

# Configure the release parameters
repo_owner = full_repo_name.split("/")[0]
repo_name = full_repo_name.split("/")[1]
artifact = os.getenv("ARTIFACT", "release")
release_name = f"{artifact.capitalize()} [{build_quality}]: {version}"
is_prerelease = build_quality != "GA"

# Fetch and format changelog
ignored_patterns = [
    re.compile(pattern, re.IGNORECASE) for pattern in [
        ".*bump.*version.*",
        ".*increase.*version.*",
        ".*version.*bump.*",
        ".*version.*increase.*",
        ".*merge.*request.*",
        ".*request.*merge.*",
    ]
]


def fetch_changes() -> List[str]:
    # first pull the latest changes and tags
    if os.path.exists(".git/shallow"):
        os.system("git fetch --unshallow")
    os.system("git fetch --tags")

    # get the most recent GA tag
    last_tag_command = "git for-each-ref --sort=-creatordate --format '%(refname:short)' refs/tags | grep '.ga$' | head -n1"
    # noinspection StandardShellInjection
    last_tag = os.popen(last_tag_command).read().strip()

    # then get the history between now and the last GA tag
    commits_diff_command = f"git log {last_tag}..HEAD --format=oneline --abbrev-commit --no-merges"
    # noinspection StandardShellInjection
    commits_diff = os.popen(commits_diff_command).read().strip().split("\n")
    print(f"Found commits diff:\n\t{commits_diff}")

    return [
        change.strip() for change in commits_diff
        if not any(pattern.match(change) for pattern in ignored_patterns)
    ]


changes = fetch_changes()
bullet = "\n* "
change_log = f"## Latest changes{bullet}{bullet.join(changes)}" if changes else "Something is better now, enjoy."

# Build the body of the release
body = {
    "tag_name": tag,
    "name": release_name,
    "body": change_log,
    "draft": False,
    "prerelease": is_prerelease,
    "target_commitish": commitish,
}

# Publish the release (fails intentionally if tag already exists)
release_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases"
headers = {"Authorization": f"token {github_token}"}
response = requests.post(release_url, json = body, headers = headers)

if response and response.status_code != 201:
    print("GitHub Release failed")
    print(response.content)
    exit(1)

release_notes = f"# Release v{version}\n\n{change_log}"
encoded_change_log = base64.b64encode(release_notes.encode('utf-8')).decode('utf-8')
print(f"Encoded change log: {encoded_change_log}")
print(f"::set-output name=encoded_change_log::{encoded_change_log}")
print("GitHub Release created successfully")
