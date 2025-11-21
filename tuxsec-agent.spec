Name:           tuxsec-agent
Version:        0.1.3
Release:        1%{?dist}
Summary:        TuxSec Agent - Secure Linux System Management

License:        MIT
URL:            https://github.com/MrMEEE/tuxsec
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-pip
BuildRequires:  python3-virtualenv
BuildRequires:  systemd-rpm-macros

# For SELinux subpackage
BuildRequires:  selinux-policy-devel

Requires:       python3 >= 3.8
Requires:       systemd
Requires(pre):  shadow-utils
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd

# Require either system packages or venv
Requires:       (tuxsec-agent-venv = %{version}-%{release} or (python3-pyyaml and python3-httpx and python3-aiohttp))

%description
TuxSec Agent provides secure, modular system management for Linux servers.
It uses a two-component architecture that separates privileged operations
from network communication.

The agent consists of:
- tuxsec-rootd: Root daemon exposing modular capabilities via Unix socket
- tuxsec-agent: Unprivileged agent bridging server and root daemon

Supports three connection modes: pull, push, and SSH.

The systeminfo module is included in the base package.

#######################
# Virtual Environment Package
#######################
%package -n tuxsec-agent-venv
Summary:        TuxSec Agent with bundled Python dependencies in virtualenv
Requires:       tuxsec-agent = %{version}-%{release}
Provides:       tuxsec-agent-python-deps = %{version}-%{release}

%description -n tuxsec-agent-venv
Self-contained virtual environment for TuxSec Agent with all Python
dependencies bundled. This package is recommended for systems where
the required Python packages are not available in the distribution
repositories.

The virtual environment is STATIC (bundled at build time) and installed 
to /opt/tuxsec/venv. It includes:
- PyYAML
- httpx
- aiohttp
- All transitive dependencies

No internet connection is required after installation.

#######################
# Firewalld Module
#######################
%package -n tuxsec-agent-firewalld
Summary:        TuxSec Agent firewalld module
Requires:       tuxsec-agent = %{version}-%{release}
Requires:       firewalld

%description -n tuxsec-agent-firewalld
Firewalld management module for TuxSec Agent.

Provides capabilities for:
- Zone management
- Service management
- Port management
- Rich rules
- Configuration queries

#######################
# SELinux Policy
#######################
%package -n tuxsec-agent-selinux
Summary:        SELinux policy module for TuxSec Agent
Requires:       tuxsec-agent = %{version}-%{release}
Requires:       selinux-policy
Requires(post): policycoreutils
Requires(post): selinux-policy-targeted
Requires(postun): policycoreutils

%description -n tuxsec-agent-selinux
SELinux policy module for TuxSec Agent. Provides the necessary security
contexts and rules for the agent to operate correctly under SELinux.

#######################
# Prep
#######################
%prep
%autosetup -n %{name}-%{version}

#######################
# Build
#######################
%build
# Build Python package (no compilation needed for noarch)
%py3_build

# Build virtualenv with dependencies
python3 -m venv %{_builddir}/venv
%{_builddir}/venv/bin/pip install --upgrade pip
%{_builddir}/venv/bin/pip install PyYAML httpx aiohttp

# Build SELinux policy
cd agent/selinux
make -f /usr/share/selinux/devel/Makefile tuxsec.pp
cd ../..

#######################
# Install
#######################
%install
# Install Python package
%py3_install

# Install virtualenv
mkdir -p %{buildroot}/opt/tuxsec
cp -a %{_builddir}/venv %{buildroot}/opt/tuxsec/

# Install systemd service files
install -D -m 0644 agent/systemd/tuxsec-rootd.service %{buildroot}%{_unitdir}/tuxsec-rootd.service
install -D -m 0644 agent/systemd/tuxsec-agent.service %{buildroot}%{_unitdir}/tuxsec-agent.service

# Install configuration example
install -D -m 0640 agent/agent.yaml.example %{buildroot}%{_sysconfdir}/tuxsec/agent.yaml.example

# Install executables
install -D -m 0755 %{buildroot}%{python3_sitelib}/agent/rootd/daemon.py %{buildroot}%{_bindir}/tuxsec-rootd
install -D -m 0755 %{buildroot}%{python3_sitelib}/agent/userspace/agent.py %{buildroot}%{_bindir}/tuxsec-agent
install -D -m 0755 %{buildroot}%{python3_sitelib}/agent/userspace/cli.py %{buildroot}%{_bindir}/tuxsec-cli
install -D -m 0755 %{buildroot}%{python3_sitelib}/agent/userspace/setup.py %{buildroot}%{_bindir}/tuxsec-setup

