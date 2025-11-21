#!/bin/bash
# Build SELinux policy module

set -e

POLICY_NAME="tuxsec"
POLICY_VERSION="1.0.0"

echo "Building SELinux policy module for TuxSec..."

# Compile the policy
checkmodule -M -m -o ${POLICY_NAME}.mod ${POLICY_NAME}.te

# Create the policy package
semodule_package -o ${POLICY_NAME}.pp -m ${POLICY_NAME}.mod -fc ${POLICY_NAME}.fc

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
