# Gitleaks

Gitleaks is a SAST tool for detecting hardcoded secrets like passwords, api keys, and tokens in git repos. Gitleaks is an **easy-to-use, all-in-one solution** for finding secrets, past or present, in your code.

All the credits goes to the Original Authors. Please find the Original Source Code [here](https://github.com/gitleaks/gitleaks).
 
### Installation
```
cd gitleaks
go build main.go
mv main gitleaks
```
Add gitleaks to the path. 

### Usage and Options
```
Usage:
  gitleaks [OPTIONS]

Application Options:
  -v, --verbose             Show verbose output from scan
  -q, --quiet               Sets log level to error and only output leaks, one json object per line
  -r, --repo-url=           Repository URL
  -p, --path=               Path to directory (repo if contains .git) or file
  -c, --config-path=        Path to config
      --repo-config-path=   Path to gitleaks config relative to repo root
      --clone-path=         Path to clone repo to disk
      --version             Version number
      --username=           Username for git repo
      --password=           Password for git repo
      --access-token=       Access token for git repo
      --threads=            Maximum number of threads gitleaks spawns
      --ssh-key=            Path to ssh key used for auth
      --unstaged            Run gitleaks on unstaged code
      --branch=             Branch to scan
      --redact              Redact secrets from log messages and leaks
      --debug               Log debug messages
      --no-git              Treat git repos as plain directories and scan those files
      --leaks-exit-code=    Exit code when leaks have been encountered (default: 1)
      --append-repo-config  Append the provided or default config with the repo config.
      --additional-config=  Path to an additional gitleaks config to append with an existing config. Can be used with --append-repo-config to append up to three configurations
  -o, --report=             Report output path
  -f, --format=             JSON, CSV, SARIF (default: json)
      --files-at-commit=    Sha of commit to scan all files at commit
      --commit=             Sha of commit to scan or "latest" to scan the last commit of the repository
      --commits=            Comma separated list of a commits to scan
      --commits-file=       Path to file of line separated list of commits to scan
      --commit-since=       Scan commits more recent than a specific date. Ex: '2006-01-02' or '2006-01-02T15:04:05-0700' format.
      --commit-until=       Scan commits older than a specific date. Ex: '2006-01-02' or '2006-01-02T15:04:05-0700' format.
      --depth=              Number of commits to scan

Help Options:
  -h, --help                Show this help message
```