# Create wrapper scripts for executables that can use either system Python or venv
cat > %{buildroot}%{_bindir}/tuxsec-rootd << 'EOF'
#!/bin/bash
if [ -d /opt/tuxsec/venv ]; then
    exec /opt/tuxsec/venv/bin/python3 -m agent.rootd.daemon "$@"
else
    exec /usr/bin/python3 -m agent.rootd.daemon "$@"
fi
EOF

cat > %{buildroot}%{_bindir}/tuxsec-agent << 'EOF'
#!/bin/bash
if [ -d /opt/tuxsec/venv ]; then
    exec /opt/tuxsec/venv/bin/python3 -m agent.userspace.agent "$@"
else
    exec /usr/bin/python3 -m agent.userspace.agent "$@"
fi
EOF

cat > %{buildroot}%{_bindir}/tuxsec-cli << 'EOF'
#!/bin/bash
if [ -d /opt/tuxsec/venv ]; then
    exec /opt/tuxsec/venv/bin/python3 -m agent.userspace.cli "$@"
else
    exec /usr/bin/python3 -m agent.userspace.cli "$@"
fi
EOF

cat > %{buildroot}%{_bindir}/tuxsec-setup << 'EOF'
#!/bin/bash
if [ -d /opt/tuxsec/venv ]; then
    exec /opt/tuxsec/venv/bin/python3 -m agent.userspace.setup "$@"
else
    exec /usr/bin/python3 -m agent.userspace.setup "$@"
fi
EOF
sys.exit(main())
EOF

chmod 0755 %{buildroot}%{_bindir}/tuxsec-*

# Create directories
install -d -m 0755 %{buildroot}%{_localstatedir}/log/tuxsec
install -d -m 0770 %{buildroot}%{_rundir}/tuxsec
install -d -m 0755 %{buildroot}%{_sharedstatedir}/tuxsec
install -d -m 0750 %{buildroot}%{_sysconfdir}/tuxsec/certs

# Install SELinux policy
install -D -m 0644 agent/selinux/tuxsec.pp %{buildroot}%{_datadir}/selinux/packages/tuxsec.pp

#######################
# Pre-install Scripts
#######################
%pre -n tuxsec-agent
# Create tuxsec user and group
getent group tuxsec >/dev/null || groupadd -r tuxsec
getent passwd tuxsec >/dev/null || \
    useradd -r -g tuxsec -d %{_sharedstatedir}/tuxsec -s /bin/bash \
    -c "TuxSec Agent System User" tuxsec
exit 0

#######################
# Post-install Scripts
#######################
%post -n tuxsec-agent
# Set correct permissions on runtime directory
if [ ! -d %{_rundir}/tuxsec ]; then
    mkdir -p %{_rundir}/tuxsec
fi
chown root:tuxsec %{_rundir}/tuxsec
chmod 0770 %{_rundir}/tuxsec

# Set correct permissions on log directory
chown tuxsec:tuxsec %{_localstatedir}/log/tuxsec
chmod 0755 %{_localstatedir}/log/tuxsec

# Set correct permissions on data directory
chown tuxsec:tuxsec %{_sharedstatedir}/tuxsec
chmod 0755 %{_sharedstatedir}/tuxsec

# Set correct permissions on config directory
chown root:root %{_sysconfdir}/tuxsec
chmod 0755 %{_sysconfdir}/tuxsec
chown root:tuxsec %{_sysconfdir}/tuxsec/certs
chmod 0750 %{_sysconfdir}/tuxsec/certs

# Copy example config if no config exists
if [ ! -f %{_sysconfdir}/tuxsec/agent.yaml ]; then
    cp %{_sysconfdir}/tuxsec/agent.yaml.example %{_sysconfdir}/tuxsec/agent.yaml
    chown root:tuxsec %{_sysconfdir}/tuxsec/agent.yaml
    chmod 0640 %{_sysconfdir}/tuxsec/agent.yaml
fi

# Reload systemd daemon
%systemd_post tuxsec-rootd.service tuxsec-agent.service

