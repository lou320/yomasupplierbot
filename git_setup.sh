#!/bin/bash

# ==================================================================
# Git Setup Script - Initialize repository for deployment
# ==================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}   Git Repository Setup${NC}"
echo -e "${BLUE}============================================================${NC}\n"

# Check if already a git repository
if [ -d .git ]; then
    echo -e "${YELLOW}Git repository already initialized.${NC}\n"
else
    echo -e "${GREEN}Initializing git repository...${NC}"
    git init
fi

# Check if files are tracked
echo -e "\n${BLUE}Files that will be committed:${NC}"
git add -n .

# Add all files (respecting .gitignore)
echo -e "\n${GREEN}Adding files to git...${NC}"
git add .

# Show status
echo -e "\n${BLUE}Git status:${NC}"
git status

echo -e "\n${YELLOW}========================================${NC}"
echo -e "${YELLOW}IMPORTANT: Files NOT included in git:${NC}"
echo -e "${YELLOW}========================================${NC}"
echo -e "✗ .env (contains secrets)"
echo -e "✗ google-credentials.json (contains API keys)"
echo -e "✗ db.sqlite3 (database)"
echo -e "✗ venv/ (virtual environment)"
echo -e "✗ __pycache__/ (compiled Python)"
echo -e "✗ *.pyc (compiled Python)"
echo -e "✗ logs/ (log files)"
echo -e "✗ media/ (uploaded files)"
echo -e "✗ staticfiles/ (collected static)"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Next steps:${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "1. Review changes: ${BLUE}git status${NC}"
echo -e "2. Make first commit: ${BLUE}git commit -m \"Initial commit\"${NC}"
echo -e "3. Add remote: ${BLUE}git remote add origin <your-repo-url>${NC}"
echo -e "4. Push to remote: ${BLUE}git push -u origin main${NC}"

echo -e "\n${YELLOW}On your VPS (after pushing):${NC}"
echo -e "${BLUE}git clone <your-repo-url>${NC}"
echo -e "${BLUE}cd yomasupplierbot${NC}"
echo -e "${BLUE}# Upload .env and google-credentials.json manually${NC}"
echo -e "${BLUE}./deploy.sh${NC}\n"
