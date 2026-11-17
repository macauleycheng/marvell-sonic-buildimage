#!/bin/bash
#
# clean_submodules.sh
#
# Remove submodules that are not needed to build the Marvell Prestera
# ECS5550-30X / ECS5550-54X (arm64) image, and stop git from fetching them
# again on `git submodule update --init` (also used by `make init`).
#
# Usage: scripts/clean_submodules.sh [options]
#   -n, --dry-run      Show what would be removed, change nothing
#   -y, --yes          Do not ask for confirmation
#   -a, --aggressive   Also remove rarely used optional submodules (TIER2)
#   -p, --purge        Also delete .git/modules/<name> (frees disk space,
#                      re-clone needed if you restore the submodule later)
#   -f, --force        Remove even if the submodule has local changes
#   -r, --restore      Re-enable every submodule that this script disabled
#   -h, --help         Show this help
#
# What it does for each removed submodule:
#   1. git submodule deinit -f <path>      (empties the working tree)
#   2. git config submodule.<name>.active false
#      git config submodule.<name>.update none
#      (so `git submodule update --init [--recursive]` skips it)
#   3. with --purge: rm -rf .git/modules/<name>
#
# The superproject tree and gitlinks are not modified, so `git status`
# stays clean and the change is fully reversible with --restore.

set -u

# Not needed for any ECS5550 (arm64, marvell-prestera) build.
TIER1=(
    platform/barefoot/sonic-platform-modules-arista
    platform/broadcom/saibcm-modules-dnx
    platform/broadcom/sonic-platform-modules-arista
    platform/broadcom/sonic-platform-modules-nokia
    platform/marvell-teralynx/mrvl-teralynx
    platform/marvell-teralynx/sonic-platform-marvell-teralynx
    platform/mellanox/hw-management/hw-mgmt
    platform/p4/SAI-P4-BM
    platform/p4/p4-hlir/p4-hlir
    platform/p4/p4-hlir/p4-hlir-v1.1
    platform/p4/p4c-bm/p4c-bm
    platform/vpp
    src/ptf
    src/ptf-py3
    src/scapy
    src/sonic-p4rt/sonic-pins
    src/sonic-platform-pde
)

# Optional features, off or unused in a plain ECS5550 image. Removing them
# breaks the build if you enable the matching INCLUDE_xxx / docker.
TIER2=(
    src/sonic-bmp
    src/sonic-dash-ha
    src/sonic-dash-api
    src/linkmgrd
    src/sonic-restapi
    src/sonic-gnmi
    src/sonic-sysmgr/gnoi
)

DRY_RUN=0
YES=0
AGGRESSIVE=0
PURGE=0
FORCE=0
RESTORE=0

usage()
{
    sed -n '3,28p' "$0" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
    case "$1" in
        -n|--dry-run)    DRY_RUN=1 ;;
        -y|--yes)        YES=1 ;;
        -a|--aggressive) AGGRESSIVE=1 ;;
        -p|--purge)      PURGE=1 ;;
        -f|--force)      FORCE=1 ;;
        -r|--restore)    RESTORE=1 ;;
        -h|--help)       usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
    esac
    shift
done

TOP=$(git rev-parse --show-toplevel 2>/dev/null) || {
    echo "Not inside a git repository" >&2
    exit 1
}
cd "$TOP" || exit 1

if [ ! -f .gitmodules ]; then
    echo ".gitmodules not found in $TOP" >&2
    exit 1
fi

run()
{
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "  [dry-run] $*"
    else
        "$@"
    fi
}

# Map submodule path -> submodule name (they can differ).
sm_name()
{
    git config -f .gitmodules --get-regexp '^submodule\..*\.path$' |
        awk -v p="$1" '$2 == p { sub(/^submodule\./, "", $1); sub(/\.path$/, "", $1); print $1 }'
}

TARGETS=("${TIER1[@]}")
if [ "$AGGRESSIVE" -eq 1 ]; then
    TARGETS+=("${TIER2[@]}")
fi

if [ "$RESTORE" -eq 1 ]; then
    for path in "${TIER1[@]}" "${TIER2[@]}"; do
        name=$(sm_name "$path")
        [ -n "$name" ] || continue
        if [ "$(git config --get "submodule.$name.update")" = "none" ]; then
            echo "Restoring $path"
            run git config --unset "submodule.$name.update"
            run git config --unset "submodule.$name.active"
        fi
    done
    echo "Done. Run 'git submodule update --init <path>' to fetch the ones you need."
    exit 0
fi

# Build the work list and check for local changes.
WORK=()
for path in "${TARGETS[@]}"; do
    name=$(sm_name "$path")
    if [ -z "$name" ]; then
        echo "skip  $path (not in .gitmodules)"
        continue
    fi
    if [ -e "$path/.git" ] && [ "$FORCE" -eq 0 ]; then
        if [ -n "$(git -C "$path" status --porcelain 2>/dev/null)" ]; then
            echo "skip  $path (has local changes, use --force)"
            continue
        fi
    fi
    WORK+=("$path|$name")
done

if [ ${#WORK[@]} -eq 0 ]; then
    echo "Nothing to do."
    exit 0
fi

echo "Submodules to remove:"
for item in "${WORK[@]}"; do
    echo "  ${item%%|*}"
done
[ "$PURGE" -eq 1 ] && echo "(.git/modules data will also be deleted)"

if [ "$DRY_RUN" -eq 0 ] && [ "$YES" -eq 0 ]; then
    read -r -p "Continue? [y/N] " ans
    case "$ans" in
        y|Y|yes|YES) ;;
        *) echo "Aborted."; exit 1 ;;
    esac
fi

for item in "${WORK[@]}"; do
    path=${item%%|*}
    name=${item##*|}
    echo "Removing $path"
    run git submodule deinit -f -- "$path" >/dev/null 2>&1 || true
    run git config "submodule.$name.active" false
    run git config "submodule.$name.update" none
    if [ "$PURGE" -eq 1 ]; then
        gitdir=$(git rev-parse --git-common-dir)/modules/$name
        if [ -d "$gitdir" ]; then
            run rm -rf -- "$gitdir"
        fi
    fi
done

echo "Done."
if [ "$DRY_RUN" -eq 0 ]; then
    du -sh "$(git rev-parse --git-common-dir)/modules" 2>/dev/null
fi
