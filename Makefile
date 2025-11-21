# TuxSec Agent - Makefile for RPM building

NAME = tuxsec-agent
VERSION = 2.0.0
RELEASE = 1

TARBALL = $(NAME)-$(VERSION).tar.gz
SPEC_FILE = $(NAME).spec

# Directories
SOURCEDIR = $(shell pwd)
BUILDDIR = $(SOURCEDIR)/build
RPMDIR = $(BUILDDIR)/rpmbuild

.PHONY: help clean tarball srpm rpm install selinux

help:
	@echo "TuxSec Agent Build System"
	@echo ""
	@echo "Available targets:"
	@echo "  tarball  - Create source tarball"
	@echo "  srpm     - Build source RPM"
	@echo "  rpm      - Build binary RPMs"
	@echo "  selinux  - Build SELinux policy module"
	@echo "  install  - Install locally (for development)"
	@echo "  clean    - Clean build artifacts"
	@echo ""

clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(BUILDDIR)
	rm -rf dist
	rm -rf *.egg-info
	rm -f $(TARBALL)
	rm -f agent/selinux/*.mod agent/selinux/*.pp
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Clean complete"

tarball:
	@echo "Creating source tarball..."
	mkdir -p $(BUILDDIR)
	git archive --format=tar.gz --prefix=$(NAME)-$(VERSION)/ HEAD -o $(BUILDDIR)/$(TARBALL)
	@echo "Tarball created: $(BUILDDIR)/$(TARBALL)"

srpm: tarball
	@echo "Building source RPM..."
	mkdir -p $(RPMDIR)/{SOURCES,SPECS,BUILD,RPMS,SRPMS}
	cp $(BUILDDIR)/$(TARBALL) $(RPMDIR)/SOURCES/
	cp $(SPEC_FILE) $(RPMDIR)/SPECS/
	rpmbuild -bs \
		--define "_topdir $(RPMDIR)" \
		$(RPMDIR)/SPECS/$(SPEC_FILE)
	@echo ""
	@echo "Source RPM created:"
	@ls -lh $(RPMDIR)/SRPMS/$(NAME)-$(VERSION)-$(RELEASE)*.src.rpm

rpm: tarball
	@echo "Building binary RPMs..."
	mkdir -p $(RPMDIR)/{SOURCES,SPECS,BUILD,RPMS,SRPMS}
	cp $(BUILDDIR)/$(TARBALL) $(RPMDIR)/SOURCES/
	cp $(SPEC_FILE) $(RPMDIR)/SPECS/
	rpmbuild -ba \
		--define "_topdir $(RPMDIR)" \
		$(RPMDIR)/SPECS/$(SPEC_FILE)
	@echo ""
	@echo "Binary RPMs created:"
	@ls -lh $(RPMDIR)/RPMS/noarch/

selinux:
	@echo "Building SELinux policy module..."
	cd agent/selinux && bash build.sh
	@echo "SELinux policy built: agent/selinux/tuxsec.pp"

install:
	@echo "Installing TuxSec Agent locally..."
	@echo "This is for development/testing only!"
	@echo ""
	python3 setup.py install --user
	@echo ""
	@echo "For production, use: make rpm && sudo dnf install <rpm-file>"

dev-install:
	@echo "Installing in development mode..."
	pip3 install -e .
	@echo ""
	@echo "Development installation complete"
	@echo "Changes to source files will be reflected immediately"

test:
	@echo "Running tests..."
	python3 -m pytest tests/ -v
	@echo "Tests complete"

lint:
	@echo "Running code linters..."
	flake8 agent/ --max-line-length=120
	black --check agent/
	@echo "Linting complete"

format:
	@echo "Formatting code..."
	black agent/
	@echo "Formatting complete"

.PHONY: all
all: clean rpm selinux
	@echo ""
	@echo "================================================"
	@echo "Build complete!"
	@echo "================================================"
	@echo ""
	@echo "RPM packages:"
	@ls -1 $(RPMDIR)/RPMS/noarch/
	@echo ""
	@echo "To install:"
	@echo "  sudo dnf install $(RPMDIR)/RPMS/noarch/tuxsec-agent-*.rpm"
	@echo ""
	@echo "Optional modules:"
	@echo "  sudo dnf install $(RPMDIR)/RPMS/noarch/tuxsec-agent-firewalld-*.rpm"
	@echo "  sudo dnf install $(RPMDIR)/RPMS/noarch/tuxsec-agent-selinux-*.rpm"
	@echo ""
