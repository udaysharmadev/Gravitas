#!/bin/bash
mv ~/.gemini/config ~/.gemini/config.bak
python3 repair_runner.py
rm -rf ~/.gemini/config
mv ~/.gemini/config.bak ~/.gemini/config
