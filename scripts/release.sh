pyi-makespec --onefile --name anime_rpc --optimize 2 --additional-hooks-dir=. launcher.py
git tag "v$(python -c 'import anime_rpc; print(anime_rpc.__version__)')"