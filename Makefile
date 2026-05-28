# ============================================================
# Makefile: Install / Uninstall Claude Code Skills
# ============================================================

# Variables
SKILL_NAME = superkepler
CC_SKILL_DIR = $(HOME)/.claude/skills/$(SKILL_NAME)

SKILL_SRC = SKILL.md
REF_SRC = references
ASSETS_SRC = assets

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
	@cp -r $(SKILL_SRC) $(CC_SKILL_DIR)/
	@if [ -d "$(REF_SRC)" ]; then cp -r $(REF_SRC) $(CC_SKILL_DIR)/; fi
	@if [ -d "$(ASSETS_SRC)" ]; then cp -r $(ASSETS_SRC) $(CC_SKILL_DIR)/; fi
	@echo "Success! Global Claude Code skill installed at: $(CC_SKILL_DIR)"
	@echo "Restart Claude Code or type '/' in your TUI session to use /$(SKILL_NAME)"

## uninstall-claudecode: Wipe out the global Claude Code skill targets
uninstall-claudecode:
	@echo "Removing Claude Code skills..."
	@rm -rf $(CC_SKILL_DIR)
	@echo "Uninstallation complete."

## help: Show available commands
help:
	@echo "Available commands:"
	@sed -n 's/^##//p' $(MAKEFILE_LIST) | column -t -s ':' |  sed -e 's/^/ /'