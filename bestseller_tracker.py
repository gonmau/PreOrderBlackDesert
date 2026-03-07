name: Bestseller Tracker

on:
  schedule:
    - cron: '0 9,21 * * *'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  track:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout
      uses: actions/checkout@v4
      with:
        fetch-depth: 0 # 전체 히스토리 가져오기

    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install Dependencies
      run: |
        pip install selenium webdriver-manager requests

    - name: Run Bestseller Tracker
      run: python bestseller_tracker.py

    - name: Commit and Push changes
      env:
        GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      run: |
        git config --local user.email "github-actions[bot]@users.noreply.github.com"
        git config --local user.name "github-actions[bot]"
        
        # 최신 데이터 유지를 위한 pull
        git pull origin main --rebase
        
        git add bestseller_history.json
        git diff --cached --quiet || (git commit -m "Update history [skip ci]" && git push origin main)
