How to use it in VS Code:
1) Unzip into your projects folder — you'll get project-effort-estimator/
2) Open that folder in VS Code
3) In the terminal: 
→ python -m venv venv 
→ venv\Scripts\activate 
→ pip install -r requirements.txt
4) Run it: python main.py --input data/sample_client_requirements.csv --client "Contoso Retail" --output output/Contoso_Proposal.docx
           python main.py --input data/enterprise_requirements_dataset.csv --client "Contoso Retail" --output output/Contoso_Proposal.docx
enterprise_requirements_dataset.csv
5) pytest tests/ -v to run the 16 unit tests (all passing)
→ to check test cases passed "python -m pytest tests/ -v"
6) git init, commit, push to a new GitHub repo — .gitignore already keeps venv/, generated docs, and logs out of the repo

git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/HarishGinjupalli/Project-Effort-Estimator-Proposal-Automation-Tool-python.git
git push -u origin main --force

Check your current remote:
git remote -v
You'll probably see something like:
origin  https://github.com/HarishGinjupalli/python-projects-project-effort-estimator.git (fetch)
origin  https://github.com/HarishGinjupalli/python-projects-project-effort-estimator.git (push)

Step 2: Change the remote URL
Instead of adding a new origin, update the existing one:
git remote set-url origin https://github.com/HarishGinjupalli/Project-Effort-Estimator-Proposal-Automation-Tool-python.git

Verify:
git remote -v
It should now show the new URL.

Step 3: Push again
git push -u origin main --force