echo ""
echo "TuxSec Agent installed successfully!"
echo ""
echo "Next steps:"
echo "  1. Run the setup wizard: sudo tuxsec-setup"
echo "  2. Or manually edit: /etc/tuxsec/agent.yaml"
echo "  3. Start services: systemctl start tuxsec-rootd tuxsec-agent"
echo "  4. Enable on boot: systemctl enable tuxsec-rootd tuxsec-agent"
echo ""

%post -n tuxsec-agent-selinux
# Install SELinux policy
semodule -n -i %{_datadir}/selinux/packages/tuxsec.pp
if /usr/sbin/selinuxenabled ; then
    /usr/sbin/load_policy
    # Relabel files
    restorecon -R %{_bindir}/tuxsec-* || :
    restorecon -R %{_sysconfdir}/tuxsec || :
    restorecon -R %{_localstatedir}/log/tuxsec || :
    restorecon -R %{_rundir}/tuxsec || :
    restorecon -R %{_sharedstatedir}/tuxsec || :
fi

#######################
# Pre-uninstall Scripts
#######################
%preun -n tuxsec-agent
%systemd_preun tuxsec-rootd.service tuxsec-agent.service

%preun -n tuxsec-agent-selinux
if [ $1 -eq 0 ]; then
    semodule -n -r tuxsec || :
    if /usr/sbin/selinuxenabled ; then
        /usr/sbin/load_policy || :
    fi
fi

#######################
# Post-uninstall Scripts
#######################
%postun -n tuxsec-agent
%systemd_postun_with_restart tuxsec-rootd.service tuxsec-agent.service

# Don't remove user or directories on upgrade
if [ $1 -eq 0 ]; then
    # Only on complete removal, not upgrade
    echo "Configuration and log files preserved in /etc/tuxsec and /var/log/tuxsec"
    echo "To completely remove: rm -rf /etc/tuxsec /var/log/tuxsec /var/lib/tuxsec"
fi

%postun -n tuxsec-agent-selinux
if [ $1 -eq 0 ]; then
    semodule -n -r tuxsec || :
    if /usr/sbin/selinuxenabled ; then
        /usr/sbin/load_policy || :
    fi
fi

#######################
# Files
#######################
%files -n tuxsec-agent
%license LICENSE
%doc README.md
%doc agent/ARCHITECTURE.md
%doc agent/MIGRATION.md

# Python package
%{python3_sitelib}/agent/
%{python3_sitelib}/shared/
%{python3_sitelib}/tuxsec_agent-*.egg-info/
%exclude %{python3_sitelib}/agent/rootd/modules/firewalld.py
%exclude %{python3_sitelib}/agent/rootd/modules/__pycache__/firewalld.*

# Executables
%{_bindir}/tuxsec-rootd
%{_bindir}/tuxsec-agent
%{_bindir}/tuxsec-cli
%{_bindir}/tuxsec-setup

# Systemd services
%{_unitdir}/tuxsec-rootd.service
%{_unitdir}/tuxsec-agent.service

# Configuration
%dir %{_sysconfdir}/tuxsec
%dir %{_sysconfdir}/tuxsec/certs
%config(noreplace) %{_sysconfdir}/tuxsec/agent.yaml.example

# Directories
%dir %attr(0755,tuxsec,tuxsec) %{_localstatedir}/log/tuxsec
%dir %attr(0770,root,tuxsec) %{_rundir}/tuxsec
%dir %attr(0755,tuxsec,tuxsec) %{_sharedstatedir}/tuxsec

%files -n tuxsec-agent-venv
/opt/tuxsec/venv/

%files -n tuxsec-agent-firewalld
%{python3_sitelib}/agent/rootd/modules/firewalld.py
%{python3_sitelib}/agent/rootd/modules/__pycache__/firewalld.*

%files -n tuxsec-agent-selinux
%{_datadir}/selinux/packages/tuxsec.pp
%ghost %{_sharedstatedir}/selinux/targeted/active/modules/200/tuxsec

#######################
# Changelog
#######################
%changelog
* Thu Nov 21 2024 MrMEEE <you@example.com> - 2.0.0-1
- Complete agent architecture redesign
- Two-component architecture: root daemon + userspace agent
- Modular plugin system for capabilities
- Support for pull, push, and SSH connection modes
- SELinux policy support
- Interactive setup tool (tuxsec-setup)
- Split packages for base and modules

* Mon Jan 01 2024 MrMEEE <you@example.com> - 1.0.0-1
- Initial RPM release
