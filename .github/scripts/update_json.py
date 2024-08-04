import requests
import json
import os

def get_latest_and_latest_pre_release(repo):
    url = f"https://api.github.com/repos/{repo}/releases"
    response = requests.get(url)
    response.raise_for_status()
    releases = response.json()

    latest_release = None
    latest_pre_release = None

    for release in releases:
        if not release["draft"]:  # Ignore draft releases
            if release["prerelease"]:
                # Update latest_pre_release if it's the first one we've found
                if latest_pre_release is None:
                    latest_pre_release = release
            else:
                # Update latest_release if it's the first non-pre-release we've found
                if latest_release is None:
                    latest_release = release
            # If we've found both, no need to continue checking
            if latest_release and latest_pre_release:
                break

    return latest_release, latest_pre_release

def fetch_manifest(repo):
    url = f"https://raw.githubusercontent.com/{repo}/main/manifest.json"
    response = requests.get(url)
    response.raise_for_status()
    # Decode using 'utf-8-sig' to handle BOM
    content = response.content.decode('utf-8-sig')
    return json.loads(content)

def append_changelog(manifest, latest_release):
    if latest_release:
        manifest["Changelog"] = latest_release["body"]
    return manifest

def append_manifest(manifest, latest_release, latest_pre_release):
    if latest_release:
        manifest["DownloadLinkInstall"] = latest_release["assets"][0]["browser_download_url"]
        manifest["AssemblyVersion"] = latest_release["tag_name"]
        manifest["DownloadLinkUpdate"] = latest_release["assets"][0]["browser_download_url"]
    if latest_pre_release:
        manifest["DownloadLinkTesting"] = latest_pre_release["assets"][0]["browser_download_url"]
        manifest["TestingAssemblyVersion"] = latest_pre_release["tag_name"]
    if latest_release is None:
        manifest["DownloadLinkInstall"] = manifest["DownloadLinkTesting"]
        manifest["AssemblyVersion"] = manifest["TestingAssemblyVersion"]
    return manifest

def append_download_count(manifest, repo):
    url = f"https://api.github.com/repos/{repo}/releases"
    response = requests.get(url)
    response.raise_for_status()
    releases = response.json()

    download_count = 0
    for release in releases:
        for asset in release["assets"]:
            download_count += asset["download_count"]

    manifest["DownloadCount"] = download_count
    return manifest

def main():
    # Get repositories from repos.txt
    with open('repos.txt', 'r') as f:
        repos = f.read().splitlines()

    combined_manifests = []
    
    for repo in repos:
        latest_release, latest_pre_release = get_latest_and_latest_pre_release(repo)
        if (latest_pre_release is None and latest_release is not None) or (latest_release is not None and latest_pre_release is not None and latest_release["tag_name"] == latest_pre_release["tag_name"]):
            latest_pre_release = None
        if (latest_release is None and latest_pre_release is None):
            print(f"Skipping {repo} as there are no releases")
            continue
        manifest = fetch_manifest(repo)
        manifest = append_manifest(manifest, latest_release, latest_pre_release)
        manifest = append_download_count(manifest, repo)
        manifest = append_changelog(manifest, latest_release)
        combined_manifests.append(manifest)
        print(f"{repo}: {latest_release['tag_name'] if latest_release else 'Testing Only'} {latest_pre_release['tag_name'] if latest_pre_release else ''}")
    
    with open('pluginmaster.json', 'w') as f:
        json.dump(combined_manifests, f, indent=4)

if __name__ == "__main__":
    main()
