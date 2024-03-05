#!/bin/bash
## V1.0.0
## pre-commit-hook.sh
## Authors: Ankit Saini

echo -e "
 ######                                                                                                     #         ###   
 #     # #####  ######        ####   ####  #    # #    # # #####    #    #  ####   ####  #    #    #    #  ##        #   #  
 #     # #    # #            #    # #    # ##  ## ##  ## #   #      #    # #    # #    # #   #     #    # # #       #     # 
 ######  #    # #####  ##### #      #    # # ## # # ## # #   #      ###### #    # #    # ####      #    #   #       #     # 
 #       #####  #            #      #    # #    # #    # #   #      #    # #    # #    # #  #      #    #   #   ### #     # 
 #       #   #  #            #    # #    # #    # #    # #   #      #    # #    # #    # #   #      #  #    #   ###  #   #  
 #       #    # ######        ####   ####  #    # #    # #   #      #    #  ####   ####  #    #      ##   ##### ###   ###   "


echo ""; echo ""
echo "Setting up the environment for pre-commit hook..."
echo ""; echo ""

if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python3 by running 'brew install python3'"
    exit 1
fi

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "pre-commit is not installed. Please install pre-commit by running 'pip3 install pre-commit'"
    exit 1
fi

echo ""; echo ""
echo "Environment setup is done"
echo ""; echo ""
echo "Installing pre-commit hook"
echo ""; echo ""

# Checking whether git directory exists or not
if [[ ! -d ~/.config/git/hooks ]]; then
    mkdir -p ~/.config/git/hooks
fi

#Checking for pre-commit file
FILE=~/.config/git/hooks/pre-commit
flag=0

if [ -f "$FILE" ]; then
    string1="pre-commit run -c ~/.config/git/.pre-commit-config.yaml"
    search=$(grep -F "${string1}" "$FILE")
    if [ -n "$search" ]; then
        echo "pre-commit file already contains the command."
        flag=1
    else
        flag=0
    fi
fi 

if [ "$flag" -eq 0 ]; then
cat << "EOF" >> ~/.config/git/hooks/pre-commit
#!/bin/bash
# Find the root of the Git repository
GIT_ROOT=$(git rev-parse --show-toplevel)

directory_exists="$GIT_ROOT/.git/hooks/pre-commit"
if [ -f "$directory_exists" ]; then
    echo "local pre-commit hooks exists. executing it first"
    bash $directory_exists
fi

pre-commit run -c ~/.config/git/.pre-commit-config.yaml
EOF
fi

#Checking for pre-commit config file
FILE=~/.config/git/.pre-commit-config.yaml
flag=0

if [ -f "$FILE" ]; then
    string1="  - repo: https://github.com/ankitsaini2609/oculus-pre-commit-hook.git"
    search=$(grep -Fx "$string1" "$FILE")
    if [ -n "$search" ]; then
        echo "pre-commit config file already contains the entry."
        flag=1
    else
        flag=0
    fi
fi

if [ "$flag" -eq 0 ]; then
cat << EOF >> ~/.config/git/.pre-commit-config.yaml
repos:
  - repo: https://github.com/ankitsaini2609/oculus-pre-commit-hook.git
    rev: v1.0
    hooks:
      - id: gitleaks
EOF
fi

git config --global core.hooksPath ~/.config/git/hooks/
chmod +x ~/.config/git/hooks/pre-commit
echo "Done!!"