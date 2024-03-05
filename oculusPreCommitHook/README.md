# Oculus PreCommit Hook
This is the  pre-commit hook component of oculus. It is using modified version of the latest [gitleaks](https://github.com/ankitsaini2609/gitleaks-for-pre-commit-hook).

## How it works
I have tested the comptability on mac machine since some macbook are still using intel processor that's why directly running the gitleaks is not feasible.
To support both pre-commit hook is first pulling [oculus-pre-commit-hook](https://github.com/ankitsaini2609/oculus-pre-commit-hook) and executing `gitleaks.sh`.
`gitleaks.sh` will figure out the architecture and execute the gitleaks binary accordingly.

## How to build gitleaks binary
**Note:** Not needed, already present in oculus-pre-commit-hook. If you want build on your own, you can use the following commands:
```
git clone https://github.com/ankitsaini2609/gitleaks-for-pre-commit-hook
cd gitleaks-for-pre-commit-hook
CGO_ENABLED=0 GOARCH=amd64 go build -o gitleaks -ldflags "-X="github.com/ankitsaini2609/gitleaks-for-pre-commit-hook/master/cmd.Version=1.0
CGO_ENABLED=0 GOARCH=arm64  go build -o gitleaks-arm64 -ldflags "-X="github.com/ankitsaini2609/gitleaks-for-pre-commit-hook/master/cmd.Version=1.0
```
## How to Run
```
git clone https://github.com/ankitsaini2609/oculus
cd oculus/oculusPreCommitHook
chmod +x pre-commit-hook.sh
./pre-commit-hook.sh
```
## How to verify if pre-commit hook is setup
- check the content of the following files:
    - `~/.config/git/.pre-commit-config.yaml` It should be like:
    ```
    repos:
      - repo: https://github.com/ankitsaini2609/oculus-pre-commit-hook.git
        rev: v1.0
        hooks:
          - id: gitleaks
    ```
    - `~/.config/git/hooks/pre-commit` It should be like:
    ```
    #!/bin/bash
    # Find the root of the Git repository
    GIT_ROOT=$(git rev-parse --show-toplevel)

    directory_exists="$GIT_ROOT/.git/hooks/pre-commit"
    if [ -f "$directory_exists" ]; then
        echo "local pre-commit hooks exists. executing it first"
        bash $directory_exists
    fi

    pre-commit run -c ~/.config/git/.pre-commit-config.yaml
    ```

## What if, It is detecting false positives
You can **prepend** `SKIP=gitleaks` to the commit command and it will skip running gitleaks. You can also use `--no-verify` which will skip the whole pre-commit.




