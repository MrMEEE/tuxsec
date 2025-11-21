#!/bin/bash
# Build SELinux policy module

set -e

POLICY_NAME="tuxsec"
POLICY_VERSION="1.0.0"

echo "Building SELinux policy module for TuxSec..."

# Make using the standard make approach for SELinux modules
if [ -f "/usr/share/selinux/devel/Makefile" ]; then
    # Use the SELinux development Makefile (preferred method)
    make -f /usr/share/selinux/devel/Makefile ${POLICY_NAME}.pp
else
    # Fallback to manual compilation
    checkmodule -M -m -o ${POLICY_NAME}.mod ${POLICY_NAME}.te
    semodule_package -o ${POLICY_NAME}.pp -m ${POLICY_NAME}.mod
    if [ -f ${POLICY_NAME}.fc ]; then
        semodule_package -o ${POLICY_NAME}.pp -m ${POLICY_NAME}.mod -fc ${POLICY_NAME}.fc
    fi
fi

echo "SELinux policy module built successfully: ${POLICY_NAME}.pp"
echo ""
echo "To install:"
echo "  semodule -i ${POLICY_NAME}.pp"
echo ""
echo "To verify installation:"
echo "  semodule -l | grep ${POLICY_NAME}"
echo ""
echo "To remove:"
echo "  semodule -r ${POLICY_NAME}"
