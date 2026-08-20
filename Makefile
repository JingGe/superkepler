# ============================================================
# Makefile: Install / Uninstall Claude Code Skills
# ============================================================

SKILL_NAME       = superkepler
SKILL_GENIE_NAME = superkepler-genie
CC_SKILLS_DIR    = $(HOME)/.claude/skills
CC_SKILL_DIR     = $(CC_SKILLS_DIR)/$(SKILL_NAME)
CC_GENIE_DIR     = $(CC_SKILLS_DIR)/$(SKILL_GENIE_NAME)

SKILL_SRC        = SKILL.md
SKILL_GENIE_SRC  = SKILL_GENIE.md
REF_SRC          = references
ASSETS_SRC       = assets
SCRIPTS_SRC      = scripts

.PHONY: all install uninstall reinstall install-claudecode uninstall-claudecode help

all: help

## install: Shorthand to install as a global Claude Code skill
install: install-claudecode

## uninstall: Shorthand to wipe out all global Claude Code skills
uninstall: uninstall-claudecode

## reinstall: Uninstall any existing skills and run a clean global installation
reinstall: uninstall install

## install-claudecode: Install superkepler as a Claude Code skill (Defaults to global)
install-claudecode:
	@echo "Installing $(SKILL_NAME) skill to Claude Code global directory..."
	@mkdir -p $(CC_SKILL_DIR)
	@cp -r $(SKILL_SRC) $(CC_SKILL_DIR)/SKILL.md
	@if [ -d "$(REF_SRC)" ]; then cp -r $(REF_SRC) $(CC_SKILL_DIR)/; fi
	@if [ -d "$(ASSETS_SRC)" ]; then cp -r $(ASSETS_SRC) $(CC_SKILL_DIR)/; fi
	@echo "Installing $(SKILL_GENIE_NAME) skill to Claude Code global directory..."
	@mkdir -p $(CC_GENIE_DIR)
	@cp -r $(SKILL_GENIE_SRC) $(CC_GENIE_DIR)/SKILL.md
	@if [ -d "$(SCRIPTS_SRC)" ]; then cp -r $(SCRIPTS_SRC) $(CC_GENIE_DIR)/; fi
	@uv venv $(CC_GENIE_DIR)/.venv --quiet
	@uv pip install --python $(CC_GENIE_DIR)/.venv/bin/python databricks-sdk --quiet
	@echo "Success! Skills installed:"
	@echo "  /$(SKILL_NAME)       -> $(CC_SKILL_DIR)"
	@echo "  /$(SKILL_GENIE_NAME) -> $(CC_GENIE_DIR)"
	@echo "Restart Claude Code to activate."

## uninstall-claudecode: Wipe out the global Claude Code skill targets
uninstall-claudecode:
	@echo "Removing Claude Code skills..."
	@rm -rf $(CC_SKILL_DIR)
	@rm -rf $(CC_GENIE_DIR)
	@echo "Uninstallation complete."

## help: Show available commands
help:
	@echo "Available commands:"
	@sed -n 's/^##//p' $(MAKEFILE_LIST) | column -t -s ':' |  sed -e 's/^/ /'
